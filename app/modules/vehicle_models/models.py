from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.makes.models import Make
    from app.modules.vehicles.models import Vehicle


class VehicleModel(Base, TimestampMixin):
    __tablename__ = "models"

    __table_args__ = (
        UniqueConstraint(
            "make_id",
            "name",
            name="uq_models_make_name",
        ),
        UniqueConstraint(
            "make_id",
            "slug",
            name="uq_models_make_slug",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    make_id: Mapped[int] = mapped_column(
        ForeignKey(
            "makes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    make: Mapped["Make"] = relationship(
        "Make",
        back_populates="models",
    )

    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle",
        back_populates="model",
    )
