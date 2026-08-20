from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.makes.repository import MakeRepository
from app.modules.vehicle_models.repository import VehicleModelRepository
from app.modules.vehicle_models.schemas import (
    VehicleModelCreate,
    VehicleModelResponse,
    VehicleModelUpdate,
)
from app.modules.vehicle_models.service import VehicleModelService

router = APIRouter(
    prefix="/models",
    tags=["Vehicle Models"],
)


def get_vehicle_model_service(
        db: AsyncSession = Depends(get_db),
) -> VehicleModelService:
    return VehicleModelService(
        repository=VehicleModelRepository(db),
        make_repository=MakeRepository(db),
    )


@router.post(
    "/make/{make_id}",
    response_model=VehicleModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a model under a make",
)
async def create_model(
        make_id: int,
        data: VehicleModelCreate,
        service: VehicleModelService = Depends(
            get_vehicle_model_service
        ),
):
    return await service.create(make_id, data)


@router.get(
    "",
    response_model=list[VehicleModelResponse],
    summary="List models, optionally filtered by make",
)
async def get_models(
        make_id: int | None = Query(
            default=None,
            description="Only return models belonging to this make",
        ),
        service: VehicleModelService = Depends(
            get_vehicle_model_service
        ),
):
    return await service.get_all(make_id)


@router.get(
    "/{model_id}",
    response_model=VehicleModelResponse,
    summary="Get a model",
)
async def get_model(
        model_id: int,
        service: VehicleModelService = Depends(
            get_vehicle_model_service
        ),
):
    return await service.get(model_id)


@router.put(
    "/{model_id}",
    response_model=VehicleModelResponse,
    summary="Update a model",
)
async def update_model(
        model_id: int,
        data: VehicleModelUpdate,
        service: VehicleModelService = Depends(
            get_vehicle_model_service
        ),
):
    return await service.update(model_id, data)


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
)
async def delete_model(
        model_id: int,
        service: VehicleModelService = Depends(
            get_vehicle_model_service
        ),
):
    await service.delete(model_id)
