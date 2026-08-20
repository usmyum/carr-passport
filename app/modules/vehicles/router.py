from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.users.dependencies import CurrentUser
from app.modules.vehicle_models.repository import VehicleModelRepository
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)
from app.modules.vehicles.service import VehicleService
from app.shared.pagination import Page, PageParams, get_page_params


router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],
)


def get_vehicle_service(
    db: AsyncSession = Depends(get_db),
) -> VehicleService:

    return VehicleService(
        repository=VehicleRepository(db),
        model_repository=VehicleModelRepository(db),
    )


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a vehicle",
)
async def create_vehicle(
    data: VehicleCreate,
    current_user: CurrentUser,
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.create(data, owner_id=current_user.id)


@router.get(
    "",
    response_model=Page[VehicleResponse],
    summary="List your vehicles",
)
async def get_vehicles(
    current_user: CurrentUser,
    params: PageParams = Depends(get_page_params),
    service: VehicleService = Depends(get_vehicle_service),
):

    items, total = await service.paginate(
        params,
        owner_id=current_user.id,
    )

    return Page[VehicleResponse].build(
        items=[
            VehicleResponse.model_validate(item)
            for item in items
        ],
        total=total,
        params=params,
    )


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Get a vehicle",
)
async def get_vehicle(
    vehicle_id: int,
    current_user: CurrentUser,
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.get(vehicle_id, owner_id=current_user.id)


@router.put(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Update a vehicle",
)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    current_user: CurrentUser,
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.update(
        vehicle_id,
        data,
        owner_id=current_user.id,
    )


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vehicle",
)
async def delete_vehicle(
    vehicle_id: int,
    current_user: CurrentUser,
    service: VehicleService = Depends(get_vehicle_service),
):
    await service.delete(vehicle_id, owner_id=current_user.id)
