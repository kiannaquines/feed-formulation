from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class OTPVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_token: str
    otp_code: str


class APIKeyCreate(BaseModel):
    key_name: str


class APIKeyResponse(BaseModel):
    api_key: str
    key_name: str
    message: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str


class Ingredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    cost_per_kg: float
    protein_percent: float = Field(0.0, ge=0.0)
    energy_me: float = Field(0.0, ge=0.0)
    calcium_percent: float = Field(0.0, ge=0.0)
    phosphorus_percent: float = Field(0.0, ge=0.0)
    min_percentage: float = Field(0.0, ge=0.0, le=1.0)
    max_percentage: float = Field(1.0, ge=0.0, le=1.0)


class NutrientRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protein_percent: float
    energy_me: float
    calcium_percent: float
    phosphorus_percent: float


class FeedFormulationRequest(BaseModel):
    ingredients: list[Ingredient]
    nutrient_requirements: NutrientRequirement
    optimization_method: str = Field(
        "highs", description="e.g., 'highs', 'revised simplex', 'interior-point'"
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "ingredients": [
                    {
                        "name": "Corn",
                        "cost_per_kg": 0.25,
                        "protein_percent": 8.0,
                        "energy_me": 3.3,
                        "calcium_percent": 0.03,
                        "phosphorus_percent": 0.25,
                        "min_percentage": 0.1,
                        "max_percentage": 0.6,
                    },
                    {
                        "name": "Soybean Meal",
                        "cost_per_kg": 0.4,
                        "protein_percent": 44.0,
                        "energy_me": 2.8,
                        "calcium_percent": 0.3,
                        "phosphorus_percent": 0.65,
                        "min_percentage": 0.1,
                        "max_percentage": 0.4,
                    },
                ],
                "nutrient_requirements": {
                    "protein_percent": 18.0,
                    "energy_me": 3.0,
                    "calcium_percent": 0.9,
                    "phosphorus_percent": 0.45,
                },
                "optimization_method": "highs",
            }
        },
    )


class FeedFormulationPreset(BaseModel):
    preset_name: str = "custom"


class IngredientBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    price: float
    crude_protein: float
    crude_fat: float
    crude_fiber: float
    metabolized_energy: float
    calcium: float
    total_phosphorus: float
    avail_phosphorus: float
    lysine: float
    methionine: float
    m_c: float
    is_available: bool = True


class IngredientCreate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    created_at: datetime


class IngredientListResponse(BaseModel):
    detail: str
    ingredients: list[IngredientResponse]


class FeedFormulationWithPayloadRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "formulation_name": "Booster",
                "formulation_description": "A balanced diet for booster chickens.",
                "payload": {
                    "status": "success",
                    "summary": {
                        "total_ingredient_percentage": 100,
                        "cost_per_kg": 96.0373,
                    },
                },
            }
        },
    )

    formulation_name: str
    formulation_description: str
    payload: dict


class NutrientRequirementsBase(BaseModel):
    nutrient_requirement_name: str
    nutrient_requirement_description: str
    composition: dict
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "nutrient_requirement_name": "Standard Layer Diet",
                "nutrient_requirement_description": "A balanced diet for laying hens.",
                "composition": {
                    "protein_percent": 16.0,
                    "energy_me": 2.8,
                    "calcium_percent": 3.5,
                    "phosphorus_percent": 0.45,
                },
            },
        },
    )


class NutrientRequirementResponse(NutrientRequirementsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None


class NutrientRequirementListResponse(BaseModel):
    detail: str
    nutrient_requirements: list[NutrientRequirementResponse]


class NutrientRequirementCreateResponse(BaseModel):
    detail: str
    nutrient_info: NutrientRequirementsBase


class NutrientRequirementUpdateResponse(BaseModel):
    detail: str
    nutrient_info: NutrientRequirementResponse


class FeedFormulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    formulation_name: str | None
    formulation_description: str | None
    user_id: int
    payload: dict


class FeedFormulationUpdateResponse(BaseModel):
    message: str
    formulation: FeedFormulationResponse


class DetailResponse(BaseModel):
    detail: str


class RegistrationResponse(BaseModel):
    message: str
    note: str


class AuthenticatedUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr


class TokenResponse(BaseModel):
    message: str
    access_token: str
    token_type: Literal["bearer"]
    expires_in_hours: int
    user: AuthenticatedUserResponse


class OTPChallengeResponse(BaseModel):
    message: str
    session_token: str
    current_otp: str
    expires_in_minutes: int
    note: str


class RootResponse(BaseModel):
    message: str
    client_ip: str
    documentation: str
    hostname: str


class HealthDetailsResponse(BaseModel):
    otp_enabled: bool
    uptime_seconds: int
    hostname: str
    cpu_usage_percent: float
    memory_usage_percent: float


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    details: HealthDetailsResponse


class FormulationInputIngredientResponse(BaseModel):
    name: str
    cost_per_kg: float
    min_percentage: float
    max_percentage: float


class FormulationInputsResponse(BaseModel):
    total_ingredients: int
    ingredients: list[FormulationInputIngredientResponse]
    nutrient_targets: dict[str, float]


class OptimizationDetailsResponse(BaseModel):
    solver_status: str
    iterations: int
    total_cost_per_kg: float


class IngredientCompositionResponse(BaseModel):
    name: str
    percentage: float
    cost_contribution: float
    included: bool


class NutrientAchievementItemResponse(BaseModel):
    achieved: float
    required: float


class NutrientAchievementResponse(BaseModel):
    protein_percent: NutrientAchievementItemResponse
    energy_me: NutrientAchievementItemResponse
    calcium_percent: NutrientAchievementItemResponse
    phosphorus_percent: NutrientAchievementItemResponse


class FormulationSummaryResponse(BaseModel):
    total_ingredient_percentage: float
    active_ingredients_count: int
    cost_per_kg: float
    formulation_feasible: Literal[True]


class OptimizationSuccessResponse(BaseModel):
    formulation_inputs: FormulationInputsResponse
    status: Literal["success"]
    message: str
    optimization_details: OptimizationDetailsResponse
    ingredient_composition: list[IngredientCompositionResponse]
    nutrient_achievement: NutrientAchievementResponse
    summary: FormulationSummaryResponse


class OptimizationErrorDetailsResponse(BaseModel):
    solver_status_code: int
    solver_message: str
    possible_causes: list[str]
    suggestions: list[str]


class OptimizationFailureResponse(BaseModel):
    formulation_inputs: FormulationInputsResponse
    status: Literal["failure"]
    detail: str
    error_details: OptimizationErrorDetailsResponse
    formulation_feasible: Literal[False]
