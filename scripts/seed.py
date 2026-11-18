"""Seed the running API with demo data so every endpoint has something to return.

Drives the real HTTP API rather than writing to the DB directly — every row
created here passes through the same validation and business logic (slug
generation, uniqueness checks, ownership) that a real client would trigger.
Requires the stack to already be up: `docker compose up -d`.

Usage:
    docker compose exec api python -m scripts.seed

Re-running is safe: makes, models, garages and the demo users are reused
(looked up first, created only if missing). Vehicles, service records and
receipts are NOT deduplicated — each run adds another batch of sample data,
so re-run whenever you want more of those to look at.
"""

import asyncio
import os
import random
from decimal import Decimal

import httpx
from faker import Faker

BASE_URL = os.environ.get(
    "SEED_BASE_URL",
    "http://localhost:8000/api/v1",
)

fake = Faker()

MAKES_AND_MODELS = {
    "Toyota": ["Corolla", "Camry", "RAV4"],
    "Honda": ["Civic", "Accord", "CR-V"],
    "Ford": ["Focus", "F-150", "Explorer"],
    "BMW": ["3 Series", "X5"],
    "Tesla": ["Model 3", "Model Y"],
}

SERVICE_TYPES = [
    "Oil change",
    "Brake service",
    "Tire rotation",
    "Annual inspection",
    "Battery replacement",
    "Coolant flush",
]

DEMO_USERS = [
    ("alice@example.com", "password123"),
    ("bob@example.com", "password123"),
]

VEHICLES_PER_USER = 3
RECORDS_PER_VEHICLE = (2, 4)
GARAGE_COUNT = 5


async def get_or_create_make(client: httpx.AsyncClient, name: str) -> dict:
    existing = await client.get("/makes")

    for make in existing.json():
        if make["name"] == name:
            return make

    response = await client.post("/makes", json={"name": name})
    response.raise_for_status()

    return response.json()


async def get_or_create_model(
        client: httpx.AsyncClient,
        make_id: int,
        name: str,
) -> dict:
    existing = await client.get("/models", params={"make_id": make_id})

    for model in existing.json():
        if model["name"] == name:
            return model

    response = await client.post(
        f"/models/make/{make_id}",
        json={"name": name},
    )
    response.raise_for_status()

    return response.json()


async def get_or_create_garage(client: httpx.AsyncClient, name: str) -> dict:
    existing = await client.get("/garages")

    for garage in existing.json():
        if garage["name"] == name:
            return garage

    response = await client.post(
        "/garages",
        json={
            "name": name,
            "address": fake.address().replace("\n", ", "),
            "phone": fake.phone_number(),
            "email": fake.company_email(),
        },
    )
    response.raise_for_status()

    return response.json()


async def get_or_create_user(
        client: httpx.AsyncClient,
        email: str,
        password: str,
) -> dict:
    """Register the demo user, or log in if a previous run already did."""

    register = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    if register.status_code == 201:
        return register.json()

    login = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    login.raise_for_status()

    return login.json()


async def create_vehicle(
        client: httpx.AsyncClient,
        headers: dict,
        model_id: int,
) -> dict:
    response = await client.post(
        "/vehicles",
        json={
            "model_id": model_id,
            "year": random.randint(2012, 2025),
            "vin": fake.unique.vin(),
            "registration_number": fake.unique.license_plate(),
            "current_mileage": random.randint(5_000, 150_000),
        },
        headers=headers,
    )
    response.raise_for_status()

    return response.json()


async def create_service_record(
        client: httpx.AsyncClient,
        headers: dict,
        vehicle_id: int,
        garage_id: int | None,
) -> dict:
    payload = {
        "garage_id": garage_id,
        "service_date": fake.date_between(
            start_date="-2y",
            end_date="today",
        ).isoformat(),
        "odometer_reading": random.randint(5_000, 150_000),
        "service_type": random.choice(SERVICE_TYPES),
        "description": fake.sentence(),
        "cost": str(Decimal(random.randrange(3000, 90000)) / 100),
    }

    response = await client.post(
        f"/service-records/vehicle/{vehicle_id}",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()

    return response.json()


async def upload_receipt(
        client: httpx.AsyncClient,
        headers: dict,
        record_id: int,
        description: str,
        cost: str,
) -> dict:
    content = f"Receipt for: {description}\nTotal: ${cost}\n".encode()

    response = await client.post(
        f"/receipts/service-record/{record_id}",
        files={"file": ("receipt.pdf", content, "application/pdf")},
        headers=headers,
    )
    response.raise_for_status()

    return response.json()


async def seed() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:

        health_url = BASE_URL.removesuffix("/api/v1") + "/health"

        try:
            await client.get(health_url)
        except httpx.ConnectError:
            raise SystemExit(
                f"Could not reach the API at {BASE_URL}. "
                "Is `docker compose up -d` running?"
            ) from None

        print(f"Seeding {BASE_URL} ...\n")

        makes = {}
        for make_name, model_names in MAKES_AND_MODELS.items():
            make = await get_or_create_make(client, make_name)
            models = [
                await get_or_create_model(client, make["id"], model_name)
                for model_name in model_names
            ]
            makes[make_name] = (make, models)

        model_pool = [
            model
            for make, models in makes.values()
            for model in models
        ]
        print(f"Makes/models ready: {len(makes)} makes, {len(model_pool)} models")

        garages = [
            await get_or_create_garage(client, fake.unique.company())
            for _ in range(GARAGE_COUNT)
        ]
        print(f"Garages ready: {len(garages)}")

        vehicle_count = 0
        record_count = 0
        receipt_count = 0

        for email, password in DEMO_USERS:

            tokens = await get_or_create_user(client, email, password)
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}

            for _ in range(VEHICLES_PER_USER):

                model = random.choice(model_pool)
                vehicle = await create_vehicle(client, headers, model["id"])
                vehicle_count += 1

                for _ in range(random.randint(*RECORDS_PER_VEHICLE)):

                    garage = (
                        random.choice(garages)
                        if random.random() < 0.7
                        else None
                    )

                    record = await create_service_record(
                        client,
                        headers,
                        vehicle["id"],
                        garage["id"] if garage else None,
                    )
                    record_count += 1

                    if random.random() < 0.5:
                        await upload_receipt(
                            client,
                            headers,
                            record["id"],
                            record["description"],
                            record["cost"],
                        )
                        receipt_count += 1

        print(f"Vehicles created: {vehicle_count}")
        print(f"Service records created: {record_count}")
        print(f"Receipts uploaded: {receipt_count}")

        print("\nDemo logins (POST /api/v1/auth/login):")
        for email, password in DEMO_USERS:
            print(f"  {email} / {password}")

        print(
            "\nSwagger UI is at /docs — log in above to get an access_token, "
            "then use the Authorize button to try the protected endpoints."
        )


if __name__ == "__main__":
    asyncio.run(seed())
