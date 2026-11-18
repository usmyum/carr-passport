from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MileageLogCreate(BaseModel):
    recorded_on: date

    odometer: int = Field(
        ge=0,
        le=10_000_000,
        description="Odometer reading on that day",
    )


class MileageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    service_record_id: int | None
    recorded_on: date
    odometer: int
    source: Literal["manual", "service_record"]
    created_at: datetime
