from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalise_code(value: Any) -> Any:
    """Plates and VINs are compared for uniqueness, so store one casing.

    Runs before field validation, so length limits (and VIN being required)
    apply to the cleaned value — a VIN of only spaces is rejected.
    """

    if not isinstance(value, str):
        return value

    return value.strip().upper() or None


class VehicleCreate(BaseModel):
    model_id: int

    year: int = Field(
        ge=1886,
        le=2100,
        description="Model year",
    )

    vin: str = Field(
        min_length=5,
        max_length=50,
        description="VIN or chassis number — the vehicle's identity",
    )

    registration_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Number plate",
    )

    current_mileage: int | None = Field(
        default=None,
        ge=0,
        description="Latest known odometer reading",
    )

    @field_validator("vin", "registration_number", mode="before")
    @classmethod
    def clean_codes(cls, value: Any) -> Any:
        return normalise_code(value)


class VehicleUpdate(BaseModel):
    model_id: int | None = None

    year: int | None = Field(
        default=None,
        ge=1886,
        le=2100,
    )

    vin: str | None = Field(
        default=None,
        min_length=5,
        max_length=50,
    )

    registration_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    current_mileage: int | None = Field(
        default=None,
        ge=0,
    )

    @field_validator("vin", "registration_number", mode="before")
    @classmethod
    def clean_codes(cls, value: Any) -> Any:
        return normalise_code(value)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    year: int
    vin: str
    registration_number: str | None
    current_mileage: int | None

    access: Literal["owner", "past_owner"] = Field(
        description="Whether you own this vehicle now, or used to",
    )

    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, vehicle: Any, access: str) -> "VehicleResponse":
        """`access` isn't a column, so it's added alongside the ORM fields."""

        fields = {
            name: getattr(vehicle, name)
            for name in cls.model_fields
            if name != "access"
        }

        return cls(**fields, access=access)
