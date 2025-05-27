from pydantic import BaseModel, Field, EmailStr
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
                        "energy_me": 3300,
                        "calcium_percent": 0.03,
                        "phosphorus_percent": 0.25,
                        "min_percentage": 0.1,
                        "max_percentage": 0.6
                    },
                    {
                        "name": "Soybean Meal",
                        "cost_per_kg": 0.4,
                        "protein_percent": 44.0,
                        "energy_me": 2800,
                        "calcium_percent": 0.3,
                        "phosphorus_percent": 0.65,
                        "min_percentage": 0.1,
                        "max_percentage": 0.4
                    }
                ],
                "nutrient_requirements": {
                    "protein_percent": 18.0,
                    "energy_me": 3000,
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