from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class VehicleShare(Base, TimestampMixin):
    """A read-only public link to a vehicle's history, e.g. for a buyer.

    The token is the whole credential (like a "anyone with the link" doc),
    so it's long and random. It's stored as-is rather than hashed so the
    owner can copy the link again later; revoking it is one call.

    A link only works while its creator still owns the car — selling the
    car silently retires every link the seller made.
    """

    __tablename__ = "vehicle_shares"

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

    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
