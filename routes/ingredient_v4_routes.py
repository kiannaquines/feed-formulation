from fastapi import APIRouter, Depends

from api.dependencies import get_ingredient_service, get_licensed_user
from api.openapi import (
    OWNED_RESOURCE_RESPONSES,
    PROTECTED_RESPONSES,
    VALIDATION_RESPONSE,
)
from schema.feed_v4 import (
    IngredientV4Create,
    IngredientV4ListResponse,
    IngredientV4Response,
)
from schema.schema import DetailResponse
from services import IngredientService


ingredient_v4_router = APIRouter(tags=["Ingredients V4"])


@ingredient_v4_router.get(
    "/ingredients/all",
    response_model=IngredientV4ListResponse | DetailResponse,
    summary="List visible ingredients with dynamic compositions",
    description=(
        "Return owned and shared ingredients with their JSON nutrient compositions."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_ingredients_v4(
    auth_user: dict = Depends(get_licensed_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.list_visible_v4(auth_user["user_id"])


@ingredient_v4_router.post(
    "/ingredients/create",
    response_model=IngredientV4Response,
    summary="Create an ingredient with a dynamic composition",
    description=(
        "Save an owned ingredient and its nutrient name/value JSON composition."
    ),
    responses={
        **PROTECTED_RESPONSES,
        409: {"model": DetailResponse, "description": "Name or quota conflict."},
        **VALIDATION_RESPONSE,
    },
)
def create_ingredient_v4(
    data: IngredientV4Create,
    auth_user: dict = Depends(get_licensed_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.create(data, auth_user["user_id"], auth_user["device_id"])


@ingredient_v4_router.put(
    "/ingredients/update/{ingredient_id}",
    response_model=IngredientV4Response,
    summary="Replace an owned dynamic ingredient",
    description="Replace an owned ingredient's metadata and full nutrient composition.",
    responses={
        **OWNED_RESOURCE_RESPONSES,
        409: {
            "model": DetailResponse,
            "description": "Ingredient name already exists.",
        },
    },
)
def update_ingredient_v4(
    ingredient_id: int,
    data: IngredientV4Create,
    auth_user: dict = Depends(get_licensed_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.update(ingredient_id, data, auth_user["user_id"])


@ingredient_v4_router.delete(
    "/ingredients/delete/{ingredient_id}",
    response_model=DetailResponse,
    summary="Delete an owned ingredient",
    description="Delete an owned dynamic or legacy ingredient by ID.",
    responses=OWNED_RESOURCE_RESPONSES,
)
def delete_ingredient_v4(
    ingredient_id: int,
    auth_user: dict = Depends(get_licensed_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.delete(ingredient_id, auth_user["user_id"])
