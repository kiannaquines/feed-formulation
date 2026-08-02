from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr
    password: str
    installation_id: UUID
    device_name: str = Field(min_length=1, max_length=120)
    device_type: Literal["phone", "laptop", "desktop"]
    referral_code: str | None = Field(default=None, min_length=6, max_length=16)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(description="Registered username or email address")
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
    series_id: int
    parent_version_id: int | None
    version_number: int
    created_at: datetime
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
    database_status: Literal["healthy", "unhealthy"]
    database_latency_ms: float | None


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


class FailedIngredientCompositionResponse(IngredientCompositionResponse):
    status: Literal["excluded", "included", "at_minimum", "at_maximum"]
    issues: list[
        Literal["minimum_bound_active", "maximum_bound_active"]
    ]


class ConstraintDiagnosticResponse(BaseModel):
    achieved: float
    required: float
    difference: float
    status: Literal["met", "under", "over"]


class FailedFormulationSummaryResponse(BaseModel):
    total_ingredient_percentage: float
    active_ingredients_count: int
    cost_per_kg: float
    normalized_violation_score: float
    formulation_feasible: Literal[False]


class OptimizationV2FailureResponse(OptimizationFailureResponse):
    ingredient_composition: list[FailedIngredientCompositionResponse]
    constraint_diagnostics: dict[str, ConstraintDiagnosticResponse]
    failed_constraints: list[str]
    summary: FailedFormulationSummaryResponse


class PlanResponse(BaseModel):
    code: Literal["starter", "premium", "ultra"]
    name: str
    currency: Literal["PHP"]
    monthly_price: int
    duration_days: Literal[30]
    ingredient_limit: int | None
    requirement_limit: int | None
    formulation_limit: None
    version_number: int
    effective_at: datetime


class PricingPlanVersionResponse(PlanResponse):
    id: int
    created_by_user_id: int | None
    created_at: datetime


class PricingPlanVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_price: int = Field(gt=0)
    ingredient_limit: int | None = Field(
        default=None,
        gt=0,
        description="Omit to keep the current limit; send null for unlimited.",
    )
    requirement_limit: int | None = Field(
        default=None,
        gt=0,
        description="Omit to keep the current limit; send null for unlimited.",
    )


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    installation_id: str
    name: str
    device_type: Literal["phone", "laptop", "desktop"]
    is_active: bool
    created_at: datetime
    last_seen_at: datetime


class LicenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    device_id: int | None
    pricing_plan_version_id: int
    plan_code: Literal["starter", "premium", "ultra"]
    license_type: Literal["trial", "paid"]
    status: Literal["active", "revoked"]
    starts_at: datetime
    expires_at: datetime
    price_php: int
    payment_reference: str | None


class QuotaUsageResponse(BaseModel):
    used: int
    limit: int | None


class LicensingStatusResponse(BaseModel):
    status: Literal["active", "expired", "unlicensed"]
    device: DeviceResponse
    license: LicenseResponse | None
    ingredients: QuotaUsageResponse
    requirements: QuotaUsageResponse


class ReferralCreditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bonus_days: int
    claimed_license_id: int | None
    claimed_at: datetime | None
    created_at: datetime


class ReferralSummaryResponse(BaseModel):
    referral_code: str
    pending_referrals: int
    qualified_referrals: int
    credits: list[ReferralCreditResponse]


class ReferralClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    license_id: int


class LicenseActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    device_id: int
    plan_code: Literal["starter", "premium", "ultra"]
    payment_reference: str = Field(min_length=1, max_length=120)


class LicenseRenewalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: Literal["starter", "premium", "ultra"]
    payment_reference: str = Field(min_length=1, max_length=120)


class LicenseReassignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: int
    reason: str = Field(min_length=1, max_length=500)


class LicenseRevocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)
