from pydantic import BaseModel, ConfigDict, Field

from schema.schema import (
    NutrientAchievementItemResponse,
    OptimizationSuccessResponse,
)


class NutrientsV3(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    protein_percent: float = Field(ge=0, le=100, description="CP: crude protein (%)")
    fat_percent: float = Field(ge=0, le=100, description="Cfat: crude fat (%)")
    fiber_percent: float = Field(ge=0, le=100, description="Cfiber: crude fiber (%)")
    energy_me: float = Field(ge=0, description="Metabolizable energy (kcal/kg), not %")
    calcium_percent: float = Field(ge=0, le=100, description="Calcium (%)")
    phosphorus_percent: float = Field(
        ge=0, le=100, description="Total P: total phosphorus (%)"
    )
    available_phosphorus_percent: float = Field(
        ge=0, le=100, description="Avail. P: available phosphorus (%)"
    )
    lysine_percent: float = Field(ge=0, le=100, description="Lysine (%)")
    methionine_percent: float = Field(ge=0, le=100, description="Met: methionine (%)")
    methionine_cystine_percent: float = Field(
        ge=0, le=100, description="M+C: methionine plus cystine (%)"
    )


class IngredientV3(NutrientsV3):
    name: str = Field(min_length=1)
    cost_per_kg: float = Field(ge=0)
    min_percentage: float = Field(0.0, ge=0, le=1)
    max_percentage: float = Field(1.0, ge=0, le=1)


class FeedFormulationV3Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredients: list[IngredientV3]
    nutrient_requirements: NutrientsV3
    optimization_method: str = Field("highs", description="SciPy linprog method")


class NutrientAchievementV3Response(BaseModel):
    protein_percent: NutrientAchievementItemResponse
    fat_percent: NutrientAchievementItemResponse
    fiber_percent: NutrientAchievementItemResponse
    energy_me: NutrientAchievementItemResponse
    calcium_percent: NutrientAchievementItemResponse
    phosphorus_percent: NutrientAchievementItemResponse
    available_phosphorus_percent: NutrientAchievementItemResponse
    lysine_percent: NutrientAchievementItemResponse
    methionine_percent: NutrientAchievementItemResponse
    methionine_cystine_percent: NutrientAchievementItemResponse


class OptimizationV3SuccessResponse(OptimizationSuccessResponse):
    nutrient_achievement: NutrientAchievementV3Response


class NutrientRequirementV2Create(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "nutrient_requirement_name": "Standard Layer Diet",
                "nutrient_requirement_description": "A balanced diet for laying hens.",
                "composition": {
                    "protein_percent": 16.0,
                    "fat_percent": 4.0,
                    "fiber_percent": 5.0,
                    "energy_me": 2800,
                    "calcium_percent": 3.5,
                    "phosphorus_percent": 0.65,
                    "available_phosphorus_percent": 0.45,
                    "lysine_percent": 0.75,
                    "methionine_percent": 0.35,
                    "methionine_cystine_percent": 0.6,
                },
            },
        },
    )

    nutrient_requirement_name: str
    nutrient_requirement_description: str
    composition: NutrientsV3


class NutrientRequirementV2CreateResponse(BaseModel):
    detail: str
    nutrient_info: NutrientRequirementV2Create
