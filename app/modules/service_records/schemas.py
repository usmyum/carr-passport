from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ServiceRecordCreate(BaseModel):
    garage_id: int | None = None

    service_date: date

    odometer_reading: int | None = Field(default=None, ge=0)

    service_type: str | None = Field(default=None, max_length=100)

    description: str = Field(min_length=1)

    cost: Decimal | None = Field(default=None, ge=0)


class ServiceRecordUpdate(BaseModel):
    garage_id: int | None = None

    service_date: date | None = None

    odometer_reading: int | None = Field(default=None, ge=0)

    service_type: str | None = Field(default=None, max_length=100)

    description: str | None = Field(default=None, min_length=1)

    cost: Decimal | None = Field(default=None, ge=0)


class ServiceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    garage_id: int | None
    service_date: date
    odometer_reading: int | None
    service_type: str | None
    description: str
    cost: Decimal | None
    created_at: datetime
    updated_at: datetime
