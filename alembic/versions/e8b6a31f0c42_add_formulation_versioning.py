"""add formulation versioning

Revision ID: e8b6a31f0c42
Revises: f0a7d6c4e921
Create Date: 2026-08-02 00:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b6a31f0c42"
down_revision: Union[str, None] = "f0a7d6c4e921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "formulation_series",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("next_version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_formulation_series_id", "formulation_series", ["id"])
    op.create_index(
        "ix_formulation_series_user_id", "formulation_series", ["user_id"]
    )

    with op.batch_alter_table("formulations") as batch_op:
        batch_op.add_column(sa.Column("series_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("parent_version_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("version_number", sa.Integer(), nullable=True)
        )

    now = datetime.utcnow()
    series = sa.table(
        "formulation_series",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("next_version_number", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )
    formulations = sa.table(
        "formulations",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("series_id", sa.Integer()),
        sa.column("parent_version_id", sa.Integer()),
        sa.column("version_number", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            formulations.c.id,
            formulations.c.user_id,
            formulations.c.created_at,
        )
    ).all()
    for row in rows:
        result = connection.execute(
            series.insert().values(
                user_id=row.user_id,
                next_version_number=2,
                created_at=row.created_at or now,
            )
        )
        series_id = result.lastrowid
        if series_id is None:
            series_id = connection.scalar(sa.select(sa.func.max(series.c.id)))
        connection.execute(
            formulations.update()
            .where(formulations.c.id == row.id)
            .values(
                series_id=series_id,
                parent_version_id=None,
                version_number=1,
                created_at=row.created_at or now,
            )
        )

    with op.batch_alter_table("formulations") as batch_op:
        batch_op.alter_column("series_id", nullable=False)
        batch_op.alter_column("version_number", nullable=False)
        batch_op.alter_column("created_at", nullable=False)
        batch_op.create_foreign_key(
            "fk_formulations_series_id_formulation_series",
            "formulation_series",
            ["series_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_formulations_parent_version_id_formulations",
            "formulations",
            ["parent_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_formulations_series_version", ["series_id", "version_number"]
        )
        batch_op.create_index("ix_formulations_series_id", ["series_id"])


def downgrade() -> None:
    with op.batch_alter_table("formulations") as batch_op:
        batch_op.drop_index("ix_formulations_series_id")
        batch_op.drop_constraint(
            "uq_formulations_series_version", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_formulations_parent_version_id_formulations", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_formulations_series_id_formulation_series", type_="foreignkey"
        )
        batch_op.drop_column("version_number")
        batch_op.drop_column("parent_version_id")
        batch_op.drop_column("series_id")

    op.drop_index("ix_formulation_series_user_id", table_name="formulation_series")
    op.drop_index("ix_formulation_series_id", table_name="formulation_series")
    op.drop_table("formulation_series")
