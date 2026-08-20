from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VehicleModelCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class VehicleModelUpdate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class VehicleModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    make_id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
