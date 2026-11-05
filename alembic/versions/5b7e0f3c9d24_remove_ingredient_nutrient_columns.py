"""Remove nutrient columns after JSON composition backfill.

Revision ID: 5b7e0f3c9d24
Revises: 4a6d9e2b8c13
"""

from alembic import op
import sqlalchemy as sa


revision: str = "5b7e0f3c9d24"
down_revision: str | None = "4a6d9e2b8c13"
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
    connection = op.get_bind()
    ingredients = sa.table(
        "ingredients",
        sa.column("id", sa.Integer()),
        sa.column("composition", sa.JSON()),
        *(sa.column(column, sa.Float()) for column in LEGACY_NUTRIENTS),
    )
    rows = list(connection.execute(sa.select(ingredients)).mappings())
    for row in rows:
        if row["composition"] is not None:
            continue
        if any(row[column] is None for column in LEGACY_NUTRIENTS):
            raise RuntimeError("Ingredient is missing both JSON and legacy nutrients")
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
        batch.alter_column("composition", existing_type=sa.JSON(), nullable=False)
        for column in LEGACY_NUTRIENTS:
            batch.drop_column(column)


def downgrade() -> None:
    connection = op.get_bind()
    ingredients = sa.table(
        "ingredients",
        sa.column("id", sa.Integer()),
        sa.column("composition", sa.JSON()),
    )
    rows = list(connection.execute(sa.select(ingredients)).mappings())
    with op.batch_alter_table("ingredients") as batch:
        batch.alter_column("composition", existing_type=sa.JSON(), nullable=True)
        for column in LEGACY_NUTRIENTS:
            batch.add_column(sa.Column(column, sa.Float(), nullable=True))

    table = sa.table(
        "ingredients",
        sa.column("id", sa.Integer()),
        *(sa.column(column, sa.Float()) for column in LEGACY_NUTRIENTS),
    )
    for row in rows:
        composition = row["composition"] or {}
        connection.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(
                {
                    column: composition.get(nutrient)
                    for column, nutrient in LEGACY_NUTRIENTS.items()
                }
            )
        )
