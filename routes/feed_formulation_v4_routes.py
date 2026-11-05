from fastapi import APIRouter, Depends

from api.dependencies import get_feed_optimization_v4_service, get_licensed_user
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.feed_v4 import FeedFormulationV4Request, OptimizationV4SuccessResponse
from schema.schema import DetailResponse, OptimizationV2FailureResponse
from services import FeedOptimizationV4Service


feed_formulation_v4_router = APIRouter(tags=["Feed Formulation V4"])


@feed_formulation_v4_router.post(
    "/feed/formulate",
    response_model=OptimizationV4SuccessResponse | OptimizationV2FailureResponse,
    summary="Calculate a least-cost formulation with dynamic nutrients",
    description=(
        "Choose nutrient targets by name and provide a value for each chosen "
        "nutrient in every ingredient. Extra ingredient nutrients are ignored. "
        "Values must use the same unit across ingredients and the target. "
        "Targets are exact; ingredient inclusion bounds are fractions from 0 to 1. "
        "Infeasible requests return a bounded candidate and diagnostics."
    ),
    responses={
        **PROTECTED_RESPONSES,
        400: {"model": DetailResponse, "description": "Ingredient bounds are invalid."},
        500: {"model": DetailResponse, "description": "Optimization could not run."},
        **VALIDATION_RESPONSE,
    },
)
def feed_formulator_v4(
    formulation_request: FeedFormulationV4Request,
    _auth_user: dict = Depends(get_licensed_user),
    service: FeedOptimizationV4Service = Depends(get_feed_optimization_v4_service),
):
    return service.formulate(formulation_request)
