from datetime import date
from decimal import Decimal

from app.db.base import utc_now
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    DashboardResponse,
    DashboardVehicle,
    DueItem,
    LastService,
)
from app.modules.documents.models import DocumentKind, VehicleDocument
from app.modules.reminders.service import reminder_status
from app.modules.vehicles.models import Vehicle
from app.shared.due import DueStatus, due_status


def vehicle_name(vehicle: Vehicle) -> str:
    return f"{vehicle.year} {vehicle.model.make.name} {vehicle.model.name}"


def latest_documents(documents: list[VehicleDocument]) -> list[VehicleDocument]:
    """A renewed policy is usually uploaded as a new document, leaving the
    old one behind. Only the newest expiry per vehicle and kind counts, so
    last year's insurance doesn't show as expired forever. ("other" is a
    catch-all, so each of those counts on its own.)"""

    latest: dict[tuple[int, str], VehicleDocument] = {}
    others = []

    for document in documents:
        if document.kind == DocumentKind.OTHER:
            others.append(document)
            continue

        key = (document.vehicle_id, document.kind)

        if key not in latest or document.expires_on > latest[key].expires_on:
            latest[key] = document

    return [*latest.values(), *others]


def urgency(item: DueItem) -> tuple:
    """Overdue first, then by date (mileage-only items after dated ones)."""

    return (
        item.status != DueStatus.OVERDUE,
        item.due_on is None,
        item.due_on or date.max,
    )


class DashboardService:

    def __init__(self, repository: DashboardRepository):
        self.repository = repository

    async def get(self, user_id: int) -> DashboardResponse:

        vehicles = await self.repository.current_vehicles(user_id)
        ids = [vehicle.id for vehicle in vehicles]

        spend = await self.repository.spend_by_vehicle(ids, user_id)
        last_services = await self.repository.last_service_by_vehicle(ids)
        reminders = await self.repository.open_reminders(ids, user_id)
        documents = await self.repository.expiring_documents(ids, user_id)

        by_id = {vehicle.id: vehicle for vehicle in vehicles}
        today = utc_now().date()
        due: list[DueItem] = []

        for reminder in reminders:
            vehicle = by_id[reminder.vehicle_id]
            status = reminder_status(reminder, vehicle.current_mileage)

            if status != DueStatus.OK:
                due.append(
                    DueItem(
                        type="reminder",
                        id=reminder.id,
                        vehicle_id=vehicle.id,
                        vehicle_name=vehicle_name(vehicle),
                        title=reminder.title,
                        due_on=reminder.due_on,
                        due_mileage=reminder.due_mileage,
                        status=status,
                    )
                )

        for document in latest_documents(documents):
            status = due_status(today, due_on=document.expires_on)

            if status != DueStatus.OK:
                vehicle = by_id[document.vehicle_id]
                due.append(
                    DueItem(
                        type="document",
                        id=document.id,
                        vehicle_id=vehicle.id,
                        vehicle_name=vehicle_name(vehicle),
                        title=document.title or f"{document.kind.capitalize()} expires",
                        due_on=document.expires_on,
                        due_mileage=None,
                        status=status,
                    )
                )

        due.sort(key=urgency)

        summaries = [
            self._summarise(vehicle, spend, last_services, due)
            for vehicle in vehicles
        ]

        return DashboardResponse(
            vehicle_count=len(vehicles),
            total_spend=sum(spend.values(), Decimal(0)),
            due=due,
            vehicles=summaries,
        )

    @staticmethod
    def _summarise(vehicle, spend, last_services, due) -> DashboardVehicle:

        last = last_services.get(vehicle.id)
        mine = [item for item in due if item.vehicle_id == vehicle.id]

        return DashboardVehicle(
            id=vehicle.id,
            name=vehicle_name(vehicle),
            registration_number=vehicle.registration_number,
            current_mileage=vehicle.current_mileage,
            last_service=(
                LastService(
                    id=last.id,
                    service_date=last.service_date,
                    description=last.description,
                )
                if last
                else None
            ),
            total_spend=spend.get(vehicle.id, Decimal(0)),
            overdue_count=sum(item.status == DueStatus.OVERDUE for item in mine),
            due_soon_count=sum(item.status == DueStatus.DUE_SOON for item in mine),
        )
