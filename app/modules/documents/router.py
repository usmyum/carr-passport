from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.documents.models import DocumentKind
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentDownloadUrlResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.modules.documents.service import DocumentService
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
from app.modules.users.dependencies import CurrentUser
from app.shared.storage import Storage, get_storage

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_document_service(
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> DocumentService:

    return DocumentService(
        repository=DocumentRepository(db),
        ownership_service=ownership_service,
        storage=storage,
    )


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (insurance, registration, inspection…)",
)
async def upload_document(
    vehicle_id: int,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    kind: DocumentKind = Form(...),
    title: str | None = Form(default=None, max_length=200),
    issued_on: date | None = Form(default=None),
    expires_on: date | None = Form(default=None),
    service: DocumentService = Depends(get_document_service),
):
    content = await file.read()

    return await service.upload(
        vehicle_id,
        DocumentCreate(
            kind=kind,
            title=title,
            issued_on=issued_on,
            expires_on=expires_on,
        ),
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        user_id=current_user.id,
    )


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=list[DocumentResponse],
    summary="List your documents for a vehicle, soonest expiry first",
)
async def get_documents(
    vehicle_id: int,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    return await service.list_for_vehicle(vehicle_id, user_id=current_user.id)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document",
)
async def get_document(
    document_id: int,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    return await service.get(document_id, user_id=current_user.id)


@router.get(
    "/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    summary="Get a temporary download link for a document",
)
async def get_document_download_url(
    document_id: int,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    url = await service.get_download_url(document_id, user_id=current_user.id)

    return DocumentDownloadUrlResponse(url=url)


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update a document's details (e.g. a renewed expiry date)",
)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    return await service.update(document_id, data, user_id=current_user.id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: int,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    await service.delete(document_id, user_id=current_user.id)
