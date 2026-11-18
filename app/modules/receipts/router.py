from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.receipts.repository import ReceiptRepository
from app.modules.receipts.schemas import (
    ReceiptDownloadUrlResponse,
    ReceiptResponse,
)
from app.modules.receipts.service import ReceiptService
from app.modules.service_records.dependencies import get_service_record_service
from app.modules.service_records.service import ServiceRecordService
from app.modules.users.dependencies import CurrentUser
from app.shared.storage import Storage, get_storage

router = APIRouter(
    prefix="/receipts",
    tags=["Receipts"],
)


def get_receipt_service(
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
    service_record_service: ServiceRecordService = Depends(
        get_service_record_service
    ),
) -> ReceiptService:

    return ReceiptService(
        repository=ReceiptRepository(db),
        service_record_service=service_record_service,
        storage=storage,
    )


@router.post(
    "/service-record/{service_record_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a receipt to a service record",
)
async def upload_receipt(
    service_record_id: int,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    service: ReceiptService = Depends(get_receipt_service),
):
    content = await file.read()

    return await service.upload(
        service_record_id,
        filename=file.filename or "receipt",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        user_id=current_user.id,
    )


@router.get(
    "/service-record/{service_record_id}",
    response_model=list[ReceiptResponse],
    summary="List a service record's receipts",
)
async def get_receipts(
    service_record_id: int,
    current_user: CurrentUser,
    service: ReceiptService = Depends(get_receipt_service),
):
    return await service.list_for_service_record(
        service_record_id,
        user_id=current_user.id,
    )


@router.get(
    "/{receipt_id}/download-url",
    response_model=ReceiptDownloadUrlResponse,
    summary="Get a temporary download link for a receipt",
)
async def get_receipt_download_url(
    receipt_id: int,
    current_user: CurrentUser,
    service: ReceiptService = Depends(get_receipt_service),
):
    url = await service.get_download_url(
        receipt_id,
        user_id=current_user.id,
    )

    return ReceiptDownloadUrlResponse(url=url)


@router.delete(
    "/{receipt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a receipt",
)
async def delete_receipt(
    receipt_id: int,
    current_user: CurrentUser,
    service: ReceiptService = Depends(get_receipt_service),
):
    await service.delete(receipt_id, user_id=current_user.id)
