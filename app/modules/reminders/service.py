import calendar
from datetime import date

from app.db.base import utc_now
from app.modules.ownerships.service import OwnershipService
from app.modules.reminders.models import Reminder
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import ReminderCreate, ReminderUpdate
from app.modules.vehicles.repository import VehicleRepository
from app.shared.due import DueStatus, due_status
from app.shared.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)

# A reminder paired with how urgent it is (None once completed).
ReminderWithStatus = tuple[Reminder, DueStatus | None]


def add_months(start: date, months: int) -> date:
    """31 Jan + 1 month = 28/29 Feb, not an error."""

    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])

    return date(year, month, day)


def reminder_status(
    reminder: Reminder,
    current_mileage: int | None,
) -> DueStatus | None:

    if reminder.completed_at is not None:
        return None

    return due_status(
        utc_now().date(),
        due_on=reminder.due_on,
        due_mileage=reminder.due_mileage,
        current_mileage=current_mileage,
    )


class ReminderService:
    """Only the current owner sees and manages reminders, and only their
    own — after a sale the seller's reminders go quiet and the buyer
    starts with none."""

    def __init__(
        self,
        repository: ReminderRepository,
        vehicle_repository: VehicleRepository,
        ownership_service: OwnershipService,
    ):
        self.repository = repository
        self.vehicle_repository = vehicle_repository
        self.ownership_service = ownership_service

    async def create(
        self,
        vehicle_id: int,
        data: ReminderCreate,
        user_id: int,
    ) -> ReminderWithStatus:

        await self._require_owner(vehicle_id, user_id)

        reminder = await self.repository.create(
            Reminder(
                vehicle_id=vehicle_id,
                created_by_id=user_id,
                **data.model_dump(),
            )
        )

        return await self._with_status(reminder)

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
        include_completed: bool = False,
    ) -> list[ReminderWithStatus]:

        await self._require_owner(vehicle_id, user_id)

        reminders = await self.repository.list_for_vehicle(
            vehicle_id,
            user_id,
            include_completed=include_completed,
        )

        mileage = await self._current_mileage(vehicle_id)

        return [(r, reminder_status(r, mileage)) for r in reminders]

    async def get(self, reminder_id: int, user_id: int) -> ReminderWithStatus:
        return await self._with_status(await self._get(reminder_id, user_id))

    async def update(
        self,
        reminder_id: int,
        data: ReminderUpdate,
        user_id: int,
    ) -> ReminderWithStatus:

        reminder = await self._get(reminder_id, user_id)

        updates = data.model_dump(exclude_unset=True)

        if "title" in updates and updates["title"] is None:
            raise ValidationException("title cannot be empty")

        due_on = updates.get("due_on", reminder.due_on)
        due_mileage = updates.get("due_mileage", reminder.due_mileage)

        if due_on is None and due_mileage is None:
            raise ValidationException("Set due_on, due_mileage, or both")

        for field, value in updates.items():
            setattr(reminder, field, value)

        return await self._with_status(await self.repository.save(reminder))

    async def complete(
        self,
        reminder_id: int,
        user_id: int,
    ) -> tuple[ReminderWithStatus, ReminderWithStatus | None]:
        """Mark done; a repeating reminder schedules its next occurrence,
        counted from today and today's mileage (not the old due date —
        an oil change done late resets the clock from when it was done)."""

        reminder = await self._get(reminder_id, user_id)

        if reminder.completed_at is not None:
            raise ConflictException("This reminder is already completed")

        now = utc_now()
        mileage = await self._current_mileage(reminder.vehicle_id)

        reminder.completed_at = now

        next_reminder = None

        if reminder.repeat_months or reminder.repeat_km:
            next_reminder = Reminder(
                vehicle_id=reminder.vehicle_id,
                created_by_id=user_id,
                title=reminder.title,
                notes=reminder.notes,
                repeat_months=reminder.repeat_months,
                repeat_km=reminder.repeat_km,
                due_on=(
                    add_months(now.date(), reminder.repeat_months)
                    if reminder.repeat_months
                    else None
                ),
                due_mileage=self._next_mileage(reminder, mileage),
            )

            # Without a known mileage a km-only repeat has nothing to count
            # from — fall back to "check again in a year" rather than lose it.
            if next_reminder.due_on is None and next_reminder.due_mileage is None:
                next_reminder.due_on = add_months(now.date(), 12)

        if next_reminder:
            # `create` commits the completion and the next one together.
            next_reminder = await self.repository.create(next_reminder)

        reminder = await self.repository.save(reminder)

        completed = (reminder, None)

        if next_reminder is None:
            return completed, None

        return completed, (next_reminder, reminder_status(next_reminder, mileage))

    async def delete(self, reminder_id: int, user_id: int) -> None:

        reminder = await self._get(reminder_id, user_id)

        await self.repository.delete(reminder)

    async def _get(self, reminder_id: int, user_id: int) -> Reminder:

        reminder = await self.repository.get_by_id(reminder_id)

        if not reminder or reminder.created_by_id != user_id:
            raise NotFoundException("Reminder not found")

        await self._require_owner(reminder.vehicle_id, user_id)

        return reminder

    async def _require_owner(self, vehicle_id: int, user_id: int) -> None:
        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

    async def _current_mileage(self, vehicle_id: int) -> int | None:
        vehicle = await self.vehicle_repository.get_by_id(vehicle_id)

        return vehicle.current_mileage if vehicle else None

    async def _with_status(self, reminder: Reminder) -> ReminderWithStatus:
        mileage = await self._current_mileage(reminder.vehicle_id)

        return reminder, reminder_status(reminder, mileage)

    @staticmethod
    def _next_mileage(reminder: Reminder, current_mileage: int | None) -> int | None:

        if not reminder.repeat_km:
            return None

        if current_mileage is not None:
            return current_mileage + reminder.repeat_km

        if reminder.due_mileage is not None:
            return reminder.due_mileage + reminder.repeat_km

        return None
