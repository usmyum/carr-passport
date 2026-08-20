from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.vehicle_models.models import VehicleModel


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    vin: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    current_mileage: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    model: Mapped["VehicleModel"] = relationship(
        "VehicleModel",
        back_populates="vehicles",
    )
