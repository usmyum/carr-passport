from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.mileage_logs.models import MileageLog
    from app.modules.ownerships.models import VehicleOwnership
    from app.modules.vehicle_models.models import VehicleModel


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    model_id: Mapped[int] = mapped_column(
        ForeignKey(
            "models.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # The vehicle's identity: its history follows the VIN from owner to
    # owner. Free-form up to 50 chars, not strict 17-char ISO VINs, because
    # older cars and Japanese imports carry chassis numbers instead.
    vin: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # The latest mileage log reading — kept in sync by `MileageLogService`.
    current_mileage: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    model: Mapped["VehicleModel"] = relationship(
        "VehicleModel",
        back_populates="vehicles",
    )

    # Who owns (and has owned) this vehicle lives in `ownerships`. Mapped
    # here only so a new vehicle and its first owner are saved together.
    # passive_deletes: the DB's ON DELETE CASCADE clears these, and nothing
    # is lazy-loaded (which would raise under an async session).
    ownerships: Mapped[list["VehicleOwnership"]] = relationship(
        "VehicleOwnership",
        passive_deletes=True,
        lazy="raise",
    )

    # Mapped only so the first odometer reading is saved with a new vehicle.
    mileage_logs: Mapped[list["MileageLog"]] = relationship(
        "MileageLog",
        passive_deletes=True,
        lazy="raise",
    )
