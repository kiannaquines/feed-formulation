from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db.database import get_db
from repositories import (
    FeedFormulationRepository,
    IngredientRepository,
    NutrientRequirementRepository,
    OTPSessionRepository,
    UserRepository,
)
from services import (
    AuthenticationService,
    FeedFormulationService,
    FeedOptimizationService,
    IngredientService,
    NutrientRequirementService,
)

security = HTTPBearer()


def get_authentication_service(
    db: Session = Depends(get_db),
) -> AuthenticationService:
    return AuthenticationService(db, UserRepository(db), OTPSessionRepository(db))


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: AuthenticationService = Depends(get_authentication_service),
) -> dict:
    return service.authenticate(credentials.credentials)


def get_ingredient_service(db: Session = Depends(get_db)) -> IngredientService:
    return IngredientService(db, IngredientRepository(db))


def get_nutrient_requirement_service(
    db: Session = Depends(get_db),
) -> NutrientRequirementService:
    return NutrientRequirementService(db, NutrientRequirementRepository(db))


def get_feed_formulation_service(
    db: Session = Depends(get_db),
) -> FeedFormulationService:
    return FeedFormulationService(db, FeedFormulationRepository(db))


def get_feed_optimization_service() -> FeedOptimizationService:
    return FeedOptimizationService()
