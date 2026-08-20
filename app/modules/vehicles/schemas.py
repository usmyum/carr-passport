from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalise_code(value: str | None) -> str | None:
    """Plates and VINs are compared for uniqueness, so store one casing."""

    if value is None:
        return None

    return value.strip().upper() or None


class VehicleCreate(BaseModel):
    model_id: int

    year: int = Field(
        ge=1886,
        le=2100,
        description="Model year",
    )

    vin: str | None = Field(
        default=None,
        min_length=5,
        max_length=50,
        description="Chassis / VIN number",
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

    @field_validator("vin", "registration_number")
    @classmethod
    def clean_codes(cls, value: str | None) -> str | None:
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

    @field_validator("vin", "registration_number")
    @classmethod
    def clean_codes(cls, value: str | None) -> str | None:
        return normalise_code(value)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    year: int
    vin: str | None
    registration_number: str | None
    current_mileage: int | None
    created_at: datetime
    updated_at: datetime
