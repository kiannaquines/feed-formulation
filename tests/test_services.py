from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import services.authentication_service as authentication_service_module
from core.authentication import hash_password
from core.exceptions import OptimizationError, PersistenceError, ValidationError
from models.models import User
from repositories import IngredientRepository, OTPSessionRepository, UserRepository
from schema.schema import (
    FeedFormulationRequest,
    IngredientCreate,
    OTPVerification,
    UserLogin,
)
from services import AuthenticationService, FeedOptimizationService, IngredientService


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


def test_ingredient_service_commits_mutation(db_session, user_factory):
    owner = user_factory("owner")
    service = IngredientService(db_session, IngredientRepository(db_session))

    created = service.create(IngredientCreate(**ingredient_payload()), owner.id)

    assert created.user_id == owner.id
    assert db_session.get(type(created), created.id) is created


def test_ingredient_service_rolls_back_repository_failure():
    db = Mock(spec=Session)
    repository = Mock()
    repository.add.side_effect = SQLAlchemyError("failure")
    service = IngredientService(db, repository)

    with pytest.raises(PersistenceError):
        service.create(IngredientCreate(**ingredient_payload()), 1)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_ingredient_service_translates_repository_read_failure():
    db = Mock(spec=Session)
    repository = Mock()
    repository.list_visible_to.side_effect = SQLAlchemyError("failure")
    service = IngredientService(db, repository)

    with pytest.raises(PersistenceError):
        service.list_visible(1)


def test_optimization_rejects_empty_ingredients():
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
        FeedOptimizationService().formulate(request)


def test_optimization_returns_feasible_solution():
    request = FeedFormulationRequest(
        ingredients=[
            {
                "name": "Complete feed",
                "cost_per_kg": 2,
                "protein_percent": 1,
                "energy_me": 1,
                "calcium_percent": 1,
                "phosphorus_percent": 1,
                "min_percentage": 0,
                "max_percentage": 1,
            }
        ],
        nutrient_requirements={
            "protein_percent": 1,
            "energy_me": 1,
            "calcium_percent": 1,
            "phosphorus_percent": 1,
        },
    )

    result = FeedOptimizationService().formulate(request)

    assert result["status"] == "success"
    assert result["summary"]["total_ingredient_percentage"] == 100


def test_optimization_rejects_inverted_bounds():
    request = FeedFormulationRequest(
        ingredients=[
            {
                "name": "Invalid",
                "cost_per_kg": 1,
                "min_percentage": 0.8,
                "max_percentage": 0.2,
            }
        ],
        nutrient_requirements={
            "protein_percent": 0,
            "energy_me": 0,
            "calcium_percent": 0,
            "phosphorus_percent": 0,
        },
    )

    with pytest.raises(ValidationError):
        FeedOptimizationService().formulate(request)


def test_optimization_returns_infeasible_result():
    request = FeedFormulationRequest(
        ingredients=[{"name": "Feed", "cost_per_kg": 1}],
        nutrient_requirements={
            "protein_percent": 2,
            "energy_me": 2,
            "calcium_percent": 2,
            "phosphorus_percent": 2,
        },
    )

    result = FeedOptimizationService().formulate(request)

    assert result["status"] == "failure"
    assert result["formulation_feasible"] is False


def test_optimization_translates_solver_failure():
    request = FeedFormulationRequest(
        ingredients=[{"name": "Feed", "cost_per_kg": 1}],
        nutrient_requirements={
            "protein_percent": 0,
            "energy_me": 0,
            "calcium_percent": 0,
            "phosphorus_percent": 0,
        },
        optimization_method="not-a-solver",
    )

    with pytest.raises(OptimizationError):
        FeedOptimizationService().formulate(request)


def test_authentication_service_completes_otp_flow(db_session, monkeypatch):
    monkeypatch.setattr(authentication_service_module, "OTP_IS_ENABLED", True)
    user = User(
        username="otp-user",
        email="otp-user@example.com",
        password_hash=hash_password("password123"),
        otp_secret="otp-secret",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    service = AuthenticationService(
        db_session,
        UserRepository(db_session),
        OTPSessionRepository(db_session),
    )

    login = service.login(UserLogin(username=user.username, password="password123"))
    verified = service.verify_otp(
        OTPVerification(
            session_token=login["session_token"],
            otp_code=login["current_otp"],
        )
    )

    assert verified["token_type"] == "bearer"
    assert verified["user"]["id"] == user.id
