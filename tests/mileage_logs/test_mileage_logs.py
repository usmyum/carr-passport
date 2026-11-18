from httpx import AsyncClient


async def add_reading(
    client: AsyncClient,
    vehicle: dict,
    headers: dict,
    recorded_on: str,
    odometer: int,
):
    return await client.post(
        f"/api/v1/mileage-logs/vehicle/{vehicle['id']}",
        json={"recorded_on": recorded_on, "odometer": odometer},
        headers=headers,
    )


async def current_mileage(client: AsyncClient, vehicle: dict, headers: dict):
    response = await client.get(f"/api/v1/vehicles/{vehicle['id']}", headers=headers)

    return response.json()["current_mileage"]


async def test_reading_sets_current_mileage(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    response = await add_reading(client, vehicle, auth_headers, "2026-03-01", 42_000)

    assert response.status_code == 201
    assert response.json()["source"] == "manual"

    # An older reading is history; it doesn't move the current mileage back.
    await add_reading(client, vehicle, auth_headers, "2025-03-01", 30_000)

    assert await current_mileage(client, vehicle, auth_headers) == 42_000

    listed = await client.get(
        f"/api/v1/mileage-logs/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert [log["odometer"] for log in listed.json()["items"]] == [42_000, 30_000]


async def test_odometer_cannot_go_backwards(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    await add_reading(client, vehicle, auth_headers, "2026-03-01", 42_000)

    lower_later = await add_reading(client, vehicle, auth_headers, "2026-04-01", 41_000)
    higher_earlier = await add_reading(client, vehicle, auth_headers, "2026-02-01", 43_000)

    assert lower_later.status_code == 422
    assert "42,000" in lower_later.json()["error"]["message"]
    assert higher_earlier.status_code == 422


async def test_service_record_odometer_is_logged(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    record = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-05-01",
            "odometer_reading": 50_000,
            "description": "Brake pads",
        },
        headers=auth_headers,
    )

    assert record.status_code == 201
    assert await current_mileage(client, vehicle, auth_headers) == 50_000

    logs_url = f"/api/v1/mileage-logs/vehicle/{vehicle['id']}"
    logs = (await client.get(logs_url, headers=auth_headers)).json()["items"]

    assert logs[0]["source"] == "service_record"
    assert logs[0]["service_record_id"] == record.json()["id"]

    # Editing the record's odometer moves its reading too…
    await client.put(
        f"/api/v1/service-records/{record.json()['id']}",
        json={"odometer_reading": 51_000},
        headers=auth_headers,
    )

    assert await current_mileage(client, vehicle, auth_headers) == 51_000

    # …the reading can only be changed through the record…
    direct = await client.delete(
        f"/api/v1/mileage-logs/{logs[0]['id']}",
        headers=auth_headers,
    )

    assert direct.status_code == 409

    # …and deleting the record removes it.
    await client.delete(
        f"/api/v1/service-records/{record.json()['id']}",
        headers=auth_headers,
    )

    assert (await client.get(logs_url, headers=auth_headers)).json()["total"] == 0
    assert await current_mileage(client, vehicle, auth_headers) is None


async def test_service_record_with_contradicting_odometer_is_rejected(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    await add_reading(client, vehicle, auth_headers, "2026-03-01", 42_000)

    record = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-05-01",
            "odometer_reading": 4_200,
            "description": "Typo'd odometer",
        },
        headers=auth_headers,
    )

    assert record.status_code == 422

    records = await client.get(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert records.json()["total"] == 0


async def test_vehicle_mileage_field_logs_a_reading(
    client: AsyncClient,
    vehicle_model: dict,
    auth_headers: dict,
):
    created = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2020,
            "vin": "WVWZZZ1KZAW000001",
            "current_mileage": 10_000,
        },
        headers=auth_headers,
    )

    vehicle = created.json()

    updated = await client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"current_mileage": 12_500},
        headers=auth_headers,
    )

    assert updated.json()["current_mileage"] == 12_500

    logs = await client.get(
        f"/api/v1/mileage-logs/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert {log["odometer"] for log in logs.json()["items"]} == {10_000, 12_500}

    backwards = await client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"current_mileage": 9_000},
        headers=auth_headers,
    )

    assert backwards.status_code == 422


async def test_stranger_cannot_read_or_add_readings(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
    other_headers: dict,
):
    added = await add_reading(client, vehicle, auth_headers, "2026-03-01", 42_000)

    listed = await client.get(
        f"/api/v1/mileage-logs/vehicle/{vehicle['id']}",
        headers=other_headers,
    )
    created = await add_reading(client, vehicle, other_headers, "2026-04-01", 43_000)
    deleted = await client.delete(
        f"/api/v1/mileage-logs/{added.json()['id']}",
        headers=other_headers,
    )

    assert listed.status_code == 404
    assert created.status_code == 404
    assert deleted.status_code == 404
