from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    otp_secret = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    referral_code = Column(String(16), unique=True, nullable=True, index=True)

    otp_sessions = relationship("OTPSession", back_populates="user")


class OTPSession(Base):
    __tablename__ = "otp_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    user = relationship("User", back_populates="otp_sessions")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    installation_id = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    device_type = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    currency = Column(String(3), nullable=False, default="PHP")
    duration_days = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PricingPlanVersion(Base):
    __tablename__ = "pricing_plan_versions"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "version_number", name="uq_pricing_plan_versions_plan_version"
        ),
        CheckConstraint("monthly_price > 0", name="ck_pricing_monthly_price_positive"),
        CheckConstraint(
            "ingredient_limit IS NULL OR ingredient_limit > 0",
            name="ck_pricing_ingredient_limit_positive",
        ),
        CheckConstraint(
            "requirement_limit IS NULL OR requirement_limit > 0",
            name="ck_pricing_requirement_limit_positive",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("pricing_plans.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    monthly_price = Column(Integer, nullable=False)
    ingredient_limit = Column(Integer, nullable=True)
    requirement_limit = Column(Integer, nullable=True)
    formulation_limit = Column(Integer, nullable=True)
    effective_at = Column(DateTime, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeviceLicense(Base):
    __tablename__ = "device_licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    pricing_plan_version_id = Column(
        Integer,
        ForeignKey("pricing_plan_versions.id"),
        nullable=False,
        index=True,
    )
    plan_code = Column(String(20), nullable=False)
    license_type = Column(String(20), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    starts_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    price_php = Column(Integer, nullable=False, default=0)
    payment_reference = Column(String(120), unique=True, nullable=True)
    activated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class LicenseEvent(Base):
    __tablename__ = "license_events"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(
        Integer, ForeignKey("device_licenses.id"), nullable=False, index=True
    )
    event_type = Column(String(30), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LicensePayment(Base):
    __tablename__ = "license_payments"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(
        Integer, ForeignKey("device_licenses.id"), nullable=False, index=True
    )
    payment_reference = Column(String(120), unique=True, nullable=False)
    price_php = Column(Integer, nullable=False)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referrals_referred_user_id"),
        CheckConstraint(
            "referrer_user_id != referred_user_id", name="ck_referrals_not_self"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    referrer_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    qualified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ReferralCredit(Base):
    __tablename__ = "referral_credits"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(
        Integer, ForeignKey("referrals.id"), unique=True, nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bonus_days = Column(Integer, nullable=False, default=30)
    claimed_license_id = Column(
        Integer, ForeignKey("device_licenses.id"), nullable=True
    )
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float, nullable=False)
    crude_protein = Column(Float, nullable=False)
    crude_fat = Column(Float, nullable=False)
    crude_fiber = Column(Float, nullable=False)
    metabolized_energy = Column(Float, nullable=False)
    calcium = Column(Float, nullable=False)
    total_phosphorus = Column(Float, nullable=False)
    avail_phosphorus = Column(Float, nullable=False)
    lysine = Column(Float, nullable=False)
    methionine = Column(Float, nullable=False)
    m_c = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FormulationSeries(Base):
    __tablename__ = "formulation_series"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    next_version_number = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FeedFormulation(Base):
    __tablename__ = "formulations"
    __table_args__ = (
        UniqueConstraint(
            "series_id", "version_number", name="uq_formulations_series_version"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    formulation_name = Column(String, nullable=True)
    formulation_description = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False)
    series_id = Column(
        Integer,
        ForeignKey("formulation_series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_version_id = Column(
        Integer,
        ForeignKey("formulations.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload = Column(JSON, nullable=False)


class NutrientRequirements(Base):
    __tablename__ = "nutrient_requirements"

    id = Column(Integer, primary_key=True, index=True)
    nutrient_requirement_name = Column(String, nullable=False)
    nutrient_requirement_description = Column(String, nullable=True)
    composition = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
