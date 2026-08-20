"""Single import point for every ORM model.

Alembic's `env.py` imports this so autogenerate can see the full metadata.
Every new module must add its models here or migrations will silently miss
the new tables.
"""

from app.modules.garages.models import Garage
from app.modules.makes.models import Make
from app.modules.receipts.models import Receipt
from app.modules.service_records.models import ServiceRecord
from app.modules.users.models import User
from app.modules.vehicle_models.models import VehicleModel
from app.modules.vehicles.models import Vehicle

__all__ = [
    "Garage",
    "Make",
    "Receipt",
    "ServiceRecord",
    "User",
    "VehicleModel",
    "Vehicle",
]
