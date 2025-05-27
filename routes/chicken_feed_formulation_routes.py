from fastapi import APIRouter, Depends, HTTPException, status
from schema.schema import *
from core.authentication import *
import numpy as np

chicken_feed_formulation_router = APIRouter(tags=["Chicken Feed Formulation"])

@chicken_feed_formulation_router.post("/chicken/feed/formulate")
async def feed_formulator(
    formulation_request: FeedFormulationRequest,
    auth_user: dict = Depends(verify_jwt_token)
):
    """Dynamic feed formulation endpoint (protected by JWT token)"""

    from scipy.optimize import linprog

    if not formulation_request.ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ingredient must be provided"
        )

    ingredients = [ing.name for ing in formulation_request.ingredients]
    costs = np.array([ing.cost_per_kg for ing in formulation_request.ingredients])
    
    nutrient_matrix = np.array([
        [ing.protein_percent for ing in formulation_request.ingredients],
        [ing.energy_me for ing in formulation_request.ingredients],
        [ing.calcium_percent for ing in formulation_request.ingredients],
        [ing.phosphorus_percent for ing in formulation_request.ingredients]
    ])
    
    nutrient_req = np.array([
        formulation_request.nutrient_requirements.protein_percent,
        formulation_request.nutrient_requirements.energy_me,
        formulation_request.nutrient_requirements.calcium_percent,
        formulation_request.nutrient_requirements.phosphorus_percent
    ])
    
    ingredient_min = np.array([ing.min_percentage for ing in formulation_request.ingredients])
    ingredient_max = np.array([ing.max_percentage for ing in formulation_request.ingredients])
    
    if any(ingredient_min < 0) or any(ingredient_max > 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient percentages must be between 0 and 1"
        )
    
    if any(ingredient_min > ingredient_max):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum percentage cannot be greater than maximum percentage"
        )
    
    sum_constraint = np.ones((1, len(ingredients)))
    A_eq = np.vstack((sum_constraint, nutrient_matrix))
    b_eq = np.hstack(([1.0], nutrient_req))
    bounds = list(zip(ingredient_min, ingredient_max))

    try:
        result = linprog(
            costs, 
            A_eq=A_eq, 
            b_eq=b_eq, 
            bounds=bounds, 
            method=formulation_request.optimization_method
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )

    base_response = {
        "authenticated_user": auth_user['username'],
        "user_id": auth_user['user_id'],
        "formulation_inputs": {
            "total_ingredients": len(ingredients),
            "optimization_method": formulation_request.optimization_method,
            "ingredients": [
                {
                    "name": ing.name,
                    "cost_per_kg": ing.cost_per_kg,
                    "min_percentage": ing.min_percentage * 100,
                    "max_percentage": ing.max_percentage * 100
                }
                for ing in formulation_request.ingredients
            ],
            "nutrient_targets": {
                "protein_percent": formulation_request.nutrient_requirements.protein_percent,
                "energy_me": formulation_request.nutrient_requirements.energy_me,
                "calcium_percent": formulation_request.nutrient_requirements.calcium_percent,
                "phosphorus_percent": formulation_request.nutrient_requirements.phosphorus_percent
            }
        }
    }

    if result.success:
        ingredient_percentages = result.x * 100
        nutrient_values = nutrient_matrix @ result.x
        costs_breakdown = costs * result.x

        base_response.update({
            "status": "success",
            "message": "Optimal feed formulation found.",
            "optimization_details": {
                "solver_status": str(result.message),
                "iterations": int(getattr(result, 'nit', 0)),
                "total_cost_per_kg": round(float(result.fun), 4)
            },
            "ingredient_composition": [
                {
                    "name": ingredients[i],
                    "percentage": round(float(ingredient_percentages[i]), 4),
                    "cost_contribution": round(float(costs_breakdown[i]), 4),
                    "included": bool(float(ingredient_percentages[i]) > 0.001)
                }
                for i in range(len(ingredients))
            ],
            "nutrient_achievement": {
                "protein_percent": {
                    "achieved": round(float(nutrient_values[0]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.protein_percent), 4),
                    "difference": round(float(nutrient_values[0] - formulation_request.nutrient_requirements.protein_percent), 4)
                },
                "energy_me": {
                    "achieved": round(float(nutrient_values[1]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.energy_me), 4),
                    "difference": round(float(nutrient_values[1] - formulation_request.nutrient_requirements.energy_me), 4)
                },
                "calcium_percent": {
                    "achieved": round(float(nutrient_values[2]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.calcium_percent), 4),
                    "difference": round(float(nutrient_values[2] - formulation_request.nutrient_requirements.calcium_percent), 4)
                },
                "phosphorus_percent": {
                    "achieved": round(float(nutrient_values[3]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.phosphorus_percent), 4),
                    "difference": round(float(nutrient_values[3] - formulation_request.nutrient_requirements.phosphorus_percent), 4)
                }
            },
            "summary": {
                "total_ingredient_percentage": round(float(sum(result.x) * 100), 6),
                "active_ingredients_count": int(sum(1 for x in ingredient_percentages if float(x) > 0.001)),
                "cost_per_kg": round(float(result.fun), 4),
                "formulation_feasible": True
            }
        })
    else:
        base_response.update({
            "status": "failure",
            "message": "No optimal solution found.",
            "error_details": {
                "solver_status_code": result.status,
                "solver_message": result.message,
                "possible_causes": [
                    "Nutrient requirements may be impossible to meet with given ingredients",
                    "Ingredient constraints may be too restrictive",
                    "Cost optimization may have no feasible solution"
                ],
                "suggestions": [
                    "Review nutrient requirements and ensure they are achievable",
                    "Check ingredient min/max percentage constraints",
                    "Consider adding more ingredient options",
                    "Verify ingredient nutrient compositions are correct"
                ]
            },
            "formulation_feasible": False
        })

    return base_response