from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from models.models import FeedFormulation, FormulationSeries


class FeedFormulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, user_id: int) -> list[FeedFormulation]:
        latest_versions = (
            select(
                FeedFormulation.series_id,
                func.max(FeedFormulation.version_number).label("version_number"),
            )
            .where(FeedFormulation.user_id == user_id)
            .group_by(FeedFormulation.series_id)
            .subquery()
        )
        statement = (
            select(FeedFormulation)
            .join(
                latest_versions,
                (FeedFormulation.series_id == latest_versions.c.series_id)
                & (
                    FeedFormulation.version_number
                    == latest_versions.c.version_number
                ),
            )
            .order_by(FeedFormulation.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(self, formulation_id: int) -> FeedFormulation | None:
        return self.db.get(FeedFormulation, formulation_id)

    def add(self, formulation: FeedFormulation) -> FeedFormulation:
        self.db.add(formulation)
        self.db.flush()
        return formulation

    def add_series(self, series: FormulationSeries) -> FormulationSeries:
        self.db.add(series)
        self.db.flush()
        return series

    def lock_series(self, series_id: int) -> FormulationSeries | None:
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            self.db.execute(
                update(FormulationSeries)
                .where(FormulationSeries.id == series_id)
                .values(id=FormulationSeries.id)
            )
        return self.db.scalar(
            select(FormulationSeries)
            .where(FormulationSeries.id == series_id)
            .with_for_update()
        )

    def get_latest_version(self, series_id: int) -> FeedFormulation | None:
        return self.db.scalar(
            select(FeedFormulation)
            .where(FeedFormulation.series_id == series_id)
            .order_by(FeedFormulation.version_number.desc())
        )

    def list_versions(self, series_id: int) -> list[FeedFormulation]:
        return list(
            self.db.scalars(
                select(FeedFormulation)
                .where(FeedFormulation.series_id == series_id)
                .order_by(FeedFormulation.version_number.desc())
            ).all()
        )

    def get_direct_child(self, version_id: int) -> FeedFormulation | None:
        return self.db.scalar(
            select(FeedFormulation).where(
                FeedFormulation.parent_version_id == version_id
            )
        )

    def count_versions(self, series_id: int) -> int:
        return self.db.scalar(
            select(func.count(FeedFormulation.id)).where(
                FeedFormulation.series_id == series_id
            )
        ) or 0

    def delete(self, formulation: FeedFormulation) -> None:
        self.db.delete(formulation)

    def delete_series(self, series: FormulationSeries) -> None:
        self.db.delete(series)
