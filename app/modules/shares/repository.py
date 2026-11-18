from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.receipts.models import Receipt
from app.modules.service_records.models import ServiceRecord
from app.modules.shares.models import VehicleShare
from app.shared.repository import BaseRepository


class ShareRepository(BaseRepository[VehicleShare]):
    model = VehicleShare

    async def get_by_token(self, token: str) -> VehicleShare | None:
        return await self.find_one(VehicleShare.token == token)

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> list[VehicleShare]:

        return await self.list(
            VehicleShare.vehicle_id == vehicle_id,
            VehicleShare.created_by_id == user_id,
            order_by=VehicleShare.created_at.desc(),
        )


class HistoryRepository:
    """Read-only: the service records for the public history, with garage
    names and receipt counts loaded in the same query."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def records_with_receipt_counts(
        self,
        vehicle_id: int,
    ) -> list[tuple[ServiceRecord, int]]:

        receipt_counts = (
            select(Receipt.service_record_id, func.count().label("count"))
            .group_by(Receipt.service_record_id)
            .subquery()
        )

        result = await self.db.execute(
            select(ServiceRecord, func.coalesce(receipt_counts.c.count, 0))
            .outerjoin(
                receipt_counts,
                receipt_counts.c.service_record_id == ServiceRecord.id,
            )
            .options(joinedload(ServiceRecord.garage))
            .where(ServiceRecord.vehicle_id == vehicle_id)
            .order_by(ServiceRecord.service_date.desc(), ServiceRecord.id.desc())
        )

        return [tuple(row) for row in result.all()]
