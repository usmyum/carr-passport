from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MakeCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class MakeUpdate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class MakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime