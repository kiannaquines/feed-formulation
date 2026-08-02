"""Correct the Premium monthly price without changing active license snapshots.

Revision ID: c7d2f8a19e04
Revises: b6c1d9e4a732
Create Date: 2026-08-02
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = "c7d2f8a19e04"
down_revision: str | None = "b6c1d9e4a732"
branch_labels: str | None = None
depends_on: str | None = None


CORRECTION_TIMESTAMP = datetime(2026, 8, 2, 12, 0, 0)


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
    if current["monthly_price"] == 35_000:
        return

    connection.execute(
        versions.insert().values(
            plan_id=plan_id,
            version_number=current["version_number"] + 1,
            monthly_price=35_000,
            ingredient_limit=current["ingredient_limit"],
            requirement_limit=current["requirement_limit"],
            formulation_limit=current["formulation_limit"],
            effective_at=CORRECTION_TIMESTAMP,
            created_by_user_id=None,
            created_at=CORRECTION_TIMESTAMP,
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
    correction = connection.execute(
        sa.select(versions.c.id, versions.c.version_number).where(
            versions.c.plan_id == plan_id,
            versions.c.effective_at == CORRECTION_TIMESTAMP,
            versions.c.created_at == CORRECTION_TIMESTAMP,
        )
    ).mappings().one_or_none()
    if correction is None:
        return

    previous_id = connection.scalar(
        sa.select(versions.c.id)
        .where(
            versions.c.plan_id == plan_id,
            versions.c.version_number < correction["version_number"],
        )
        .order_by(versions.c.version_number.desc())
        .limit(1)
    )
    connection.execute(
        licenses.update()
        .where(licenses.c.pricing_plan_version_id == correction["id"])
        .values(pricing_plan_version_id=previous_id)
    )
    connection.execute(versions.delete().where(versions.c.id == correction["id"]))
