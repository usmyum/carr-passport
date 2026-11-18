from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
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
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> VehicleService:

    return VehicleService(
        repository=VehicleRepository(db),
        model_repository=VehicleModelRepository(db),
        ownership_service=ownership_service,
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
    vehicle, access = await service.create(data, owner_id=current_user.id)

    return VehicleResponse.build(vehicle, access.role)


@router.get(
    "",
    response_model=Page[VehicleResponse],
    summary="List your vehicles",
)
async def get_vehicles(
    current_user: CurrentUser,
    include_past: bool = Query(
        default=False,
        description="Also list vehicles you used to own (read-only)",
    ),
    params: PageParams = Depends(get_page_params),
    service: VehicleService = Depends(get_vehicle_service),
):

    items, total = await service.paginate(
        params,
        user_id=current_user.id,
        include_past=include_past,
    )

    return Page[VehicleResponse].build(
        items=[
            VehicleResponse.build(vehicle, access.role)
            for vehicle, access in items
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
    vehicle, access = await service.get(vehicle_id, user_id=current_user.id)

    return VehicleResponse.build(vehicle, access.role)


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
    vehicle, access = await service.update(
        vehicle_id,
        data,
        user_id=current_user.id,
    )

    return VehicleResponse.build(vehicle, access.role)


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
    await service.delete(vehicle_id, user_id=current_user.id)
