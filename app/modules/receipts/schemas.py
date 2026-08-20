from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_record_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class ReceiptDownloadUrlResponse(BaseModel):
    url: str
