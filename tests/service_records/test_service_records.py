from httpx import AsyncClient


async def test_create_service_record(
        client: AsyncClient,
        vehicle: dict,
        garage: dict,
        auth_headers: dict,
):
    response = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "garage_id": garage["id"],
            "service_date": "2026-01-15",
            "odometer_reading": 85000,
            "service_type": "Oil change",
            "description": "Full synthetic oil + filter",
            "cost": "89.99",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["vehicle_id"] == vehicle["id"]
    assert body["garage_id"] == garage["id"]
    assert body["cost"] == "89.99"


async def test_create_service_record_without_garage(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    response = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-01-15",
            "description": "Tyre rotation",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["garage_id"] is None


async def test_create_service_record_for_someone_elses_vehicle_returns_404(
        client: AsyncClient,
        vehicle: dict,
):
    other_user = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "supersecret"},
    )
    other_headers = {
        "Authorization": f"Bearer {other_user.json()['access_token']}"
    }

    response = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-01-15",
            "description": "Should not be allowed",
        },
        headers=other_headers,
    )

    assert response.status_code == 404


async def test_list_service_records_for_vehicle(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    for description in ("Oil change", "Brake pads"):
        await client.post(
            f"/api/v1/service-records/vehicle/{vehicle['id']}",
            json={
                "service_date": "2026-01-15",
                "description": description,
            },
            headers=auth_headers,
        )

    response = await client.get(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_update_service_record(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    created = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-01-15",
            "description": "Oil change",
        },
        headers=auth_headers,
    )
    record_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/service-records/{record_id}",
        json={"odometer_reading": 90000},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["odometer_reading"] == 90000
    assert response.json()["description"] == "Oil change"


async def test_delete_service_record(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    created = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-01-15",
            "description": "Oil change",
        },
        headers=auth_headers,
    )
    record_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/service-records/{record_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204
