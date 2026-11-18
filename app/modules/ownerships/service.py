from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.db.base import utc_now
from app.modules.ownerships.models import (
    OwnershipTransfer,
    TransferStatus,
    VehicleOwnership,
)
from app.modules.ownerships.repository import (
    OwnershipTransferRepository,
    VehicleOwnershipRepository,
)
from app.modules.ownerships.schemas import OwnershipTransferCreate
from app.modules.users.models import User
from app.shared.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)

TRANSFER_EXPIRY = timedelta(days=14)


@dataclass(frozen=True)
class VehicleAccess:
    """What one user may do with one vehicle."""

    is_current_owner: bool

    # Past owners see the history up to the day they sold, nothing after.
    # None means no cutoff (the current owner sees everything).
    visible_until: date | None

    @classmethod
    def from_ended_at(cls, ended_at: datetime | None) -> "VehicleAccess":
        """Access implied by the end of the user's latest ownership period."""

        if ended_at is None:
            return cls(is_current_owner=True, visible_until=None)

        return cls(is_current_owner=False, visible_until=ended_at.date())

    @property
    def role(self) -> str:
        return "owner" if self.is_current_owner else "past_owner"

    def can_see(self, service_date: date) -> bool:
        return self.visible_until is None or service_date <= self.visible_until


class OwnershipService:
    """The one place that answers "can this user see / change this vehicle?".

    `vehicles`, `service_records` and `receipts` all go through
    `require_access` instead of each checking ownership their own way.
    """

    def __init__(
        self,
        repository: VehicleOwnershipRepository,
        transfer_repository: OwnershipTransferRepository,
    ):
        self.repository = repository
        self.transfer_repository = transfer_repository

    async def require_access(
        self,
        vehicle_id: int,
        user_id: int,
        write: bool = False,
    ) -> VehicleAccess:

        ownership = await self.repository.get_latest_for_user(
            vehicle_id,
            user_id,
        )

        # Never owned it: same 404 as a vehicle that doesn't exist, so the
        # API never confirms someone else's vehicle is there.
        if not ownership:
            raise NotFoundException("Vehicle not found")

        access = VehicleAccess.from_ended_at(ownership.ended_at)

        # A past owner already knows the car exists, so a write attempt gets
        # an honest 403 rather than a 404.
        if write and not access.is_current_owner:
            raise ForbiddenException(
                "Only the current owner can change this vehicle"
            )

        return access

    async def has_changed_hands(self, vehicle_id: int) -> bool:
        return await self.repository.count_for_vehicle(vehicle_id) > 1

    # ---- transfers ---------------------------------------------------------

    async def start_transfer(
        self,
        vehicle_id: int,
        data: OwnershipTransferCreate,
        user: User,
    ) -> OwnershipTransfer:

        await self.require_access(vehicle_id, user.id, write=True)

        self._ensure_verified(user)

        to_email = data.to_email.strip().lower()

        if to_email == user.email:
            raise ValidationException("You already own this vehicle")

        now = utc_now()

        if await self.transfer_repository.get_pending_for_vehicle(
            vehicle_id,
            now,
        ):
            raise ConflictException(
                "This vehicle already has a pending transfer. "
                "Cancel it before starting a new one."
            )

        transfer = OwnershipTransfer(
            vehicle_id=vehicle_id,
            from_user_id=user.id,
            to_email=to_email,
            status=TransferStatus.PENDING,
            expires_at=now + TRANSFER_EXPIRY,
        )

        return await self.transfer_repository.create(transfer)

    async def list_incoming(self, user: User) -> list[OwnershipTransfer]:
        return await self.transfer_repository.list_incoming(
            user.email,
            utc_now(),
        )

    async def list_outgoing(self, user: User) -> list[OwnershipTransfer]:
        return await self.transfer_repository.list_outgoing(user.id)

    async def accept(
        self,
        transfer_id: int,
        user: User,
    ) -> OwnershipTransfer:

        transfer = await self._get_incoming(transfer_id, user)

        # Transfers are addressed by email, so the buyer must prove they own
        # it — otherwise anyone could sign up with that address and accept.
        self._ensure_verified(user)

        current = await self.repository.get_current(transfer.vehicle_id)

        # The seller must still own the car — guards against a transfer
        # that was overtaken by something else.
        if not current or current.user_id != transfer.from_user_id:
            raise ConflictException("This transfer is no longer valid")

        now = utc_now()

        current.ended_at = now

        transfer.status = TransferStatus.ACCEPTED
        transfer.completed_at = now

        # `create` commits the whole session: the seller's ownership ending,
        # the transfer closing and the buyer's ownership starting all land
        # in one transaction, or none of them do.
        await self.repository.create(
            VehicleOwnership(
                vehicle_id=transfer.vehicle_id,
                user_id=user.id,
                started_at=now,
            )
        )

        return transfer

    async def decline(
        self,
        transfer_id: int,
        user: User,
    ) -> OwnershipTransfer:

        transfer = await self._get_incoming(transfer_id, user)

        transfer.status = TransferStatus.DECLINED
        transfer.completed_at = utc_now()

        return await self.transfer_repository.save(transfer)

    async def cancel(
        self,
        transfer_id: int,
        user: User,
    ) -> OwnershipTransfer:

        transfer = await self.transfer_repository.get_by_id(transfer_id)

        if not transfer or transfer.from_user_id != user.id:
            raise NotFoundException("Transfer not found")

        self._ensure_pending(transfer)

        transfer.status = TransferStatus.CANCELLED
        transfer.completed_at = utc_now()

        return await self.transfer_repository.save(transfer)

    async def _get_incoming(
        self,
        transfer_id: int,
        user: User,
    ) -> OwnershipTransfer:

        transfer = await self.transfer_repository.get_by_id(transfer_id)

        if not transfer or transfer.to_email != user.email:
            raise NotFoundException("Transfer not found")

        self._ensure_pending(transfer)

        return transfer

    @staticmethod
    def _ensure_verified(user: User) -> None:

        if not user.is_email_verified:
            raise ForbiddenException(
                "Verify your email address before transferring a vehicle"
            )

    @staticmethod
    def _ensure_pending(transfer: OwnershipTransfer) -> None:

        if transfer.status != TransferStatus.PENDING:
            raise ConflictException(f"This transfer is already {transfer.status}")

        if transfer.expires_at <= utc_now():
            raise ConflictException("This transfer has expired")
