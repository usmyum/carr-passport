from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.garages.repository import GarageRepository
from app.modules.garages.schemas import (
    GarageCreate,
    GarageResponse,
    GarageUpdate,
)
from app.modules.garages.service import GarageService


router = APIRouter(
    prefix="/garages",
    tags=["Garages"],
)


def get_garage_service(
    db: AsyncSession = Depends(get_db),
) -> GarageService:

    return GarageService(
        GarageRepository(db)
    )


@router.post(
    "",
    response_model=GarageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a garage",
)
async def create_garage(
    data: GarageCreate,
    service: GarageService = Depends(get_garage_service),
):
    return await service.create(data)


@router.get(
    "",
    response_model=list[GarageResponse],
    summary="List all garages",
)
async def get_garages(
    service: GarageService = Depends(get_garage_service),
):
    return await service.get_all()


@router.get(
    "/{garage_id}",
    response_model=GarageResponse,
    summary="Get a garage",
)
async def get_garage(
    garage_id: int,
    service: GarageService = Depends(get_garage_service),
):
    return await service.get(garage_id)


@router.put(
    "/{garage_id}",
    response_model=GarageResponse,
    summary="Update a garage",
)
async def update_garage(
    garage_id: int,
    data: GarageUpdate,
    service: GarageService = Depends(get_garage_service),
):
    return await service.update(garage_id, data)


@router.delete(
    "/{garage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a garage",
)
async def delete_garage(
    garage_id: int,
    service: GarageService = Depends(get_garage_service),
):
    await service.delete(garage_id)
