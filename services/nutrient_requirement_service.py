from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import PersistenceError
from models.models import NutrientRequirements
from repositories import NutrientRequirementRepository
from schema.schema import NutrientRequirementsBase
from services.ownership import require_mutable_owner


class NutrientRequirementService:
    def __init__(
        self, db: Session, requirements: NutrientRequirementRepository
    ):
        self.db = db
        self.requirements = requirements

    def list_visible(self, user_id: int) -> dict:
        requirements = self._read(
            lambda: self.requirements.list_visible_to(user_id)
        )
        if not requirements:
            return {"detail": "No nutrient requirements found"}
        return {
            "detail": f"Found {len(requirements)} nutrient requirements",
            "nutrient_requirements": requirements,
        }

    def create(self, data: NutrientRequirementsBase, user_id: int) -> dict:
        requirement = NutrientRequirements(**data.model_dump(), user_id=user_id)
        self._commit(lambda: self.requirements.add(requirement))
        self.db.refresh(requirement)
        return {
            "detail": "Nutrient requirement created successfully",
            "nutrient_info": data,
        }

    def update(
        self, requirement_id: int, data: NutrientRequirementsBase, user_id: int
    ) -> dict:
        requirement = self._read(
            lambda: self.requirements.get_by_id(requirement_id)
        )
        require_mutable_owner(requirement, user_id, "Nutrient requirement")
        for key, value in data.model_dump().items():
            setattr(requirement, key, value)
        self._commit()
        self.db.refresh(requirement)
        return {
            "detail": "Nutrient requirements updated successfully",
            "nutrient_info": requirement,
        }

    def delete(self, requirement_id: int, user_id: int) -> dict:
        requirement = self._read(
            lambda: self.requirements.get_by_id(requirement_id)
        )
        require_mutable_owner(requirement, user_id, "Nutrient requirement")
        self._commit(lambda: self.requirements.delete(requirement))
        return {"detail": "Nutrient requirement deleted successfully"}

    def _commit(self, operation=None) -> None:
        try:
            if operation:
                operation()
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc
