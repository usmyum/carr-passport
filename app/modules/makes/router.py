from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.makes.repository import MakeRepository
from app.modules.makes.schemas import (
    MakeCreate,
    MakeResponse,
    MakeUpdate,
)
from app.modules.makes.service import MakeService

router = APIRouter(
    prefix="/makes",
    tags=["Makes"],
)


def get_make_service(
    db: AsyncSession = Depends(get_db),
) -> MakeService:

    return MakeService(
        MakeRepository(db)
    )


@router.post(
    "",
    response_model=MakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a make",
)
async def create_make(
    data: MakeCreate,
    service: MakeService = Depends(get_make_service),
):
    return await service.create(data)


@router.get(
    "",
    response_model=list[MakeResponse],
    summary="List all makes",
)
async def get_makes(
    service: MakeService = Depends(get_make_service),
):
    return await service.get_all()


@router.get(
    "/{make_id}",
    response_model=MakeResponse,
    summary="Get a make",
)
async def get_make(
    make_id: int,
    service: MakeService = Depends(get_make_service),
):
    return await service.get(make_id)


@router.put(
    "/{make_id}",
    response_model=MakeResponse,
    summary="Update a make",
)
async def update_make(
    make_id: int,
    data: MakeUpdate,
    service: MakeService = Depends(get_make_service),
):
    return await service.update(make_id, data)


@router.delete(
    "/{make_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a make",
)
async def delete_make(
    make_id: int,
    service: MakeService = Depends(get_make_service),
):
    await service.delete(make_id)
