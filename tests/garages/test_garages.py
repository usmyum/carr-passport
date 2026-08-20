from httpx import AsyncClient


async def test_create_garage(client: AsyncClient):
    response = await client.post(
        "/api/v1/garages",
        json={"name": "Joe's Auto Shop", "phone": "555-1234"},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "Joe's Auto Shop"
    assert body["slug"] == "joe-s-auto-shop"


async def test_duplicate_garage_is_rejected(client: AsyncClient):
    await client.post("/api/v1/garages", json={"name": "Joe's Auto Shop"})

    response = await client.post(
        "/api/v1/garages",
        json={"name": "Joe's Auto Shop"},
    )

    assert response.status_code == 409


async def test_list_garages(client: AsyncClient):
    await client.post("/api/v1/garages", json={"name": "Zed Motors"})
    await client.post("/api/v1/garages", json={"name": "Ace Garage"})

    response = await client.get("/api/v1/garages")

    assert response.status_code == 200

    names = [garage["name"] for garage in response.json()]

    assert names == ["Ace Garage", "Zed Motors"]


async def test_update_garage(client: AsyncClient):
    created = await client.post(
        "/api/v1/garages",
        json={"name": "Old Name"},
    )
    garage_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/garages/{garage_id}",
        json={"name": "New Name"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


async def test_delete_garage(client: AsyncClient):
    created = await client.post(
        "/api/v1/garages",
        json={"name": "Temporary Garage"},
    )
    garage_id = created.json()["id"]

    response = await client.delete(f"/api/v1/garages/{garage_id}")

    assert response.status_code == 204

    follow_up = await client.get(f"/api/v1/garages/{garage_id}")

    assert follow_up.status_code == 404
