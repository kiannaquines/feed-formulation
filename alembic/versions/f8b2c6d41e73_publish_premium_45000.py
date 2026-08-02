"""Publish the authoritative Premium monthly price.

Revision ID: f8b2c6d41e73
Revises: e3f4a1b72c90
Create Date: 2026-08-02
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = "f8b2c6d41e73"
down_revision: str | None = "e3f4a1b72c90"
branch_labels: str | None = None
depends_on: str | None = None


PUBLISHED_TIMESTAMP = datetime(2026, 8, 2, 17, 0, 0)


def upgrade() -> None:
    connection = op.get_bind()
    plans = sa.table(
        "pricing_plans",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
    )
    versions = sa.table(
        "pricing_plan_versions",
        sa.column("id", sa.Integer()),
        sa.column("plan_id", sa.Integer()),
        sa.column("version_number", sa.Integer()),
        sa.column("monthly_price", sa.Integer()),
        sa.column("ingredient_limit", sa.Integer()),
        sa.column("requirement_limit", sa.Integer()),
        sa.column("formulation_limit", sa.Integer()),
        sa.column("effective_at", sa.DateTime()),
        sa.column("created_by_user_id", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )

    plan_id = connection.scalar(
        sa.select(plans.c.id).where(plans.c.code == "premium")
    )
    current = connection.execute(
        sa.select(versions)
        .where(versions.c.plan_id == plan_id)
        .order_by(versions.c.version_number.desc())
        .limit(1)
    ).mappings().one()
    if current["monthly_price"] == 45_000:
        return

    connection.execute(
        versions.insert().values(
            plan_id=plan_id,
            version_number=current["version_number"] + 1,
            monthly_price=45_000,
            ingredient_limit=current["ingredient_limit"],
            requirement_limit=current["requirement_limit"],
            formulation_limit=current["formulation_limit"],
            effective_at=PUBLISHED_TIMESTAMP,
            created_by_user_id=None,
            created_at=PUBLISHED_TIMESTAMP,
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    plans = sa.table(
        "pricing_plans",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
    )
    versions = sa.table(
        "pricing_plan_versions",
        sa.column("id", sa.Integer()),
        sa.column("plan_id", sa.Integer()),
        sa.column("version_number", sa.Integer()),
        sa.column("effective_at", sa.DateTime()),
        sa.column("created_at", sa.DateTime()),
    )
    licenses = sa.table(
        "device_licenses",
        sa.column("pricing_plan_version_id", sa.Integer()),
    )

    plan_id = connection.scalar(
        sa.select(plans.c.id).where(plans.c.code == "premium")
    )
    published = connection.execute(
        sa.select(versions.c.id, versions.c.version_number).where(
            versions.c.plan_id == plan_id,
            versions.c.effective_at == PUBLISHED_TIMESTAMP,
            versions.c.created_at == PUBLISHED_TIMESTAMP,
        )
    ).mappings().one_or_none()
    if published is None:
        return

    previous_id = connection.scalar(
        sa.select(versions.c.id)
        .where(
            versions.c.plan_id == plan_id,
            versions.c.version_number < published["version_number"],
        )
        .order_by(versions.c.version_number.desc())
        .limit(1)
    )
    connection.execute(
        licenses.update()
        .where(licenses.c.pricing_plan_version_id == published["id"])
        .values(pricing_plan_version_id=previous_id)
    )
    connection.execute(versions.delete().where(versions.c.id == published["id"]))
