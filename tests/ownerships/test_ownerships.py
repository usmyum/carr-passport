from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.modules.ownerships.models import OwnershipTransfer

BUYER_EMAIL = "other@example.com"  # the `other_headers` fixture's user


async def sell(
        client: AsyncClient,
        vehicle: dict,
        seller_headers: dict,
        buyer_headers: dict,
) -> dict:
    """Run a full transfer: the seller offers, the buyer accepts."""

    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": BUYER_EMAIL},
        headers=seller_headers,
    )
    assert offer.status_code == 201

    accepted = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/accept",
        headers=buyer_headers,
    )
    assert accepted.status_code == 200

    return accepted.json()


async def test_transfer_hands_vehicle_to_buyer(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
        other_headers: dict,
):
    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": BUYER_EMAIL.upper()},
        headers=auth_headers,
    )

    assert offer.status_code == 201
    assert offer.json()["status"] == "pending"

    incoming = await client.get(
        "/api/v1/transfers/incoming",
        headers=other_headers,
    )

    assert [t["id"] for t in incoming.json()] == [offer.json()["id"]]

    accepted = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/accept",
        headers=other_headers,
    )

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    buyer_vehicles = await client.get("/api/v1/vehicles", headers=other_headers)

    assert [v["id"] for v in buyer_vehicles.json()["items"]] == [vehicle["id"]]
    assert buyer_vehicles.json()["items"][0]["access"] == "owner"

    seller_current = await client.get("/api/v1/vehicles", headers=auth_headers)

    assert seller_current.json()["total"] == 0


async def test_past_owner_keeps_read_only_access(
        client: AsyncClient,
        vehicle: dict,
        service_record: dict,
        auth_headers: dict,
        other_headers: dict,
):
    await sell(client, vehicle, auth_headers, other_headers)

    past = await client.get(
        "/api/v1/vehicles",
        params={"include_past": True},
        headers=auth_headers,
    )

    assert past.json()["items"][0]["access"] == "past_owner"

    detail = await client.get(
        f"/api/v1/vehicles/{vehicle['id']}",
        headers=auth_headers,
    )

    assert detail.status_code == 200
    assert detail.json()["access"] == "past_owner"

    # Their own pre-sale record is still readable…
    record = await client.get(
        f"/api/v1/service-records/{service_record['id']}",
        headers=auth_headers,
    )

    assert record.status_code == 200

    # …but nothing can be changed any more.
    edit_vehicle = await client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"current_mileage": 1},
        headers=auth_headers,
    )
    edit_record = await client.put(
        f"/api/v1/service-records/{service_record['id']}",
        json={"description": "Rewritten"},
        headers=auth_headers,
    )
    add_record = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={"service_date": "2026-01-20", "description": "Sneaky"},
        headers=auth_headers,
    )

    assert edit_vehicle.status_code == 403
    assert edit_record.status_code == 403
    assert add_record.status_code == 403


async def test_past_owner_does_not_see_records_after_the_sale(
        client: AsyncClient,
        vehicle: dict,
        service_record: dict,
        auth_headers: dict,
        other_headers: dict,
):
    await sell(client, vehicle, auth_headers, other_headers)

    after_sale = await client.post(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        json={
            "service_date": (date.today() + timedelta(days=2)).isoformat(),
            "description": "New owner's first service",
        },
        headers=other_headers,
    )

    assert after_sale.status_code == 201

    seller_list = await client.get(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert [r["id"] for r in seller_list.json()["items"]] == [service_record["id"]]

    seller_detail = await client.get(
        f"/api/v1/service-records/{after_sale.json()['id']}",
        headers=auth_headers,
    )

    assert seller_detail.status_code == 404

    # The buyer sees the whole history, theirs and the seller's.
    buyer_list = await client.get(
        f"/api/v1/service-records/vehicle/{vehicle['id']}",
        headers=other_headers,
    )

    assert buyer_list.json()["total"] == 2


async def test_new_owner_cannot_rewrite_previous_owners_records(
        client: AsyncClient,
        vehicle: dict,
        service_record: dict,
        auth_headers: dict,
        other_headers: dict,
):
    await sell(client, vehicle, auth_headers, other_headers)

    edit = await client.put(
        f"/api/v1/service-records/{service_record['id']}",
        json={"description": "Never happened"},
        headers=other_headers,
    )
    delete = await client.delete(
        f"/api/v1/service-records/{service_record['id']}",
        headers=other_headers,
    )
    attach = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("r.pdf", b"%PDF-1.4", "application/pdf")},
        headers=other_headers,
    )

    assert edit.status_code == 403
    assert delete.status_code == 403
    assert attach.status_code == 403


