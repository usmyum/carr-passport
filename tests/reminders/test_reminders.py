from datetime import date, timedelta

from httpx import AsyncClient

from app.modules.reminders.service import add_months


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


async def create(client: AsyncClient, vehicle: dict, headers: dict, **fields):
    return await client.post(
        f"/api/v1/reminders/vehicle/{vehicle['id']}",
        json={"title": "Oil change", **fields},
        headers=headers,
    )


async def set_mileage(client: AsyncClient, vehicle: dict, headers: dict, km: int):
    await client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"current_mileage": km},
        headers=headers,
    )


async def test_status_by_date(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    overdue = await create(client, vehicle, auth_headers, due_on=in_days(-1))
    soon = await create(client, vehicle, auth_headers, due_on=in_days(7))
    later = await create(client, vehicle, auth_headers, due_on=in_days(90))

    assert overdue.status_code == 201
    assert overdue.json()["status"] == "overdue"
    assert soon.json()["status"] == "due_soon"
    assert later.json()["status"] == "ok"

    listed = await client.get(
        f"/api/v1/reminders/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert [r["status"] for r in listed.json()] == ["overdue", "due_soon", "ok"]


async def test_status_by_mileage_follows_the_odometer(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    await set_mileage(client, vehicle, auth_headers, 9_000)

    reminder = (await create(client, vehicle, auth_headers, due_mileage=10_000)).json()

    assert reminder["status"] == "due_soon"

    await set_mileage(client, vehicle, auth_headers, 10_200)

    again = await client.get(f"/api/v1/reminders/{reminder['id']}", headers=auth_headers)

    assert again.json()["status"] == "overdue"


async def test_needs_a_date_or_mileage(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    response = await create(client, vehicle, auth_headers)

    assert response.status_code == 422


async def test_completing_a_repeating_reminder_schedules_the_next(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    await set_mileage(client, vehicle, auth_headers, 20_000)

    reminder = (
        await create(
            client,
            vehicle,
            auth_headers,
            due_on=in_days(-5),
            repeat_months=12,
            repeat_km=10_000,
        )
    ).json()

    done = await client.post(
        f"/api/v1/reminders/{reminder['id']}/complete",
        headers=auth_headers,
    )

    assert done.status_code == 200

    body = done.json()

    assert body["completed"]["completed_at"] is not None
    assert body["completed"]["status"] is None

    # Counted from when it was actually done, not the old due date.
    assert body["next"]["due_on"] == add_months(date.today(), 12).isoformat()
    assert body["next"]["due_mileage"] == 30_000
    assert body["next"]["status"] == "ok"

    again = await client.post(
        f"/api/v1/reminders/{reminder['id']}/complete",
        headers=auth_headers,
    )

    assert again.status_code == 409

    open_only = await client.get(
        f"/api/v1/reminders/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    assert [r["id"] for r in open_only.json()] == [body["next"]["id"]]


async def test_one_off_reminder_has_no_next(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    reminder = (await create(client, vehicle, auth_headers, due_on=in_days(3))).json()

    done = await client.post(
        f"/api/v1/reminders/{reminder['id']}/complete",
        headers=auth_headers,
    )

    assert done.json()["next"] is None


async def test_reminders_do_not_pass_to_the_buyer(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
    other_headers: dict,
    sell_vehicle,
):
    reminder = (await create(client, vehicle, auth_headers, due_on=in_days(3))).json()

    await sell_vehicle()

    buyer_list = await client.get(
        f"/api/v1/reminders/vehicle/{vehicle['id']}",
        headers=other_headers,
    )
    seller_get = await client.get(
        f"/api/v1/reminders/{reminder['id']}",
        headers=auth_headers,
    )

    assert buyer_list.json() == []
    assert seller_get.status_code == 403


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
