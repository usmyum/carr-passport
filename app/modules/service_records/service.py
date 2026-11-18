from app.modules.garages.repository import GarageRepository
from app.modules.mileage_logs.service import MileageLogService
from app.modules.ownerships.service import OwnershipService
from app.modules.service_records.models import ServiceRecord
from app.modules.service_records.repository import ServiceRecordRepository
from app.modules.service_records.schemas import (
    ServiceRecordCreate,
    ServiceRecordUpdate,
)
from app.shared.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.shared.pagination import PageParams


class ServiceRecordService:

    def __init__(
        self,
        repository: ServiceRecordRepository,
        garage_repository: GarageRepository,
        ownership_service: OwnershipService,
        mileage_log_service: MileageLogService,
    ):
        self.repository = repository
        self.garage_repository = garage_repository
        self.ownership_service = ownership_service
        self.mileage_log_service = mileage_log_service

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

        if data.odometer_reading is not None:
            await self.mileage_log_service.validate_reading(
                vehicle_id,
                data.service_date,
                data.odometer_reading,
            )

        record = ServiceRecord(
            vehicle_id=vehicle_id,
            created_by_id=user_id,
            **data.model_dump(),
        )

        record = await self.repository.create(record)

        # The odometer reading also lands in the mileage log, so it's
        # never typed twice.
        await self.mileage_log_service.sync_service_record(record)

        return record

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

        for field in ("service_date", "description"):
            if field in updates and updates[field] is None:
                raise ValidationException(f"{field} cannot be empty")

        odometer = updates.get("odometer_reading", record.odometer_reading)

        if odometer is not None:
            await self.mileage_log_service.validate_reading(
                record.vehicle_id,
                updates.get("service_date") or record.service_date,
                odometer,
                service_record_id=record.id,
            )

        for field, value in updates.items():
            setattr(record, field, value)

        record = await self.repository.save(record)

        await self.mileage_log_service.sync_service_record(record)

        return record

    async def delete(self, record_id: int, user_id: int) -> None:

        record = await self.get_editable(record_id, user_id)

        # Its mileage reading goes with it (ON DELETE CASCADE).
        await self.repository.delete(record)

        await self.mileage_log_service.refresh_current_mileage(record.vehicle_id)

    async def _ensure_garage_exists(self, garage_id: int) -> None:

        if not await self.garage_repository.get_by_id(garage_id):
            raise NotFoundException("Garage not found")
