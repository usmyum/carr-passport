from httpx import AsyncClient


async def test_create_vehicle(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": "jtdbr32e720012345",
            "registration_number": "abc-123",
            "current_mileage": 84000,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["year"] == 2019
    assert body["vin"] == "JTDBR32E720012345"
    assert body["registration_number"] == "ABC-123"
    assert body["access"] == "owner"


async def test_create_vehicle_without_token_returns_401(
        client: AsyncClient,
        vehicle_model: dict,
):
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
        },
    )

    assert response.status_code == 401


async def test_create_vehicle_with_unknown_model_returns_404(
        client: AsyncClient,
        auth_headers: dict,
):
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": 9999,
            "year": 2019,
            "vin": "JTDBR32E720012345",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


async def test_duplicate_vin_conflicts(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    payload = {
        "model_id": vehicle_model["id"],
        "year": 2019,
        "vin": "JTDBR32E720012345",
    }

    await client.post(
        "/api/v1/vehicles",
        json=payload,
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/vehicles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 409


async def test_list_vehicles_is_paginated(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    for year in (2018, 2019, 2020):
        await client.post(
            "/api/v1/vehicles",
            json={
                "model_id": vehicle_model["id"],
                "year": year,
                "vin": f"TESTVIN{year}",
            },
            headers=auth_headers,
        )

    response = await client.get(
        "/api/v1/vehicles",
        params={"page": 1, "size": 2},
        headers=auth_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2


async def test_list_vehicles_only_returns_your_own(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": "JTDBR32E720012345",
        },
        headers=auth_headers,
    )

    other_user = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "supersecret"},
    )
    other_headers = {
        "Authorization": f"Bearer {other_user.json()['access_token']}"
    }

    response = await client.get(
        "/api/v1/vehicles",
        headers=other_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_update_vehicle_mileage(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    created = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": "JTDBR32E720012345",
            "current_mileage": 84000,
        },
        headers=auth_headers,
    )

    vehicle_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/vehicles/{vehicle_id}",
        json={"current_mileage": 91000},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["current_mileage"] == 91000
    assert response.json()["year"] == 2019


async def test_delete_vehicle(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    created = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": "JTDBR32E720012345",
        },
        headers=auth_headers,
    )

    vehicle_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/vehicles/{vehicle_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204


async def test_impossible_year_is_rejected(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 1500,
            "vin": "JTDBR32E720012345",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_vin_is_required(
        client: AsyncClient,
        vehicle_model: dict,
        auth_headers: dict,
):
    for vin in (None, "     "):
        response = await client.post(
            "/api/v1/vehicles",
            json={
                "model_id": vehicle_model["id"],
                "year": 2019,
                "vin": vin,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


async def test_vin_cannot_be_cleared(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    response = await client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"vin": None},
        headers=auth_headers,
    )

    assert response.status_code == 422
