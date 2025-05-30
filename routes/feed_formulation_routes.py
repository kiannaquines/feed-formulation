from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from schema.schema import *
from core.authentication import *
import numpy as np
from db.database import get_db
from models.models import FeedFormulation

feed_formulation_router = APIRouter(tags=["Feed Formulation"])

@feed_formulation_router.post("/feed/formulate")
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
        "formulation_inputs": {
            "total_ingredients": len(ingredients),
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
                },
                "energy_me": {
                    "achieved": round(float(nutrient_values[1]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.energy_me), 4),
                },
                "calcium_percent": {
                    "achieved": round(float(nutrient_values[2]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.calcium_percent), 4),
                },
                "phosphorus_percent": {
                    "achieved": round(float(nutrient_values[3]), 4),
                    "required": round(float(formulation_request.nutrient_requirements.phosphorus_percent), 4),
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
            "detail": "No optimal solution found.",
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

@feed_formulation_router.post("/feed/formulation/save", status_code=status.HTTP_201_CREATED)
async def save_formulation(
    formulation: FeedFormulationWithPayloadRequest,
    db=Depends(get_db),
    auth_user: dict = Depends(verify_jwt_token)
):
    try:
        if auth_user["user_id"] != formulation.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only save formulations for your own account."
            )

        new_entry = FeedFormulation(
            formulation_name=formulation.formulation_name,
            formulation_description=formulation.formulation_description,
            user_id=formulation.user_id,
            payload=formulation.payload
        )
        
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
                
        return {
            "detail": "Formulation saved successfully.",
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@feed_formulation_router.get('/feed/formulation/all', status_code=status.HTTP_200_OK)
async def get_all_formulation(db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    formulations = db.query(FeedFormulation).all()
    return formulations

@feed_formulation_router.delete('/feed/formulation/remove/{formulation_id}', status_code=status.HTTP_200_OK)
async def remove_formulation(formulation_id: int, db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    try:

        remove_formulation = db.query(FeedFormulation).filter(FeedFormulation.id == formulation_id).delete()
        db.commit()
        if remove_formulation:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail=f"Formulation details has been successfully removed."
            )
        else:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Formulation details not found."
            )
    
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occured: {str(e)}"
        )        

@feed_formulation_router.put('/feed/formulation/update/{formulation_id}', status_code=status.HTTP_200_OK)
async def update_formulation(
    formulation_id: int,
    payload: FeedFormulationWithPayloadRequest,
    db: Session = Depends(get_db),
    auth_user: dict = Depends(verify_jwt_token)
):
    try:
        if auth_user["user_id"] != payload.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to update formulations for other users."
            )

        formulation = db.query(FeedFormulation).filter(
            FeedFormulation.id == formulation_id,
            FeedFormulation.user_id == payload.user_id
        ).first()

        if not formulation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Formulation not found."
            )
        
        formulation.payload = payload.payload
        formulation.formulation_name = payload.formulation_name
        formulation.formulation_description = payload.formulation_description

        db.commit()
        db.refresh(formulation)

        return {
            "message": "Formulation updated successfully.",
            "formulation": formulation
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the formulation: {str(e)}"
        )


@feed_formulation_router.get('/my/feed/formulation/',status_code=status.HTTP_200_OK)
async def get_my_formulations(db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    try:
        my_formulations = db.query(FeedFormulation).filter(FeedFormulation.user_id == auth_user['user_id']).all()
        return my_formulations
    
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )    