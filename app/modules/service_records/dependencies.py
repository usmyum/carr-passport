"""`get_service_record_service`, shared with `receipts`.

A receipt's access rules are its service record's rules, so `receipts`
builds on `ServiceRecordService` rather than re-checking ownership itself.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.garages.repository import GarageRepository
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
from app.modules.service_records.repository import ServiceRecordRepository
from app.modules.service_records.service import ServiceRecordService


def get_service_record_service(
    db: AsyncSession = Depends(get_db),
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> ServiceRecordService:

    return ServiceRecordService(
        repository=ServiceRecordRepository(db),
        garage_repository=GarageRepository(db),
        ownership_service=ownership_service,
    )
