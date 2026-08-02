"""add formulation created timestamp

Revision ID: 093a8297fd39
Revises: c7e9a21b8f64
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "093a8297fd39"
down_revision: Union[str, None] = "c7e9a21b8f64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("formulations") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("formulations") as batch_op:
        batch_op.drop_column("created_at")
