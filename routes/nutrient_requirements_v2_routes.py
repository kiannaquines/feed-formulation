from fastapi import APIRouter, Depends, status

from api.dependencies import get_licensed_user, get_nutrient_requirement_service
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.feed_v3 import NutrientRequirementV2Create, NutrientRequirementV2CreateResponse
from services import NutrientRequirementService

nutrient_requirements_v2_router = APIRouter(tags=["Nutrient Requirements V2"])


@nutrient_requirements_v2_router.post(
    "/nutrient-requirements/create",
    response_model=NutrientRequirementV2CreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a nutrient requirement with ten-nutrient composition",
    description=(
        "Create a named nutrient target owned by the authenticated user, using "
        "the same ten-nutrient composition as V3 feed formulation (CP, crude fat, "
        "crude fiber, ME, calcium, total P, available P, lysine, methionine, and "
        "methionine plus cystine). Ownership is derived from the Bearer token and "
        "cannot be supplied in the request."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def create_nutrient_requirement_v2(
    nutrient_requirement: NutrientRequirementV2Create,
    auth_user: dict = Depends(get_licensed_user),
    service: NutrientRequirementService = Depends(get_nutrient_requirement_service),
):
    return service.create(
        nutrient_requirement, auth_user["user_id"], auth_user["device_id"]
    )
