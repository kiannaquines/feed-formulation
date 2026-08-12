from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError, ConflictError, PersistenceError
from models.models import FeedFormulation, FormulationSeries
from repositories import FeedFormulationRepository
from schema.schema import FeedFormulationWithPayloadRequest
from services.ownership import require_mutable_owner


class FeedFormulationService:
    def __init__(self, db: Session, formulations: FeedFormulationRepository):
        self.db = db
        self.formulations = formulations

    def save(self, data: FeedFormulationWithPayloadRequest, user_id: int) -> dict:
        def create_formulation() -> FeedFormulation:
            series = self.formulations.add_series(
                FormulationSeries(user_id=user_id, next_version_number=2)
            )
            return self.formulations.add(
                FeedFormulation(
                    **data.model_dump(),
                    user_id=user_id,
                    series_id=series.id,
                    parent_version_id=None,
                    version_number=1,
                )
            )

        formulation = self._commit(create_formulation)
        self.db.refresh(formulation)
        return {
            "message": "Formulation saved successfully.",
            "formulation": formulation,
        }

    def list_for_user(self, user_id: int) -> list[FeedFormulation]:
        return self._read(lambda: self.formulations.list_by_user(user_id))

    def edit(
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
            "message": "Formulation edited successfully.",
            "formulation": formulation,
        }

    def create_version(
        self,
        formulation_id: int,
        data: FeedFormulationWithPayloadRequest,
        user_id: int,
    ) -> dict:
        source = self._read(
            lambda: self.formulations.get_by_id(formulation_id)
        )
        require_mutable_owner(source, user_id, "Formulation")

        def append_version() -> FeedFormulation:
            series = self.formulations.lock_series(source.series_id)
            latest = self.formulations.get_latest_version(source.series_id)
            if not series or not latest:
                raise PersistenceError("Formulation series is incomplete")
            if latest.id != source.id:
                raise ConflictError("A newer formulation version already exists")
            version = self.formulations.add(
                FeedFormulation(
                    **data.model_dump(),
                    user_id=user_id,
                    series_id=series.id,
                    parent_version_id=source.id,
                    version_number=series.next_version_number,
                )
            )
            series.next_version_number += 1
            return version

        formulation = self._commit(append_version)
        self.db.refresh(formulation)
        return {
            "message": "Formulation version created successfully.",
            "formulation": formulation,
        }

    def list_versions(
        self, formulation_id: int, user_id: int
    ) -> list[FeedFormulation]:
        formulation = self._read(
            lambda: self.formulations.get_by_id(formulation_id)
        )
        require_mutable_owner(formulation, user_id, "Formulation")
        return self._read(
            lambda: self.formulations.list_versions(formulation.series_id)
        )

    def delete(self, formulation_id: int, user_id: int) -> dict:
        formulation = self._read(
            lambda: self.formulations.get_by_id(formulation_id)
        )
        require_mutable_owner(formulation, user_id, "Formulation")
        version_number = formulation.version_number
        series_id = formulation.series_id

        def delete_version() -> None:
            series = self.formulations.lock_series(series_id)
            if not series:
                raise PersistenceError("Formulation series is incomplete")
            child = self.formulations.get_direct_child(formulation.id)
            if child:
                child.parent_version_id = formulation.parent_version_id
            self.formulations.delete(formulation)
            self.db.flush()
            if self.formulations.count_versions(series.id) == 0:
                self.formulations.delete_series(series)

        self._commit(delete_version)
        return {
            "detail": (
                f"Formulation version {version_number} from series {series_id} "
                "was deleted."
            )
        }

    def _commit(self, operation=None):
        try:
            result = None
            if operation:
                result = operation()
            self.db.commit()
            return result
        except ApplicationError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc
