from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.documents.models import VehicleDocument
from app.modules.ownerships.models import VehicleOwnership
from app.modules.reminders.models import Reminder
from app.modules.service_records.models import ServiceRecord
from app.modules.vehicle_models.models import VehicleModel
from app.modules.vehicles.models import Vehicle


class DashboardRepository:
    """Read-only queries across several modules' tables.

    Not a `BaseRepository`: the dashboard owns no table of its own. Each
    query is batched over all the user's vehicles at once, so the page
    costs the same handful of queries however many cars they have.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def current_vehicles(self, user_id: int) -> list[Vehicle]:

        result = await self.db.execute(
            select(Vehicle)
            .join(VehicleOwnership, VehicleOwnership.vehicle_id == Vehicle.id)
            .where(
                VehicleOwnership.user_id == user_id,
                VehicleOwnership.ended_at.is_(None),
            )
            .options(joinedload(Vehicle.model).joinedload(VehicleModel.make))
            .order_by(Vehicle.id.desc())
        )

        return list(result.scalars().all())

    async def spend_by_vehicle(
        self,
        vehicle_ids: list[int],
        user_id: int,
    ) -> dict[int, Decimal]:
        """What the user has spent: costs on records they added."""

        result = await self.db.execute(
            select(ServiceRecord.vehicle_id, func.sum(ServiceRecord.cost))
            .where(
                ServiceRecord.vehicle_id.in_(vehicle_ids),
                ServiceRecord.created_by_id == user_id,
            )
            .group_by(ServiceRecord.vehicle_id)
        )

        return {vehicle_id: total or Decimal(0) for vehicle_id, total in result.all()}

    async def last_service_by_vehicle(
        self,
        vehicle_ids: list[int],
    ) -> dict[int, ServiceRecord]:

        result = await self.db.execute(
            select(ServiceRecord)
            .where(ServiceRecord.vehicle_id.in_(vehicle_ids))
            .distinct(ServiceRecord.vehicle_id)
            .order_by(
                ServiceRecord.vehicle_id,
                ServiceRecord.service_date.desc(),
                ServiceRecord.id.desc(),
            )
        )

        return {record.vehicle_id: record for record in result.scalars().all()}

    async def open_reminders(
        self,
        vehicle_ids: list[int],
        user_id: int,
    ) -> list[Reminder]:

        result = await self.db.execute(
            select(Reminder).where(
                Reminder.vehicle_id.in_(vehicle_ids),
                Reminder.created_by_id == user_id,
                Reminder.completed_at.is_(None),
            )
        )

        return list(result.scalars().all())

    async def expiring_documents(
        self,
        vehicle_ids: list[int],
        user_id: int,
    ) -> list[VehicleDocument]:

        result = await self.db.execute(
            select(VehicleDocument).where(
                VehicleDocument.vehicle_id.in_(vehicle_ids),
                VehicleDocument.created_by_id == user_id,
                VehicleDocument.expires_on.is_not(None),
            )
        )

        return list(result.scalars().all())
