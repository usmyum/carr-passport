from datetime import date, timedelta

from httpx import AsyncClient


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


async def upload_document(client, vehicle, headers, kind, expires_on):
    return await client.post(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        data={"kind": kind, "expires_on": expires_on},
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        headers=headers,
    )


async def test_empty_dashboard(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/dashboard", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "vehicle_count": 0,
        "total_spend": "0",
        "due": [],
        "vehicles": [],
    }


async def test_dashboard_summarises_vehicles_and_due_items(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    url = f"/api/v1/service-records/vehicle/{vehicle['id']}"

    await client.post(
        url,
        json={"service_date": "2026-01-10", "description": "Tyres", "cost": "300.00"},
        headers=auth_headers,
    )
    await client.post(
        url,
        json={
            "service_date": "2026-02-10",
            "description": "Oil change",
            "cost": "89.50",
            "odometer_reading": 40_000,
        },
        headers=auth_headers,
    )

    reminders = f"/api/v1/reminders/vehicle/{vehicle['id']}"

    await client.post(
        reminders,
        json={"title": "Service", "due_mileage": 40_500},
        headers=auth_headers,
    )
    await client.post(
        reminders,
        json={"title": "Wipers", "due_on": in_days(-2)},
        headers=auth_headers,
    )
    await client.post(
        reminders,
        json={"title": "Far away", "due_on": in_days(300)},
        headers=auth_headers,
    )

    # Last year's insurance was replaced by a new policy: only the new one
    # counts, so the expired one doesn't nag.
    await upload_document(client, vehicle, auth_headers, "insurance", in_days(-200))
    await upload_document(client, vehicle, auth_headers, "insurance", in_days(20))

    body = (await client.get("/api/v1/dashboard", headers=auth_headers)).json()

    assert body["vehicle_count"] == 1
    assert body["total_spend"] == "389.50"

    assert [(i["type"], i["title"], i["status"]) for i in body["due"]] == [
        ("reminder", "Wipers", "overdue"),
        ("document", "Insurance expires", "due_soon"),
        ("reminder", "Service", "due_soon"),
    ]

    summary = body["vehicles"][0]

    assert summary["name"] == "2019 Toyota Corolla"
    assert summary["current_mileage"] == 40_000
    assert summary["last_service"]["description"] == "Oil change"
    assert summary["overdue_count"] == 1
    assert summary["due_soon_count"] == 2


async def test_sold_vehicle_leaves_the_dashboard(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
    other_headers: dict,
    sell_vehicle,
):
    await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={"service_date": "2026-01-10", "description": "Tyres", "cost": "300.00"},
        headers=auth_headers,
    )

    await sell_vehicle()

    seller = (await client.get("/api/v1/dashboard", headers=auth_headers)).json()
    buyer = (await client.get("/api/v1/dashboard", headers=other_headers)).json()

    assert seller["vehicle_count"] == 0

    # The buyer sees the car and its last service, but the seller's
    # spending isn't theirs.
    assert buyer["vehicle_count"] == 1
    assert buyer["vehicles"][0]["last_service"]["description"] == "Tyres"
    assert buyer["total_spend"] == "0"
