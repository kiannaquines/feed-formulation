import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from core.authentication import hash_password
from db.database import get_db
from main import app
from models.models import Device, DeviceLicense, PricingPlan, PricingPlanVersion


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_url: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment.setdefault("JWT_SECRET_KEY", "a" * 64)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
    )


def test_legacy_user_upgrade_backfills_login_device_and_premium_price(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'legacy-upgrade.db'}"
    run_alembic(database_url, "c7e9a21b8f64")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, otp_secret, is_active,
                    is_email_verified, is_superuser, created_at, last_login_at
                ) VALUES (
                    :username, :email, :password_hash, :otp_secret, :is_active,
                    :is_email_verified, :is_superuser, :created_at, NULL
                )
                """
            ),
            {
                "username": "legacy-user",
                "email": "legacy-user@example.com",
                "password_hash": hash_password("password123"),
                "otp_secret": "legacy-secret",
                "is_active": True,
                "is_email_verified": True,
                "is_superuser": False,
                "created_at": datetime.utcnow(),
            },
        )

    run_alembic(database_url, "e3f4a1b72c90")
    with engine.begin() as connection:
        user_id = connection.scalar(
            text("SELECT id FROM users WHERE username = 'legacy-user'")
        )
        device_id = connection.scalar(
            text("SELECT id FROM devices WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        premium_version_id = connection.scalar(
            text(
                """
                SELECT v.id
                FROM pricing_plan_versions v
                JOIN pricing_plans p ON p.id = v.plan_id
                WHERE p.code = 'premium'
                ORDER BY v.version_number DESC
                LIMIT 1
                """
            )
        )
        now = datetime.utcnow()
        connection.execute(
            text(
                """
                INSERT INTO device_licenses (
                    user_id, device_id, pricing_plan_version_id, plan_code,
                    license_type, status, starts_at, expires_at, price_php,
                    payment_reference, activated_by_user_id, created_at, updated_at
                ) VALUES (
                    :user_id, :device_id, :version_id, 'premium', 'paid', 'active',
                    :starts_at, :expires_at, 35000, 'LEGACY-PREMIUM', NULL,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "user_id": user_id,
                "device_id": device_id,
                "version_id": premium_version_id,
                "starts_at": now,
                "expires_at": now + timedelta(days=30),
                "created_at": now,
                "updated_at": now,
            },
        )

    run_alembic(database_url, "head")
    testing_session = sessionmaker(bind=engine)
    with testing_session() as session:
        device = session.scalar(select(Device))
        license_record = session.scalar(select(DeviceLicense))
        premium_price = session.scalar(
            select(PricingPlanVersion.monthly_price)
            .join(PricingPlan, PricingPlan.id == PricingPlanVersion.plan_id)
            .where(PricingPlan.code == "premium")
            .order_by(PricingPlanVersion.version_number.desc())
            .limit(1)
        )
        active_snapshot_price = session.scalar(
            select(PricingPlanVersion.monthly_price)
            .join(
                DeviceLicense,
                DeviceLicense.pricing_plan_version_id == PricingPlanVersion.id,
            )
            .where(DeviceLicense.payment_reference == "LEGACY-PREMIUM")
        )

    with engine.connect() as connection:
        device_id_column = next(
            row
            for row in connection.execute(text("PRAGMA table_info(device_licenses)"))
            if row.name == "device_id"
        )

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"username": "legacy-user", "password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert device.name == "Migrated desktop"
    assert device.device_type == "desktop"
    assert device.is_active is True
    assert license_record.device_id == device.id
    assert device_id_column.notnull == 1
    assert premium_price == 45_000
    assert active_snapshot_price == 35_000
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
