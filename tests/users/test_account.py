"""Email verification, password reset, refresh-token rotation, rate limits."""

from httpx import AsyncClient

NEW_EMAIL = "new@example.com"


async def register(client: AsyncClient, email: str = NEW_EMAIL) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret"},
    )
    assert response.status_code == 201

    return response.json()


def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---- email verification ------------------------------------------------------

async def test_register_sends_verification_email(client: AsyncClient, outbox):
    tokens = await register(client)

    assert [e.to for e in outbox.sent] == [NEW_EMAIL]
    assert "/verify-email?token=" in outbox.sent[0].body

    me = await client.get("/api/v1/users/me", headers=bearer(tokens))

    assert me.json()["email_verified"] is False


async def test_verify_email(client: AsyncClient, outbox):
    tokens = await register(client)

    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": outbox.latest_token(NEW_EMAIL)},
    )

    assert response.status_code == 200
    assert response.json()["email_verified"] is True

    me = await client.get("/api/v1/users/me", headers=bearer(tokens))

    assert me.json()["email_verified"] is True


async def test_verification_link_works_once(client: AsyncClient, outbox):
    await register(client)
    token = outbox.latest_token(NEW_EMAIL)

    await client.post("/api/v1/auth/verify-email", json={"token": token})
    again = await client.post("/api/v1/auth/verify-email", json={"token": token})

    assert again.status_code == 422


async def test_resend_verification_retires_the_old_link(client: AsyncClient, outbox):
    tokens = await register(client)
    old_token = outbox.latest_token(NEW_EMAIL)

    resent = await client.post(
        "/api/v1/auth/resend-verification",
        headers=bearer(tokens),
    )

    assert resent.status_code == 202
    assert len(outbox.sent) == 2

    old = await client.post("/api/v1/auth/verify-email", json={"token": old_token})
    new = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": outbox.latest_token(NEW_EMAIL)},
    )

    assert old.status_code == 422
    assert new.status_code == 200


async def test_resend_verification_when_already_verified_conflicts(
        client: AsyncClient,
        auth_headers: dict,
):
    response = await client.post(
        "/api/v1/auth/resend-verification",
        headers=auth_headers,
    )

    assert response.status_code == 409


async def test_garbage_verification_token_is_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": "not-a-real-token"},
    )

    assert response.status_code == 422


# ---- password reset ----------------------------------------------------------

async def test_forgot_password_for_unknown_email_looks_the_same(
        client: AsyncClient,
        outbox,
):
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 202
    assert outbox.sent == []


async def test_reset_password(client: AsyncClient, outbox, user: dict):
    await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "OWNER@example.com"},
    )

    token = outbox.latest_token("owner@example.com")

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "brand-new-password"},
    )

    assert reset.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "supersecret"},
    )
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "brand-new-password"},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200

    # Every session from before the reset is logged out…
    old_session = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    assert old_session.status_code == 401

    # …and the link can't be used a second time.
    reuse = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "another-password"},
    )

    assert reuse.status_code == 422


async def test_reset_password_also_verifies_email(client: AsyncClient, outbox):
    await register(client)

    await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": NEW_EMAIL},
    )

    await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": outbox.latest_token(NEW_EMAIL),
            "new_password": "brand-new-password",
        },
    )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": NEW_EMAIL, "password": "brand-new-password"},
    )
    me = await client.get("/api/v1/users/me", headers=bearer(login.json()))

    assert me.json()["email_verified"] is True


async def test_verification_token_cannot_reset_password(client: AsyncClient, outbox):
    await register(client)

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": outbox.latest_token(NEW_EMAIL),
            "new_password": "brand-new-password",
        },
    )

    assert response.status_code == 422


# ---- refresh tokens ----------------------------------------------------------

async def test_refresh_rotates_the_refresh_token(client: AsyncClient, user: dict):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != user["refresh_token"]

    me = await client.get("/api/v1/users/me", headers=bearer(response.json()))

    assert me.status_code == 200


async def test_reused_refresh_token_logs_out_the_whole_session(
        client: AsyncClient,
        user: dict,
):
    rotated = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    # Someone replays the old token (e.g. it was stolen)…
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    assert replay.status_code == 401

    # …so the legitimate newer token is dead too, and the user logs in again.
    newer = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated.json()["refresh_token"]},
    )

    assert newer.status_code == 401


async def test_reuse_only_affects_that_session(client: AsyncClient, user: dict):
    """A replay on one device doesn't log out a separate login."""

    other_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "supersecret"},
    )

    await client.post("/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]})
    await client.post("/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]})

    other = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": other_login.json()["refresh_token"]},
    )

    assert other.status_code == 200


async def test_logout(client: AsyncClient, user: dict):
    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": user["refresh_token"]},
    )

    assert logout.status_code == 204

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user["refresh_token"]},
    )

    assert refresh.status_code == 401


# ---- rate limiting & request IDs ---------------------------------------------

async def test_login_is_rate_limited(client: AsyncClient):
    payload = {"email": "nobody@example.com", "password": "wrong"}

    statuses = [
        (await client.post("/api/v1/auth/login", json=payload)).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429

    blocked = await client.post("/api/v1/auth/login", json=payload)

    assert blocked.json()["error"]["code"] == "rate_limited"


async def test_responses_carry_a_request_id(client: AsyncClient):
    generated = await client.get("/health")
    echoed = await client.get("/health", headers={"X-Request-ID": "abc123"})

    assert len(generated.headers["X-Request-ID"]) == 32
    assert echoed.headers["X-Request-ID"] == "abc123"
