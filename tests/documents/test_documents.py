from datetime import date, timedelta

from httpx import AsyncClient


async def upload(
    client: AsyncClient,
    vehicle: dict,
    headers: dict,
    **fields,
):
    return await client.post(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        data={"kind": "insurance", **fields},
        files={"file": ("policy.pdf", b"%PDF-1.4 policy", "application/pdf")},
        headers=headers,
    )


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


async def test_upload_and_download_document(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    response = await upload(
        client,
        vehicle,
        auth_headers,
        title="Aviva policy",
        expires_on=in_days(10),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["kind"] == "insurance"
    assert body["expiry_status"] == "due_soon"

    url = await client.get(
        f"/api/v1/documents/{body['id']}/download-url",
        headers=auth_headers,
    )

    assert url.status_code == 200
    assert url.json()["url"].startswith("http")


async def test_expiry_status(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    await upload(client, vehicle, auth_headers, expires_on=in_days(-1))
    await upload(client, vehicle, auth_headers, expires_on=in_days(200))
    await upload(client, vehicle, auth_headers, kind="registration")

    listed = await client.get(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )

    # Soonest expiry first, never-expiring last.
    assert [d["expiry_status"] for d in listed.json()] == ["overdue", "ok", None]


async def test_renewing_updates_expiry(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    document = (await upload(client, vehicle, auth_headers, expires_on=in_days(-1))).json()

    renewed = await client.put(
        f"/api/v1/documents/{document['id']}",
        json={"expires_on": in_days(365)},
        headers=auth_headers,
    )

    assert renewed.json()["expiry_status"] == "ok"


async def test_expiry_before_issue_is_rejected(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    response = await upload(
        client,
        vehicle,
        auth_headers,
        issued_on="2026-06-01",
        expires_on="2026-01-01",
    )

    assert response.status_code == 422


async def test_unknown_kind_and_bad_file_type_are_rejected(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
):
    bad_kind = await upload(client, vehicle, auth_headers, kind="passport")
    bad_file = await client.post(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        data={"kind": "insurance"},
        files={"file": ("x.exe", b"MZ", "application/x-msdownload")},
        headers=auth_headers,
    )

    assert bad_kind.status_code == 422
    assert bad_file.status_code == 422


async def test_documents_stay_with_the_person_not_the_car(
    client: AsyncClient,
    vehicle: dict,
    auth_headers: dict,
    other_headers: dict,
    sell_vehicle,
):
    document = (await upload(client, vehicle, auth_headers)).json()

    await sell_vehicle()

    # The buyer gets the service history, not the seller's insurance.
    buyer_list = await client.get(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        headers=other_headers,
    )
    buyer_get = await client.get(
        f"/api/v1/documents/{document['id']}",
        headers=other_headers,
    )

    assert buyer_list.json() == []
    assert buyer_get.status_code == 404

    # The seller can still read their own, but not add new ones…
    seller_list = await client.get(
        f"/api/v1/documents/vehicle/{vehicle['id']}",
        headers=auth_headers,
    )
    seller_upload = await upload(client, vehicle, auth_headers)

    assert [d["id"] for d in seller_list.json()] == [document["id"]]
    assert seller_upload.status_code == 403

    # …and can delete them.
    deleted = await client.delete(
        f"/api/v1/documents/{document['id']}",
        headers=auth_headers,
    )

    assert deleted.status_code == 204
