"""Shared test fixtures.

Every test runs against `TEST_DATABASE_URL` with the schema rebuilt from
`Base.metadata`, so tests never see dev data and never depend on each other.

The test database must exist. Docker Compose creates it on a fresh volume; on
an existing one, create it by hand:

    docker compose exec postgres \\
        psql -U car_passport -d car_passport \\
        -c "CREATE DATABASE car_passport_test OWNER car_passport;"
"""

import re
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db import models  # noqa: F401  — registers every table on Base
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.shared.email import Email, EmailSender, get_email_sender
from app.shared.rate_limit import reset_rate_limits

TEST_DATABASE_URL = (
        settings.test_database_url
        or settings.database_url + "_test"
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def engine() -> AsyncGenerator:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=None,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


class Outbox(EmailSender):
    """Stands in for SMTP: keeps every email so tests can read the links."""

    def __init__(self):
        self.sent: list[Email] = []

    async def send(self, email: Email) -> None:
        self.sent.append(email)

    def latest_token(self, to: str) -> str:
        """The `?token=` from the newest email sent to `to`."""

        email = next(e for e in reversed(self.sent) if e.to == to)

        return re.search(r"token=([\w-]+)", email.body).group(1)


@pytest.fixture
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Every test starts with clean counters — all requests share one IP."""

    reset_rate_limits()


@pytest.fixture
async def client(
        db: AsyncSession,
        outbox: Outbox,
) -> AsyncGenerator[AsyncClient]:
    """An HTTP client wired to the app, sharing the test's session."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: outbox

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()


@pytest.fixture
async def make(client: AsyncClient) -> dict:
    """A persisted make, for tests that need something to hang a model off."""

    response = await client.post(
        "/api/v1/makes",
        json={"name": "Toyota"},
    )

    return response.json()


@pytest.fixture
async def vehicle_model(
        client: AsyncClient,
        make: dict,
) -> dict:
    response = await client.post(
        f"/api/v1/models/make/{make['id']}",
        json={"name": "Corolla"},
    )

    return response.json()


@pytest.fixture
async def garage(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/garages",
        json={"name": "Joe's Auto Shop"},
    )

    return response.json()


async def register_verified(
        client: AsyncClient,
        outbox: Outbox,
        email: str,
) -> dict:
    """Sign up and click the verification link, like a real user would."""

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret",
        },
    )

    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": outbox.latest_token(email)},
    )
    assert verified.status_code == 200

    return response.json()


@pytest.fixture
async def user(client: AsyncClient, outbox: Outbox) -> dict:
    """A registered, verified user with tokens, for tests that need auth."""

    return await register_verified(client, outbox, "owner@example.com")


@pytest.fixture
def auth_headers(user: dict) -> dict:
    return {"Authorization": f"Bearer {user['access_token']}"}


@pytest.fixture
async def other_headers(client: AsyncClient, outbox: Outbox) -> dict:
    """Auth headers for a second verified user — a buyer, or a stranger."""

    tokens = await register_verified(client, outbox, "other@example.com")

    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def vehicle(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
) -> dict:
    """A vehicle owned by the `user` fixture."""

    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": "JTDBR32E720012345",
        },
        headers=auth_headers,
    )

    return response.json()


@pytest.fixture
async def service_record(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
) -> dict:
    response = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-01-15",
            "description": "Oil change",
        },
        headers=auth_headers,
    )

    return response.json()
