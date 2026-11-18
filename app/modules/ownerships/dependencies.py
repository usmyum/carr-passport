"""`get_ownership_service`, shared with every module that checks vehicle access.

`vehicles`, `service_records` and `receipts` build their services on top of
this one, so it lives here rather than inside this module's router.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.ownerships.repository import (
    OwnershipTransferRepository,
    VehicleOwnershipRepository,
)
from app.modules.ownerships.service import OwnershipService


def get_ownership_service(
    db: AsyncSession = Depends(get_db),
) -> OwnershipService:

    return OwnershipService(
        repository=VehicleOwnershipRepository(db),
        transfer_repository=OwnershipTransferRepository(db),
    )
