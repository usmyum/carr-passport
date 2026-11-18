"""When is something due? Shared by `documents` (expiry), `reminders` and
`dashboard`, so "due soon" means the same thing everywhere."""

from datetime import date, timedelta
from enum import StrEnum

DUE_SOON_DAYS = 30
DUE_SOON_KM = 1_000


class DueStatus(StrEnum):
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    OK = "ok"


def due_status(
    today: date,
    due_on: date | None = None,
    due_mileage: int | None = None,
    current_mileage: int | None = None,
) -> DueStatus:
    """Whichever comes first, date or mileage, decides.

    A mileage target can't be judged without a current reading, so it's
    ignored until the vehicle has one.
    """

    statuses = []

    if due_on is not None:
        if due_on < today:
            statuses.append(DueStatus.OVERDUE)
        elif due_on <= today + timedelta(days=DUE_SOON_DAYS):
            statuses.append(DueStatus.DUE_SOON)

    if due_mileage is not None and current_mileage is not None:
        if current_mileage >= due_mileage:
            statuses.append(DueStatus.OVERDUE)
        elif current_mileage >= due_mileage - DUE_SOON_KM:
            statuses.append(DueStatus.DUE_SOON)

    if DueStatus.OVERDUE in statuses:
        return DueStatus.OVERDUE

    if DueStatus.DUE_SOON in statuses:
        return DueStatus.DUE_SOON

    return DueStatus.OK
