from app.core.config import settings
from app.modules.receipts.models import Receipt
from app.modules.receipts.repository import ReceiptRepository
from app.modules.service_records.models import ServiceRecord
from app.modules.service_records.repository import ServiceRecordRepository
from app.modules.vehicles.repository import VehicleRepository
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
        service_record_repository: ServiceRecordRepository,
        vehicle_repository: VehicleRepository,
        storage: Storage,
    ):
        self.repository = repository
        self.service_record_repository = service_record_repository
        self.vehicle_repository = vehicle_repository
        self.storage = storage

    async def upload(
        self,
        service_record_id: int,
        filename: str,
        content_type: str,
        content: bytes,
        owner_id: int,
    ) -> Receipt:

        await self._get_owned_service_record(service_record_id, owner_id)

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
        owner_id: int,
    ) -> list[Receipt]:

        await self._get_owned_service_record(service_record_id, owner_id)

        return await self.repository.get_for_service_record(
            service_record_id
        )

    async def get_download_url(
        self,
        receipt_id: int,
        owner_id: int,
    ) -> str:

        receipt = await self._get_owned_receipt(receipt_id, owner_id)

        return await self.storage.get_url(receipt.file_key)

    async def delete(self, receipt_id: int, owner_id: int) -> None:

        receipt = await self._get_owned_receipt(receipt_id, owner_id)

        await self.storage.delete(receipt.file_key)

        await self.repository.delete(receipt)

    async def _get_owned_service_record(
        self,
        service_record_id: int,
        owner_id: int,
    ) -> ServiceRecord:
        """Ownership is two hops up: receipt -> service record -> vehicle."""

        record = await self.service_record_repository.get_by_id(
            service_record_id
        )

        if not record:
            raise NotFoundException("Service record not found")

        vehicle = await self.vehicle_repository.get_by_id(
            record.vehicle_id
        )

        if not vehicle or vehicle.owner_id != owner_id:
            raise NotFoundException("Service record not found")

        return record

    async def _get_owned_receipt(
        self,
        receipt_id: int,
        owner_id: int,
    ) -> Receipt:

        receipt = await self.repository.get_by_id(receipt_id)

        if not receipt:
            raise NotFoundException("Receipt not found")

        await self._get_owned_service_record(
            receipt.service_record_id,
            owner_id,
        )

        return receipt
