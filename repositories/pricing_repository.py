from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from models.models import PricingPlan, PricingPlanVersion


class PricingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, record):
        self.db.add(record)
        self.db.flush()
        return record

    def list_current(self) -> list[tuple[PricingPlan, PricingPlanVersion]]:
        latest_versions = (
            select(
                PricingPlanVersion.plan_id,
                func.max(PricingPlanVersion.version_number).label("version_number"),
            )
            .group_by(PricingPlanVersion.plan_id)
            .subquery()
        )
        return list(
            self.db.execute(
                select(PricingPlan, PricingPlanVersion)
                .join(
                    latest_versions,
                    latest_versions.c.plan_id == PricingPlan.id,
                )
                .join(
                    PricingPlanVersion,
                    (PricingPlanVersion.plan_id == PricingPlan.id)
                    & (
                        PricingPlanVersion.version_number
                        == latest_versions.c.version_number
                    ),
                )
                .order_by(PricingPlan.id)
            ).all()
        )

    def get_plan_by_code(self, code: str) -> PricingPlan | None:
        return self.db.scalar(select(PricingPlan).where(PricingPlan.code == code))

    def get_current_by_code(
        self, code: str
    ) -> tuple[PricingPlan, PricingPlanVersion] | None:
        row = self.db.execute(
            select(PricingPlan, PricingPlanVersion)
            .join(PricingPlanVersion, PricingPlanVersion.plan_id == PricingPlan.id)
            .where(PricingPlan.code == code)
            .order_by(PricingPlanVersion.version_number.desc())
            .limit(1)
        ).first()
        return tuple(row) if row else None

    def get_version(self, version_id: int) -> PricingPlanVersion | None:
        return self.db.get(PricingPlanVersion, version_id)

    def get_plan_and_version(
        self, version_id: int
    ) -> tuple[PricingPlan, PricingPlanVersion] | None:
        row = self.db.execute(
            select(PricingPlan, PricingPlanVersion)
            .join(PricingPlanVersion, PricingPlanVersion.plan_id == PricingPlan.id)
            .where(PricingPlanVersion.id == version_id)
        ).first()
        return tuple(row) if row else None

    def list_versions(
        self, plan_id: int
    ) -> list[tuple[PricingPlan, PricingPlanVersion]]:
        return list(
            self.db.execute(
                select(PricingPlan, PricingPlanVersion)
                .join(PricingPlanVersion, PricingPlanVersion.plan_id == PricingPlan.id)
                .where(PricingPlan.id == plan_id)
                .order_by(PricingPlanVersion.version_number.desc())
            ).all()
        )

    def lock_plan(self, plan_id: int) -> PricingPlan | None:
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            self.db.execute(
                update(PricingPlan)
                .where(PricingPlan.id == plan_id)
                .values(id=PricingPlan.id)
            )
        return self.db.scalar(
            select(PricingPlan)
            .where(PricingPlan.id == plan_id)
            .with_for_update()
        )
