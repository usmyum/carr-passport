from app.modules.garages.models import Garage
from app.modules.garages.repository import GarageRepository
from app.modules.garages.schemas import GarageCreate, GarageUpdate
from app.shared.exceptions import ConflictException, NotFoundException
from app.shared.slug import generate_slug


class GarageService:

    def __init__(self, repository: GarageRepository):
        self.repository = repository

    async def create(self, data: GarageCreate) -> Garage:

        name = data.name.strip()

        await self._ensure_name_is_free(name)

        garage = Garage(
            name=name,
            slug=generate_slug(name),
            address=data.address,
            phone=data.phone,
            email=data.email,
            notes=data.notes,
        )

        return await self.repository.create(garage)

    async def get(self, garage_id: int) -> Garage:

        garage = await self.repository.get_by_id(garage_id)

        if not garage:
            raise NotFoundException("Garage not found")

        return garage

    async def get_all(self) -> list[Garage]:
        return await self.repository.get_all()

    async def update(
            self,
            garage_id: int,
            data: GarageUpdate,
    ) -> Garage:

        garage = await self.get(garage_id)

        name = data.name.strip()

        await self._ensure_name_is_free(
            name,
            exclude_id=garage.id,
        )

        garage.name = name
        garage.slug = generate_slug(name)
        garage.address = data.address
        garage.phone = data.phone
        garage.email = data.email
        garage.notes = data.notes

        return await self.repository.save(garage)

    async def delete(self, garage_id: int) -> None:

        garage = await self.get(garage_id)

        await self.repository.delete(garage)

    async def _ensure_name_is_free(
            self,
            name: str,
            exclude_id: int | None = None,
    ) -> None:

        existing = await self.repository.get_by_name(name)

        if existing and existing.id != exclude_id:
            raise ConflictException("Garage already exists")
