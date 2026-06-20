from fastapi import APIRouter, Depends, status
from db.database import get_db
from models.models import NutrientRequirements
from schema.schema import NutrientRequirementsBase
from core.authentication import *
nutrient_requirements_router = APIRouter(tags=["Nutrient Requirements"])

@nutrient_requirements_router.get("/nutrient-requirements/all", status_code=status.HTTP_200_OK)
def get_nutrient_requirements(db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    """
    Retrieve all nutrient requirements.
    """
    nutrient_requirements = db.query(NutrientRequirements).all()
    if not nutrient_requirements:
        return {
            "detail": "No nutrient requirements found",
        }

    return {
        "detail": f"Found {len(nutrient_requirements)} nutrient requirements",
        "nutrient_requirements": nutrient_requirements,
    }

@nutrient_requirements_router.post("/nutrient-requirements/create", status_code=status.HTTP_200_OK)
def create_nutrient_requirements(nutrient_requirement: NutrientRequirementsBase, db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    """
    Create a new nutrient requirement.
    """
    db_nutrient_requirement = NutrientRequirements(
        nutrient_requirement_name=nutrient_requirement.nutrient_requirement_name,
        nutrient_requirement_description=nutrient_requirement.nutrient_requirement_description,
        composition=nutrient_requirement.composition,
        user_id=auth_user["user_id"]
    )
    db.add(db_nutrient_requirement)
    db.commit()
    db.refresh(db_nutrient_requirement)

    return {
        "detail": "Nutrient requirement created successfully",
        "nutrient_info": nutrient_requirement,
    }

@nutrient_requirements_router.put('/nutrient-requrments/update/{nutrient_requirment_id}', status_code=status.HTTP_200_OK)
def update_nutrient_requirement(nutrient_requirement_id: int, nutrient_requirment_payload: NutrientRequirementsBase, db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    nutrient_requirement = db.query(NutrientRequirements).filter(NutrientRequirements.id == nutrient_requirement_id).first()

    if not nutrient_requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nutrient requirement not found"
        )
    nutrient_requirement.nutrient_requirement_name = nutrient_requirment_payload.nutrient_requirement_name
    nutrient_requirement.nutrient_requirement_description = nutrient_requirment_payload.nutrient_requirement_description
    nutrient_requirement.composition = nutrient_requirment_payload.composition

    db.commit()
    db.refresh(nutrient_requirement)

    return {
        "detail": "Nutrient requirements updated successfully",
        "nutrient_info": nutrient_requirement,
    }

@nutrient_requirements_router.delete('/nutrient-requrments/delete/{nutrient_requirment_id}', status_code=status.HTTP_200_OK)
def delete_nutrient_requirement(nutrient_requirement_id: int, db=Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    nutrient_requirement = db.query(NutrientRequirements).filter(NutrientRequirements.id == nutrient_requirement_id).first()
    if not nutrient_requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nutrient requirement not found"
        )
    db.delete(nutrient_requirement)
    db.commit()
    return {
        "detail": "Nutrient requirement deleted successfully"
    }
