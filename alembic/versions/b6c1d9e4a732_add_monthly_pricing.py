"""add monthly pricing

Revision ID: b6c1d9e4a732
Revises: e8b6a31f0c42
Create Date: 2026-08-02 00:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c1d9e4a732"
down_revision: Union[str, None] = "e8b6a31f0c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pricing_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pricing_plans_id", "pricing_plans", ["id"])
    op.create_index(
        "ix_pricing_plans_code", "pricing_plans", ["code"], unique=True
    )

    op.create_table(
        "pricing_plan_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("monthly_price", sa.Integer(), nullable=False),
        sa.Column("ingredient_limit", sa.Integer(), nullable=True),
        sa.Column("requirement_limit", sa.Integer(), nullable=True),
        sa.Column("formulation_limit", sa.Integer(), nullable=True),
        sa.Column("effective_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "monthly_price > 0", name="ck_pricing_monthly_price_positive"
        ),
        sa.CheckConstraint(
            "ingredient_limit IS NULL OR ingredient_limit > 0",
            name="ck_pricing_ingredient_limit_positive",
        ),
        sa.CheckConstraint(
            "requirement_limit IS NULL OR requirement_limit > 0",
            name="ck_pricing_requirement_limit_positive",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["pricing_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "version_number",
            name="uq_pricing_plan_versions_plan_version",
        ),
    )
    op.create_index(
        "ix_pricing_plan_versions_id", "pricing_plan_versions", ["id"]
    )
    op.create_index(
        "ix_pricing_plan_versions_plan_id",
        "pricing_plan_versions",
        ["plan_id"],
    )

    now = datetime.utcnow()
    plans = sa.table(
        "pricing_plans",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("currency", sa.String()),
        sa.column("duration_days", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
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
    connection = op.get_bind()
    seeds = [
        ("starter", "Starter", 35_000, 10, 10),
        ("premium", "Premium", 35_000, 50, 50),
        ("ultra", "Ultra", 50_000, None, None),
    ]
    version_ids = {}
    for code, name, monthly_price, ingredient_limit, requirement_limit in seeds:
        connection.execute(
            plans.insert().values(
                code=code,
                name=name,
                currency="PHP",
                duration_days=30,
                created_at=now,
            )
        )
        plan_id = connection.scalar(
            sa.select(plans.c.id).where(plans.c.code == code)
        )
        connection.execute(
            versions.insert().values(
                plan_id=plan_id,
                version_number=1,
                monthly_price=monthly_price,
                ingredient_limit=ingredient_limit,
                requirement_limit=requirement_limit,
                formulation_limit=None,
                effective_at=now,
                created_by_user_id=None,
                created_at=now,
            )
        )
        version_ids[code] = connection.scalar(
            sa.select(versions.c.id).where(versions.c.plan_id == plan_id)
        )

    with op.batch_alter_table("device_licenses") as batch_op:
        batch_op.add_column(
            sa.Column("pricing_plan_version_id", sa.Integer(), nullable=True)
        )

    licenses = sa.table(
        "device_licenses",
        sa.column("plan_code", sa.String()),
        sa.column("pricing_plan_version_id", sa.Integer()),
    )
    for code, version_id in version_ids.items():
        connection.execute(
            licenses.update()
            .where(licenses.c.plan_code == code)
            .values(pricing_plan_version_id=version_id)
        )

    with op.batch_alter_table("device_licenses") as batch_op:
        batch_op.alter_column("pricing_plan_version_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_device_licenses_pricing_plan_version_id",
            "pricing_plan_versions",
            ["pricing_plan_version_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_device_licenses_pricing_plan_version_id",
            ["pricing_plan_version_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("device_licenses") as batch_op:
        batch_op.drop_index("ix_device_licenses_pricing_plan_version_id")
        batch_op.drop_constraint(
            "fk_device_licenses_pricing_plan_version_id", type_="foreignkey"
        )
        batch_op.drop_column("pricing_plan_version_id")

    op.drop_index(
        "ix_pricing_plan_versions_plan_id", table_name="pricing_plan_versions"
    )
    op.drop_index("ix_pricing_plan_versions_id", table_name="pricing_plan_versions")
    op.drop_table("pricing_plan_versions")
    op.drop_index("ix_pricing_plans_code", table_name="pricing_plans")
    op.drop_index("ix_pricing_plans_id", table_name="pricing_plans")
    op.drop_table("pricing_plans")
