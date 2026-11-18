from datetime import date as date_type
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MileageSource(StrEnum):
    MANUAL = "manual"
    SERVICE_RECORD = "service_record"


class MileageLog(Base, TimestampMixin):
    """One odometer reading on one day.

    The vehicle's `current_mileage` is always the latest of these — it's
    kept in sync by `MileageLogService`, never set directly.
    """

    __tablename__ = "mileage_logs"

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

    # Set when the reading came from a service record's odometer field.
    # Unique: a record has at most one reading, and deleting the record
    # deletes the reading with it.
    service_record_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "service_records.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        unique=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    recorded_on: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )

    odometer: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MileageSource.MANUAL,
    )
