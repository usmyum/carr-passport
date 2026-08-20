"""Shared repository base.

Every domain repository inherits from this so the four boring queries
(create / read / save / delete) are written once. Domain-specific queries
still belong in the domain's own repository — this class is a floor,
not a ceiling.

`save()` exists so services never have to touch `repository.db` themselves:
mutate the entity, then hand it back to the repository to persist.
"""

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Subclasses must set `model` to their SQLAlchemy class."""

    model: type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
            self,
            entity: ModelType,
    ) -> ModelType:

        self.db.add(entity)

        await self.db.commit()
        await self.db.refresh(entity)

        return entity

    async def save(
            self,
            entity: ModelType,
    ) -> ModelType:
        """Persist in-memory changes made to an already-loaded entity."""

        await self.db.commit()
        await self.db.refresh(entity)

        return entity

    async def get_by_id(
            self,
            entity_id: Any,
    ) -> ModelType | None:

        return await self.db.get(
            self.model,
            entity_id,
        )

    async def list(
            self,
            *filters: ColumnElement[bool],
            order_by: Any = None,
            limit: int | None = None,
            offset: int | None = None,
    ) -> list[ModelType]:

        query = select(self.model)

        if filters:
            query = query.where(*filters)

        if order_by is not None:
            query = query.order_by(order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def count(
            self,
            *filters: ColumnElement[bool],
    ) -> int:

        query = select(func.count()).select_from(self.model)

        if filters:
            query = query.where(*filters)

        result = await self.db.execute(query)

        return result.scalar_one()

    async def exists(
            self,
            *filters: ColumnElement[bool],
    ) -> bool:

        return await self.count(*filters) > 0

    async def find_one(
            self,
            *filters: ColumnElement[bool],
    ) -> ModelType | None:

        result = await self.db.execute(
            select(self.model).where(*filters)
        )

        return result.scalar_one_or_none()

    async def delete(
            self,
            entity: ModelType,
    ) -> None:

        await self.db.delete(entity)
        await self.db.commit()

    async def delete_many(
            self,
            entities: Sequence[ModelType],
    ) -> None:

        for entity in entities:
            await self.db.delete(entity)

        await self.db.commit()
