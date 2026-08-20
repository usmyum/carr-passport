from httpx import AsyncClient


async def test_create_model_under_make(
        client: AsyncClient,
        make: dict,
):
    response = await client.post(
        f"/api/v1/models/make/{make['id']}",
        json={"name": "Corolla"},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "Corolla"
    assert body["slug"] == "corolla"
    assert body["make_id"] == make["id"]


async def test_create_model_under_missing_make_returns_404(
        client: AsyncClient,
):
    response = await client.post(
        "/api/v1/models/make/9999",
        json={"name": "Corolla"},
    )

    assert response.status_code == 404


async def test_same_name_under_different_makes_is_allowed(
        client: AsyncClient,
        make: dict,
):
    other = await client.post(
        "/api/v1/makes",
        json={"name": "Honda"},
    )

    await client.post(
        f"/api/v1/models/make/{make['id']}",
        json={"name": "Civic"},
    )

    response = await client.post(
        f"/api/v1/models/make/{other.json()['id']}",
        json={"name": "Civic"},
    )

    assert response.status_code == 201


async def test_duplicate_model_under_same_make_conflicts(
        client: AsyncClient,
        make: dict,
        vehicle_model: dict,
):
    response = await client.post(
        f"/api/v1/models/make/{make['id']}",
        json={"name": "Corolla"},
    )

    assert response.status_code == 409


async def test_filter_models_by_make(
        client: AsyncClient,
        make: dict,
        vehicle_model: dict,
):
    response = await client.get(
        "/api/v1/models",
        params={"make_id": make["id"]},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_update_model(
        client: AsyncClient,
        vehicle_model: dict,
):
    response = await client.put(
        f"/api/v1/models/{vehicle_model['id']}",
        json={"name": "Camry"},
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "camry"


async def test_delete_model(
        client: AsyncClient,
        vehicle_model: dict,
):
    response = await client.delete(
        f"/api/v1/models/{vehicle_model['id']}"
    )

    assert response.status_code == 204


async def test_deleting_make_cascades_to_models(
        client: AsyncClient,
        make: dict,
        vehicle_model: dict,
):
    await client.delete(f"/api/v1/makes/{make['id']}")

    response = await client.get(
        f"/api/v1/models/{vehicle_model['id']}"
    )

    assert response.status_code == 404
