from app.modules.reminders.models import Reminder
from app.shared.repository import BaseRepository


class ReminderRepository(BaseRepository[Reminder]):
    model = Reminder

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
        include_completed: bool = False,
    ) -> list[Reminder]:

        filters = [
            Reminder.vehicle_id == vehicle_id,
            Reminder.created_by_id == user_id,
        ]

        if not include_completed:
            filters.append(Reminder.completed_at.is_(None))

        return await self.list(
            *filters,
            order_by=(
                Reminder.completed_at.desc().nulls_first(),
                Reminder.due_on.asc().nulls_last(),
                Reminder.due_mileage.asc().nulls_last(),
            ),
        )
