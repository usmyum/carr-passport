from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.modules.shares.models import VehicleShare


async def share(client: AsyncClient, vehicle: dict, headers: dict, **body):
    return await client.post(
        f"/api/v1/shares/vehicle/{vehicle['id']}",
        json=body or None,
        headers=headers,
    )


async def test_public_history(
    client: AsyncClient,
    vehicle: dict,
    garage: dict,
    auth_headers: dict,
):
    record = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": "2026-02-10",
            "description": "Timing belt — replaced at 60k",
            "odometer_reading": 60_000,
            "cost": "450.00",
            "garage_id": garage["id"],
        },
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/receipts/service-record/{record.json()['id']}",
        files={"file": ("r.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_headers,
    )

    link = await share(client, vehicle, auth_headers)

    assert link.status_code == 201
    assert link.json()["url"].endswith(f"/history/{link.json()['token']}")

    # No auth header: anyone with the link.
    response = await client.get(f"/api/v1/public/history/{link.json()['token']}")

    assert response.status_code == 200

    body = response.json()

    assert body["vehicle"]["name"] == "2019 Toyota Corolla"
    assert body["vehicle"]["vin"] == vehicle["vin"]
    assert body["vehicle"]["current_mileage"] == 60_000
    assert body["vehicle"]["owner_count"] == 1
    assert body["service_records"][0]["garage"] == "Joe's Auto Shop"
    assert body["service_records"][0]["receipt_count"] == 1
    assert body["mileage"] == [{"recorded_on": "2026-02-10", "odometer": 60_000}]
    assert body["total_spend"] == "450.00"

    # Nothing identifying the owner leaks into the public page.
    assert "owner@example.com" not in response.text
    assert "created_by" not in response.text

    listed = await client.get(
        f"/api/v1/shares/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert listed.json()[0]["view_count"] == 1


async def test_public_history_pdf(
    client: AsyncClient,
    vehicle: dict,
    service_record: dict,
    auth_headers: dict,
):
    link = (await share(client, vehicle, auth_headers)).json()

    response = await client.get(link["pdf_path"])

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert vehicle["vin"] in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


async def test_revoked_link_stops_working(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    link = (await share(client, vehicle, auth_headers)).json()

    revoked = await client.delete(f"/api/v1/shares/{link['id']}", headers=auth_headers)

    assert revoked.status_code == 204

    response = await client.get(f"/api/v1/public/history/{link['token']}")

    assert response.status_code == 404


async def test_expired_link_stops_working(
    client: AsyncClient,
    db: AsyncSession,
    vehicle: dict,
    auth_headers: dict,
):
    link = (await share(client, vehicle, auth_headers, expires_in_days=7)).json()

    await db.execute(
        update(VehicleShare)
        .where(VehicleShare.id == link["id"])
        .values(expires_at=utc_now() - timedelta(minutes=1))
    )
    await db.commit()

    response = await client.get(f"/api/v1/public/history/{link['token']}")

    assert response.status_code == 404


async def test_selling_the_car_retires_the_sellers_links(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
    sell_vehicle,
):
    link = (await share(client, vehicle, auth_headers)).json()

    await sell_vehicle()

    response = await client.get(f"/api/v1/public/history/{link['token']}")

    assert response.status_code == 404


async def test_only_the_current_owner_can_share(
    client: AsyncClient,
    vehicle: dict,
    other_headers: dict,
):
    response = await share(client, vehicle, other_headers)

    assert response.status_code == 404


async def test_unknown_token(client: AsyncClient):
    response = await client.get("/api/v1/public/history/not-a-token")

    assert response.status_code == 404
