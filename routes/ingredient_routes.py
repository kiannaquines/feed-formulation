from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_ingredient_service
from schema.schema import (
    DetailResponse,
    IngredientCreate,
    IngredientListResponse,
    IngredientResponse,
)
from services import IngredientService

ingredient_router = APIRouter(tags=["Ingredients"])


@ingredient_router.get(
    "/ingredients/all", response_model=IngredientListResponse | DetailResponse
)
def get_ingredients(
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.list_visible(auth_user["user_id"])


@ingredient_router.post(
    "/ingredients/create", response_model=IngredientResponse
)
def create_ingredient(
    data: IngredientCreate,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.create(data, auth_user["user_id"])


@ingredient_router.put(
    "/ingredients/update/{ingredient_id}", response_model=IngredientResponse
)
def update_ingredient(
    ingredient_id: int,
    data: IngredientCreate,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.update(ingredient_id, data, auth_user["user_id"])


@ingredient_router.delete(
    "/ingredients/delete/{ingredient_id}", response_model=DetailResponse
)
def delete_ingredient(
    ingredient_id: int,
    auth_user: dict = Depends(get_current_user),
    service: IngredientService = Depends(get_ingredient_service),
):
    return service.delete(ingredient_id, auth_user["user_id"])
