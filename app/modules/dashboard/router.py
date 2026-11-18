from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.service import DashboardService
from app.modules.users.dependencies import CurrentUser

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


def get_dashboard_service(
    db: AsyncSession = Depends(get_db),
) -> DashboardService:

    return DashboardService(repository=DashboardRepository(db))


@router.get(
    "",
    response_model=DashboardResponse,
    summary="What's due, what you've spent, and each car at a glance",
)
async def get_dashboard(
    current_user: CurrentUser,
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get(user_id=current_user.id)
