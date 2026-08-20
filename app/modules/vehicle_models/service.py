from app.modules.makes.repository import MakeRepository
from app.modules.vehicle_models.models import VehicleModel
from app.modules.vehicle_models.repository import VehicleModelRepository
from app.modules.vehicle_models.schemas import (
    VehicleModelCreate,
    VehicleModelUpdate,
)
from app.shared.exceptions import ConflictException, NotFoundException
from app.shared.slug import generate_slug


class VehicleModelService:

    def __init__(
        self,
        repository: VehicleModelRepository,
        make_repository: MakeRepository,
    ):
        self.repository = repository
        self.make_repository = make_repository

    async def create(
        self,
        make_id: int,
        data: VehicleModelCreate,
    ) -> VehicleModel:

        if not await self.make_repository.get_by_id(make_id):
            raise NotFoundException("Make not found")

        name = data.name.strip()

        await self._ensure_name_is_free(make_id, name)

        model = VehicleModel(
            make_id=make_id,
            name=name,
            slug=generate_slug(name),
        )

        return await self.repository.create(model)

    async def get(self, model_id: int) -> VehicleModel:

        model = await self.repository.get_by_id(model_id)

        if not model:
            raise NotFoundException("Vehicle model not found")

        return model

    async def get_all(
        self,
        make_id: int | None = None,
    ) -> list[VehicleModel]:

        return await self.repository.get_all(make_id)

    async def update(
        self,
        model_id: int,
        data: VehicleModelUpdate,
    ) -> VehicleModel:

        model = await self.get(model_id)

        name = data.name.strip()

        await self._ensure_name_is_free(
            model.make_id,
            name,
            exclude_id=model.id,
        )

        model.name = name
        model.slug = generate_slug(name)

        return await self.repository.save(model)

    async def delete(self, model_id: int) -> None:

        model = await self.get(model_id)

        await self.repository.delete(model)

    async def _ensure_name_is_free(
        self,
        make_id: int,
        name: str,
        exclude_id: int | None = None,
    ) -> None:

        existing = await self.repository.get_by_name(make_id, name)

        if existing and existing.id != exclude_id:
            raise ConflictException(
                "Model already exists for this make"
            )
