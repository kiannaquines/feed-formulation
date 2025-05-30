from pydantic import BaseModel, Field, EmailStr, Json
from typing import List
from datetime import datetime

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class OTPVerification(BaseModel):
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
    name: str
    cost_per_kg: float
    protein_percent: float = Field(0.0, ge=0.0)
    energy_me: float = Field(0.0, ge=0.0)
    calcium_percent: float = Field(0.0, ge=0.0)
    phosphorus_percent: float = Field(0.0, ge=0.0)
    min_percentage: float = Field(0.0, ge=0.0, le=1.0)
    max_percentage: float = Field(1.0, ge=0.0, le=1.0)

class NutrientRequirement(BaseModel):
    protein_percent: float
    energy_me: float
    calcium_percent: float
    phosphorus_percent: float

class FeedFormulationRequest(BaseModel):
    ingredients: List[Ingredient]
    nutrient_requirements: NutrientRequirement
    optimization_method: str = Field("highs", description="e.g., 'highs', 'revised simplex', 'interior-point'")

    class Config:
        json_schema_extra = {
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
                        "max_percentage": 0.6
                    },
                    {
                        "name": "Soybean Meal",
                        "cost_per_kg": 0.4,
                        "protein_percent": 44.0,
                        "energy_me": 2.8,
                        "calcium_percent": 0.3,
                        "phosphorus_percent": 0.65,
                        "min_percentage": 0.1,
                        "max_percentage": 0.4
                    }
                ],
                "nutrient_requirements": {
                    "protein_percent": 18.0,
                    "energy_me": 3.0,
                    "calcium_percent": 0.9,
                    "phosphorus_percent": 0.45
                },
                "optimization_method": "highs"
            }
        }

class FeedFormulationPreset(BaseModel):
    preset_name: str = "custom"

class IngredientBase(BaseModel):
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
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FeedFormulationWithPayloadRequest(BaseModel):
    formulation_name: str
    formulation_description: str
    user_id: int
    payload: dict

    class Config:
        json_schema_extra = {
            "example": {
                "formulation_name": "Booster",
                "formulation_description": "A balanced diet for booster chickens.",
                "user_id": 1,
                "payload": {
                    "formulation_inputs": {
                        "total_ingredients": 15,
                        "ingredients": [
                        {
                            "name": "Corn",
                            "cost_per_kg": 75,
                            "min_percentage": 45,
                            "max_percentage": 70
                        },
                        {
                            "name": "Soybean Meal",
                            "cost_per_kg": 100,
                            "min_percentage": 25,
                            "max_percentage": 30
                        },
                        {
                            "name": "Skimmilk",
                            "cost_per_kg": 250,
                            "min_percentage": 2,
                            "max_percentage": 100
                        },
                        {
                            "name": "Rice bran D1",
                            "cost_per_kg": 80,
                            "min_percentage": 5,
                            "max_percentage": 50
                        },
                        {
                            "name": "Fish Meal",
                            "cost_per_kg": 150,
                            "min_percentage": 1,
                            "max_percentage": 50
                        },
                        {
                            "name": "Coconut Oil",
                            "cost_per_kg": 50,
                            "min_percentage": 0,
                            "max_percentage": 100
                        },
                        {
                            "name": "Limestone",
                            "cost_per_kg": 6.3,
                            "min_percentage": 0,
                            "max_percentage": 100
                        },
                        {
                            "name": "Monodical Phosphate",
                            "cost_per_kg": 80,
                            "min_percentage": 0,
                            "max_percentage": 100
                        },
                        {
                            "name": "Vitamin Premix",
                            "cost_per_kg": 185,
                            "min_percentage": 0.25,
                            "max_percentage": 0.25
                        },
                        {
                            "name": "Choline",
                            "cost_per_kg": 640,
                            "min_percentage": 0.25,
                            "max_percentage": 0.25
                        },
                        {
                            "name": "Salt",
                            "cost_per_kg": 28,
                            "min_percentage": 0.25,
                            "max_percentage": 0.25
                        },
                        {
                            "name": "L-lysine",
                            "cost_per_kg": 1279,
                            "min_percentage": 0.25,
                            "max_percentage": 0.25
                        },
                        {
                            "name": "DL-Methionine",
                            "cost_per_kg": 120,
                            "min_percentage": 0,
                            "max_percentage": 100
                        },
                        {
                            "name": "Antioxidant",
                            "cost_per_kg": 200,
                            "min_percentage": 0.25,
                            "max_percentage": 0.25
                        },
                        {
                            "name": "Azolla",
                            "cost_per_kg": 350,
                            "min_percentage": 1,
                            "max_percentage": 1
                        }
                        ],
                        "nutrient_targets": {
                            "protein_percent": 22.3,
                            "energy_me": 2.9,
                            "calcium_percent": 0.87,
                            "phosphorus_percent": 0.48
                        }
                    },
                    "status": "success",
                    "message": "Optimal feed formulation found.",
                    "optimization_details": {
                        "solver_status": "Optimization terminated successfully. (HiGHS Status 7: Optimal)",
                        "iterations": 5,
                        "total_cost_per_kg": 96.0373
                    },
                    "ingredient_composition": [
                        {
                            "name": "Corn",
                            "percentage": 45,
                            "cost_contribution": 33.75,
                            "included": True
                        },
                        {
                            "name": "Soybean Meal",
                            "percentage": 30,
                            "cost_contribution": 30,
                            "included": True
                        },
                        {
                            "name": "Skimmilk",
                            "percentage": 2,
                            "cost_contribution": 5,
                            "included": True
                        },
                        {
                            "name": "Rice bran D1",
                            "percentage": 8.976,
                            "cost_contribution": 7.1808,
                            "included": True
                        },
                        {
                            "name": "Fish Meal",
                            "percentage": 1,
                            "cost_contribution": 1.5,
                            "included": True
                        },
                        {
                            "name": "Coconut Oil",
                            "percentage": 2.7661,
                            "cost_contribution": 1.3831,
                            "included": True
                        },
                        {
                            "name": "Limestone",
                            "percentage": 0.8755,
                            "cost_contribution": 0.0552,
                            "included": True
                        },
                        {
                            "name": "Monodical Phosphate",
                            "percentage": 1.8014,
                            "cost_contribution": 1.4411,
                            "included": True
                        },
                        {
                            "name": "Vitamin Premix",
                            "percentage": 0.25,
                            "cost_contribution": 0.4625,
                            "included": True
                        },
                        {
                            "name": "Choline",
                            "percentage": 0.25,
                            "cost_contribution": 1.6,
                            "included": True
                        },
                        {
                            "name": "Salt",
                            "percentage": 0.25,
                            "cost_contribution": 0.07,
                            "included": True
                        },
                        {
                            "name": "L-lysine",
                            "percentage": 0.25,
                            "cost_contribution": 3.1975,
                            "included": True
                        },
                        {
                            "name": "DL-Methionine",
                            "percentage": 5.331,
                            "cost_contribution": 6.3972,
                            "included": True
                        },
                        {
                            "name": "Antioxidant",
                            "percentage": 0.25,
                            "cost_contribution": 0.5,
                            "included": True
                        },
                        {
                            "name": "Azolla",
                            "percentage": 1,
                            "cost_contribution": 3.5,
                            "included": True
                        }
                    ],
                    "nutrient_achievement": {
                        "protein_percent": {
                            "achieved": 22.3,
                            "required": 22.3
                        },
                        "energy_me": {
                            "achieved": 2.9,
                            "required": 2.9
                        },
                        "calcium_percent": {
                            "achieved": 0.87,
                            "required": 0.87
                        },
                        "phosphorus_percent": {
                            "achieved": 0.48,
                            "required": 0.48
                        }
                    },
                    "summary": {
                        "total_ingredient_percentage": 100,
                        "active_ingredients_count": 15,
                        "cost_per_kg": 96.0373,
                        "formulation_feasible": True
                    }
                }
            }
        }

class NutrientRequirementsBase(BaseModel):
    nutrient_requirement_name: str
    nutrient_requirement_description: str
    composition: dict

    class Config:
        json_schema_extra = {
            "example": {
                "nutrient_requirement_name": "Standard Layer Diet",
                "nutrient_requirement_description": "A balanced diet for laying hens.",
                "composition": {
                    "protein_percent": 16.0,
                    "energy_me": 2.8,
                    "calcium_percent": 3.5,
                    "phosphorus_percent": 0.45
                }
            }
        }