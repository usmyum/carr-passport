from app.modules.vehicle_models.models import VehicleModel
from app.shared.repository import BaseRepository


class VehicleModelRepository(BaseRepository[VehicleModel]):
    model = VehicleModel

    async def get_by_name(
            self,
            make_id: int,
            name: str,
    ) -> VehicleModel | None:
        return await self.find_one(
            VehicleModel.make_id == make_id,
            VehicleModel.name == name,
        )

    async def get_all(
            self,
            make_id: int | None = None,
    ) -> list[VehicleModel]:
        filters = (
            [VehicleModel.make_id == make_id]
            if make_id is not None
            else []
        )

        return await self.list(
            *filters,
            order_by=VehicleModel.name,
        )
