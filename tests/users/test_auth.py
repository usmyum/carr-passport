from httpx import AsyncClient


async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "supersecret"},
    )

    assert response.status_code == 201

    body = response.json()

    assert "access_token" in body
    assert "refresh_token" in body


async def test_duplicate_email_conflicts(client: AsyncClient, user: dict):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "supersecret"},
    )

    assert response.status_code == 409


async def test_login(client: AsyncClient, user: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "supersecret"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_with_wrong_password_returns_401(
        client: AsyncClient,
        user: dict,
):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_refresh_returns_new_access_token(
        client: AsyncClient,
        user: dict,
):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_get_me(client: AsyncClient, user: dict, auth_headers: dict):
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"


async def test_get_me_without_token_returns_401(client: AsyncClient):
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


async def test_get_me_with_garbage_token_returns_401(client: AsyncClient):
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


async def test_get_me_with_expired_token_returns_401(
        client: AsyncClient,
        user: dict,
):
    import jwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import settings

    expired_token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


async def test_get_me_with_refresh_token_returns_401(
        client: AsyncClient,
        user: dict,
):
    """A refresh token must not work as an access token."""

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user['refresh_token']}"},
    )

    assert response.status_code == 401
