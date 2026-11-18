from app.modules.garages.repository import GarageRepository
from app.modules.ownerships.service import OwnershipService
from app.modules.service_records.models import ServiceRecord
from app.modules.service_records.repository import ServiceRecordRepository
from app.modules.service_records.schemas import (
    ServiceRecordCreate,
    ServiceRecordUpdate,
)
from app.shared.exceptions import ForbiddenException, NotFoundException
from app.shared.pagination import PageParams


class ServiceRecordService:

    def __init__(
        self,
        repository: ServiceRecordRepository,
        garage_repository: GarageRepository,
        ownership_service: OwnershipService,
    ):
        self.repository = repository
        self.garage_repository = garage_repository
        self.ownership_service = ownership_service

    async def create(
        self,
        vehicle_id: int,
        data: ServiceRecordCreate,
        user_id: int,
    ) -> ServiceRecord:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        if data.garage_id is not None:
            await self._ensure_garage_exists(data.garage_id)

        record = ServiceRecord(
            vehicle_id=vehicle_id,
            created_by_id=user_id,
            **data.model_dump(),
        )

        return await self.repository.create(record)

    async def get(self, record_id: int, user_id: int) -> ServiceRecord:
        """A record the user may read: the current owner sees all of them,
        a past owner only those dated up to the day they sold."""

        record = await self.repository.get_by_id(record_id)

        if not record:
            raise NotFoundException("Service record not found")

        access = await self.ownership_service.require_access(
            record.vehicle_id,
            user_id,
        )

        # Same 404 as a missing record: a past owner isn't told what the
        # new owner has added since.
        if not access.can_see(record.service_date):
            raise NotFoundException("Service record not found")

        return record

    async def get_editable(
        self,
        record_id: int,
        user_id: int,
    ) -> ServiceRecord:
        """A record the user may change: they're the current owner *and*
        they added it. Also used by `receipts` before touching attachments."""

        record = await self.get(record_id, user_id)

        await self.ownership_service.require_access(
            record.vehicle_id,
            user_id,
            write=True,
        )

        if record.created_by_id != user_id:
            raise ForbiddenException(
                "You can only change service records you added"
            )

        return record

    async def paginate_for_vehicle(
        self,
        vehicle_id: int,
        params: PageParams,
        user_id: int,
    ) -> tuple[list[ServiceRecord], int]:

        access = await self.ownership_service.require_access(
            vehicle_id,
            user_id,
        )

        return await self.repository.paginate_for_vehicle(
            vehicle_id,
            params,
            visible_until=access.visible_until,
        )

    async def update(
        self,
        record_id: int,
        data: ServiceRecordUpdate,
        user_id: int,
    ) -> ServiceRecord:

        record = await self.get_editable(record_id, user_id)

        updates = data.model_dump(exclude_unset=True)

        if updates.get("garage_id") is not None:
            await self._ensure_garage_exists(updates["garage_id"])

        for field, value in updates.items():
            setattr(record, field, value)

        return await self.repository.save(record)

    async def delete(self, record_id: int, user_id: int) -> None:

        record = await self.get_editable(record_id, user_id)

        await self.repository.delete(record)

    async def _ensure_garage_exists(self, garage_id: int) -> None:

        if not await self.garage_repository.get_by_id(garage_id):
            raise NotFoundException("Garage not found")
