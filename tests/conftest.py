import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 64)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import get_db
from main import app
from datetime import datetime, timedelta
from uuid import uuid4

from models.models import Base, Device, DeviceLicense, User


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db_session: Session):
    def create_user(username: str) -> User:
        user = User(
            username=username,
            email=f"{username}@example.com",
            password_hash="unused",
            otp_secret="secret",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        device = Device(
            user_id=user.id,
            installation_id=str(uuid4()),
            name=f"{username} laptop",
            device_type="laptop",
        )
        db_session.add(device)
        db_session.flush()
        db_session.add(
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
        db_session.commit()
        db_session.refresh(user)
        user.test_device_id = device.id
        return user

    return create_user
