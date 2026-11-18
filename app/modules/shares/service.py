import asyncio
from datetime import timedelta
from decimal import Decimal

from app.db.base import utc_now
from app.modules.mileage_logs.repository import MileageLogRepository
from app.modules.ownerships.service import OwnershipService
from app.modules.shares.models import VehicleShare
from app.modules.shares.pdf import render_history_pdf
from app.modules.shares.repository import HistoryRepository, ShareRepository
from app.modules.shares.schemas import (
    PublicHistory,
    PublicMileageReading,
    PublicServiceRecord,
    PublicVehicle,
    ShareCreate,
)
from app.modules.vehicles.repository import VehicleRepository
from app.shared.exceptions import NotFoundException
from app.shared.security import generate_one_time_token


class ShareService:

    def __init__(
        self,
        repository: ShareRepository,
        history_repository: HistoryRepository,
        vehicle_repository: VehicleRepository,
        mileage_log_repository: MileageLogRepository,
        ownership_service: OwnershipService,
    ):
        self.repository = repository
        self.history_repository = history_repository
        self.vehicle_repository = vehicle_repository
        self.mileage_log_repository = mileage_log_repository
        self.ownership_service = ownership_service

    # ---- the owner's side ---------------------------------------------------

    async def create(
        self,
        vehicle_id: int,
        data: ShareCreate,
        user_id: int,
    ) -> VehicleShare:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        share = VehicleShare(
            vehicle_id=vehicle_id,
            created_by_id=user_id,
            token=generate_one_time_token(),
            expires_at=utc_now() + timedelta(days=data.expires_in_days),
        )

        return await self.repository.create(share)

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> list[VehicleShare]:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        return await self.repository.list_for_vehicle(vehicle_id, user_id)

    async def revoke(self, share_id: int, user_id: int) -> None:

        share = await self.repository.get_by_id(share_id)

        if not share or share.created_by_id != user_id:
            raise NotFoundException("Share link not found")

        if share.revoked_at is None:
            share.revoked_at = utc_now()
            await self.repository.save(share)

    # ---- the public side (no login) -----------------------------------------

    async def get_public_history(self, token: str) -> PublicHistory:

        share = await self._get_active_share(token)

        share.view_count += 1
        share.last_viewed_at = utc_now()
        await self.repository.save(share)

        vehicle = await self.vehicle_repository.get_with_model(share.vehicle_id)
        records = await self.history_repository.records_with_receipt_counts(
            share.vehicle_id
        )
        readings = await self.mileage_log_repository.list_for_vehicle(
            share.vehicle_id
        )

        make = vehicle.model.make.name
        model = vehicle.model.name

        return PublicHistory(
            vehicle=PublicVehicle(
                name=f"{vehicle.year} {make} {model}",
                year=vehicle.year,
                make=make,
                model=model,
                vin=vehicle.vin,
                registration_number=vehicle.registration_number,
                current_mileage=vehicle.current_mileage,
                owner_count=await self.ownership_service.count_owners(vehicle.id),
            ),
            service_records=[
                PublicServiceRecord(
                    service_date=record.service_date,
                    odometer_reading=record.odometer_reading,
                    service_type=record.service_type,
                    description=record.description,
                    cost=record.cost,
                    garage=record.garage.name if record.garage else None,
                    receipt_count=receipt_count,
                )
                for record, receipt_count in records
            ],
            mileage=[
                PublicMileageReading(
                    recorded_on=reading.recorded_on,
                    odometer=reading.odometer,
                )
                for reading in readings
            ],
            total_spend=sum(
                (record.cost for record, _ in records if record.cost is not None),
                Decimal(0),
            ),
            generated_at=utc_now(),
            link_expires_at=share.expires_at,
        )

    async def get_public_pdf(self, token: str) -> tuple[bytes, str]:
        """The PDF bytes and a filename for the download."""

        history = await self.get_public_history(token)

        # Rendering is CPU work in a sync library — keep it off the loop.
        content = await asyncio.to_thread(render_history_pdf, history)

        return content, f"vehicle-history-{history.vehicle.vin}.pdf"

    async def _get_active_share(self, token: str) -> VehicleShare:

        share = await self.repository.get_by_token(token)

        # One answer for every way a link can be dead, so the response
        # doesn't reveal whether a token ever existed.
        if (
            not share
            or share.revoked_at is not None
            or share.expires_at <= utc_now()
            or not await self.ownership_service.is_current_owner(
                share.vehicle_id,
                share.created_by_id,
            )
        ):
            raise NotFoundException("This link is invalid or has expired")

        return share
