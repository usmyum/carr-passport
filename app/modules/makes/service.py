from app.modules.makes.models import Make
from app.modules.makes.repository import MakeRepository
from app.modules.makes.schemas import MakeCreate, MakeUpdate
from app.shared.exceptions import ConflictException, NotFoundException
from app.shared.slug import generate_slug


class MakeService:

    def __init__(self, repository: MakeRepository):
        self.repository = repository

    async def create(self, data: MakeCreate) -> Make:

        name = data.name.strip()

        await self._ensure_name_is_free(name)

        make = Make(
            name=name,
            slug=generate_slug(name),
        )

        return await self.repository.create(make)

    async def get(self, make_id: int) -> Make:
        """Fetch or raise. Routers call this so they never repeat a 404 check."""

        make = await self.repository.get_by_id(make_id)

        if not make:
            raise NotFoundException("Make not found")

        return make

    async def get_all(self) -> list[Make]:
        return await self.repository.get_all()

    async def update(
            self,
            make_id: int,
            data: MakeUpdate,
    ) -> Make:

        make = await self.get(make_id)

        name = data.name.strip()

        await self._ensure_name_is_free(
            name,
            exclude_id=make.id,
        )

        make.name = name
        make.slug = generate_slug(name)

        return await self.repository.save(make)

    async def delete(self, make_id: int) -> None:

        make = await self.get(make_id)

        await self.repository.delete(make)

    async def _ensure_name_is_free(
            self,
            name: str,
            exclude_id: int | None = None,
    ) -> None:

        existing = await self.repository.get_by_name(name)

        if existing and existing.id != exclude_id:
            raise ConflictException("Make already exists")
