"""`current_user`, owned by this module per CLAUDE.md's auth convention.

Other modules (`vehicles`, `service_records`, `receipts`) import `CurrentUser`
from here rather than each parsing the bearer token themselves.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.exceptions import UnauthorizedException
from app.shared.security import decode_token

# FastAPI's HTTPBearer defaults to raising a bare 403 when the header is
# missing, bypassing our error shape entirely. auto_error=False here means a
# missing header goes through the same UnauthorizedException as a bad one.
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedException("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type="access")

    user = await UserRepository(db).get_by_id(int(payload["sub"]))

    if not user:
        raise UnauthorizedException("User not found")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
