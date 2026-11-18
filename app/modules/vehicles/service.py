from app.modules.ownerships.models import VehicleOwnership
from app.modules.ownerships.service import OwnershipService, VehicleAccess
from app.modules.vehicle_models.repository import VehicleModelRepository
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate
from app.shared.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.shared.pagination import PageParams

# Optional in `VehicleUpdate` (leave out to keep), but never clearable.
NON_NULLABLE_FIELDS = ("model_id", "year", "vin")


class VehicleService:

    def __init__(
        self,
        repository: VehicleRepository,
        model_repository: VehicleModelRepository,
        ownership_service: OwnershipService,
    ):
        self.repository = repository
        self.model_repository = model_repository
        self.ownership_service = ownership_service

    async def create(
        self,
        data: VehicleCreate,
        owner_id: int,
    ) -> tuple[Vehicle, VehicleAccess]:

        await self._ensure_model_exists(data.model_id)

        await self._ensure_vin_is_free(data.vin)

        # Saved together with its first ownership period, in one commit.
        vehicle = Vehicle(
            **data.model_dump(),
            ownerships=[VehicleOwnership(user_id=owner_id)],
        )

        vehicle = await self.repository.create(vehicle)

        return vehicle, VehicleAccess.from_ended_at(None)

    async def get(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> tuple[Vehicle, VehicleAccess]:

        access = await self.ownership_service.require_access(
            vehicle_id,
            user_id,
        )

        return await self._get_vehicle(vehicle_id), access

    async def paginate(
        self,
        params: PageParams,
        user_id: int,
        include_past: bool = False,
    ) -> tuple[list[tuple[Vehicle, VehicleAccess]], int]:

        rows, total = await self.repository.paginate_for_user(
            user_id,
            params,
            include_past=include_past,
        )

        items = [
            (vehicle, VehicleAccess.from_ended_at(ended_at))
            for vehicle, ended_at in rows
        ]

        return items, total

    async def update(
        self,
        vehicle_id: int,
        data: VehicleUpdate,
        user_id: int,
    ) -> tuple[Vehicle, VehicleAccess]:

        access = await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        vehicle = await self._get_vehicle(vehicle_id)

        updates = data.model_dump(exclude_unset=True)

        for field in NON_NULLABLE_FIELDS:
            if field in updates and updates[field] is None:
                raise ValidationException(f"{field} cannot be empty")

        if "model_id" in updates:
            await self._ensure_model_exists(updates["model_id"])

        if "vin" in updates:
            await self._ensure_vin_is_free(
                updates["vin"],
                exclude_id=vehicle.id,
            )

        for field, value in updates.items():
            setattr(vehicle, field, value)

        return await self.repository.save(vehicle), access

    async def delete(self, vehicle_id: int, user_id: int) -> None:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        # Once a car has been sold, its history belongs to everyone who has
        # owned it — the current owner can't wipe it.
        if await self.ownership_service.has_changed_hands(vehicle_id):
            raise ConflictException(
                "This vehicle has had previous owners, so its history "
                "can't be deleted"
            )

        vehicle = await self._get_vehicle(vehicle_id)

        await self.repository.delete(vehicle)

    async def _get_vehicle(self, vehicle_id: int) -> Vehicle:
        """Load a vehicle whose access has already been checked."""

        vehicle = await self.repository.get_by_id(vehicle_id)

        if not vehicle:
            raise NotFoundException("Vehicle not found")

        return vehicle

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
                "A vehicle with this VIN is already registered. If you've "
                "bought it, ask the current owner to transfer it to you."
            )
