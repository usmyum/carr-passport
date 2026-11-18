from httpx import AsyncClient


async def test_upload_receipt(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
):

    response = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("receipt.pdf", b"total: $89.99", "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["original_filename"] == "receipt.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(b"total: $89.99")


async def test_upload_receipt_with_disallowed_content_type_is_rejected(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
):

    response = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={
            "file": ("receipt.exe", b"MZ...", "application/x-msdownload")
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_upload_receipt_over_size_limit_is_rejected(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
    monkeypatch,
):

    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)

    response = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("receipt.pdf", b"tiny but too big now", "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_upload_receipt_for_someone_elses_record_returns_404(
    client: AsyncClient,
    service_record: dict,
):

    other_user = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "supersecret"},
    )
    other_headers = {
        "Authorization": f"Bearer {other_user.json()['access_token']}"
    }

    response = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("receipt.pdf", b"nope", "application/pdf")},
        headers=other_headers,
    )

    assert response.status_code == 404


async def test_list_receipts_for_service_record(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
):

    await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={
            "file": ("receipt.pdf", b"receipt one", "application/pdf")
        },
        headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_receipt_download_url(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
):

    uploaded = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("receipt.pdf", b"total: $89.99", "application/pdf")},
        headers=auth_headers,
    )
    receipt_id = uploaded.json()["id"]

    response = await client.get(
        f"/api/v1/receipts/{receipt_id}/download-url",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["url"].startswith("http")


async def test_delete_receipt(
    client: AsyncClient,
    service_record: dict,
    auth_headers: dict,
):

    uploaded = await client.post(
        f"/api/v1/receipts/service-record/{service_record['id']}",
        files={"file": ("receipt.pdf", b"total: $89.99", "application/pdf")},
        headers=auth_headers,
    )
    receipt_id = uploaded.json()["id"]

    response = await client.delete(
        f"/api/v1/receipts/{receipt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204
