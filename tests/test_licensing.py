from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.authentication import create_jwt_token
from core.exceptions import QuotaExceededError
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
    Base,
)
from repositories import IngredientRepository, LicensingRepository
from schema.schema import IngredientCreate
from services import IngredientService, LicensingService


def auth_header(user) -> dict:
    token = create_jwt_token(user.id, user.username, user.test_device_id)
    return {"Authorization": f"Bearer {token}"}


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


def login_payload(username: str, installation_id: str, name: str) -> dict:
    return {
        "username": username,
        "password": "password123",
        "installation_id": installation_id,
        "device_name": name,
        "device_type": "laptop",
    }


def test_registration_creates_trial_referral_code_and_binds_first_device(
    client, db_session
):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "username": "trial-user",
            "email": "trial-user@example.com",
            "password": "password123",
        },
    )
    user = db_session.scalar(select(User).where(User.username == "trial-user"))
    trial = db_session.scalar(
        select(DeviceLicense).where(DeviceLicense.user_id == user.id)
    )

    logged_in = client.post(
        "/api/v1/auth/login",
        json=login_payload(
            "trial-user",
            "7cc806c3-bff2-4606-8414-55b6e6448e83",
            "Trial laptop",
        ),
    )
    db_session.refresh(trial)
    device = db_session.get(Device, trial.device_id)

    assert registered.status_code == 200
    assert len(user.referral_code) == 12
    assert trial.license_type == "trial"
    assert trial.expires_at - trial.starts_at == timedelta(days=14)
    assert device.installation_id == "7cc806c3-bff2-4606-8414-55b6e6448e83"
    assert logged_in.status_code == 200


def test_invalid_referral_rolls_back_registration(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "invalid-referral",
            "email": "invalid-referral@example.com",
            "password": "password123",
            "referral_code": "MISSING1",
        },
    )

    stored = db_session.scalar(
        select(User).where(User.username == "invalid-referral")
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Referral code is invalid"}
    assert stored is None


def test_expired_license_blocks_business_data_but_preserves_status_access(
    client, db_session, user_factory
):
    user = user_factory("expired")
    license_record = db_session.scalar(
        select(DeviceLicense).where(DeviceLicense.user_id == user.id)
    )
    license_record.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    business = client.get("/api/v1/ingredients/all", headers=auth_header(user))
    licensing = client.get("/api/v1/licensing/status", headers=auth_header(user))

    assert business.status_code == 403
    assert "active trial or paid license" in business.json()["detail"]
    assert licensing.status_code == 200
    assert licensing.json()["status"] == "expired"


def test_starter_quota_counts_only_owned_ingredients(
    client, db_session, user_factory
):
    user = user_factory("quota")
    db_session.add(Ingredient(**ingredient_payload("shared quota"), user_id=None))
    db_session.add_all(
        [
            Ingredient(**ingredient_payload(f"quota ingredient {index}"), user_id=user.id)
            for index in range(10)
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("over quota"),
        headers=auth_header(user),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The Starter plan allows up to 10 saved ingredients"
    }


def test_premium_limit_and_ultra_unlimited_ingredient_saving(
    client, db_session, user_factory
):
    premium = user_factory("premium-quota")
    ultra = user_factory("ultra-quota")
    premium_license = db_session.scalar(
        select(DeviceLicense).where(DeviceLicense.user_id == premium.id)
    )
    ultra_license = db_session.scalar(
        select(DeviceLicense).where(DeviceLicense.user_id == ultra.id)
    )
    premium_license.plan_code = "premium"
    ultra_license.plan_code = "ultra"
    db_session.add_all(
        [
            Ingredient(
                **ingredient_payload(f"premium ingredient {index}"),
                user_id=premium.id,
            )
            for index in range(49)
        ]
        + [
            Ingredient(
                **ingredient_payload(f"ultra ingredient {index}"),
                user_id=ultra.id,
            )
            for index in range(51)
        ]
    )
    db_session.commit()

    fiftieth = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("premium ingredient 50"),
        headers=auth_header(premium),
    )
    fifty_first = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("premium ingredient 51"),
        headers=auth_header(premium),
    )
    ultra_extra = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("ultra ingredient 52"),
        headers=auth_header(ultra),
    )

    assert fiftieth.status_code == 200
    assert fifty_first.status_code == 409
    assert ultra_extra.status_code == 200


def test_starter_requirement_quota_is_enforced(client, db_session, user_factory):
    user = user_factory("requirement-quota")
    db_session.add_all(
        [
            NutrientRequirements(
                nutrient_requirement_name=f"Requirement {index}",
                nutrient_requirement_description="Description",
                composition={},
                user_id=user.id,
            )
            for index in range(10)
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/nutrient-requirements/create",
        json={
            "nutrient_requirement_name": "Over quota",
            "nutrient_requirement_description": "Description",
            "composition": {},
        },
        headers=auth_header(user),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The Starter plan allows up to 10 saved requirements"
    }


def test_concurrent_starter_creates_cannot_exceed_quota(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'quota.db'}")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as session:
        user = User(
            username="concurrent",
            email="concurrent@example.com",
            password_hash="unused",
            otp_secret="secret",
        )
        session.add(user)
        session.flush()
        device = Device(
            user_id=user.id,
            installation_id="667cab50-c870-4887-8627-b3cf5cda7309",
            name="Concurrent laptop",
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
                    **ingredient_payload(f"concurrent ingredient {index}"),
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
        results = list(
            executor.map(create_ingredient, ["concurrent A", "concurrent B"])
        )
    with testing_session() as session:
        stored_count = session.scalar(
            select(Ingredient).where(Ingredient.user_id == user_id)
        )
        total = session.query(Ingredient).filter_by(user_id=user_id).count()
    engine.dispose()

    assert sorted(results) == ["created", "quota"]
    assert stored_count is not None
    assert total == 10


def test_admin_activation_qualifies_referral_and_credit_extends_chosen_license(
    client, db_session, user_factory
):
    admin = user_factory("admin")
    admin.is_superuser = True
    referrer = user_factory("referrer")
    referred = user_factory("referred")
    referrer.referral_code = "REFER1234567"
    referral = Referral(referrer_user_id=referrer.id, referred_user_id=referred.id)
    db_session.add(referral)
    db_session.commit()

    referrer_activation = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": referrer.id,
            "device_id": referrer.test_device_id,
            "plan_code": "starter",
            "payment_reference": "PAY-REFERRER-1",
        },
        headers=auth_header(admin),
    )
    referred_activation = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": referred.id,
            "device_id": referred.test_device_id,
            "plan_code": "premium",
            "payment_reference": "PAY-REFERRED-1",
        },
        headers=auth_header(admin),
    )
    credit = db_session.scalar(
        select(ReferralCredit).where(ReferralCredit.user_id == referrer.id)
    )
    paid_license_id = referrer_activation.json()["id"]
    previous_expiry = db_session.get(DeviceLicense, paid_license_id).expires_at

    claimed = client.post(
        f"/api/v1/referrals/credits/{credit.id}/claim",
        json={"license_id": paid_license_id},
        headers=auth_header(referrer),
    )
    claimed_again = client.post(
        f"/api/v1/referrals/credits/{credit.id}/claim",
        json={"license_id": paid_license_id},
        headers=auth_header(referrer),
    )
    db_session.expire_all()
    extended = db_session.get(DeviceLicense, paid_license_id)

    assert referrer_activation.status_code == 201
    assert referred_activation.status_code == 201
    assert referral.status == "qualified"
    assert claimed.status_code == 200
    assert claimed_again.status_code == 409
    assert extended.expires_at == previous_expiry + timedelta(days=30)
    assert credit.claimed_license_id == paid_license_id


def test_license_reassignment_requires_same_owner_and_records_event(
    client, db_session, user_factory
):
    admin = user_factory("reassign-admin")
    admin.is_superuser = True
    owner = user_factory("reassign-owner")
    other = user_factory("reassign-other")
    target = Device(
        user_id=owner.id,
        installation_id="04287eec-b302-4c67-81b5-6380a0b9487d",
        name="Replacement desktop",
        device_type="desktop",
    )
    db_session.add(target)
    db_session.commit()

    activated = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": owner.id,
            "device_id": owner.test_device_id,
            "plan_code": "ultra",
            "payment_reference": "PAY-REASSIGN-1",
        },
        headers=auth_header(admin),
    )
    license_id = activated.json()["id"]
    rejected = client.post(
        f"/api/v1/admin/licenses/{license_id}/reassign",
        json={"device_id": other.test_device_id, "reason": "Wrong owner"},
        headers=auth_header(admin),
    )
    moved = client.post(
        f"/api/v1/admin/licenses/{license_id}/reassign",
        json={"device_id": target.id, "reason": "Replaced failed computer"},
        headers=auth_header(admin),
    )
    event = db_session.scalar(
        select(LicenseEvent)
        .where(
            LicenseEvent.license_id == license_id,
            LicenseEvent.event_type == "reassigned",
        )
    )

    assert rejected.status_code == 403
    assert moved.status_code == 200
    assert moved.json()["device_id"] == target.id
    assert event.details["reason"] == "Replaced failed computer"


def test_license_renewal_preserves_payment_history_and_adds_365_days(
    client, db_session, user_factory
):
    admin = user_factory("renew-admin")
    admin.is_superuser = True
    owner = user_factory("renew-owner")
    db_session.commit()
    activated = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": owner.id,
            "device_id": owner.test_device_id,
            "plan_code": "starter",
            "payment_reference": "PAY-RENEW-1",
        },
        headers=auth_header(admin),
    )
    license_id = activated.json()["id"]
    first_expiry = db_session.get(DeviceLicense, license_id).expires_at

    renewed = client.post(
        f"/api/v1/admin/licenses/{license_id}/renew",
        json={"plan_code": "premium", "payment_reference": "PAY-RENEW-2"},
        headers=auth_header(admin),
    )
    duplicate_payment = client.post(
        f"/api/v1/admin/licenses/{license_id}/renew",
        json={"plan_code": "ultra", "payment_reference": "PAY-RENEW-1"},
        headers=auth_header(admin),
    )
    payments = list(
        db_session.scalars(
            select(LicensePayment)
            .where(LicensePayment.license_id == license_id)
            .order_by(LicensePayment.created_at)
        ).all()
    )

    assert renewed.status_code == 200
    assert duplicate_payment.status_code == 409
    assert renewed.json()["plan_code"] == "premium"
    assert db_session.get(DeviceLicense, license_id).expires_at == (
        first_expiry + timedelta(days=365)
    )
    assert [payment.payment_reference for payment in payments] == [
        "PAY-RENEW-1",
        "PAY-RENEW-2",
    ]


def test_non_superuser_cannot_activate_license(client, user_factory):
    user = user_factory("not-admin")

    response = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": user.id,
            "device_id": user.test_device_id,
            "plan_code": "starter",
            "payment_reference": "PAY-NOT-ADMIN",
        },
        headers=auth_header(user),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Superuser access is required"}
