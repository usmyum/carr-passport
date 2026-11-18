import logging
import uuid
from collections.abc import Callable
from datetime import timedelta

from app.core.config import settings
from app.db.base import utc_now
from app.modules.users import emails
from app.modules.users.models import (
    OneTimeToken,
    OneTimeTokenPurpose,
    RefreshToken,
    User,
)
from app.modules.users.repository import (
    OneTimeTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.modules.users.schemas import (
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.shared.email import Email, EmailSender
from app.shared.exceptions import (
    ConflictException,
    UnauthorizedException,
    ValidationException,
)
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_one_time_token,
    hash_one_time_token,
    hash_password,
    refresh_token_lifetime,
    verify_password,
)

logger = logging.getLogger(__name__)


class UserService:

    def __init__(
        self,
        repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        one_time_token_repository: OneTimeTokenRepository,
        email_sender: EmailSender,
    ):
        self.repository = repository
        self.refresh_token_repository = refresh_token_repository
        self.one_time_token_repository = one_time_token_repository
        self.email_sender = email_sender

    # ---- sign up / log in ----------------------------------------------------

    async def register(
        self,
        data: RegisterRequest,
    ) -> tuple[User, str, str]:

        email = data.email.strip().lower()

        if await self.repository.get_by_email(email):
            raise ConflictException("Email is already registered")

        user = User(
            email=email,
            password_hash=hash_password(data.password),
        )

        user = await self.repository.create(user)

        await self._send_verification_email(user)

        return user, *await self._issue_tokens(user)

    async def login(
        self,
        data: LoginRequest,
    ) -> tuple[User, str, str]:

        email = data.email.strip().lower()

        user = await self.repository.get_by_email(email)

        # Same error whether the email is unknown or the password is wrong —
        # the response must never confirm which one it was.
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedException("Invalid credentials")

        return user, *await self._issue_tokens(user)

    # ---- refresh tokens ------------------------------------------------------

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Swap a refresh token for a new access + refresh pair.

        The presented token is used up. If it was *already* used, someone
        has a copy — the whole login (token family) is revoked.
        """

        stored = await self._get_stored_refresh_token(refresh_token)

        now = utc_now()

        if stored.revoked_at is not None:
            await self.refresh_token_repository.revoke_family(
                stored.family_id,
                now,
            )
            logger.warning(
                "Refresh token reuse detected; revoked family",
                extra={"user_id": stored.user_id, "family_id": stored.family_id},
            )
            raise UnauthorizedException(
                "This session is no longer valid. Log in again."
            )

        user = await self.repository.get_by_id(stored.user_id)

        if not user:
            raise UnauthorizedException("User not found")

        stored.revoked_at = now

        # Committed together with the new token in `_issue_tokens`.
        return await self._issue_tokens(user, family_id=stored.family_id)

    async def logout(self, refresh_token: str) -> None:
        """End this login: every token rotated from it stops working.

        Access tokens already issued stay valid until they expire (minutes)
        — they're never looked up, which is what keeps them cheap.
        """

        stored = await self._get_stored_refresh_token(refresh_token)

        await self.refresh_token_repository.revoke_family(
            stored.family_id,
            utc_now(),
        )

    # ---- email verification --------------------------------------------------

    async def verify_email(self, token: str) -> User:

        one_time = await self._use_one_time_token(
            token,
            OneTimeTokenPurpose.VERIFY_EMAIL,
        )

        user = await self._get_user(one_time.user_id)

        if user.email_verified_at is None:
            user.email_verified_at = utc_now()

        return await self.repository.save(user)

    async def resend_verification(self, user: User) -> None:

        if user.is_email_verified:
            raise ConflictException("Your email is already verified")

        await self._send_verification_email(user)

    # ---- password reset ------------------------------------------------------

    async def forgot_password(self, email: str) -> None:
        """Always succeeds from the caller's point of view, so the endpoint
        can't be used to find out which emails have accounts."""

        user = await self.repository.get_by_email(email.strip().lower())

        if not user:
            return

        await self._send_one_time_link(
            user,
            OneTimeTokenPurpose.RESET_PASSWORD,
            timedelta(minutes=settings.password_reset_expire_minutes),
            emails.password_reset_email,
        )

    async def reset_password(self, data: ResetPasswordRequest) -> None:

        one_time = await self._use_one_time_token(
            data.token,
            OneTimeTokenPurpose.RESET_PASSWORD,
        )

        user = await self._get_user(one_time.user_id)

        now = utc_now()

        user.password_hash = hash_password(data.new_password)

        # Opening the emailed link proves they own the address.
        if user.email_verified_at is None:
            user.email_verified_at = now

        # Log out every session — if the password was stolen, the attacker's
        # refresh tokens die here. This commits the session, so the new
        # password, the used link and the revocations land together.
        await self.refresh_token_repository.revoke_all_for_user(user.id, now)

    # ---- helpers -------------------------------------------------------------

    async def _issue_tokens(
        self,
        user: User,
        family_id: str | None = None,
    ) -> tuple[str, str]:
        """A new access + refresh pair. No `family_id` = a brand-new login."""

        token_id = str(uuid.uuid4())
        family_id = family_id or str(uuid.uuid4())

        await self.refresh_token_repository.create(
            RefreshToken(
                id=token_id,
                user_id=user.id,
                family_id=family_id,
                expires_at=utc_now() + refresh_token_lifetime(),
            )
        )

        return (
            create_access_token(user.id),
            create_refresh_token(user.id, token_id, family_id),
        )

    async def _get_stored_refresh_token(self, refresh_token: str) -> RefreshToken:

        payload = decode_token(refresh_token, expected_type="refresh")

        # Tokens issued before rotation existed have no `jti` — they just
        # stop working, and the user logs in again.
        token_id = payload.get("jti")

        stored = (
            await self.refresh_token_repository.get_by_id(token_id)
            if token_id
            else None
        )

        if not stored:
            raise UnauthorizedException("Token is not valid")

        return stored

    async def _send_verification_email(self, user: User) -> None:

        await self._send_one_time_link(
            user,
            OneTimeTokenPurpose.VERIFY_EMAIL,
            timedelta(hours=settings.email_verification_expire_hours),
            emails.verification_email,
        )

    async def _send_one_time_link(
        self,
        user: User,
        purpose: OneTimeTokenPurpose,
        lifetime: timedelta,
        build_email: Callable[[str, str], Email],
    ) -> None:

        now = utc_now()
        token = generate_one_time_token()

        await self.one_time_token_repository.invalidate_unused(
            user.id,
            purpose,
            now,
        )

        await self.one_time_token_repository.create(
            OneTimeToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=hash_one_time_token(token),
                expires_at=now + lifetime,
            )
        )

        # A mail outage shouldn't fail sign-up: the account exists either
        # way, and the user can ask for the email again.
        try:
            await self.email_sender.send(build_email(user.email, token))
        except Exception:
            logger.exception("Could not send %s email", purpose)

    async def _use_one_time_token(
        self,
        token: str,
        purpose: OneTimeTokenPurpose,
    ) -> OneTimeToken:
        """Mark a link's token as used. The caller's next save commits it."""

        one_time = await self.one_time_token_repository.get_by_hash(
            hash_one_time_token(token)
        )

        # One message for every failure: unknown, wrong kind, used, expired.
        if (
            not one_time
            or one_time.purpose != purpose
            or one_time.used_at is not None
            or one_time.expires_at <= utc_now()
        ):
            raise ValidationException("This link is invalid or has expired")

        one_time.used_at = utc_now()

        return one_time

    async def _get_user(self, user_id: int) -> User:

        user = await self.repository.get_by_id(user_id)

        if not user:
            raise ValidationException("This link is invalid or has expired")

        return user
