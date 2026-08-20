from app.modules.garages.models import Garage
from app.shared.repository import BaseRepository


class GarageRepository(BaseRepository[Garage]):
    model = Garage

    async def get_by_name(self, name: str) -> Garage | None:
        return await self.find_one(Garage.name == name)

    async def get_all(self) -> list[Garage]:
        return await self.list(order_by=Garage.name)
