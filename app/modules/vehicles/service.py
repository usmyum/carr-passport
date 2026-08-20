from app.modules.vehicle_models.repository import VehicleModelRepository
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate
from app.shared.exceptions import ConflictException, NotFoundException
from app.shared.pagination import PageParams


class VehicleService:

    def __init__(
            self,
            repository: VehicleRepository,
            model_repository: VehicleModelRepository,
    ):
        self.repository = repository
        self.model_repository = model_repository

    async def create(
            self,
            data: VehicleCreate,
            owner_id: int,
    ) -> Vehicle:

        await self._ensure_model_exists(data.model_id)

        if data.vin:
            await self._ensure_vin_is_free(data.vin)

        vehicle = Vehicle(
            owner_id=owner_id,
            **data.model_dump(),
        )

        return await self.repository.create(vehicle)

    async def get(self, vehicle_id: int, owner_id: int) -> Vehicle:

        vehicle = await self.repository.get_by_id(vehicle_id)

        # A non-owner gets the same 404 as a vehicle that doesn't exist —
        # the API never confirms someone else's vehicle exists.
        if not vehicle or vehicle.owner_id != owner_id:
            raise NotFoundException("Vehicle not found")

        return vehicle

    async def paginate(
            self,
            params: PageParams,
            owner_id: int,
    ) -> tuple[list[Vehicle], int]:

        return await self.repository.paginate(
            params,
            Vehicle.owner_id == owner_id,
        )

    async def update(
            self,
            vehicle_id: int,
            data: VehicleUpdate,
            owner_id: int,
    ) -> Vehicle:

        vehicle = await self.get(vehicle_id, owner_id)

        updates = data.model_dump(exclude_unset=True)

        if "model_id" in updates:
            await self._ensure_model_exists(updates["model_id"])

        if updates.get("vin"):
            await self._ensure_vin_is_free(
                updates["vin"],
                exclude_id=vehicle.id,
            )

        for field, value in updates.items():
            setattr(vehicle, field, value)

        return await self.repository.save(vehicle)

    async def delete(self, vehicle_id: int, owner_id: int) -> None:

        vehicle = await self.get(vehicle_id, owner_id)

        await self.repository.delete(vehicle)

    async def _ensure_model_exists(self, model_id: int) -> None:

        if not await self.model_repository.get_by_id(model_id):
            raise NotFoundException("Vehicle model not found")

    async def _ensure_vin_is_free(
            self,
            vin: str,
            exclude_id: int | None = None,
    ) -> None:
        """The unique index is the real guarantee — this just makes the
        common case a clear 409 instead of an integrity error."""

        existing = await self.repository.get_by_vin(vin)

        if existing and existing.id != exclude_id:
            raise ConflictException(
                "A vehicle with this VIN already exists"
            )
