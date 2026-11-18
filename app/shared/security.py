"""Password hashing and JWT encoding.

Deliberately model-free: this module knows nothing about `User`, so it can be
imported by anything. The `current_user` dependency that *does* know about
users lives in the auth module.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.shared.exceptions import UnauthorizedException

# bcrypt silently ignores everything past 72 bytes, so a 200-character
# password would authenticate against its own first 72 bytes. Reject instead.
BCRYPT_MAX_BYTES = 72

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"Password must be at most {BCRYPT_MAX_BYTES} bytes"
        )

    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(
    password: str,
    password_hash: str,
) -> bool:

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > BCRYPT_MAX_BYTES:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8"),
        )
    except ValueError:
        # Malformed hash in the database — treat as a failed login.
        return False


def _create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:

    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:

    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes
        ),
        extra_claims=extra_claims,
    )


def create_refresh_token(
    subject: str | int,
    token_id: str,
    family_id: str,
) -> str:
    """`jti` names this exact token, so it can be used once and then
    revoked; `fam` ties together every token rotated from the same login."""

    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=refresh_token_lifetime(),
        extra_claims={"jti": token_id, "fam": family_id},
    )


def refresh_token_lifetime() -> timedelta:
    return timedelta(days=settings.refresh_token_expire_days)


def generate_one_time_token() -> str:
    """A random token for emailed links (verify email, reset password)."""

    return secrets.token_urlsafe(32)


def hash_one_time_token(token: str) -> str:
    """Only this hash is stored, never the token itself — like a password,
    a leaked database row can't be turned back into a working link.

    SHA-256 rather than bcrypt: the token is 256 random bits, so there's
    nothing to brute-force and a fast hash is enough.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(
    token: str,
    expected_type: TokenType,
) -> dict[str, Any]:

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired") from None
    except jwt.PyJWTError:
        raise UnauthorizedException("Token is not valid") from None

    if payload.get("type") != expected_type:
        # Stops a refresh token being replayed as an access token.
        raise UnauthorizedException("Wrong token type")

    if not payload.get("sub"):
        raise UnauthorizedException("Token is missing a subject")

    return payload
