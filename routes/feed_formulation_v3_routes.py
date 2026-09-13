from fastapi import APIRouter, Depends

from api.dependencies import get_feed_optimization_v3_service, get_licensed_user
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.feed_v3 import FeedFormulationV3Request, OptimizationV3SuccessResponse
from schema.schema import DetailResponse, OptimizationV2FailureResponse
from services import FeedOptimizationV3Service


feed_formulation_v3_router = APIRouter(tags=["Feed Formulation V3"])


@feed_formulation_v3_router.post(
    "/feed/formulate",
    response_model=OptimizationV3SuccessResponse | OptimizationV2FailureResponse,
    summary="Calculate a V3 least-cost feed formulation with ten nutrients",
    description=(
        "Match CP, crude fat, crude fiber, ME, calcium, total P, available P, "
        "lysine, methionine, and methionine plus cystine targets exactly. "
        "Supply all ten values for every ingredient and the nutrient requirements; "
        "use explicit zero for known zero content. Nutrients use percentage points "
        "(23 means 23%), except ME in kcal/kg. Ingredient inclusion bounds use "
        "fractions from 0 to 1. Infeasible requests return a bounded candidate "
        "and diagnostics for all ten nutrients and the mixture total; candidates "
        "may not total 100% and remain marked infeasible."
    ),
    responses={
        **PROTECTED_RESPONSES,
        400: {
            "model": DetailResponse,
            "description": "Ingredients or inclusion bounds are invalid.",
        },
        500: {
            "model": DetailResponse,
            "description": "The primary or diagnostic solver could not be executed.",
        },
        **VALIDATION_RESPONSE,
    },
)
def feed_formulator_v3(
    formulation_request: FeedFormulationV3Request,
    _auth_user: dict = Depends(get_licensed_user),
    service: FeedOptimizationV3Service = Depends(get_feed_optimization_v3_service),
):
    return service.formulate(formulation_request)
