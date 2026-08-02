import secrets
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    LicenseRequiredError,
    NotFoundError,
    PersistenceError,
    QuotaExceededError,
    ValidationError,
)
from core.licensing import REFERRAL_BONUS_DAYS, TRIAL_DAYS
from models.models import Device, DeviceLicense, Referral, ReferralCredit, User
from repositories import LicensingRepository, PricingRepository, UserRepository
from schema.schema import UserRegister


class LicensingService:
    def __init__(
        self,
        db: Session,
        licensing: LicensingRepository,
        users: UserRepository | None = None,
        pricing: PricingRepository | None = None,
    ):
        self.db = db
        self.licensing = licensing
        self.users = users or UserRepository(db)
        self.pricing = pricing or PricingRepository(db)

    def initialize_account(
        self, user: User, data: UserRegister, current_time: datetime | None = None
    ) -> None:
        now = current_time or datetime.utcnow()
        user.referral_code = self._new_referral_code()
        if data.referral_code:
            referrer = self.licensing.get_referrer_by_code(data.referral_code)
            if not referrer:
                raise ValidationError("Referral code is invalid")
            if referrer.id == user.id:
                raise ValidationError("Users cannot refer themselves")
            self._add(
                Referral(referrer_user_id=referrer.id, referred_user_id=user.id)
            )
        installation_id = str(data.installation_id)
        if self.licensing.get_device_by_installation(installation_id):
            raise ConflictError("This installation is registered to another account")
        device = self._add(
            Device(
                user_id=user.id,
                installation_id=installation_id,
                name=data.device_name,
                device_type=data.device_type,
                last_seen_at=now,
            )
        )
        starter_plan = self._current_plan("starter")
        trial = self._add(
            DeviceLicense(
                user_id=user.id,
                device_id=device.id,
                pricing_plan_version_id=starter_plan[1].id,
                plan_code="starter",
                license_type="trial",
                status="active",
                starts_at=now,
                expires_at=now + timedelta(days=TRIAL_DAYS),
                price_php=0,
            )
        )
        self.licensing.add_event(trial.id, "trial_created", user.id, {})

    def get_login_device(
        self, user: User, current_time: datetime | None = None
    ) -> Device:
        now = current_time or datetime.utcnow()
        device = self._read(lambda: self.licensing.get_registered_device(user.id))
        if not device:
            raise AuthenticationError("No registered device found for this account")
        if not device.is_active:
            raise AuthenticationError("Device is inactive")
        device.last_seen_at = now
        return device

    def require_entitlement(self, auth_user: dict) -> dict:
        license_record = self._read(
            lambda: self.licensing.get_effective_license(
                auth_user["user_id"], auth_user["device_id"], datetime.utcnow()
            )
        )
        if not license_record:
            raise LicenseRequiredError(
                "An active trial or paid license is required for this device"
            )
        return {**auth_user, "license": license_record}

    def require_quota(self, user_id: int, device_id: int, resource: str) -> None:
        now = datetime.utcnow()
        self.licensing.lock_user(user_id)
        license_record = self.licensing.get_effective_license(user_id, device_id, now)
        if not license_record:
            raise LicenseRequiredError(
                "An active trial or paid license is required for this device"
            )
        plan = self._plan_for_license(license_record)
        if resource == "ingredients":
            used = self.licensing.count_owned_ingredients(user_id)
            limit = plan[1].ingredient_limit
        else:
            used = self.licensing.count_owned_requirements(user_id)
            limit = plan[1].requirement_limit
        if limit is not None and used >= limit:
            raise QuotaExceededError(
                f"The {plan[0].name} plan allows up to {limit} saved {resource}"
            )

    def plans(self) -> list[dict]:
        return [self._plan_response(*row) for row in self._read(self.pricing.list_current)]

    def status(self, auth_user: dict) -> dict:
        now = datetime.utcnow()
        device = self._read(
            lambda: self.licensing.get_owned_device(
                auth_user["device_id"], auth_user["user_id"]
            )
        )
        active_license = self._read(
            lambda: self.licensing.get_effective_license(
                auth_user["user_id"], auth_user["device_id"], now
            )
        )
        license_record = active_license or self.licensing.get_latest_license(
            auth_user["user_id"], auth_user["device_id"]
        )
        if active_license:
            state = "active"
            plan = self._plan_for_license(active_license)
        elif license_record:
            state = "expired"
            plan = self._plan_for_license(license_record)
        else:
            state = "unlicensed"
            plan = None
        return {
            "status": state,
            "device": device,
            "license": license_record,
            "ingredients": {
                "used": self.licensing.count_owned_ingredients(auth_user["user_id"]),
                "limit": plan[1].ingredient_limit if plan else None,
            },
            "requirements": {
                "used": self.licensing.count_owned_requirements(auth_user["user_id"]),
                "limit": plan[1].requirement_limit if plan else None,
            },
        }

    def devices(self, user_id: int) -> list[Device]:
        return self._read(lambda: self.licensing.list_devices(user_id))

    def referral_summary(self, user_id: int) -> dict:
        user = self._read(lambda: self.users.get_by_id(user_id))
        referrals = self._read(lambda: self.licensing.list_referrals(user_id))
        credits = self._read(lambda: self.licensing.list_referral_credits(user_id))
        return {
            "referral_code": user.referral_code,
            "pending_referrals": sum(row.status == "pending" for row in referrals),
            "qualified_referrals": sum(row.status == "qualified" for row in referrals),
            "credits": credits,
        }

    def claim_referral_credit(
        self, credit_id: int, license_id: int, user_id: int
    ) -> DeviceLicense:
        credit = self._read(
            lambda: self.licensing.get_referral_credit(credit_id, user_id)
        )
        if not credit:
            existing_credit = self._read(
                lambda: self.licensing.get_owned_referral_credit(credit_id, user_id)
            )
            if existing_credit and existing_credit.claimed_at:
                raise ConflictError("Referral credit has already been claimed")
            raise NotFoundError("Referral credit not found")
        if credit.claimed_at:
            raise ConflictError("Referral credit has already been claimed")
        license_record = self._read(lambda: self.licensing.get_license(license_id))
        now = datetime.utcnow()
        if (
            not license_record
            or license_record.user_id != user_id
            or license_record.license_type != "paid"
            or license_record.status != "active"
            or license_record.expires_at <= now
        ):
            raise ValidationError("An active paid license owned by the user is required")
        old_expiry = license_record.expires_at
        license_record.expires_at += timedelta(days=credit.bonus_days)
        credit.claimed_license_id = license_record.id
        credit.claimed_at = now
        self.licensing.add_event(
            license_record.id,
            "referral_extended",
            user_id,
            {
                "credit_id": credit.id,
                "bonus_days": credit.bonus_days,
                "previous_expires_at": old_expiry.isoformat(),
            },
        )
        self._commit()
        self.db.refresh(license_record)
        return license_record

    def _new_referral_code(self) -> str:
        for _ in range(10):
            code = secrets.token_hex(6).upper()
            if not self.licensing.get_referrer_by_code(code):
                return code
        raise PersistenceError("Could not generate a unique referral code")

    def _current_plan(self, code: str):
        plan = self._read(lambda: self.pricing.get_current_by_code(code))
        if not plan:
            raise PersistenceError(f"Pricing plan {code!r} is unavailable")
        return plan

    def _plan_for_license(self, license_record: DeviceLicense):
        plan = self._read(
            lambda: self.pricing.get_plan_and_version(
                license_record.pricing_plan_version_id
            )
        )
        if not plan:
            raise PersistenceError("License pricing version is unavailable")
        return plan

    @staticmethod
    def _plan_response(plan, version) -> dict:
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

    def _commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Licensing data conflicts with an existing record") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    def _add(self, record):
        try:
            return self.licensing.add(record)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "Licensing data conflicts with an existing record"
            ) from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc


