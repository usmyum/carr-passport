from app.core.config import settings
from app.modules.receipts.models import Receipt
from app.modules.receipts.repository import ReceiptRepository
from app.modules.service_records.service import ServiceRecordService
from app.shared.exceptions import NotFoundException, ValidationException
from app.shared.storage import Storage, build_object_key

# A client-supplied content_type is just a claim, not a guarantee — this
# doesn't sniff the actual bytes. It's a floor (block obvious junk like
# executables), not a real security boundary.
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
}


class ReceiptService:

    def __init__(
        self,
        repository: ReceiptRepository,
        service_record_service: ServiceRecordService,
        storage: Storage,
    ):
        self.repository = repository
        self.service_record_service = service_record_service
        self.storage = storage

    async def upload(
        self,
        service_record_id: int,
        filename: str,
        content_type: str,
        content: bytes,
        user_id: int,
    ) -> Receipt:

        # Attaching a receipt changes the record, so it follows the record's
        # edit rules: current owner, and only records they added.
        await self.service_record_service.get_editable(
            service_record_id,
            user_id,
        )

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                f"Unsupported file type: {content_type}. "
                f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            )

        if len(content) > settings.max_upload_size_bytes:
            raise ValidationException(
                f"File exceeds the {settings.max_upload_size_mb}MB limit"
            )

        key = build_object_key("receipts", filename)

        await self.storage.upload(key, content, content_type)

        receipt = Receipt(
            service_record_id=service_record_id,
            file_key=key,
            original_filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )

        return await self.repository.create(receipt)

    async def list_for_service_record(
        self,
        service_record_id: int,
        user_id: int,
    ) -> list[Receipt]:

        await self.service_record_service.get(service_record_id, user_id)

        return await self.repository.get_for_service_record(
            service_record_id
        )

    async def get_download_url(
        self,
        receipt_id: int,
        user_id: int,
    ) -> str:

        receipt = await self._get_receipt(receipt_id)

        await self.service_record_service.get(
            receipt.service_record_id,
            user_id,
        )

        return await self.storage.get_url(receipt.file_key)

    async def delete(self, receipt_id: int, user_id: int) -> None:

        receipt = await self._get_receipt(receipt_id)

        await self.service_record_service.get_editable(
            receipt.service_record_id,
            user_id,
        )

        await self.storage.delete(receipt.file_key)

        await self.repository.delete(receipt)

    async def _get_receipt(self, receipt_id: int) -> Receipt:
        """Load a receipt. Callers check access via its service record —
        a record you can't see gives the same 404 as a missing receipt."""

        receipt = await self.repository.get_by_id(receipt_id)

        if not receipt:
            raise NotFoundException("Receipt not found")

        return receipt
