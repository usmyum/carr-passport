from app.modules.makes.models import Make
from app.shared.repository import BaseRepository


class MakeRepository(BaseRepository[Make]):
    model = Make

    async def get_by_name(self, name: str) -> Make | None:
        return await self.find_one(Make.name == name)

    async def get_by_slug(self, slug: str) -> Make | None:
        return await self.find_one(Make.slug == slug)

    async def get_all(self) -> list[Make]:
        return await self.list(order_by=Make.name)
