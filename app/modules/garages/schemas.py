from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GarageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class GarageUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class GarageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    address: str | None
    phone: str | None
    email: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
