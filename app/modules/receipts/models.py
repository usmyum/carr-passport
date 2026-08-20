from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.service_records.models import ServiceRecord


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    service_record_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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

    service_record: Mapped["ServiceRecord"] = relationship(
        "ServiceRecord",
    )
