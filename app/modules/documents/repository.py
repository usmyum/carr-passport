from app.modules.documents.models import VehicleDocument
from app.shared.repository import BaseRepository


class DocumentRepository(BaseRepository[VehicleDocument]):
    model = VehicleDocument

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> list[VehicleDocument]:

        # Soonest expiry first; documents that never expire go last.
        return await self.list(
            VehicleDocument.vehicle_id == vehicle_id,
            VehicleDocument.created_by_id == user_id,
            order_by=(
                VehicleDocument.expires_on.asc().nulls_last(),
                VehicleDocument.created_at.desc(),
            ),
        )
