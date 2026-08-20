from fastapi import FastAPI

from app.core.config import settings
from app.modules.garages.router import router as garages_router
from app.modules.makes.router import router as makes_router
from app.modules.receipts.router import router as receipts_router
from app.modules.service_records.router import router as service_records_router
from app.modules.users.router import auth_router, users_router
from app.modules.vehicle_models.router import router as vehicle_models_router
from app.modules.vehicles.router import router as vehicles_router
from app.shared.handlers import register_exception_handlers


API_PREFIX = "/api/v1"


app = FastAPI(
    title="Car Passport API",
    description=(
        "One place for a vehicle's whole life: services, repairs, receipts, "
        "mileage and documents, whichever garage did the work."
    ),
    version="0.1.0",
)


register_exception_handlers(app)


for router in (
    auth_router,
    users_router,
    makes_router,
    vehicle_models_router,
    vehicles_router,
    garages_router,
    service_records_router,
    receipts_router,
):
    app.include_router(
        router,
        prefix=API_PREFIX,
    )


@app.get(
    "/health",
    tags=["System"],
    summary="Liveness probe",
)
async def health():
    return {
        "status": "ok",
        "environment": settings.app_env,
    }
