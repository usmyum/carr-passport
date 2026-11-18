from fastapi import APIRouter, Depends, status

from app.modules.mileage_logs.dependencies import get_mileage_log_service
from app.modules.mileage_logs.schemas import MileageLogCreate, MileageLogResponse
from app.modules.mileage_logs.service import MileageLogService
from app.modules.users.dependencies import CurrentUser
from app.shared.pagination import Page, PageParams, get_page_params

router = APIRouter(
    prefix="/mileage-logs",
    tags=["Mileage Logs"],
)


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=MileageLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an odometer reading",
)
async def create_mileage_log(
    vehicle_id: int,
    data: MileageLogCreate,
    current_user: CurrentUser,
    service: MileageLogService = Depends(get_mileage_log_service),
):
    return await service.create(vehicle_id, data, user_id=current_user.id)


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=Page[MileageLogResponse],
    summary="List a vehicle's odometer readings, newest first",
)
async def get_mileage_logs(
    vehicle_id: int,
    current_user: CurrentUser,
    params: PageParams = Depends(get_page_params),
    service: MileageLogService = Depends(get_mileage_log_service),
):

    items, total = await service.paginate_for_vehicle(
        vehicle_id,
        params,
        user_id=current_user.id,
    )

    return Page[MileageLogResponse].build(
        items=[MileageLogResponse.model_validate(item) for item in items],
        total=total,
        params=params,
    )


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an odometer reading you entered",
)
async def delete_mileage_log(
    log_id: int,
    current_user: CurrentUser,
    service: MileageLogService = Depends(get_mileage_log_service),
):
    await service.delete(log_id, user_id=current_user.id)
