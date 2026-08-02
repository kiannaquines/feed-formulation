import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from core.exceptions import ConflictError, QuotaExceededError
from db.database import get_db
from main import app
from models.models import (
    Device,
    DeviceLicense,
    FeedFormulation,
    FormulationSeries,
    Ingredient,
    User,
)
from repositories import (
    FeedFormulationRepository,
    IngredientRepository,
    LicensingRepository,
)
from schema.schema import FeedFormulationWithPayloadRequest, IngredientCreate
from services import FeedFormulationService, IngredientService, LicensingService


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APPLICATION_TABLES = [
    "referral_credits",
    "referrals",
    "license_payments",
    "license_events",
    "device_licenses",
    "otp_sessions",
    "formulations",
    "formulation_series",
    "devices",
    "nutrient_requirements",
    "ingredients",
    "users",
]

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture(scope="session")
def postgres_engine():
    url = make_url(TEST_DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "feedprime_test":
        pytest.fail("TEST_DATABASE_URL must target the feedprime_test PostgreSQL database")

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    environment = os.environ.copy()
    environment["DATABASE_URL"] = TEST_DATABASE_URL
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_postgres(postgres_engine):
    table_list = ", ".join(f'"{name}"' for name in APPLICATION_TABLES)
    with postgres_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
    try:
        yield
    finally:
        with postgres_engine.begin() as connection:
            connection.execute(
                text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")
            )


def formulation_payload(revision: int) -> dict:
    return {
        "formulation_name": "PostgreSQL concurrent version",
        "formulation_description": f"Revision {revision}",
        "payload": {"revision": revision},
    }


def ingredient_payload(name: str) -> dict:
    return {
        "name": name,
        "price": 1,
        "crude_protein": 1,
        "crude_fat": 1,
        "crude_fiber": 1,
        "metabolized_energy": 1,
        "calcium": 1,
        "total_phosphorus": 1,
        "avail_phosphorus": 1,
        "lysine": 1,
        "methionine": 1,
        "m_c": 1,
        "is_available": True,
    }


def test_postgres_alembic_upgrade_reaches_head(postgres_engine):
    with postgres_engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))

    assert revision == "e8b6a31f0c42"


def test_postgres_registration_email_login_and_health(postgres_engine):
    testing_session = sessionmaker(bind=postgres_engine)

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "postgres-user",
                    "email": "postgres-user@example.com",
                    "password": "password123",
                    "installation_id": "60e5c315-7558-48d6-97d9-7f20e16edc75",
                    "device_name": "PostgreSQL laptop",
                    "device_type": "laptop",
                },
            )
            logged_in = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "postgres-user@example.com",
                    "password": "password123",
                },
            )
            health = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    with testing_session() as session:
        device = session.scalar(select(Device))
        license_record = session.scalar(select(DeviceLicense))

    assert registered.status_code == 200
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"
    assert device.id == license_record.device_id
    assert health.json()["details"]["database_status"] == "healthy"


def test_postgres_serializes_concurrent_formulation_versions(postgres_engine):
    testing_session = sessionmaker(bind=postgres_engine)
    with testing_session() as session:
        user = User(
            username="postgres-version",
            email="postgres-version@example.com",
            password_hash="unused",
            otp_secret="secret",
        )
        session.add(user)
        session.flush()
        series = FormulationSeries(user_id=user.id, next_version_number=2)
        session.add(series)
        session.flush()
        version_one = FeedFormulation(
            **formulation_payload(1),
            user_id=user.id,
            series_id=series.id,
            version_number=1,
        )
        session.add(version_one)
        session.commit()
        user_id = user.id
        version_one_id = version_one.id

    barrier = Barrier(2)

    def create_version(revision: int) -> str:
        with testing_session() as session:
            service = FeedFormulationService(
                session, FeedFormulationRepository(session)
            )
            barrier.wait()
            try:
                service.create_version(
                    version_one_id,
                    FeedFormulationWithPayloadRequest(
                        **formulation_payload(revision)
                    ),
                    user_id,
                )
                return "created"
            except ConflictError:
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_version, [2, 3]))

    with testing_session() as session:
        versions = list(
            session.scalars(
                select(FeedFormulation).order_by(FeedFormulation.version_number)
            ).all()
        )

    assert sorted(results) == ["created", "stale"]
    assert [version.version_number for version in versions] == [1, 2]


def test_postgres_serializes_concurrent_starter_quota(postgres_engine):
    testing_session = sessionmaker(bind=postgres_engine)
    with testing_session() as session:
        user = User(
            username="postgres-quota",
            email="postgres-quota@example.com",
            password_hash="unused",
            otp_secret="secret",
        )
        session.add(user)
        session.flush()
        device = Device(
            user_id=user.id,
            installation_id="70e5c315-7558-48d6-97d9-7f20e16edc75",
            name="Quota laptop",
            device_type="laptop",
        )
        session.add(device)
        session.flush()
        session.add(
            DeviceLicense(
                user_id=user.id,
                device_id=device.id,
                plan_code="starter",
                license_type="trial",
                status="active",
                starts_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=14),
                price_php=0,
            )
        )
        session.add_all(
            [
                Ingredient(
                    **ingredient_payload(f"postgres ingredient {index}"),
                    user_id=user.id,
                )
                for index in range(9)
            ]
        )
        session.commit()
        user_id = user.id
        device_id = device.id

    barrier = Barrier(2)

    def create_ingredient(name: str) -> str:
        with testing_session() as session:
            service = IngredientService(
                session,
                IngredientRepository(session),
                LicensingService(session, LicensingRepository(session)),
            )
            barrier.wait()
            try:
                service.create(
                    IngredientCreate(**ingredient_payload(name)),
                    user_id,
                    device_id,
                )
                return "created"
            except QuotaExceededError:
                session.rollback()
                return "quota"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_ingredient, ["postgres A", "postgres B"]))

    with testing_session() as session:
        total = session.query(Ingredient).filter_by(user_id=user_id).count()

    assert sorted(results) == ["created", "quota"]
    assert total == 10
