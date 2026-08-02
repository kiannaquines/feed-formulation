from fastapi import APIRouter, Depends

from api.dependencies import get_feed_optimization_v2_service, get_licensed_user
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.schema import (
    DetailResponse,
    FeedFormulationRequest,
    OptimizationSuccessResponse,
    OptimizationV2FailureResponse,
)
from services import FeedOptimizationV2Service


feed_formulation_v2_router = APIRouter(tags=["Feed Formulation V2"])


@feed_formulation_v2_router.post(
    "/feed/formulate",
    response_model=OptimizationSuccessResponse | OptimizationV2FailureResponse,
    summary="Calculate a V2 least-cost feed formulation",
    description=(
        "Use the unchanged V1 optimizer for the primary calculation. When the exact "
        "formulation is infeasible, return the closest bounded candidate with "
        "ingredient and aggregate-constraint diagnostics."
    ),
    responses={
        **PROTECTED_RESPONSES,
        400: {
            "model": DetailResponse,
            "description": "Ingredients or percentage constraints are invalid.",
        },
        500: {
            "model": DetailResponse,
            "description": "The primary or diagnostic solver could not be executed.",
        },
        **VALIDATION_RESPONSE,
    },
)
def feed_formulator_v2(
    formulation_request: FeedFormulationRequest,
    _auth_user: dict = Depends(get_licensed_user),
    service: FeedOptimizationV2Service = Depends(
        get_feed_optimization_v2_service
    ),
):
    return service.formulate(formulation_request)
