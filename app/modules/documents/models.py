from datetime import date as date_type
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utc_now
from app.shared.due import DueStatus, due_status


class DocumentKind(StrEnum):
    INSURANCE = "insurance"
    REGISTRATION = "registration"
    INSPECTION = "inspection"
    WARRANTY = "warranty"
    OTHER = "other"


class VehicleDocument(Base, TimestampMixin):
    """A paper that belongs with the car: insurance, registration, MOT…

    Unlike service records, documents are private to whoever uploaded them —
    an insurance policy or registration certificate carries the owner's name
    and address, so it doesn't pass to the next owner with the history.
    """

    __tablename__ = "vehicle_documents"

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

    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    issued_on: Mapped[date_type | None] = mapped_column(
        Date,
        nullable=True,
    )

    expires_on: Mapped[date_type | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    file_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    @property
    def expiry_status(self) -> DueStatus | None:
        if self.expires_on is None:
            return None

        return due_status(utc_now().date(), due_on=self.expires_on)
