from fastapi import APIRouter, Depends, HTTPException
from core.authentication import verify_jwt_token
from db.database import get_db
from models.models import Ingredient
from schema.schema import IngredientCreate, IngredientResponse
from sqlalchemy.orm import Session

ingredient_router = APIRouter(tags=["Ingredients"])


@ingredient_router.get("/ingredients/all")
def get_ingredients(db: Session = Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    """
    Retrieve a list of all ingredients.
    """
    ingredients = db.query(Ingredient).order_by(Ingredient.created_at).all()
    
    if not ingredients:
        return {"detail": "Ingredients are currently empty"}
    
    return {
        "detail": f"Found {len(ingredients)} ingredients",
        "ingredients": ingredients,
    }

@ingredient_router.post("/ingredients/create", response_model=IngredientResponse)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    ingredient = Ingredient(**data.dict())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient

@ingredient_router.put("/ingredients/update/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(ingredient_id: int, data: IngredientCreate, db: Session = Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    for key, value in data.dict().items():
        setattr(ingredient, key, value)
    
    db.commit()
    db.refresh(ingredient)
    return ingredient

@ingredient_router.delete("/ingredients/delete/{ingredient_id}")
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db), auth_user: dict = Depends(verify_jwt_token)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    db.delete(ingredient)
    db.commit()
    return {"detail": "Ingredient deleted successfully"}