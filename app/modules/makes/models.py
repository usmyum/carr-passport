from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.vehicle_models.models import VehicleModel


class Make(Base, TimestampMixin):
    __tablename__ = "makes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    models: Mapped[list["VehicleModel"]] = relationship(
        "VehicleModel",
        back_populates="make",
        cascade="all, delete-orphan",
    )
