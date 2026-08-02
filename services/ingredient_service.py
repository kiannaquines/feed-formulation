from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import ConflictError, PersistenceError
from models.models import Ingredient
from repositories import IngredientRepository
from schema.schema import IngredientCreate
from services.ownership import require_mutable_owner


class IngredientService:
    def __init__(self, db: Session, ingredients: IngredientRepository):
        self.db = db
        self.ingredients = ingredients

    def list_visible(self, user_id: int) -> dict:
        ingredients = self._read(lambda: self.ingredients.list_visible_to(user_id))
        if not ingredients:
            return {"detail": "Ingredients are currently empty"}
        return {
            "detail": f"Found {len(ingredients)} ingredients",
            "ingredients": ingredients,
        }

    def create(self, data: IngredientCreate, user_id: int) -> Ingredient:
        ingredient = Ingredient(**data.model_dump(), user_id=user_id)
        self._commit(lambda: self.ingredients.add(ingredient))
        self.db.refresh(ingredient)
        return ingredient

    def update(
        self, ingredient_id: int, data: IngredientCreate, user_id: int
    ) -> Ingredient:
        ingredient = self._read(lambda: self.ingredients.get_by_id(ingredient_id))
        require_mutable_owner(ingredient, user_id, "Ingredient")
        for key, value in data.model_dump().items():
            setattr(ingredient, key, value)
        self._commit()
        self.db.refresh(ingredient)
        return ingredient

    def delete(self, ingredient_id: int, user_id: int) -> dict:
        ingredient = self._read(lambda: self.ingredients.get_by_id(ingredient_id))
        require_mutable_owner(ingredient, user_id, "Ingredient")
        self._commit(lambda: self.ingredients.delete(ingredient))
        return {"detail": "Ingredient deleted successfully"}

    def _commit(self, operation=None) -> None:
        try:
            if operation:
                operation()
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Ingredient name already exists") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc
