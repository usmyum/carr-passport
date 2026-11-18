from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utc_now


class VehicleOwnership(Base):
    """One person's period of owning one vehicle.

    The car's history belongs to the car, not to whoever owns it today —
    this table is what decides who can see it. `ended_at` is NULL for the
    current owner; a sale fills it in and opens a new row for the buyer.
    """

    __tablename__ = "vehicle_ownerships"

    __table_args__ = (
        # Exactly one current owner per vehicle, enforced by the DB rather
        # than trusted to the service layer.
        Index(
            "uq_vehicle_ownerships_current_owner",
            "vehicle_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

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

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class TransferStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class OwnershipTransfer(Base, TimestampMixin):
    """A seller's offer to hand a vehicle (and its history) to a buyer.

    Addressed by email rather than user id, so the buyer doesn't need an
    account yet when the seller starts it.
    """

    __tablename__ = "ownership_transfers"

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

    from_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    to_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Plain string, not a Postgres ENUM: adding a status later is then a
    # code change, not a migration.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TransferStatus.PENDING,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
