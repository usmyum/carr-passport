from datetime import datetime

from sqlalchemy import update

from app.modules.users.models import OneTimeToken, RefreshToken, User
from app.shared.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one(User.email == email)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def revoke_family(self, family_id: str, now: datetime) -> None:
        await self._revoke(RefreshToken.family_id == family_id, now)

    async def revoke_all_for_user(self, user_id: int, now: datetime) -> None:
        await self._revoke(RefreshToken.user_id == user_id, now)

    async def _revoke(self, condition, now: datetime) -> None:

        await self.db.execute(
            update(RefreshToken)
            .where(condition, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

        await self.db.commit()


class OneTimeTokenRepository(BaseRepository[OneTimeToken]):
    model = OneTimeToken

    async def get_by_hash(self, token_hash: str) -> OneTimeToken | None:
        return await self.find_one(OneTimeToken.token_hash == token_hash)

    async def invalidate_unused(
        self,
        user_id: int,
        purpose: str,
        now: datetime,
    ) -> None:
        """Retire older links of this kind — only the newest email works."""

        await self.db.execute(
            update(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.purpose == purpose,
                OneTimeToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
