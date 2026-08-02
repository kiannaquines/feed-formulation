from fastapi import APIRouter, Depends, status

from api.dependencies import get_current_user, get_nutrient_requirement_service
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