class AdminLicensingService(LicensingService):
    def list_licenses(
        self,
        user_id: int | None = None,
        status: str | None = None,
        plan_code: str | None = None,
        expires_before: datetime | None = None,
    ) -> list[DeviceLicense]:
        return self._read(
            lambda: self.licensing.list_licenses(
                user_id, status, plan_code, expires_before
            )
        )

    def activate(
        self,
        user_id: int,
        device_id: int,
        plan_code: str,
        payment_reference: str,
        admin_user_id: int,
    ) -> DeviceLicense:
        now = datetime.utcnow()
        user = self._read(lambda: self.users.get_by_id(user_id))
        device = self._read(
            lambda: self.licensing.get_owned_device(device_id, user_id)
        )
        if not user or not device:
            raise NotFoundError("User or owned device not found")
        if self.licensing.get_active_paid_license_for_device(device_id, now):
            raise ConflictError("This device already has an active paid license")
        plan, version = self._current_plan(plan_code)
        license_record = self._add(
            DeviceLicense(
                user_id=user_id,
                device_id=device_id,
                pricing_plan_version_id=version.id,
                plan_code=plan.code,
                license_type="paid",
                status="active",
                starts_at=now,
                expires_at=now + timedelta(days=plan.duration_days),
                price_php=version.monthly_price,
                payment_reference=payment_reference,
                activated_by_user_id=admin_user_id,
            )
        )
        self.licensing.add_payment(
            license_record.id, payment_reference, version.monthly_price, admin_user_id
        )
        self.licensing.add_event(
            license_record.id,
            "activated",
            admin_user_id,
            {
                "plan_code": plan.code,
                "pricing_plan_version_id": version.id,
                "device_id": device_id,
            },
        )
        self._qualify_referral(user_id, now)
        self._commit()
        self.db.refresh(license_record)
        return license_record

    def renew(
        self,
        license_id: int,
        plan_code: str,
        payment_reference: str,
        admin_user_id: int,
    ) -> DeviceLicense:
        license_record = self._paid_license(license_id)
        if license_record.status == "revoked":
            raise ValidationError("Revoked licenses cannot be renewed")
        now = datetime.utcnow()
        plan, version = self._current_plan(plan_code)
        old_expiry = license_record.expires_at
        license_record.starts_at = min(license_record.starts_at, now)
        license_record.expires_at = max(old_expiry, now) + timedelta(
            days=plan.duration_days
        )
        license_record.plan_code = plan.code
        license_record.pricing_plan_version_id = version.id
        license_record.price_php = version.monthly_price
        license_record.payment_reference = payment_reference
        license_record.status = "active"
        self.licensing.add_payment(
            license_record.id, payment_reference, version.monthly_price, admin_user_id
        )
        self.licensing.add_event(
            license_record.id,
            "renewed",
            admin_user_id,
            {
                "plan_code": plan.code,
                "pricing_plan_version_id": version.id,
                "previous_expires_at": old_expiry.isoformat(),
            },
        )
        self._commit()
        self.db.refresh(license_record)
        return license_record

    def revoke(
        self, license_id: int, reason: str, admin_user_id: int
    ) -> DeviceLicense:
        license_record = self._paid_license(license_id)
        if license_record.status == "revoked":
            raise ConflictError("License is already revoked")
        license_record.status = "revoked"
        self.licensing.add_event(
            license_record.id, "revoked", admin_user_id, {"reason": reason}
        )
        self._commit()
        self.db.refresh(license_record)
        return license_record

    def reassign(
        self,
        license_id: int,
        device_id: int,
        reason: str,
        admin_user_id: int,
    ) -> DeviceLicense:
        license_record = self._paid_license(license_id)
        if (
            license_record.status != "active"
            or license_record.expires_at <= datetime.utcnow()
        ):
            raise ValidationError("Only an active paid license can be reassigned")
        device = self._read(
            lambda: self.licensing.get_owned_device(device_id, license_record.user_id)
        )
        if not device:
            raise ForbiddenError("The target device must belong to the license owner")
        existing = self.licensing.get_active_paid_license_for_device(
            device_id, datetime.utcnow()
        )
        if existing and existing.id != license_record.id:
            raise ConflictError("The target device already has an active paid license")
        old_device_id = license_record.device_id
        license_record.device_id = device.id
        self.licensing.add_event(
            license_record.id,
            "reassigned",
            admin_user_id,
            {
                "previous_device_id": old_device_id,
                "device_id": device.id,
                "reason": reason,
            },
        )
        self._commit()
        self.db.refresh(license_record)
        return license_record

    def _paid_license(self, license_id: int) -> DeviceLicense:
        license_record = self._read(lambda: self.licensing.get_license(license_id))
        if not license_record:
            raise NotFoundError("License not found")
        if license_record.license_type != "paid":
            raise ValidationError("Trial licenses cannot be modified")
        return license_record

    def _qualify_referral(self, user_id: int, current_time: datetime) -> None:
        referral = self.licensing.get_referral_for_referred_user(user_id)
        if not referral or referral.status != "pending":
            return
        referral.status = "qualified"
        referral.qualified_at = current_time
        self._add(
            ReferralCredit(
                referral_id=referral.id,
                user_id=referral.referrer_user_id,
                bonus_days=REFERRAL_BONUS_DAYS,
            )
        )
