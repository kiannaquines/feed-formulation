from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_ingredient_service
from api.openapi import (
    OWNED_RESOURCE_RESPONSES,
    PROTECTED_RESPONSES,
    VALIDATION_RESPONSE,
)
from schema.schema import (
    DetailResponse,
    IngredientCreate,
    IngredientListResponse,
    IngredientResponse,
)
from services import IngredientService

ingredient_router = APIRouter(tags=["Ingredients"])


@ingredient_router.get(
    "/ingredients/all",
    response_model=IngredientListResponse | DetailResponse,
    summary="List visible ingredients",
    description=(
        "Return ingredients owned by the authenticated user together with shared "
        "legacy ingredients whose owner is null."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_ingredients(
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.list_visible(auth_user["user_id"])


@ingredient_router.post(
    "/ingredients/create",
    response_model=IngredientResponse,
    summary="Create an ingredient",
    description=(
        "Create an ingredient owned by the authenticated user. Ownership is always "
        "derived from the Bearer token. Ingredient names are globally unique."
    ),
    responses={
        **PROTECTED_RESPONSES,
        409: {"model": DetailResponse, "description": "Ingredient name already exists."},
        **VALIDATION_RESPONSE,
    },
)
def create_ingredient(
    data: IngredientCreate,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.create(data, auth_user["user_id"])


@ingredient_router.put(
    "/ingredients/update/{ingredient_id}",
    response_model=IngredientResponse,
    summary="Update an owned ingredient",
    description=(
        "Replace the editable composition, price, and availability fields of an "
        "ingredient owned by the authenticated user."
    ),
    responses={
        **OWNED_RESOURCE_RESPONSES,
        409: {"model": DetailResponse, "description": "Ingredient name already exists."},
    },
)
def update_ingredient(
    ingredient_id: int,
    data: IngredientCreate,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.update(ingredient_id, data, auth_user["user_id"])


@ingredient_router.delete(
    "/ingredients/delete/{ingredient_id}",
    response_model=DetailResponse,
    summary="Delete an owned ingredient",
    description=(
        "Delete an ingredient owned by the authenticated user. Shared ingredients "
        "cannot be deleted."
    ),
    responses=OWNED_RESOURCE_RESPONSES,
)
def delete_ingredient(
    ingredient_id: int,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.delete(ingredient_id, auth_user["user_id"])
