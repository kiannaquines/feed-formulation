from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.models import Ingredient


class IngredientRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_visible_to(self, user_id: int) -> list[Ingredient]:
        statement = (
            select(Ingredient)
            .where(
                or_(
                    Ingredient.user_id == user_id,
                    Ingredient.user_id.is_(None),
                )
            )
            .order_by(Ingredient.created_at)
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(self, ingredient_id: int) -> Ingredient | None:
        return self.db.get(Ingredient, ingredient_id)

    def add(self, ingredient: Ingredient) -> Ingredient:
        self.db.add(ingredient)
        self.db.flush()
        return ingredient

    def delete(self, ingredient: Ingredient) -> None:
        self.db.delete(ingredient)
