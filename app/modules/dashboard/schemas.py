from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.due import DueStatus


class DueItem(BaseModel):
    """A reminder that's due, or a document that's expiring."""

    type: Literal["reminder", "document"]
    id: int
    vehicle_id: int
    vehicle_name: str
    title: str
    due_on: date | None
    due_mileage: int | None
    status: DueStatus


class LastService(BaseModel):
    id: int
    service_date: date
    description: str


class DashboardVehicle(BaseModel):
    id: int
    name: str = Field(description='e.g. "2019 Toyota Corolla"')
    registration_number: str | None
    current_mileage: int | None
    last_service: LastService | None
    total_spend: Decimal = Field(description="Costs on service records you added")
    overdue_count: int
    due_soon_count: int


class DashboardResponse(BaseModel):
    vehicle_count: int
    total_spend: Decimal

    due: list[DueItem] = Field(
        description="Overdue and due-soon items across all your vehicles, "
        "most urgent first",
    )

    vehicles: list[DashboardVehicle]
