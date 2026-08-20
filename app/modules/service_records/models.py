from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.garages.models import Garage
    from app.modules.vehicles.models import Vehicle


class ServiceRecord(Base, TimestampMixin):
    __tablename__ = "service_records"

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

    garage_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "garages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    service_date: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )

    odometer_reading: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    service_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
    )

    garage: Mapped["Garage | None"] = relationship(
        "Garage",
    )
