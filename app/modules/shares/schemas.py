from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class ShareCreate(BaseModel):
    expires_in_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="How long the link works",
    )


class ShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    token: str

    url: str = Field(description="The page to send to a buyer")
    pdf_path: str = Field(description="API path of the PDF version")

    expires_at: datetime
    revoked_at: datetime | None
    view_count: int
    last_viewed_at: datetime | None
    created_at: datetime

    @classmethod
    def build(cls, share: Any) -> "ShareResponse":

        fields = {
            name: getattr(share, name)
            for name in cls.model_fields
            if name not in ("url", "pdf_path")
        }

        return cls(
            **fields,
            url=f"{settings.frontend_url}/history/{share.token}",
            # Hard-coded prefix: app.main.API_PREFIX can't be imported here
            # without a circular import.
            pdf_path=f"/api/v1/public/history/{share.token}/pdf",
        )


# ---- the public history ------------------------------------------------------
# Deliberately its own set of schemas: nothing here may carry a user id,
# an email, or anything else that identifies an owner.

class PublicVehicle(BaseModel):
    name: str
    year: int
    make: str
    model: str
    vin: str
    registration_number: str | None
    current_mileage: int | None
    owner_count: int


class PublicServiceRecord(BaseModel):
    service_date: date
    odometer_reading: int | None
    service_type: str | None
    description: str
    cost: Decimal | None
    garage: str | None
    receipt_count: int


class PublicMileageReading(BaseModel):
    recorded_on: date
    odometer: int


class PublicHistory(BaseModel):
    vehicle: PublicVehicle
    service_records: list[PublicServiceRecord] = Field(description="Newest first")
    mileage: list[PublicMileageReading] = Field(description="Oldest first")
    total_spend: Decimal
    generated_at: datetime
    link_expires_at: datetime

    disclaimer: str = (
        "Records are entered by the vehicle's owners and are not "
        "independently verified."
    )
