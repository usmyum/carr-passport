"""Offset pagination shared by every list endpoint that can grow unbounded.

Small reference catalogs (makes, vehicle models) intentionally return plain
lists — they are read straight into dropdowns and paginating them would only
make the client's job harder.
"""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

ItemType = TypeVar("ItemType")


class PageParams(BaseModel):
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def get_page_params(
        page: int = Query(
            default=1,
            ge=1,
            description="1-based page number",
        ),
        size: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Items per page",
        ),
) -> PageParams:
    return PageParams(
        page=page,
        size=size,
    )


class Page(BaseModel, Generic[ItemType]):
    model_config = ConfigDict(from_attributes=True)

    items: list[ItemType]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(
            cls,
            items: list[ItemType],
            total: int,
            params: PageParams,
    ) -> "Page[ItemType]":
        pages = (
            (total + params.size - 1) // params.size
            if params.size
            else 0
        )

        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
        )
