"""add device licensing

Revision ID: d40d94c9a812
Revises: c7e9a21b8f64
Create Date: 2026-08-02 00:00:00.000000

"""
from datetime import datetime, timedelta
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "d40d94c9a812"
down_revision: Union[str, None] = "c7e9a21b8f64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("referral_code", sa.String(16), nullable=True))
        batch_op.create_index(
            "ix_users_referral_code", ["referral_code"], unique=True
        )

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("installation_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("device_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("installation_id"),
    )
    op.create_index("ix_devices_id", "devices", ["id"])
    op.create_index("ix_devices_user_id", "devices", ["user_id"])
    op.create_index(
        "ix_devices_installation_id", "devices", ["installation_id"], unique=True
    )

    with op.batch_alter_table("otp_sessions") as batch_op:
        batch_op.add_column(sa.Column("device_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_otp_sessions_device_id_devices", "devices", ["device_id"], ["id"]
        )

    op.create_table(
        "device_licenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("plan_code", sa.String(20), nullable=False),
        sa.Column("license_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("price_php", sa.Integer(), nullable=False),
        sa.Column("payment_reference", sa.String(120), nullable=True),
        sa.Column("activated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index("ix_device_licenses_id", "device_licenses", ["id"])
    op.create_index("ix_device_licenses_user_id", "device_licenses", ["user_id"])
    op.create_index("ix_device_licenses_device_id", "device_licenses", ["device_id"])
    op.create_index("ix_device_licenses_expires_at", "device_licenses", ["expires_at"])

    op.create_table(
        "license_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("license_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["license_id"], ["device_licenses.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_license_events_id", "license_events", ["id"])
    op.create_index("ix_license_events_license_id", "license_events", ["license_id"])

    op.create_table(
        "license_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("license_id", sa.Integer(), nullable=False),
        sa.Column("payment_reference", sa.String(120), nullable=False),
        sa.Column("price_php", sa.Integer(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["license_id"], ["device_licenses.id"]),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index("ix_license_payments_id", "license_payments", ["id"])
    op.create_index(
        "ix_license_payments_license_id", "license_payments", ["license_id"]
    )

    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referrer_user_id", sa.Integer(), nullable=False),
        sa.Column("referred_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("qualified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "referrer_user_id != referred_user_id", name="ck_referrals_not_self"
        ),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referred_user_id", name="uq_referrals_referred_user_id"),
    )
    op.create_index("ix_referrals_id", "referrals", ["id"])
    op.create_index("ix_referrals_referrer_user_id", "referrals", ["referrer_user_id"])

    op.create_table(
        "referral_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referral_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bonus_days", sa.Integer(), nullable=False),
        sa.Column("claimed_license_id", sa.Integer(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["referral_id"], ["referrals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["claimed_license_id"], ["device_licenses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_id"),
    )
    op.create_index("ix_referral_credits_id", "referral_credits", ["id"])
    op.create_index("ix_referral_credits_user_id", "referral_credits", ["user_id"])

    now = datetime.utcnow()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("referral_code", sa.String()),
    )
    licenses = sa.table(
        "device_licenses",
        sa.column("user_id", sa.Integer()),
        sa.column("device_id", sa.Integer()),
        sa.column("plan_code", sa.String()),
        sa.column("license_type", sa.String()),
        sa.column("status", sa.String()),
        sa.column("starts_at", sa.DateTime()),
        sa.column("expires_at", sa.DateTime()),
        sa.column("price_php", sa.Integer()),
        sa.column("payment_reference", sa.String()),
        sa.column("activated_by_user_id", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    connection = op.get_bind()
    user_ids = [row.id for row in connection.execute(sa.select(users.c.id))]
    referral_codes: set[str] = set()
    for user_id in user_ids:
        referral_code = uuid4().hex[:12].upper()
        while referral_code in referral_codes:
            referral_code = uuid4().hex[:12].upper()
        referral_codes.add(referral_code)
        connection.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(referral_code=referral_code)
        )
        connection.execute(
            licenses.insert().values(
                user_id=user_id,
                device_id=None,
                plan_code="starter",
                license_type="trial",
                status="active",
                starts_at=now,
                expires_at=now + timedelta(days=14),
                price_php=0,
                payment_reference=None,
                activated_by_user_id=None,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    op.drop_index("ix_referral_credits_user_id", table_name="referral_credits")
    op.drop_index("ix_referral_credits_id", table_name="referral_credits")
    op.drop_table("referral_credits")
    op.drop_index("ix_referrals_referrer_user_id", table_name="referrals")
    op.drop_index("ix_referrals_id", table_name="referrals")
    op.drop_table("referrals")
    op.drop_index("ix_license_payments_license_id", table_name="license_payments")
    op.drop_index("ix_license_payments_id", table_name="license_payments")
    op.drop_table("license_payments")
    op.drop_index("ix_license_events_license_id", table_name="license_events")
    op.drop_index("ix_license_events_id", table_name="license_events")
    op.drop_table("license_events")
    op.drop_index("ix_device_licenses_expires_at", table_name="device_licenses")
    op.drop_index("ix_device_licenses_device_id", table_name="device_licenses")
    op.drop_index("ix_device_licenses_user_id", table_name="device_licenses")
    op.drop_index("ix_device_licenses_id", table_name="device_licenses")
    op.drop_table("device_licenses")
    with op.batch_alter_table("otp_sessions") as batch_op:
        batch_op.drop_constraint("fk_otp_sessions_device_id_devices", type_="foreignkey")
        batch_op.drop_column("device_id")
    op.drop_index("ix_devices_installation_id", table_name="devices")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_index("ix_devices_id", table_name="devices")
    op.drop_table("devices")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_referral_code")
        batch_op.drop_column("referral_code")
