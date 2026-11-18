from fastapi import APIRouter, Depends, status

from app.modules.service_records.dependencies import get_service_record_service
from app.modules.service_records.schemas import (
    ServiceRecordCreate,
    ServiceRecordResponse,
    ServiceRecordUpdate,
)
from app.modules.service_records.service import ServiceRecordService
from app.modules.users.dependencies import CurrentUser
from app.shared.pagination import Page, PageParams, get_page_params

router = APIRouter(
    prefix="/service-records",
    tags=["Service Records"],
)


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=ServiceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a service record to a vehicle",
)
async def create_service_record(
    vehicle_id: int,
    data: ServiceRecordCreate,
    current_user: CurrentUser,
    service: ServiceRecordService = Depends(get_service_record_service),
):
    return await service.create(
        vehicle_id,
        data,
        user_id=current_user.id,
    )


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=Page[ServiceRecordResponse],
    summary="List a vehicle's service records",
)
async def get_service_records(
    vehicle_id: int,
    current_user: CurrentUser,
    params: PageParams = Depends(get_page_params),
    service: ServiceRecordService = Depends(get_service_record_service),
):

    items, total = await service.paginate_for_vehicle(
        vehicle_id,
        params,
        user_id=current_user.id,
    )

    return Page[ServiceRecordResponse].build(
        items=[
            ServiceRecordResponse.model_validate(item)
            for item in items
        ],
        total=total,
        params=params,
    )


@router.get(
    "/{record_id}",
    response_model=ServiceRecordResponse,
    summary="Get a service record",
)
async def get_service_record(
    record_id: int,
    current_user: CurrentUser,
    service: ServiceRecordService = Depends(get_service_record_service),
):
    return await service.get(record_id, user_id=current_user.id)


@router.put(
    "/{record_id}",
    response_model=ServiceRecordResponse,
    summary="Update a service record",
)
async def update_service_record(
    record_id: int,
    data: ServiceRecordUpdate,
    current_user: CurrentUser,
    service: ServiceRecordService = Depends(get_service_record_service),
):
    return await service.update(
        record_id,
        data,
        user_id=current_user.id,
    )


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service record",
)
async def delete_service_record(
    record_id: int,
    current_user: CurrentUser,
    service: ServiceRecordService = Depends(get_service_record_service),
):
    await service.delete(record_id, user_id=current_user.id)
