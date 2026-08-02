from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.models import NutrientRequirements


class NutrientRequirementRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_visible_to(self, user_id: int) -> list[NutrientRequirements]:
        statement = select(NutrientRequirements).where(
            or_(
                NutrientRequirements.user_id == user_id,
                NutrientRequirements.user_id.is_(None),
            )
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(self, requirement_id: int) -> NutrientRequirements | None:
        return self.db.get(NutrientRequirements, requirement_id)

    def add(self, requirement: NutrientRequirements) -> NutrientRequirements:
        self.db.add(requirement)
        self.db.flush()
        return requirement

    def delete(self, requirement: NutrientRequirements) -> None:
        self.db.delete(requirement)
