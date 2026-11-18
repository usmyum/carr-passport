from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.mileage_logs.repository import MileageLogRepository
from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.service import OwnershipService
from app.modules.shares.repository import HistoryRepository, ShareRepository
from app.modules.shares.schemas import PublicHistory, ShareCreate, ShareResponse
from app.modules.shares.service import ShareService
from app.modules.users.dependencies import CurrentUser
from app.modules.vehicles.repository import VehicleRepository
from app.shared.rate_limit import rate_limit

router = APIRouter(
    prefix="/shares",
    tags=["Sharing"],
)

# No login: anyone with the link. Rate-limited so tokens can't be guessed
# by brute force (they're 256-bit, but there's no reason to allow trying).
public_router = APIRouter(
    prefix="/public/history",
    tags=["Sharing"],
    dependencies=[Depends(rate_limit("public_history", 60, 60))],
)


def get_share_service(
    db: AsyncSession = Depends(get_db),
    ownership_service: OwnershipService = Depends(get_ownership_service),
) -> ShareService:

    return ShareService(
        repository=ShareRepository(db),
        history_repository=HistoryRepository(db),
        vehicle_repository=VehicleRepository(db),
        mileage_log_repository=MileageLogRepository(db),
        ownership_service=ownership_service,
    )


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a read-only link to this vehicle's history",
)
async def create_share(
    vehicle_id: int,
    current_user: CurrentUser,
    data: ShareCreate | None = None,
    service: ShareService = Depends(get_share_service),
):
    share = await service.create(
        vehicle_id,
        data or ShareCreate(),
        user_id=current_user.id,
    )

    return ShareResponse.build(share)


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=list[ShareResponse],
    summary="List the links you've made for a vehicle",
)
async def get_shares(
    vehicle_id: int,
    current_user: CurrentUser,
    service: ShareService = Depends(get_share_service),
):
    shares = await service.list_for_vehicle(vehicle_id, user_id=current_user.id)

    return [ShareResponse.build(share) for share in shares]


@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a link",
)
async def revoke_share(
    share_id: int,
    current_user: CurrentUser,
    service: ShareService = Depends(get_share_service),
):
    await service.revoke(share_id, user_id=current_user.id)


@public_router.get(
    "/{token}",
    response_model=PublicHistory,
    summary="A shared vehicle history (no login needed)",
)
async def get_public_history(
    token: str,
    service: ShareService = Depends(get_share_service),
):
    return await service.get_public_history(token)


@public_router.get(
    "/{token}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="A shared vehicle history as a PDF (no login needed)",
)
async def get_public_history_pdf(
    token: str,
    service: ShareService = Depends(get_share_service),
):
    content, filename = await service.get_public_pdf(token)

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
