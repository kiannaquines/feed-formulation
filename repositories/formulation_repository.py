from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import FeedFormulation


class FeedFormulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, user_id: int) -> list[FeedFormulation]:
        statement = select(FeedFormulation).where(
            FeedFormulation.user_id == user_id
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(self, formulation_id: int) -> FeedFormulation | None:
        return self.db.get(FeedFormulation, formulation_id)

    def add(self, formulation: FeedFormulation) -> FeedFormulation:
        self.db.add(formulation)
        self.db.flush()
        return formulation

    def delete(self, formulation: FeedFormulation) -> None:
        self.db.delete(formulation)
