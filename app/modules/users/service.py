from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import LoginRequest, RegisterRequest
from app.shared.exceptions import ConflictException, UnauthorizedException
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

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

        return user, *self._issue_tokens(user)

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

        return user, *self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> str:

        payload = decode_token(refresh_token, expected_type="refresh")

        user = await self.repository.get_by_id(int(payload["sub"]))

        if not user:
            raise UnauthorizedException("User not found")

        return create_access_token(user.id)

    def _issue_tokens(self, user: User) -> tuple[str, str]:
        return (
            create_access_token(user.id),
            create_refresh_token(user.id),
        )
