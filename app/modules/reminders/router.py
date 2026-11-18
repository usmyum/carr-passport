from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import (
    ReminderCompleteResponse,
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.modules.reminders.service import ReminderService
from app.modules.users.dependencies import CurrentUser
from app.modules.vehicles.repository import VehicleRepository

router = APIRouter(
    prefix="/reminders",
    tags=["Reminders"],
)


def get_reminder_service(
    db: AsyncSession = Depends(get_db),
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> ReminderService:

    return ReminderService(
        repository=ReminderRepository(db),
        vehicle_repository=VehicleRepository(db),
        ownership_service=ownership_service,
    )


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a reminder by date, mileage, or both",
)
async def create_reminder(
    vehicle_id: int,
    data: ReminderCreate,
    current_user: CurrentUser,
    service: ReminderService = Depends(get_reminder_service),
):
    reminder, due = await service.create(vehicle_id, data, user_id=current_user.id)

    return ReminderResponse.build(reminder, due)


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=list[ReminderResponse],
    summary="List your reminders for a vehicle, soonest first",
)
async def get_reminders(
    vehicle_id: int,
    current_user: CurrentUser,
    include_completed: bool = Query(default=False),
    service: ReminderService = Depends(get_reminder_service),
):
    items = await service.list_for_vehicle(
        vehicle_id,
        user_id=current_user.id,
        include_completed=include_completed,
    )

    return [ReminderResponse.build(reminder, due) for reminder, due in items]


@router.get(
    "/{reminder_id}",
    response_model=ReminderResponse,
    summary="Get a reminder",
)
async def get_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    service: ReminderService = Depends(get_reminder_service),
):
    reminder, due = await service.get(reminder_id, user_id=current_user.id)

    return ReminderResponse.build(reminder, due)


@router.put(
    "/{reminder_id}",
    response_model=ReminderResponse,
    summary="Update a reminder",
)
async def update_reminder(
    reminder_id: int,
    data: ReminderUpdate,
    current_user: CurrentUser,
    service: ReminderService = Depends(get_reminder_service),
):
    reminder, due = await service.update(reminder_id, data, user_id=current_user.id)

    return ReminderResponse.build(reminder, due)


@router.post(
    "/{reminder_id}/complete",
    response_model=ReminderCompleteResponse,
    summary="Mark a reminder done (repeating ones schedule the next)",
)
async def complete_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    service: ReminderService = Depends(get_reminder_service),
):
    completed, upcoming = await service.complete(reminder_id, user_id=current_user.id)

    return ReminderCompleteResponse(
        completed=ReminderResponse.build(*completed),
        next=ReminderResponse.build(*upcoming) if upcoming else None,
    )


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reminder",
)
async def delete_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    service: ReminderService = Depends(get_reminder_service),
):
    await service.delete(reminder_id, user_id=current_user.id)
