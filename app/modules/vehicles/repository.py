from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.modules.vehicle_models.models import VehicleModel
from app.modules.vehicles.models import Vehicle
from app.shared.pagination import PageParams
from app.shared.repository import BaseRepository


class VehicleRepository(BaseRepository[Vehicle]):
    model = Vehicle

    async def get_by_vin(self, vin: str) -> Vehicle | None:
        return await self.find_one(Vehicle.vin == vin)

    async def get_by_registration_number(
            self,
            registration_number: str,
    ) -> Vehicle | None:
        return await self.find_one(
            Vehicle.registration_number == registration_number
        )

    async def get_with_model(
            self,
            vehicle_id: int,
    ) -> Vehicle | None:
        """Vehicle plus its model and make in one round trip.

        Relationships are always eager-loaded here: under an async session a
        lazy load on attribute access raises instead of quietly querying.
        """

        result = await self.db.execute(
            select(Vehicle)
            .options(
                joinedload(Vehicle.model)
                .joinedload(VehicleModel.make)
            )
            .where(Vehicle.id == vehicle_id)
        )

        return result.scalar_one_or_none()

    async def paginate(
            self,
            params: PageParams,
            *filters: ColumnElement[bool],
    ) -> tuple[list[Vehicle], int]:
        items = await self.list(
            *filters,
            order_by=Vehicle.id.desc(),
            limit=params.limit,
            offset=params.offset,
        )

        total = await self.count(*filters)

        return items, total
