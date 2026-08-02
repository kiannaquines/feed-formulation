from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import PersistenceError
from models.models import FeedFormulation
from repositories import FeedFormulationRepository
from schema.schema import FeedFormulationWithPayloadRequest
from services.ownership import require_mutable_owner


class FeedFormulationService:
    def __init__(self, db: Session, formulations: FeedFormulationRepository):
        self.db = db
        self.formulations = formulations

    def save(self, data: FeedFormulationWithPayloadRequest, user_id: int) -> dict:
        formulation = FeedFormulation(**data.model_dump(), user_id=user_id)
        self._commit(lambda: self.formulations.add(formulation))
        return {"detail": "Formulation saved successfully."}

    def list_for_user(self, user_id: int) -> list[FeedFormulation]:
        return self._read(lambda: self.formulations.list_by_user(user_id))

    def update(
        self,
        formulation_id: int,
        data: FeedFormulationWithPayloadRequest,
        user_id: int,
    ) -> dict:
        formulation = self._read(
            lambda: self.formulations.get_by_id(formulation_id)
        )
        require_mutable_owner(formulation, user_id, "Formulation")
        for key, value in data.model_dump().items():
            setattr(formulation, key, value)
        self._commit()
        self.db.refresh(formulation)
        return {
            "message": "Formulation updated successfully.",
            "formulation": formulation,
        }

    def delete(self, formulation_id: int, user_id: int) -> dict:
        formulation = self._read(
            lambda: self.formulations.get_by_id(formulation_id)
        )
        require_mutable_owner(formulation, user_id, "Formulation")
        self._commit(lambda: self.formulations.delete(formulation))
        return {"detail": "Formulation details has been successfully removed."}

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
