from app.modules.receipts.models import Receipt
from app.shared.repository import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    model = Receipt

    async def get_for_service_record(
        self,
        service_record_id: int,
    ) -> list[Receipt]:

        return await self.list(
            Receipt.service_record_id == service_record_id,
            order_by=Receipt.created_at.desc(),
        )
