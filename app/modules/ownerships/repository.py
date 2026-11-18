from datetime import datetime

from sqlalchemy import func, select

from app.modules.ownerships.models import (
    OwnershipTransfer,
    TransferStatus,
    VehicleOwnership,
)
from app.shared.repository import BaseRepository


class VehicleOwnershipRepository(BaseRepository[VehicleOwnership]):
    model = VehicleOwnership

    async def get_current(self, vehicle_id: int) -> VehicleOwnership | None:
        return await self.find_one(
            VehicleOwnership.vehicle_id == vehicle_id,
            VehicleOwnership.ended_at.is_(None),
        )

    async def get_latest_for_user(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> VehicleOwnership | None:
        """The user's most recent period with this vehicle.

        Someone can sell a car and buy it back, so there may be several —
        the latest one is what decides their access today.
        """

        result = await self.db.execute(
            select(VehicleOwnership)
            .where(
                VehicleOwnership.vehicle_id == vehicle_id,
                VehicleOwnership.user_id == user_id,
            )
            # NULLs (= still the owner) sort first under DESC in Postgres.
            .order_by(VehicleOwnership.ended_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def count_for_vehicle(self, vehicle_id: int) -> int:
        return await self.count(VehicleOwnership.vehicle_id == vehicle_id)

    async def count_owners(self, vehicle_id: int) -> int:
        """Distinct people — someone who sold and bought back counts once."""

        result = await self.db.execute(
            select(func.count(func.distinct(VehicleOwnership.user_id)))
            .where(VehicleOwnership.vehicle_id == vehicle_id)
        )

        return result.scalar_one()


class OwnershipTransferRepository(BaseRepository[OwnershipTransfer]):
    model = OwnershipTransfer

    async def get_pending_for_vehicle(
        self,
        vehicle_id: int,
        now: datetime,
    ) -> OwnershipTransfer | None:

        return await self.find_one(
            OwnershipTransfer.vehicle_id == vehicle_id,
            OwnershipTransfer.status == TransferStatus.PENDING,
            OwnershipTransfer.expires_at > now,
        )

    async def list_incoming(
        self,
        email: str,
        now: datetime,
    ) -> list[OwnershipTransfer]:

        return await self.list(
            OwnershipTransfer.to_email == email,
            OwnershipTransfer.status == TransferStatus.PENDING,
            OwnershipTransfer.expires_at > now,
            order_by=OwnershipTransfer.created_at.desc(),
        )

    async def list_outgoing(self, user_id: int) -> list[OwnershipTransfer]:
        return await self.list(
            OwnershipTransfer.from_user_id == user_id,
            order_by=OwnershipTransfer.created_at.desc(),
        )
