import pytest
from pydantic import ValidationError

from core.authentication import create_jwt_token
from schema.feed_v3 import FeedFormulationV3Request
from services import FeedOptimizationV3Service


# Mulberry Leaf meal Feed Formulation.xls, Sheet1, C3:U4 (alternating columns).
# Prices below are synthetic test inputs, not prices from the workbook.
NUTRIENTS = (
    "protein_percent", "fat_percent", "fiber_percent", "energy_me",
    "calcium_percent", "phosphorus_percent", "available_phosphorus_percent",
    "lysine_percent", "methionine_percent", "methionine_cystine_percent",
)
CORN = dict(zip(NUTRIENTS, [7.8, 3.4, 2.8, 3300, 0.07, 0.25, 0.06, 0.26, 0.18, 0.36]))
SOYBEAN = dict(zip(NUTRIENTS, [43.1, 1.8, 5, 2240, 0.45, 0.63, 0.19, 2.73, 0.63, 1.29]))


def payload():
    return {
        "ingredients": [
            {"name": "Corn", "cost_per_kg": 2, **CORN},
            {"name": "Soybean Meal", "cost_per_kg": 4, **SOYBEAN},
        ],
        "nutrient_requirements": {
            name: 0.6 * CORN[name] + 0.4 * SOYBEAN[name] for name in NUTRIENTS
        },
    }


def headers(user):
    token = create_jwt_token(user.id, user.username, user.test_device_id)
    return {"Authorization": f"Bearer {token}"}


def test_v3_calculates_workbook_nutrients_and_least_cost():
    data = payload()
    data["ingredients"].append(
        {**data["ingredients"][0], "name": "Expensive corn", "cost_per_kg": 10}
    )
    result = FeedOptimizationV3Service().formulate(FeedFormulationV3Request(**data))

    assert result["status"] == "success"
    assert [i["percentage"] for i in result["ingredient_composition"]] == [60, 40, 0]
    assert result["summary"]["cost_per_kg"] == 2.8
    assert result["summary"]["total_ingredient_percentage"] == 100
    assert set(result["nutrient_achievement"]) == set(NUTRIENTS)
    for name, target in data["nutrient_requirements"].items():
        assert result["nutrient_achievement"][name] == {
            "achieved": round(target, 4), "required": round(target, 4)
        }


@pytest.mark.parametrize("nutrient", NUTRIENTS)
def test_each_nutrient_independently_constrains_the_solution(nutrient):
    # Identical compositions except one nutrient: that nutrient must force a mix.
    data = payload()
    data["ingredients"][1].update(CORN)
    data["ingredients"][1][nutrient] = CORN[nutrient] + 1
    data["nutrient_requirements"] = {**CORN, nutrient: CORN[nutrient] + 0.25}
    result = FeedOptimizationV3Service().formulate(FeedFormulationV3Request(**data))

    assert result["status"] == "success"
    assert [i["percentage"] for i in result["ingredient_composition"]] == [75, 25]


@pytest.mark.parametrize("nutrient", NUTRIENTS)
def test_each_impossible_nutrient_is_reported_by_the_route(client, user_factory, nutrient):
    data = payload()
    data["ingredients"] = [{**data["ingredients"][0], "min_percentage": 1}]
    data["nutrient_requirements"] = {**CORN, nutrient: CORN[nutrient] + 1}
    response = client.post(
        "/v3/feed/formulate", json=data, headers=headers(user_factory("v3-failure"))
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failure"
    assert result["failed_constraints"] == [nutrient]
    assert len(result["constraint_diagnostics"]) == 11
    assert result["constraint_diagnostics"][nutrient]["status"] == "under"
    assert result["summary"]["formulation_feasible"] is False
    assert result["ingredient_composition"][0]["percentage"] == 100


def test_v3_route_preserves_all_achievements_and_requires_entitlement(client, user_factory, db_session):
    from models.models import DeviceLicense

    assert client.post("/v3/feed/formulate", json=payload()).status_code == 403
    user = user_factory("v3-success")
    response = client.post("/v3/feed/formulate", json=payload(), headers=headers(user))
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert set(response.json()["nutrient_achievement"]) == set(NUTRIENTS)
    license = db_session.query(DeviceLicense).filter_by(user_id=user.id).one()
    license.status = "revoked"
    db_session.commit()
    assert client.post("/v3/feed/formulate", json=payload(), headers=headers(user)).status_code == 403


@pytest.mark.parametrize("section", ["ingredient", "nutrient_requirements"])
@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf"), None, "invalid"])
def test_v3_rejects_invalid_nutrient_values(section, value):
    data = payload()
    target = data["ingredients"][0] if section == "ingredient" else data[section]
    target["fat_percent"] = value
    with pytest.raises(ValidationError):
        FeedFormulationV3Request(**data)


@pytest.mark.parametrize("section", ["ingredient", "nutrient_requirements"])
def test_v3_does_not_silently_treat_missing_nutrients_as_zero(client, user_factory, section):
    data = payload()
    target = data["ingredients"][0] if section == "ingredient" else data[section]
    del target["available_phosphorus_percent"]
    response = client.post("/v3/feed/formulate", json=data, headers=headers(user_factory("v3-missing")))
    assert response.status_code == 422


def test_v3_handles_invalid_bounds_empty_ingredients_and_solver_errors(client, user_factory):
    auth = headers(user_factory("v3-invalid"))
    for change, code in [("bounds", 400), ("empty", 400), ("method", 500)]:
        data = payload()
        if change == "bounds":
            data["ingredients"][0].update(min_percentage=0.8, max_percentage=0.2)
        elif change == "empty":
            data["ingredients"] = []
        else:
            data["optimization_method"] = "not-a-solver"
        response = client.post("/v3/feed/formulate", json=data, headers=auth)
        assert response.status_code == code


def test_v3_failure_candidate_respects_bounds_when_total_is_impossible():
    data = payload()
    for ingredient in data["ingredients"]:
        ingredient["max_percentage"] = 0.2
    result = FeedOptimizationV3Service().formulate(FeedFormulationV3Request(**data))
    assert result["status"] == "failure"
    assert "total_ingredient_percentage" in result["failed_constraints"]
    assert all(0 <= item["percentage"] <= 20 for item in result["ingredient_composition"])


def test_v3_docs_are_isolated_and_describe_ten_required_nutrients(client):
    document = client.get("/openapi/v3.json").json()
    assert set(document["paths"]) == {"/v3/feed/formulate"}
    assert document["info"]["version"] == "3.0.0"
    assert set(document["components"]["schemas"]["NutrientsV3"]["required"]) == set(NUTRIENTS)
    assert "/openapi/v3.json" in client.get("/docs/v3").text
    for version in (1, 2):
        old = client.get(f"/openapi/v{version}.json").json()
        assert "/v3/feed/formulate" not in old["paths"]
        assert "NutrientsV3" not in old["components"]["schemas"]
