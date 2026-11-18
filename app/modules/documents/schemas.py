from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.documents.models import DocumentKind
from app.shared.due import DueStatus


class DocumentCreate(BaseModel):
    """The form fields sent alongside the uploaded file."""

    kind: DocumentKind
    title: str | None = Field(default=None, max_length=200)
    issued_on: date | None = None
    expires_on: date | None = None


class DocumentUpdate(BaseModel):
    kind: DocumentKind | None = None
    title: str | None = Field(default=None, max_length=200)
    issued_on: date | None = None
    expires_on: date | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    kind: DocumentKind
    title: str | None
    issued_on: date | None
    expires_on: date | None

    expiry_status: DueStatus | None = Field(
        description="overdue = expired, due_soon = expires within 30 days; "
        "null when the document doesn't expire",
    )

    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocumentDownloadUrlResponse(BaseModel):
    url: str
