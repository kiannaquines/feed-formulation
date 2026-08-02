import numpy as np
import pytest

from core.authentication import create_jwt_token
from core.exceptions import OptimizationError, ValidationError
from schema.schema import FeedFormulationRequest
from services import FeedOptimizationService, FeedOptimizationV2Service


def auth_header(user) -> dict:
    token = create_jwt_token(user.id, user.username, user.test_device_id)
    return {"Authorization": f"Bearer {token}"}


def feasible_request() -> FeedFormulationRequest:
    return FeedFormulationRequest(
        ingredients=[
            {
                "name": "Complete feed",
                "cost_per_kg": 2,
                "protein_percent": 1,
                "energy_me": 1,
                "calcium_percent": 1,
                "phosphorus_percent": 1,
            }
        ],
        nutrient_requirements={
            "protein_percent": 1,
            "energy_me": 1,
            "calcium_percent": 1,
            "phosphorus_percent": 1,
        },
    )


def infeasible_request() -> FeedFormulationRequest:
    return FeedFormulationRequest(
        ingredients=[{"name": "Feed", "cost_per_kg": 1}],
        nutrient_requirements={
            "protein_percent": 2,
            "energy_me": 2,
            "calcium_percent": 2,
            "phosphorus_percent": 2,
        },
    )


def test_v1_contract_remains_unchanged_and_v2_success_matches_it():
    v1_success = FeedOptimizationService().formulate(feasible_request())
    v2_success = FeedOptimizationV2Service().formulate(feasible_request())
    v1_failure = FeedOptimizationService().formulate(infeasible_request())

    assert v2_success == v1_success
    assert set(v1_failure) == {
        "formulation_inputs",
        "status",
        "detail",
        "error_details",
        "formulation_feasible",
    }


def test_v2_infeasible_result_returns_candidate_and_failed_parts():
    result = FeedOptimizationV2Service().formulate(infeasible_request())

    assert result["status"] == "failure"
    assert result["ingredient_composition"] == [
        {
            "name": "Feed",
            "percentage": 100.0,
            "cost_contribution": 1.0,
            "included": True,
            "status": "at_maximum",
            "issues": ["maximum_bound_active"],
        }
    ]
    assert result["constraint_diagnostics"]["total_ingredient_percentage"][
        "status"
    ] == "met"
    assert result["constraint_diagnostics"]["protein_percent"]["status"] == "under"
    assert result["failed_constraints"] == [
        "protein_percent",
        "energy_me",
        "calcium_percent",
        "phosphorus_percent",
    ]
    assert result["summary"]["formulation_feasible"] is False


def test_v2_ingredient_statuses_cover_usage_and_active_bounds():
    request = FeedFormulationRequest(
        ingredients=[
            {"name": "Excluded", "cost_per_kg": 1},
            {
                "name": "Minimum",
                "cost_per_kg": 1,
                "min_percentage": 0.2,
            },
            {
                "name": "Maximum",
                "cost_per_kg": 1,
                "max_percentage": 0.4,
            },
            {"name": "Included", "cost_per_kg": 1},
            {
                "name": "Fixed",
                "cost_per_kg": 1,
                "min_percentage": 0.1,
                "max_percentage": 0.1,
            },
        ],
        nutrient_requirements={
            "protein_percent": 0,
            "energy_me": 0,
            "calcium_percent": 0,
            "phosphorus_percent": 0,
        },
    )

    composition = FeedOptimizationV2Service._ingredient_composition(
        request,
        np.array([0.0, 0.2, 0.4, 0.3, 0.1]),
        np.ones(5),
    )

    assert [item["status"] for item in composition] == [
        "excluded",
        "at_minimum",
        "at_maximum",
        "included",
        "at_minimum",
    ]
    assert composition[0]["issues"] == ["minimum_bound_active"]
    assert composition[1]["issues"] == ["minimum_bound_active"]
    assert composition[2]["issues"] == ["maximum_bound_active"]
    assert composition[3]["issues"] == []
    assert composition[4]["issues"] == [
        "minimum_bound_active",
        "maximum_bound_active",
    ]

    diagnostics = FeedOptimizationV2Service._constraint_diagnostics(
        np.array([1.0, 2.0, 0.5, 1.0, 1.0]),
        np.ones(5),
    )
    assert diagnostics["protein_percent"]["status"] == "over"
    assert diagnostics["energy_me"]["status"] == "under"


def test_v2_preserves_v1_validation_errors():
    request = FeedFormulationRequest(
        ingredients=[],
        nutrient_requirements={
            "protein_percent": 1,
            "energy_me": 1,
            "calcium_percent": 1,
            "phosphorus_percent": 1,
        },
    )

    with pytest.raises(ValidationError):
        FeedOptimizationV2Service().formulate(request)


def test_v2_preserves_v1_solver_execution_errors():
    request = feasible_request()
    request.optimization_method = "not-a-solver"

    with pytest.raises(OptimizationError):
        FeedOptimizationV2Service().formulate(request)


def test_v2_route_is_separate_from_v1_prefix(client, user_factory):
    user = user_factory("solver-v2")
    payload = infeasible_request().model_dump()

    response = client.post(
        "/v2/feed/formulate", json=payload, headers=auth_header(user)
    )
    wrong_prefix = client.post(
        "/api/v1/v2/feed/formulate", json=payload, headers=auth_header(user)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failure"
    assert wrong_prefix.status_code == 404
