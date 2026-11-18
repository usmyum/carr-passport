from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.modules.ownerships.models import VehicleOwnership
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

    async def paginate_for_user(
        self,
        user_id: int,
        params: PageParams,
        include_past: bool = False,
    ) -> tuple[list[tuple[Vehicle, datetime | None]], int]:
        """The user's vehicles, each paired with when their ownership ended.

        `ended_at` is None for vehicles they own now. A user may have owned
        the same car more than once, so only their latest period counts.
        """

        latest = (
            select(
                VehicleOwnership.vehicle_id,
                VehicleOwnership.ended_at,
            )
            .where(VehicleOwnership.user_id == user_id)
            # DISTINCT ON keeps the first row per vehicle; DESC puts the
            # NULL (still-owned) period first in Postgres.
            .distinct(VehicleOwnership.vehicle_id)
            .order_by(
                VehicleOwnership.vehicle_id,
                VehicleOwnership.ended_at.desc(),
            )
            .subquery()
        )

        query = (
            select(Vehicle, latest.c.ended_at)
            .join(latest, latest.c.vehicle_id == Vehicle.id)
        )

        if not include_past:
            query = query.where(latest.c.ended_at.is_(None))

        total = (
            await self.db.execute(
                select(func.count()).select_from(query.subquery())
            )
        ).scalar_one()

        result = await self.db.execute(
            query
            .order_by(Vehicle.id.desc())
            .limit(params.limit)
            .offset(params.offset)
        )

        return [tuple(row) for row in result.all()], total
