from datetime import date

from app.modules.service_records.models import ServiceRecord
from app.shared.pagination import PageParams
from app.shared.repository import BaseRepository


class ServiceRecordRepository(BaseRepository[ServiceRecord]):
    model = ServiceRecord

    async def paginate_for_vehicle(
        self,
        vehicle_id: int,
        params: PageParams,
        visible_until: date | None = None,
    ) -> tuple[list[ServiceRecord], int]:

        filters = [ServiceRecord.vehicle_id == vehicle_id]

        if visible_until is not None:
            filters.append(ServiceRecord.service_date <= visible_until)

        items = await self.list(
            *filters,
            order_by=ServiceRecord.service_date.desc(),
            limit=params.limit,
            offset=params.offset,
        )

        total = await self.count(*filters)

        return items, total
