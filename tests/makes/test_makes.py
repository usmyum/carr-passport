from httpx import AsyncClient


async def test_create_make(client: AsyncClient):

    response = await client.post(
        "/api/v1/makes",
        json={"name": "Toyota"},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "Toyota"
    assert body["slug"] == "toyota"


async def test_duplicate_make_is_rejected(client: AsyncClient):

    await client.post("/api/v1/makes", json={"name": "Toyota"})

    response = await client.post(
        "/api/v1/makes",
        json={"name": "Toyota"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_list_makes(client: AsyncClient):

    await client.post("/api/v1/makes", json={"name": "Honda"})
    await client.post("/api/v1/makes", json={"name": "Audi"})

    response = await client.get("/api/v1/makes")

    assert response.status_code == 200

    names = [make["name"] for make in response.json()]

    assert names == ["Audi", "Honda"]


async def test_get_make(client: AsyncClient, make: dict):

    response = await client.get(f"/api/v1/makes/{make['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == make["id"]


async def test_get_missing_make_returns_404(client: AsyncClient):

    response = await client.get("/api/v1/makes/9999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_update_make(client: AsyncClient, make: dict):

    response = await client.put(
        f"/api/v1/makes/{make['id']}",
        json={"name": "Lexus"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Lexus"
    assert response.json()["slug"] == "lexus"


async def test_update_make_to_existing_name_conflicts(
    client: AsyncClient,
    make: dict,
):

    await client.post("/api/v1/makes", json={"name": "Honda"})

    response = await client.put(
        f"/api/v1/makes/{make['id']}",
        json={"name": "Honda"},
    )

    assert response.status_code == 409


async def test_delete_make(client: AsyncClient, make: dict):

    response = await client.delete(f"/api/v1/makes/{make['id']}")

    assert response.status_code == 204

    follow_up = await client.get(f"/api/v1/makes/{make['id']}")

    assert follow_up.status_code == 404


async def test_blank_name_is_a_validation_error(client: AsyncClient):

    response = await client.post(
        "/api/v1/makes",
        json={"name": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
