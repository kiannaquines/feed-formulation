from fastapi import APIRouter, Depends, status

from api.dependencies import get_current_user, get_nutrient_requirement_service
from api.openapi import OWNED_RESOURCE_RESPONSES, PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.schema import (
    DetailResponse,
    NutrientRequirementCreateResponse,
    NutrientRequirementListResponse,
    NutrientRequirementUpdateResponse,
    NutrientRequirementsBase,
)
from services import NutrientRequirementService

nutrient_requirements_router = APIRouter(tags=["Nutrient Requirements"])


@nutrient_requirements_router.get(
    "/nutrient-requirements/all",
    response_model=NutrientRequirementListResponse | DetailResponse,
    status_code=status.HTTP_200_OK,
    summary="List visible nutrient requirements",
    description=(
        "Return nutrient requirements owned by the authenticated user together with "
        "shared legacy requirements whose owner is null."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_nutrient_requirements(
    auth_user: dict = Depends(get_current_user),
    service: NutrientRequirementService = Depends(
        get_nutrient_requirement_service
    ),
):
    return service.list_visible(auth_user["user_id"])


@nutrient_requirements_router.post(
    "/nutrient-requirements/create",
    response_model=NutrientRequirementCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a nutrient requirement",
    description=(
        "Create a named nutrient target owned by the authenticated user. Ownership "
        "is derived from the Bearer token and cannot be supplied in the request."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def create_nutrient_requirements(
    nutrient_requirement: NutrientRequirementsBase,
    auth_user: dict = Depends(get_current_user),
    service: NutrientRequirementService = Depends(
        get_nutrient_requirement_service
    ),
):
    return service.create(nutrient_requirement, auth_user["user_id"])


@nutrient_requirements_router.put(
    "/nutrient-requirements/update/{nutrient_requirement_id}",
    response_model=NutrientRequirementUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an owned nutrient requirement",
    description=(
        "Replace the name, description, and composition of a nutrient requirement "
        "owned by the authenticated user."
    ),
    responses=OWNED_RESOURCE_RESPONSES,
)
@nutrient_requirements_router.put(
    "/nutrient-requrments/update/{nutrient_requirement_id}",
    response_model=NutrientRequirementUpdateResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    deprecated=True,
)
def update_nutrient_requirement(
    nutrient_requirement_id: int,
    payload: NutrientRequirementsBase,
    auth_user: dict = Depends(get_current_user),
    service: NutrientRequirementService = Depends(
        get_nutrient_requirement_service
    ),
):
    return service.update(nutrient_requirement_id, payload, auth_user["user_id"])


@nutrient_requirements_router.delete(
    "/nutrient-requirements/delete/{nutrient_requirement_id}",
    response_model=DetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an owned nutrient requirement",
    description=(
        "Delete a nutrient requirement owned by the authenticated user. Shared "
        "requirements cannot be deleted."
    ),
    responses=OWNED_RESOURCE_RESPONSES,
)
@nutrient_requirements_router.delete(
    "/nutrient-requrments/delete/{nutrient_requirement_id}",
    response_model=DetailResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    deprecated=True,
)
def delete_nutrient_requirement(
    nutrient_requirement_id: int,
    auth_user: dict = Depends(get_current_user),
    service: NutrientRequirementService = Depends(
        get_nutrient_requirement_service
    ),
):
    return service.delete(nutrient_requirement_id, auth_user["user_id"])
