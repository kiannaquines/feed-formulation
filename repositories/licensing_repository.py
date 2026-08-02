from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from models.models import (
    Device,
    DeviceLicense,
    Ingredient,
    LicenseEvent,
    LicensePayment,
    NutrientRequirements,
    Referral,
    ReferralCredit,
    User,
)


class LicensingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, record):
        self.db.add(record)
        self.db.flush()
        return record

    def get_device_by_installation(self, installation_id: str) -> Device | None:
        return self.db.scalar(
            select(Device).where(Device.installation_id == installation_id)
        )

    def get_device(self, device_id: int) -> Device | None:
        return self.db.get(Device, device_id)

    def get_owned_device(self, device_id: int, user_id: int) -> Device | None:
        return self.db.scalar(
            select(Device).where(Device.id == device_id, Device.user_id == user_id)
        )

    def list_devices(self, user_id: int) -> list[Device]:
        return list(
            self.db.scalars(
                select(Device)
                .where(Device.user_id == user_id)
                .order_by(Device.created_at)
            ).all()
        )

    def get_unassigned_trial(
        self, user_id: int, current_time: datetime
    ) -> DeviceLicense | None:
        return self.db.scalar(
            select(DeviceLicense).where(
                DeviceLicense.user_id == user_id,
                DeviceLicense.device_id.is_(None),
                DeviceLicense.license_type == "trial",
                DeviceLicense.status == "active",
                DeviceLicense.starts_at <= current_time,
                DeviceLicense.expires_at > current_time,
            )
        )

    def get_effective_license(
        self, user_id: int, device_id: int, current_time: datetime
    ) -> DeviceLicense | None:
        paid_first = case((DeviceLicense.license_type == "paid", 0), else_=1)
        return self.db.scalar(
            select(DeviceLicense)
            .where(
                DeviceLicense.user_id == user_id,
                DeviceLicense.device_id == device_id,
                DeviceLicense.status == "active",
                DeviceLicense.starts_at <= current_time,
                DeviceLicense.expires_at > current_time,
            )
            .order_by(paid_first, DeviceLicense.expires_at.desc())
        )

    def get_license(self, license_id: int) -> DeviceLicense | None:
        return self.db.get(DeviceLicense, license_id)

    def get_latest_license(
        self, user_id: int, device_id: int
    ) -> DeviceLicense | None:
        return self.db.scalar(
            select(DeviceLicense)
            .where(
                DeviceLicense.user_id == user_id,
                DeviceLicense.device_id == device_id,
            )
            .order_by(DeviceLicense.expires_at.desc())
        )

    def get_active_paid_license_for_device(
        self, device_id: int, current_time: datetime
    ) -> DeviceLicense | None:
        return self.db.scalar(
            select(DeviceLicense).where(
                DeviceLicense.device_id == device_id,
                DeviceLicense.license_type == "paid",
                DeviceLicense.status == "active",
                DeviceLicense.expires_at > current_time,
            )
        )

    def list_licenses(
        self,
        user_id: int | None = None,
        status: str | None = None,
        plan_code: str | None = None,
        expires_before: datetime | None = None,
    ) -> list[DeviceLicense]:
        statement = select(DeviceLicense)
        if user_id is not None:
            statement = statement.where(DeviceLicense.user_id == user_id)
        if status is not None:
            statement = statement.where(DeviceLicense.status == status)
        if plan_code is not None:
            statement = statement.where(DeviceLicense.plan_code == plan_code)
        if expires_before is not None:
            statement = statement.where(DeviceLicense.expires_at <= expires_before)
        return list(self.db.scalars(statement.order_by(DeviceLicense.created_at)).all())

    def lock_user(self, user_id: int) -> User | None:
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            self.db.execute(
                update(User).where(User.id == user_id).values(id=User.id)
            )
        return self.db.scalar(select(User).where(User.id == user_id).with_for_update())

    def count_owned_ingredients(self, user_id: int) -> int:
        return self.db.scalar(
            select(func.count(Ingredient.id)).where(Ingredient.user_id == user_id)
        ) or 0

    def count_owned_requirements(self, user_id: int) -> int:
        return self.db.scalar(
            select(func.count(NutrientRequirements.id)).where(
                NutrientRequirements.user_id == user_id
            )
        ) or 0

    def get_referrer_by_code(self, referral_code: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.referral_code == referral_code.upper())
        )

    def get_referral_for_referred_user(self, user_id: int) -> Referral | None:
        return self.db.scalar(
            select(Referral).where(Referral.referred_user_id == user_id)
        )

    def list_referrals(self, referrer_user_id: int) -> list[Referral]:
        return list(
            self.db.scalars(
                select(Referral).where(
                    Referral.referrer_user_id == referrer_user_id
                )
            ).all()
        )

    def list_referral_credits(self, user_id: int) -> list[ReferralCredit]:
        return list(
            self.db.scalars(
                select(ReferralCredit)
                .where(ReferralCredit.user_id == user_id)
                .order_by(ReferralCredit.created_at)
            ).all()
        )

    def get_referral_credit(
        self, credit_id: int, user_id: int
    ) -> ReferralCredit | None:
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            result = self.db.execute(
                update(ReferralCredit)
                .where(
                    ReferralCredit.id == credit_id,
                    ReferralCredit.user_id == user_id,
                    ReferralCredit.claimed_at.is_(None),
                )
                .values(id=ReferralCredit.id)
            )
            if result.rowcount != 1:
                return None
        return self.db.scalar(
            select(ReferralCredit)
            .where(
                ReferralCredit.id == credit_id,
                ReferralCredit.user_id == user_id,
            )
            .with_for_update()
        )

    def get_owned_referral_credit(
        self, credit_id: int, user_id: int
    ) -> ReferralCredit | None:
        return self.db.scalar(
            select(ReferralCredit).where(
                ReferralCredit.id == credit_id,
                ReferralCredit.user_id == user_id,
            )
        )

    def add_event(
        self,
        license_id: int,
        event_type: str,
        actor_user_id: int | None,
        details: dict,
    ) -> LicenseEvent:
        event = LicenseEvent(
            license_id=license_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            details=details,
        )
        self.db.add(event)
        return event

    def add_payment(
        self,
        license_id: int,
        payment_reference: str,
        price_php: int,
        recorded_by_user_id: int,
    ) -> LicensePayment:
        payment = LicensePayment(
            license_id=license_id,
            payment_reference=payment_reference,
            price_php=price_php,
            recorded_by_user_id=recorded_by_user_id,
        )
        self.db.add(payment)
        return payment
