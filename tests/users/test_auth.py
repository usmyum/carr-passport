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
