from app.modules.garages.repository import GarageRepository
from app.modules.service_records.models import ServiceRecord
from app.modules.service_records.repository import ServiceRecordRepository
from app.modules.service_records.schemas import (
    ServiceRecordCreate,
    ServiceRecordUpdate,
)
from app.modules.vehicles.repository import VehicleRepository
from app.shared.exceptions import NotFoundException
from app.shared.pagination import PageParams


class ServiceRecordService:

    def __init__(
            self,
            repository: ServiceRecordRepository,
            vehicle_repository: VehicleRepository,
            garage_repository: GarageRepository,
    ):
        self.repository = repository
        self.vehicle_repository = vehicle_repository
        self.garage_repository = garage_repository

    async def create(
            self,
            vehicle_id: int,
            data: ServiceRecordCreate,
            owner_id: int,
    ) -> ServiceRecord:

        await self._ensure_vehicle_is_owned(vehicle_id, owner_id)

        if data.garage_id is not None:
            await self._ensure_garage_exists(data.garage_id)

        record = ServiceRecord(
            vehicle_id=vehicle_id,
            **data.model_dump(),
        )

        return await self.repository.create(record)

    async def get(self, record_id: int, owner_id: int) -> ServiceRecord:

        record = await self.repository.get_by_id(record_id)

        if not record:
            raise NotFoundException("Service record not found")

        # Ownership lives one level up, on the vehicle — same 404-not-403
        # masking used everywhere else, so this never confirms someone
        # else's service record exists.
        await self._ensure_vehicle_is_owned(record.vehicle_id, owner_id)

        return record

    async def paginate_for_vehicle(
            self,
            vehicle_id: int,
            params: PageParams,
            owner_id: int,
    ) -> tuple[list[ServiceRecord], int]:

        await self._ensure_vehicle_is_owned(vehicle_id, owner_id)

        return await self.repository.paginate_for_vehicle(
            vehicle_id,
            params,
        )

    async def update(
            self,
            record_id: int,
            data: ServiceRecordUpdate,
            owner_id: int,
    ) -> ServiceRecord:

        record = await self.get(record_id, owner_id)

        updates = data.model_dump(exclude_unset=True)

        if updates.get("garage_id") is not None:
            await self._ensure_garage_exists(updates["garage_id"])

        for field, value in updates.items():
            setattr(record, field, value)

        return await self.repository.save(record)

    async def delete(self, record_id: int, owner_id: int) -> None:

        record = await self.get(record_id, owner_id)

        await self.repository.delete(record)

    async def _ensure_vehicle_is_owned(
            self,
            vehicle_id: int,
            owner_id: int,
    ) -> None:

        vehicle = await self.vehicle_repository.get_by_id(vehicle_id)

        if not vehicle or vehicle.owner_id != owner_id:
            raise NotFoundException("Vehicle not found")

    async def _ensure_garage_exists(self, garage_id: int) -> None:

        if not await self.garage_repository.get_by_id(garage_id):
            raise NotFoundException("Garage not found")
