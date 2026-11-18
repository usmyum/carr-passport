from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class OwnershipTransferCreate(BaseModel):
    to_email: EmailStr


class OwnershipTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    to_email: str
    status: str
    expires_at: datetime
    completed_at: datetime | None
    created_at: datetime
