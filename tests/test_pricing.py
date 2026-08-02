from datetime import timedelta

from sqlalchemy import select

from core.authentication import create_jwt_token
from models.models import DeviceLicense, Ingredient, PricingPlan, PricingPlanVersion


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


def test_public_monthly_pricing_and_deprecated_alias(client):
    pricing = client.get("/api/v1/pricing/plans")
    legacy = client.get("/api/v1/licensing/plans")

    assert pricing.status_code == 200
    assert pricing.json() == legacy.json()
    assert [plan["code"] for plan in pricing.json()] == [
        "starter",
        "premium",
        "ultra",
    ]
    assert [plan["monthly_price"] for plan in pricing.json()] == [
        35_000,
        45_000,
        50_000,
    ]
    assert all(plan["duration_days"] == 30 for plan in pricing.json())
    assert all("annual_price" not in plan for plan in pricing.json())


def test_only_admin_can_publish_immutable_pricing_versions(
    client, db_session, user_factory
):
    admin = user_factory("pricing-admin")
    admin.is_superuser = True
    user = user_factory("pricing-user")
    db_session.commit()
    payload = {
        "monthly_price": 36_000,
        "ingredient_limit": 12,
        "requirement_limit": 12,
    }

    forbidden = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json=payload,
        headers=auth_header(user),
    )
    published = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json=payload,
        headers=auth_header(admin),
    )
    history = client.get(
        "/api/v1/admin/pricing/plans/starter/versions",
        headers=auth_header(admin),
    )
    invalid = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json={**payload, "monthly_price": 0},
        headers=auth_header(admin),
    )

    assert forbidden.status_code == 403
    assert published.status_code == 201
    assert published.json()["version_number"] == 2
    assert published.json()["created_by_user_id"] == admin.id
    assert [version["version_number"] for version in history.json()] == [2, 1]
    assert history.json()[1]["monthly_price"] == 35_000
    assert invalid.status_code == 422


def test_active_license_keeps_snapshot_until_monthly_renewal(
    client, db_session, user_factory
):
    admin = user_factory("snapshot-admin")
    admin.is_superuser = True
    owner = user_factory("snapshot-owner")
    db_session.commit()

    activated = client.post(
        "/api/v1/admin/licenses/activate",
        json={
            "user_id": owner.id,
            "device_id": owner.test_device_id,
            "plan_code": "starter",
            "payment_reference": "PRICE-SNAPSHOT-1",
        },
        headers=auth_header(admin),
    )
    license_id = activated.json()["id"]
    original_version_id = activated.json()["pricing_plan_version_id"]
    original_expiry = db_session.get(DeviceLicense, license_id).expires_at

    published = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json={
            "monthly_price": 36_000,
            "ingredient_limit": 12,
            "requirement_limit": 12,
        },
        headers=auth_header(admin),
    )
    db_session.add_all(
        [
            Ingredient(
                **ingredient_payload(f"snapshot ingredient {index}"),
                user_id=owner.id,
            )
            for index in range(10)
        ]
    )
    db_session.commit()
    blocked_before_renewal = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("snapshot ingredient 11"),
        headers=auth_header(owner),
    )

    renewed = client.post(
        f"/api/v1/admin/licenses/{license_id}/renew",
        json={
            "plan_code": "starter",
            "payment_reference": "PRICE-SNAPSHOT-2",
        },
        headers=auth_header(admin),
    )
    allowed_after_renewal = client.post(
        "/api/v1/ingredients/create",
        json=ingredient_payload("snapshot ingredient 11"),
        headers=auth_header(owner),
    )
    stored_license = db_session.get(DeviceLicense, license_id)

    assert activated.status_code == 201
    assert activated.json()["expires_at"]
    assert blocked_before_renewal.status_code == 409
    assert renewed.status_code == 200
    assert renewed.json()["pricing_plan_version_id"] == published.json()["id"]
    assert renewed.json()["pricing_plan_version_id"] != original_version_id
    assert renewed.json()["price_php"] == 36_000
    assert stored_license.expires_at == original_expiry + timedelta(days=30)
    assert allowed_after_renewal.status_code == 200


def test_price_only_publication_inherits_omitted_quotas_and_null_is_unlimited(
    client, db_session, user_factory
):
    admin = user_factory("quota-inheritance-admin")
    admin.is_superuser = True
    db_session.commit()

    price_only = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json={"monthly_price": 36_000},
        headers=auth_header(admin),
    )
    unlimited_ingredients = client.post(
        "/api/v1/admin/pricing/plans/starter/versions",
        json={"monthly_price": 37_000, "ingredient_limit": None},
        headers=auth_header(admin),
    )

    assert price_only.status_code == 201
    assert price_only.json()["ingredient_limit"] == 10
    assert price_only.json()["requirement_limit"] == 10
    assert unlimited_ingredients.status_code == 201
    assert unlimited_ingredients.json()["ingredient_limit"] is None
    assert unlimited_ingredients.json()["requirement_limit"] == 10


def test_seeded_pricing_versions_are_linked_to_trial_licenses(
    db_session, user_factory
):
    user = user_factory("pricing-link")
    license_record = db_session.scalar(
        select(DeviceLicense).where(DeviceLicense.user_id == user.id)
    )
    version = db_session.get(
        PricingPlanVersion, license_record.pricing_plan_version_id
    )
    plan = db_session.get(PricingPlan, version.plan_id)

    assert plan.code == "starter"
    assert version.monthly_price == 35_000
