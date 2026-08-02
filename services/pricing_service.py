from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import ConflictError, NotFoundError, PersistenceError
from models.models import PricingPlan, PricingPlanVersion
from repositories import PricingRepository
from schema.schema import PricingPlanVersionCreate


class PricingService:
    def __init__(self, db: Session, pricing: PricingRepository):
        self.db = db
        self.pricing = pricing

    def list_current(self) -> list[dict]:
        return [self._response(*row) for row in self._read(self.pricing.list_current)]

    @staticmethod
    def _response(plan: PricingPlan, version: PricingPlanVersion) -> dict:
        return {
            "code": plan.code,
            "name": plan.name,
            "currency": plan.currency,
            "monthly_price": version.monthly_price,
            "duration_days": plan.duration_days,
            "ingredient_limit": version.ingredient_limit,
            "requirement_limit": version.requirement_limit,
            "formulation_limit": version.formulation_limit,
            "version_number": version.version_number,
            "effective_at": version.effective_at,
        }

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc


class AdminPricingService(PricingService):
    def list_current_versions(self) -> list[dict]:
        return [
            self._version_response(*row)
            for row in self._read(self.pricing.list_current)
        ]

    def list_versions(self, code: str) -> list[dict]:
        plan = self._read(lambda: self.pricing.get_plan_by_code(code))
        if not plan:
            raise NotFoundError("Pricing plan not found")
        rows = self._read(lambda: self.pricing.list_versions(plan.id))
        return [self._version_response(*row) for row in rows]

    def publish(
        self,
        code: str,
        data: PricingPlanVersionCreate,
        admin_user_id: int,
    ) -> dict:
        try:
            plan = self.pricing.get_plan_by_code(code)
            if not plan:
                raise NotFoundError("Pricing plan not found")
            plan = self.pricing.lock_plan(plan.id)
            current = self.pricing.get_current_by_code(code)
            if not plan or not current:
                raise PersistenceError("Pricing plan has no current version")
            current_version = current[1]
            version = self.pricing.add(
                PricingPlanVersion(
                    plan_id=plan.id,
                    version_number=current_version.version_number + 1,
                    monthly_price=data.monthly_price,
                    ingredient_limit=(
                        data.ingredient_limit
                        if "ingredient_limit" in data.model_fields_set
                        else current_version.ingredient_limit
                    ),
                    requirement_limit=(
                        data.requirement_limit
                        if "requirement_limit" in data.model_fields_set
                        else current_version.requirement_limit
                    ),
                    formulation_limit=None,
                    effective_at=datetime.utcnow(),
                    created_by_user_id=admin_user_id,
                )
            )
            self.db.commit()
            self.db.refresh(version)
            return self._version_response(plan, version)
        except (NotFoundError, PersistenceError):
            self.db.rollback()
            raise
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("A pricing version was published concurrently") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @classmethod
    def _version_response(
        cls, plan: PricingPlan, version: PricingPlanVersion
    ) -> dict:
        return {
            **cls._response(plan, version),
            "id": version.id,
            "created_by_user_id": version.created_by_user_id,
            "created_at": version.created_at,
        }
