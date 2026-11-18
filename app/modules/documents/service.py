from app.modules.documents.models import VehicleDocument
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import DocumentCreate, DocumentUpdate
from app.modules.ownerships.service import OwnershipService
from app.shared.exceptions import NotFoundException, ValidationException
from app.shared.storage import Storage, build_object_key, ensure_upload_allowed


class DocumentService:
    """Documents are private to whoever uploaded them (see the model).

    Uploading and editing need the current owner. After a sale the seller
    can still read — and delete — their own old documents.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        ownership_service: OwnershipService,
        storage: Storage,
    ):
        self.repository = repository
        self.ownership_service = ownership_service
        self.storage = storage

    async def upload(
        self,
        vehicle_id: int,
        data: DocumentCreate,
        filename: str,
        content_type: str,
        content: bytes,
        user_id: int,
    ) -> VehicleDocument:

        await self.ownership_service.require_access(
            vehicle_id,
            user_id,
            write=True,
        )

        self._ensure_dates_make_sense(data.issued_on, data.expires_on)

        ensure_upload_allowed(content_type, len(content))

        key = build_object_key("documents", filename)

        await self.storage.upload(key, content, content_type)

        document = VehicleDocument(
            vehicle_id=vehicle_id,
            created_by_id=user_id,
            file_key=key,
            original_filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            **data.model_dump(),
        )

        return await self.repository.create(document)

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
    ) -> list[VehicleDocument]:

        await self.ownership_service.require_access(vehicle_id, user_id)

        return await self.repository.list_for_vehicle(vehicle_id, user_id)

    async def get(self, document_id: int, user_id: int) -> VehicleDocument:

        document = await self.repository.get_by_id(document_id)

        # Someone else's document is as invisible as a missing one.
        if not document or document.created_by_id != user_id:
            raise NotFoundException("Document not found")

        return document

    async def get_download_url(self, document_id: int, user_id: int) -> str:

        document = await self.get(document_id, user_id)

        return await self.storage.get_url(document.file_key)

    async def update(
        self,
        document_id: int,
        data: DocumentUpdate,
        user_id: int,
    ) -> VehicleDocument:

        document = await self.get(document_id, user_id)

        await self.ownership_service.require_access(
            document.vehicle_id,
            user_id,
            write=True,
        )

        updates = data.model_dump(exclude_unset=True)

        if "kind" in updates and updates["kind"] is None:
            raise ValidationException("kind cannot be empty")

        self._ensure_dates_make_sense(
            updates.get("issued_on", document.issued_on),
            updates.get("expires_on", document.expires_on),
        )

        for field, value in updates.items():
            setattr(document, field, value)

        return await self.repository.save(document)

    async def delete(self, document_id: int, user_id: int) -> None:

        document = await self.get(document_id, user_id)

        await self.storage.delete(document.file_key)

        await self.repository.delete(document)

    @staticmethod
    def _ensure_dates_make_sense(issued_on, expires_on) -> None:

        if issued_on and expires_on and expires_on < issued_on:
            raise ValidationException("expires_on can't be before issued_on")