async def test_vehicle_that_changed_hands_cannot_be_deleted(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
        other_headers: dict,
):
    await sell(client, vehicle, auth_headers, other_headers)

    response = await client.delete(
        f"/api/v1/vehicles/{vehicle['id']}",
        headers=other_headers,
    )

    assert response.status_code == 409


async def test_stranger_cannot_transfer_or_accept(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
        other_headers: dict,
):
    steal = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": BUYER_EMAIL},
        headers=other_headers,
    )

    assert steal.status_code == 404

    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": "someone-else@example.com"},
        headers=auth_headers,
    )

    accept = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/accept",
        headers=other_headers,
    )

    assert accept.status_code == 404


async def test_only_one_pending_transfer_at_a_time(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    url = f"/api/v1/transfers/vehicle/{vehicle['id']}"

    first = await client.post(url, json={"to_email": "a@example.com"}, headers=auth_headers)
    second = await client.post(url, json={"to_email": "b@example.com"}, headers=auth_headers)

    assert second.status_code == 409

    cancelled = await client.post(
        f"/api/v1/transfers/{first.json()['id']}/cancel",
        headers=auth_headers,
    )

    assert cancelled.json()["status"] == "cancelled"

    retry = await client.post(url, json={"to_email": "b@example.com"}, headers=auth_headers)

    assert retry.status_code == 201


async def test_declined_transfer_leaves_seller_as_owner(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
        other_headers: dict,
):
    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": BUYER_EMAIL},
        headers=auth_headers,
    )

    declined = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/decline",
        headers=other_headers,
    )

    assert declined.json()["status"] == "declined"

    seller = await client.get(
        f"/api/v1/vehicles/{vehicle['id']}",
        headers=auth_headers,
    )

    assert seller.json()["access"] == "owner"


async def test_expired_transfer_cannot_be_accepted(
        client: AsyncClient,
        db: AsyncSession,
        vehicle: dict,
        auth_headers: dict,
        other_headers: dict,
):
    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": BUYER_EMAIL},
        headers=auth_headers,
    )

    await db.execute(
        update(OwnershipTransfer)
        .where(OwnershipTransfer.id == offer.json()["id"])
        .values(expires_at=utc_now() - timedelta(minutes=1))
    )
    await db.commit()

    accept = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/accept",
        headers=other_headers,
    )

    assert accept.status_code == 409


async def test_cannot_transfer_to_yourself(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    response = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": "owner@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_registering_an_owned_vin_points_to_a_transfer(
        client: AsyncClient,
        vehicle: dict,
        vehicle_model: dict,
        other_headers: dict,
):
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "model_id": vehicle_model["id"],
            "year": 2019,
            "vin": vehicle["vin"],
        },
        headers=other_headers,
    )

    assert response.status_code == 409
    assert "transfer" in response.json()["error"]["message"]


async def test_unverified_buyer_cannot_accept(
        client: AsyncClient,
        vehicle: dict,
        auth_headers: dict,
):
    """Transfers go to an email address, so the buyer has to prove they
    own it — otherwise anyone could sign up with it and take the car."""

    offer = await client.post(
        f"/api/v1/transfers/vehicle/{vehicle['id']}",
        json={"to_email": "unverified@example.com"},
        headers=auth_headers,
    )

    signup = await client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@example.com", "password": "supersecret"},
    )

    accept = await client.post(
        f"/api/v1/transfers/{offer.json()['id']}/accept",
        headers={"Authorization": f"Bearer {signup.json()['access_token']}"},
    )

    assert accept.status_code == 403
