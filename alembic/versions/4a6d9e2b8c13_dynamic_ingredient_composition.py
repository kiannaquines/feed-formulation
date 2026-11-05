"""Add and backfill JSON ingredient compositions.

Revision ID: 4a6d9e2b8c13
Revises: f8b2c6d41e73
"""

from alembic import op
import sqlalchemy as sa


revision: str = "4a6d9e2b8c13"
down_revision: str | None = "f8b2c6d41e73"
branch_labels: str | None = None
depends_on: str | None = None


LEGACY_NUTRIENTS = {
    "crude_protein": "protein_percent",
    "crude_fat": "fat_percent",
    "crude_fiber": "fiber_percent",
    "metabolized_energy": "energy_me",
    "calcium": "calcium_percent",
    "total_phosphorus": "phosphorus_percent",
    "avail_phosphorus": "available_phosphorus_percent",
    "lysine": "lysine_percent",
    "methionine": "methionine_percent",
    "m_c": "methionine_cystine_percent",
}


def upgrade() -> None:
    op.add_column("ingredients", sa.Column("composition", sa.JSON(), nullable=True))
    connection = op.get_bind()
    ingredients = sa.table(
        "ingredients",
        sa.column("id", sa.Integer()),
        sa.column("composition", sa.JSON()),
    )
    rows = connection.execute(
        sa.text(f"SELECT id, {', '.join(LEGACY_NUTRIENTS)} FROM ingredients")
    ).mappings()
    for row in rows:
        connection.execute(
            ingredients.update()
            .where(ingredients.c.id == row["id"])
            .values(
                composition={
                    nutrient: row[column]
                    for column, nutrient in LEGACY_NUTRIENTS.items()
                }
            )
        )

    with op.batch_alter_table("ingredients") as batch:
        for column in LEGACY_NUTRIENTS:
            batch.alter_column(column, existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    ingredients = sa.table(
        "ingredients",
        sa.column("id", sa.Integer()),
        sa.column("composition", sa.JSON()),
        *(sa.column(column, sa.Float()) for column in LEGACY_NUTRIENTS),
    )
    rows = list(connection.execute(sa.select(ingredients)).mappings())
    if any(
        any(row[column] is None for column in LEGACY_NUTRIENTS)
        and (
            not isinstance(row["composition"], dict)
            or not set(LEGACY_NUTRIENTS.values()) <= row["composition"].keys()
        )
        for row in rows
    ):
        raise RuntimeError(
            "Cannot downgrade while ingredients have dynamic-only compositions"
        )

    for row in rows:
        if all(row[column] is not None for column in LEGACY_NUTRIENTS):
            continue
        connection.execute(
            ingredients.update()
            .where(ingredients.c.id == row["id"])
            .values(
                {
                    column: row["composition"][nutrient]
                    for column, nutrient in LEGACY_NUTRIENTS.items()
                }
            )
        )

    with op.batch_alter_table("ingredients") as batch:
        for column in LEGACY_NUTRIENTS:
            batch.alter_column(column, existing_type=sa.Float(), nullable=False)
        batch.drop_column("composition")
