"""`get_mileage_log_service`, shared with `vehicles` and `service_records`.

Both of them write odometer readings (the vehicle form's mileage field, a
service record's odometer), and every reading goes through this service so
`Vehicle.current_mileage` stays in step with the log.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.mileage_logs.repository import MileageLogRepository
from app.modules.mileage_logs.service import MileageLogService
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
from app.modules.vehicles.repository import VehicleRepository


def get_mileage_log_service(
    db: AsyncSession = Depends(get_db),
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> MileageLogService:

    return MileageLogService(
        repository=MileageLogRepository(db),
        vehicle_repository=VehicleRepository(db),
        ownership_service=ownership_service,
    )
