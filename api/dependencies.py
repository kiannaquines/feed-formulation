from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.exceptions import ForbiddenError
from db.database import get_db
from repositories import (
    FeedFormulationRepository,
    IngredientRepository,
    LicensingRepository,
    NutrientRequirementRepository,
    OTPSessionRepository,
    PricingRepository,
    UserRepository,
)
from services import (
    AdminLicensingService,
    AuthenticationService,
    FeedFormulationService,
    FeedOptimizationService,
    FeedOptimizationV2Service,
    IngredientService,
    LicensingService,
    NutrientRequirementService,
    AdminPricingService,
    PricingService,
)

security = HTTPBearer()


def get_authentication_service(
    db: Session = Depends(get_db),
) -> AuthenticationService:
    licensing = LicensingService(db, LicensingRepository(db), UserRepository(db))
    return AuthenticationService(
        db, UserRepository(db), OTPSessionRepository(db), licensing
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: AuthenticationService = Depends(get_authentication_service),
) -> dict:
    return service.authenticate(credentials.credentials)


def get_licensing_service(db: Session = Depends(get_db)) -> LicensingService:
    return LicensingService(db, LicensingRepository(db), UserRepository(db))


def get_licensed_user(
    auth_user: dict = Depends(get_current_user),
    service: LicensingService = Depends(get_licensing_service),
) -> dict:
    return service.require_entitlement(auth_user)


def get_current_admin(auth_user: dict = Depends(get_current_user)) -> dict:
    if not auth_user["is_superuser"]:
        raise ForbiddenError("Superuser access is required")
    return auth_user


def get_admin_licensing_service(
    db: Session = Depends(get_db),
) -> AdminLicensingService:
    return AdminLicensingService(db, LicensingRepository(db), UserRepository(db))


def get_pricing_service(db: Session = Depends(get_db)) -> PricingService:
    return PricingService(db, PricingRepository(db))


def get_admin_pricing_service(
    db: Session = Depends(get_db),
) -> AdminPricingService:
    return AdminPricingService(db, PricingRepository(db))


def get_ingredient_service(db: Session = Depends(get_db)) -> IngredientService:
    return IngredientService(
        db,
        IngredientRepository(db),
        LicensingService(db, LicensingRepository(db)),
    )


def get_nutrient_requirement_service(
    db: Session = Depends(get_db),
) -> NutrientRequirementService:
    return NutrientRequirementService(
        db,
        NutrientRequirementRepository(db),
        LicensingService(db, LicensingRepository(db)),
    )


def get_feed_formulation_service(
    db: Session = Depends(get_db),
) -> FeedFormulationService:
    return FeedFormulationService(db, FeedFormulationRepository(db))


def get_feed_optimization_service() -> FeedOptimizationService:
    return FeedOptimizationService()


def get_feed_optimization_v2_service() -> FeedOptimizationV2Service:
    return FeedOptimizationV2Service()
