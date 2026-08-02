"""Backfill devices for licenses created during the licensing migration.

Revision ID: e3f4a1b72c90
Revises: c7d2f8a19e04
Create Date: 2026-08-02
"""

from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a1b72c90"
down_revision: str | None = "c7d2f8a19e04"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    connection = op.get_bind()
    devices = sa.table(
        "devices",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("installation_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("device_type", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("last_seen_at", sa.DateTime()),
    )
    licenses = sa.table(
        "device_licenses",
        sa.column("user_id", sa.Integer()),
        sa.column("device_id", sa.Integer()),
    )
    now = datetime.utcnow()
    affected_user_ids = connection.scalars(
        sa.select(licenses.c.user_id)
        .where(licenses.c.device_id.is_(None))
        .distinct()
        .order_by(licenses.c.user_id)
    ).all()

    for user_id in affected_user_ids:
        device_id = connection.scalar(
            sa.select(devices.c.id)
            .where(devices.c.user_id == user_id)
            .order_by(devices.c.created_at, devices.c.id)
            .limit(1)
        )
        if device_id is None:
            installation_id = str(
                uuid5(NAMESPACE_URL, f"feedprime:migrated-user:{user_id}")
            )
            connection.execute(
                devices.insert().values(
                    user_id=user_id,
                    installation_id=installation_id,
                    name="Migrated desktop",
                    device_type="desktop",
                    is_active=True,
                    created_at=now,
                    last_seen_at=now,
                )
            )
            device_id = connection.scalar(
                sa.select(devices.c.id).where(
                    devices.c.installation_id == installation_id
                )
            )

        connection.execute(
            licenses.update()
            .where(
                licenses.c.user_id == user_id,
                licenses.c.device_id.is_(None),
            )
            .values(device_id=device_id)
        )

    with op.batch_alter_table("device_licenses") as batch_op:
        batch_op.alter_column("device_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("device_licenses") as batch_op:
        batch_op.alter_column("device_id", existing_type=sa.Integer(), nullable=True)
