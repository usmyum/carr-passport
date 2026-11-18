from datetime import date

from app.modules.mileage_logs.models import MileageLog, MileageSource
from app.modules.mileage_logs.repository import MileageLogRepository
from app.modules.mileage_logs.schemas import MileageLogCreate
from app.modules.ownerships.service import OwnershipService
from app.modules.service_records.models import ServiceRecord
from app.modules.vehicles.repository import VehicleRepository
from app.shared.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.shared.pagination import PageParams


class MileageLogService:
    """Odometer history, and the one place `Vehicle.current_mileage` is set.

    Readings come from two places: entered by hand here, or copied from a
    service record's odometer field (`service_records` calls
    `validate_reading` / `sync_service_record` / `refresh_current_mileage`).
    """

    def __init__(
        self,
        repository: MileageLogRepository,
        vehicle_repository: VehicleRepository,
        ownership_service: OwnershipService,
    ):
        self.repository = repository
        self.vehicle_repository = vehicle_repository
        self.ownership_service = ownership_service

    async def create(
        self,
        vehicle_id: int,
        data: MileageLogCreate,
        user_id: int,
    ) -> MileageLog:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        await self.validate_reading(vehicle_id, data.recorded_on, data.odometer)

        log = await self.repository.create(
            MileageLog(
                vehicle_id=vehicle_id,
                created_by_id=user_id,
                source=MileageSource.MANUAL,
                **data.model_dump(),
            )
        )

        await self.refresh_current_mileage(vehicle_id)

        return log

    async def paginate_for_vehicle(
        self,
        vehicle_id: int,
        params: PageParams,
        user_id: int,
    ) -> tuple[list[MileageLog], int]:

        access = await self.ownership_service.require_access(
            vehicle_id,
            user_id,
        )

        return await self.repository.paginate_for_vehicle(
            vehicle_id,
            params,
            visible_until=access.visible_until,
        )

    async def delete(self, log_id: int, user_id: int) -> None:

        log = await self.repository.get_by_id(log_id)

        if not log:
            raise NotFoundException("Mileage log not found")

        access = await self.ownership_service.require_access(
            log.vehicle_id,
            user_id,
        )

        if not access.can_see(log.recorded_on):
            raise NotFoundException("Mileage log not found")

        await self.ownership_service.require_access(
            log.vehicle_id,
            user_id,
            write=True,
        )

        if log.source == MileageSource.SERVICE_RECORD:
            raise ConflictException(
                "This reading comes from a service record — change the "
                "record's odometer instead"
            )

        if log.created_by_id != user_id:
            raise ForbiddenException("You can only delete readings you added")

        await self.repository.delete(log)

        await self.refresh_current_mileage(log.vehicle_id)

    # ---- used by `vehicles` and `service_records` ---------------------------

    async def add_reading(
        self,
        vehicle_id: int,
        recorded_on: date,
        odometer: int,
        user_id: int,
    ) -> MileageLog:
        """A manual reading whose access has already been checked — for
        setting `current_mileage` from the vehicle form."""

        # `validate_reading` lets two readings on the same day disagree
        # (morning and evening), but the form means "the mileage now".
        latest = await self.repository.get_latest(vehicle_id)

        if latest and odometer < latest.odometer:
            raise ValidationException(
                f"Mileage can't go down: the latest reading is "
                f"{latest.odometer:,} on {latest.recorded_on}"
            )

        await self.validate_reading(vehicle_id, recorded_on, odometer)

        log = await self.repository.create(
            MileageLog(
                vehicle_id=vehicle_id,
                created_by_id=user_id,
                source=MileageSource.MANUAL,
                recorded_on=recorded_on,
                odometer=odometer,
            )
        )

        await self.refresh_current_mileage(vehicle_id)

        return log

    async def validate_reading(
        self,
        vehicle_id: int,
        recorded_on: date,
        odometer: int,
        service_record_id: int | None = None,
    ) -> None:
        """Odometers only go up. Reject a reading that contradicts the
        history — it's either a typo or a wound-back clock, and a buyer
        reading the history should be able to trust it.

        `service_record_id`: the record being edited, whose own current
        reading is about to be replaced and so doesn't count.
        """

        exclude_id = None

        if service_record_id is not None:
            existing = await self.repository.get_for_service_record(
                service_record_id
            )
            exclude_id = existing.id if existing else None

        conflict = await self.repository.find_contradicting(
            vehicle_id,
            recorded_on,
            odometer,
            exclude_id=exclude_id,
        )

        if conflict:
            raise ValidationException(
                f"An odometer reading of {odometer:,} on {recorded_on} "
                f"contradicts {conflict.odometer:,} recorded on "
                f"{conflict.recorded_on}"
            )

    async def sync_service_record(self, record: ServiceRecord) -> None:
        """Make the record's reading (if any) match its odometer field.

        Call `validate_reading` before saving the record — this assumes
        the reading has already been checked.
        """

        log = await self.repository.get_for_service_record(record.id)

        if record.odometer_reading is None:
            if log:
                await self.repository.delete(log)

        elif log:
            log.recorded_on = record.service_date
            log.odometer = record.odometer_reading
            await self.repository.save(log)

        else:
            await self.repository.create(
                MileageLog(
                    vehicle_id=record.vehicle_id,
                    service_record_id=record.id,
                    created_by_id=record.created_by_id,
                    source=MileageSource.SERVICE_RECORD,
                    recorded_on=record.service_date,
                    odometer=record.odometer_reading,
                )
            )

        await self.refresh_current_mileage(record.vehicle_id)

    async def refresh_current_mileage(self, vehicle_id: int) -> None:
        """Set the vehicle's mileage to its latest reading (or none)."""

        vehicle = await self.vehicle_repository.get_by_id(vehicle_id)

        if not vehicle:
            return

        latest = await self.repository.get_latest(vehicle_id)
        mileage = latest.odometer if latest else None

        if vehicle.current_mileage != mileage:
            vehicle.current_mileage = mileage
            await self.vehicle_repository.save(vehicle)
