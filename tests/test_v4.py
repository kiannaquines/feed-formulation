import pytest

from core.authentication import create_jwt_token
from models.models import Ingredient
from schema.feed_v4 import FeedFormulationV4Request
from services import FeedOptimizationV4Service


def headers(user):
    token = create_jwt_token(user.id, user.username, user.test_device_id)
    return {"Authorization": f"Bearer {token}"}


def formulation_payload():
    return {
        "ingredients": [
            {
                "name": "Corn",
                "cost_per_kg": 2,
                "nutrients": {"selenium_mg_kg": 1, "protein_percent": 8},
            },
            {
                "name": "Soybean",
                "cost_per_kg": 4,
                "nutrients": {"selenium_mg_kg": 3},
            },
        ],
        "nutrient_requirements": {"selenium_mg_kg": 1.5},
    }


def legacy_ingredient_payload(name="Legacy corn"):
    return {
        "name": name,
        "price": 2,
        "crude_protein": 8,
        "crude_fat": 3,
        "crude_fiber": 2,
        "metabolized_energy": 3300,
        "calcium": 0.1,
        "total_phosphorus": 0.2,
        "avail_phosphorus": 0.1,
        "lysine": 0.3,
        "methionine": 0.2,
        "m_c": 0.4,
    }


def test_v4_optimizes_selected_nutrient_and_ignores_extra_measurements(
    client, user_factory
):
    response = client.post(
        "/v4/feed/formulate",
        json=formulation_payload(),
        headers=headers(user_factory("v4-success")),
    )
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "success"
    assert [item["percentage"] for item in result["ingredient_composition"]] == [75, 25]
    assert result["summary"]["cost_per_kg"] == 2.5
    assert result["nutrient_achievement"] == {
        "selenium_mg_kg": {"achieved": 1.5, "required": 1.5}
    }


def test_v4_accepts_dynamic_nutrient_names_with_units():
    data = formulation_payload()
    for ingredient in data["ingredients"]:
        ingredient["nutrients"]["vitamin A (IU/kg)"] = ingredient["nutrients"].pop(
            "selenium_mg_kg"
        )
    data["nutrient_requirements"] = {"vitamin A (IU/kg)": 1.5}

    result = FeedOptimizationV4Service().formulate(FeedFormulationV4Request(**data))
    assert result["status"] == "success"
    assert result["nutrient_achievement"]["vitamin A (IU/kg)"]["achieved"] == 1.5


def test_v4_infeasible_result_reports_dynamic_nutrient(client, user_factory):
    data = formulation_payload()
    data["ingredients"] = [data["ingredients"][0]]
    response = client.post(
        "/v4/feed/formulate", json=data, headers=headers(user_factory("v4-failure"))
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failure"
    assert result["failed_constraints"] == ["selenium_mg_kg"]
    assert result["constraint_diagnostics"]["selenium_mg_kg"]["status"] == "under"
    assert result["summary"]["formulation_feasible"] is False


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data["ingredients"][1]["nutrients"].clear(),
        lambda data: data["ingredients"][0]["nutrients"].pop("selenium_mg_kg"),
        lambda data: data["ingredients"][1]["nutrients"].update({"selenium_mg_kg": -1}),
        lambda data: data["nutrient_requirements"].update(
            {"selenium_mg_kg": "Infinity"}
        ),
        lambda data: data["nutrient_requirements"].update({"name": 1}),
    ],
)
def test_v4_rejects_invalid_dynamic_nutrients(client, user_factory, change):
    data = formulation_payload()
    change(data)
    response = client.post(
        "/v4/feed/formulate", json=data, headers=headers(user_factory("v4-invalid"))
    )
    assert response.status_code == 422


def test_v4_ingredient_json_and_legacy_api_compatibility(
    client, db_session, user_factory
):
    user = user_factory("v4-ingredients")
    other = user_factory("v4-other")
    auth = headers(user)
    dynamic = {
        "name": "Algae",
        "price": 3,
        "composition": {"selenium_mg_kg": 0.7},
    }
    created = client.post("/v4/ingredients/create", json=dynamic, headers=auth)
    assert created.status_code == 200
    assert created.json()["composition"] == dynamic["composition"]
    saved = db_session.get(Ingredient, created.json()["id"])
    assert saved.composition == dynamic["composition"]
    assert client.put(
        f"/v4/ingredients/update/{saved.id}",
        json=dynamic,
        headers=headers(other),
    ).status_code == 403

    legacy_created = client.post(
        "/api/v1/ingredients/create",
        json=legacy_ingredient_payload(),
        headers=auth,
    )
    assert legacy_created.status_code == 200
    legacy_id = legacy_created.json()["id"]
    assert db_session.get(Ingredient, legacy_id).composition["protein_percent"] == 8

    v4_names = [
        item["name"] for item in
        client.get("/v4/ingredients/all", headers=auth).json()["ingredients"]
    ]
    legacy_names = [
        item["name"] for item in
        client.get("/api/v1/ingredients/all", headers=auth).json()["ingredients"]
    ]
    assert v4_names == ["Algae", "Legacy corn"]
    assert legacy_names == ["Legacy corn"]

    updated = client.put(
        f"/v4/ingredients/update/{saved.id}",
        json={**dynamic, "composition": {"zinc_mg_kg": 3}},
        headers=auth,
    )
    assert updated.status_code == 200
    assert updated.json()["composition"] == {"zinc_mg_kg": 3}

    legacy_updated = client.put(
        f"/api/v1/ingredients/update/{legacy_id}",
        json={**legacy_ingredient_payload(), "crude_protein": 9},
        headers=auth,
    )
    assert legacy_updated.status_code == 200
    assert db_session.get(Ingredient, legacy_id).composition["protein_percent"] == 9


def test_v4_docs_are_isolated(client):
    document = client.get("/openapi/v4.json").json()
    assert document["info"]["version"] == "4.0.0"
    assert set(document["paths"]) == {
        "/v4/feed/formulate",
        "/v4/ingredients/all",
        "/v4/ingredients/create",
        "/v4/ingredients/update/{ingredient_id}",
        "/v4/ingredients/delete/{ingredient_id}",
    }
    assert "/openapi/v4.json" in client.get("/docs/v4").text
    for version in (1, 2, 3):
        old_paths = client.get(f"/openapi/v{version}.json").json()["paths"]
        assert "/v4/feed/formulate" not in old_paths
