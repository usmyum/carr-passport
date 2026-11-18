from datetime import date

from sqlalchemy import and_, or_, select

from app.modules.mileage_logs.models import MileageLog
from app.shared.pagination import PageParams
from app.shared.repository import BaseRepository


class MileageLogRepository(BaseRepository[MileageLog]):
    model = MileageLog

    async def paginate_for_vehicle(
        self,
        vehicle_id: int,
        params: PageParams,
        visible_until: date | None = None,
    ) -> tuple[list[MileageLog], int]:

        filters = [MileageLog.vehicle_id == vehicle_id]

        if visible_until is not None:
            filters.append(MileageLog.recorded_on <= visible_until)

        items = await self.list(
            *filters,
            order_by=(MileageLog.recorded_on.desc(), MileageLog.odometer.desc()),
            limit=params.limit,
            offset=params.offset,
        )

        total = await self.count(*filters)

        return items, total

    async def list_for_vehicle(self, vehicle_id: int) -> list[MileageLog]:
        """Every reading, oldest first — for the public history."""

        return await self.list(
            MileageLog.vehicle_id == vehicle_id,
            order_by=(MileageLog.recorded_on, MileageLog.odometer),
        )

    async def get_latest(self, vehicle_id: int) -> MileageLog | None:

        result = await self.db.execute(
            select(MileageLog)
            .where(MileageLog.vehicle_id == vehicle_id)
            .order_by(MileageLog.recorded_on.desc(), MileageLog.odometer.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_for_service_record(
        self,
        service_record_id: int,
    ) -> MileageLog | None:

        return await self.find_one(
            MileageLog.service_record_id == service_record_id
        )

    async def find_contradicting(
        self,
        vehicle_id: int,
        recorded_on: date,
        odometer: int,
        exclude_id: int | None = None,
    ) -> MileageLog | None:
        """A reading that makes this one impossible: a higher one on an
        earlier day, or a lower one on a later day."""

        query = (
            select(MileageLog)
            .where(
                MileageLog.vehicle_id == vehicle_id,
                or_(
                    and_(
                        MileageLog.recorded_on < recorded_on,
                        MileageLog.odometer > odometer,
                    ),
                    and_(
                        MileageLog.recorded_on > recorded_on,
                        MileageLog.odometer < odometer,
                    ),
                ),
            )
            .order_by(MileageLog.recorded_on)
            .limit(1)
        )

        if exclude_id is not None:
            query = query.where(MileageLog.id != exclude_id)

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
