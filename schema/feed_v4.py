from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schema.schema import NutrientAchievementItemResponse, OptimizationSuccessResponse


NutrientValue = Annotated[float, Field(ge=0, allow_inf_nan=False)]
RESERVED_NUTRIENT_NAMES = {
    "name", "cost_per_kg", "min_percentage", "max_percentage",
    "total_ingredient_percentage", "model_dump",
}


def validate_nutrient_names(values: dict[str, float]) -> dict[str, float]:
    if any(
        not name or name != name.strip() or name.startswith("_")
        or name in RESERVED_NUTRIENT_NAMES
        for name in values
    ):
        raise ValueError("Nutrient names must be nonblank, trimmed, and not reserved")
    return values


class IngredientV4Create(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    composition: dict[str, NutrientValue] = Field(min_length=1)
    is_available: bool = True

    @field_validator("composition")
    @classmethod
    def valid_composition(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_nutrient_names(values)


class IngredientV4Response(IngredientV4Create):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    created_at: datetime


class IngredientV4ListResponse(BaseModel):
    detail: str
    ingredients: list[IngredientV4Response]


class FormulationIngredientV4(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1)
    cost_per_kg: float = Field(ge=0)
    min_percentage: float = Field(0.0, ge=0, le=1)
    max_percentage: float = Field(1.0, ge=0, le=1)
    nutrients: dict[str, NutrientValue] = Field(min_length=1)

    @field_validator("nutrients")
    @classmethod
    def valid_nutrients(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_nutrient_names(values)


class FeedFormulationV4Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredients: list[FormulationIngredientV4] = Field(min_length=1)
    nutrient_requirements: dict[str, NutrientValue] = Field(min_length=1)
    optimization_method: str = Field("highs", description="SciPy linprog method")

    @field_validator("nutrient_requirements")
    @classmethod
    def valid_requirements(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_nutrient_names(values)

    @model_validator(mode="after")
    def ingredients_cover_requirements(self):
        required = set(self.nutrient_requirements)
        for ingredient in self.ingredients:
            missing = required - ingredient.nutrients.keys()
            if missing:
                raise ValueError(
                    f"Ingredient {ingredient.name!r} is missing nutrients: "
                    f"{', '.join(sorted(missing))}"
                )
        return self


class OptimizationV4SuccessResponse(OptimizationSuccessResponse):
    nutrient_achievement: dict[str, NutrientAchievementItemResponse]
