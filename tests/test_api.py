from sqlalchemy import select

from core.authentication import create_jwt_token
from models.models import (
    FeedFormulation,
    FormulationSeries,
    Ingredient,
    NutrientRequirements,
)


def auth_header(user) -> dict:
    return {
        "Authorization": (
            f"Bearer {create_jwt_token(user.id, user.username, user.test_device_id)}"
        )
    }


def ingredient_payload(name: str = "Corn") -> dict:
    return {
        "name": name,
        "price": 1,
        "crude_protein": 1,
        "crude_fat": 1,
        "crude_fiber": 1,
        "metabolized_energy": 1,
        "calcium": 1,
        "total_phosphorus": 1,
        "avail_phosphorus": 1,
        "lysine": 1,
        "methionine": 1,
        "m_c": 1,
        "is_available": True,
    }


def nutrient_payload(name: str = "Layer") -> dict:
    return {
        "nutrient_requirement_name": name,
        "nutrient_requirement_description": "Description",
        "composition": {"protein_percent": 16},
    }


def test_health_includes_database_status(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["details"]["database_status"] == "healthy"
    assert response.json()["details"]["database_latency_ms"] >= 0


def test_api_uses_feedprime_identity(client):
    root = client.get("/api/v1/")
    document = client.get("/openapi.json").json()

    assert root.status_code == 200
    assert root.json()["message"] == "Welcome to the FeedPrime API!"
    assert document["info"]["title"] == "FeedPrime API"


def test_versioned_swagger_documents_isolate_api_routes(client):
    v1_document = client.get("/openapi/v1.json").json()
    v2_document = client.get("/openapi/v2.json").json()
    v1_docs = client.get("/docs/v1")
    v2_docs = client.get("/docs/v2")

    assert v1_document["info"]["title"] == "FeedPrime API V1"
    assert v1_document["info"]["version"] == "1.0.0"
    assert v1_document["paths"]
    assert all(path.startswith("/api/v1/") for path in v1_document["paths"])
    assert "/v2/feed/formulate" not in v1_document["paths"]

    assert v2_document["info"]["title"] == "FeedPrime API V2"
    assert v2_document["info"]["version"] == "2.0.0"
    assert set(v2_document["paths"]) == {"/v2/feed/formulate"}
    assert v1_docs.status_code == 200
    assert "/openapi/v1.json" in v1_docs.text
    assert v2_docs.status_code == 200
    assert "/openapi/v2.json" in v2_docs.text


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/v1/ingredients/all")

    assert response.status_code == 403


def test_registration_login_and_invalid_token(client):
    registration = {
        "username": "new-user",
        "email": "new-user@example.com",
        "password": "password123",
        "installation_id": "2a4f56ef-a930-4934-a283-a6e476a6607a",
        "device_name": "Main laptop",
        "device_type": "laptop",
    }

    registered = client.post("/api/v1/auth/register", json=registration)
    duplicate = client.post("/api/v1/auth/register", json=registration)
    conflicting_identifier = client.post(
        "/api/v1/auth/register",
        json={
            "username": "new-user@example.com",
            "email": "different@example.com",
            "password": "password123",
            "installation_id": "bf23f020-4716-4ae6-a98f-b1157c55470c",
            "device_name": "Conflicting laptop",
            "device_type": "laptop",
        },
    )
    logged_in = client.post(
        "/api/v1/auth/login",
        json={
            "username": "new-user",
            "password": "password123",
        },
    )
    logged_in_by_email = client.post(
        "/api/v1/auth/login",
        json={
            "username": "new-user@example.com",
            "password": "password123",
        },
    )
    invalid_token = client.get(
        "/api/v1/ingredients/all",
        headers={"Authorization": "Bearer invalid"},
    )

    assert registered.status_code == 200
    assert duplicate.status_code == 400
    assert conflicting_identifier.status_code == 400
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"
    assert logged_in_by_email.status_code == 200
    assert logged_in_by_email.json()["token_type"] == "bearer"
    assert invalid_token.status_code == 401


def test_inactive_user_token_is_rejected(client, db_session, user_factory):
    user = user_factory("inactive")
    headers = auth_header(user)
    user.is_active = False
    db_session.commit()

    response = client.get("/api/v1/ingredients/all", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "User not found or inactive"}


def test_ingredient_visibility_and_mixed_ownership_errors(
    client, db_session, user_factory
):
    owner = user_factory("owner")
    other = user_factory("other")
    shared = Ingredient(**ingredient_payload("shared"), user_id=None)
    other_row = Ingredient(**ingredient_payload("other"), user_id=other.id)
    own_row = Ingredient(**ingredient_payload("own"), user_id=owner.id)
    db_session.add_all([shared, other_row, own_row])
    db_session.commit()

    listed = client.get(
        "/api/v1/ingredients/all", headers=auth_header(owner)
    )
    names = [item["name"] for item in listed.json()["ingredients"]]
    shared_update = client.put(
        f"/api/v1/ingredients/update/{shared.id}",
        json=ingredient_payload("changed"),
        headers=auth_header(owner),
    )
    other_update = client.put(
        f"/api/v1/ingredients/update/{other_row.id}",
        json=ingredient_payload("changed"),
        headers=auth_header(owner),
    )

    assert names == ["shared", "own"]
    assert shared_update.status_code == 404
    assert other_update.status_code == 403


def test_formulation_owner_comes_from_jwt_and_lists_are_scoped(
    client, db_session, user_factory
):
    owner = user_factory("owner")
    other = user_factory("other")
    other_series = FormulationSeries(user_id=other.id)
    db_session.add(other_series)
    db_session.flush()
    db_session.add(
        FeedFormulation(
            formulation_name="Other",
            formulation_description="Other",
            user_id=other.id,
            series_id=other_series.id,
            version_number=1,
            payload={},
        )
    )
    db_session.commit()
    payload = {
        "formulation_name": "Mine",
        "formulation_description": "Description",
        "payload": {"status": "success"},
    }

    created = client.post(
        "/api/v1/feed/formulation/save",
        json=payload,
        headers=auth_header(owner),
    )
    listed = client.get(
        "/api/v1/feed/formulation/all", headers=auth_header(owner)
    )
    rejected_owner = client.post(
        "/api/v1/feed/formulation/save",
        json={**payload, "user_id": other.id},
        headers=auth_header(owner),
    )

    assert created.status_code == 201
    assert created.json()["formulation"]["version_number"] == 1
    assert [item["formulation_name"] for item in listed.json()] == ["Mine"]
    assert listed.json()[0]["user_id"] == owner.id
    assert rejected_owner.status_code == 422


def test_corrected_and_legacy_nutrient_routes(
    client, db_session, user_factory
):
    owner = user_factory("owner")
    requirement = NutrientRequirements(
        **nutrient_payload(), user_id=owner.id
    )
    db_session.add(requirement)
    db_session.commit()

    canonical = client.put(
        f"/api/v1/nutrient-requirements/update/{requirement.id}",
        json=nutrient_payload("Canonical"),
        headers=auth_header(owner),
    )
    legacy = client.put(
        f"/api/v1/nutrient-requrments/update/{requirement.id}",
        json=nutrient_payload("Legacy"),
        headers=auth_header(owner),
    )
    paths = client.get("/openapi.json").json()["paths"]

    assert canonical.status_code == 200
    assert legacy.status_code == 200
    assert "/api/v1/nutrient-requirements/update/{nutrient_requirement_id}" in paths
    assert "/api/v1/nutrient-requrments/update/{nutrient_requirement_id}" not in paths


def test_nutrient_create_derives_owner_and_preserves_response_contract(
    client, db_session, user_factory
):
    owner = user_factory("owner")

    created = client.post(
        "/api/v1/nutrient-requirements/create",
        json=nutrient_payload(),
        headers=auth_header(owner),
    )
    rejected_owner = client.post(
        "/api/v1/nutrient-requirements/create",
        json={**nutrient_payload(), "user_id": owner.id},
        headers=auth_header(owner),
    )
    stored = db_session.scalar(select(NutrientRequirements))

    assert created.status_code == 200
    assert set(created.json()["nutrient_info"]) == {
        "nutrient_requirement_name",
        "nutrient_requirement_description",
        "composition",
    }
    assert stored.user_id == owner.id
    assert rejected_owner.status_code == 422


def test_openapi_contains_detailed_operation_and_response_documentation(client):
    document = client.get("/openapi.json").json()
    operations = [
        operation
        for path in document["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "delete", "patch"}
    ]
    tag_names = {tag["name"] for tag in document["tags"]}
    formulation_response = document["paths"]["/api/v1/feed/formulate"]["post"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]

    assert "## Authentication" in document["info"]["description"]
    assert tag_names == {
        "System",
        "Authentication",
        "Feed Formulation",
        "Feed Formulation V2",
        "Feed Formulation V3",
        "Ingredients",
        "Nutrient Requirements",
        "Licensing",
        "License Administration",
        "Pricing",
        "Pricing Administration",
    }
    assert all(operation.get("summary") for operation in operations)
    assert all(operation.get("description") for operation in operations)
    assert "anyOf" in formulation_response
    assert "HTTPBearer" in document["components"]["securitySchemes"]
