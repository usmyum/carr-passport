from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Reminder(Base, TimestampMixin):
    """Something the owner wants to do by a date, a mileage, or both
    ("oil change: every 12 months or 10,000 km, whichever comes first").

    Private to the owner who set it: a reminder is a to-do, not history,
    so it doesn't pass to the next owner.
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vehicles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    due_on: Mapped[date_type | None] = mapped_column(
        Date,
        nullable=True,
    )

    due_mileage: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # When set, completing the reminder schedules the next one this far
    # from the day (and mileage) it was done.
    repeat_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    repeat_km: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
