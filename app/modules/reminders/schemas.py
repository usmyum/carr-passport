from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.due import DueStatus


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = None

    due_on: date | None = None
    due_mileage: int | None = Field(default=None, ge=0)

    repeat_months: int | None = Field(default=None, ge=1, le=120)
    repeat_km: int | None = Field(default=None, ge=100, le=1_000_000)

    @model_validator(mode="after")
    def needs_a_target(self) -> "ReminderCreate":

        if self.due_on is None and self.due_mileage is None:
            raise ValueError("Set due_on, due_mileage, or both")

        return self


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None

    due_on: date | None = None
    due_mileage: int | None = Field(default=None, ge=0)

    repeat_months: int | None = Field(default=None, ge=1, le=120)
    repeat_km: int | None = Field(default=None, ge=100, le=1_000_000)


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    title: str
    notes: str | None
    due_on: date | None
    due_mileage: int | None
    repeat_months: int | None
    repeat_km: int | None
    completed_at: datetime | None

    status: DueStatus | None = Field(
        description="null once completed",
    )

    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, reminder: Any, status: DueStatus | None) -> "ReminderResponse":
        """`status` depends on the vehicle's mileage, so it's passed in."""

        fields = {
            name: getattr(reminder, name)
            for name in cls.model_fields
            if name != "status"
        }

        return cls(**fields, status=status)


class ReminderCompleteResponse(BaseModel):
    completed: ReminderResponse

    next: ReminderResponse | None = Field(
        description="The next occurrence, for repeating reminders",
    )
