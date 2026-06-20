"""add_user_id_to_nutrient_requirements

Revision ID: c7e9a21b8f64
Revises: bf5d6f2a4e31
Create Date: 2026-06-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9a21b8f64'
down_revision: Union[str, None] = 'bf5d6f2a4e31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('nutrient_requirements') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_nutrient_requirements_user_id_users',
            'users',
            ['user_id'],
            ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('nutrient_requirements') as batch_op:
        batch_op.drop_constraint('fk_nutrient_requirements_user_id_users', type_='foreignkey')
        batch_op.drop_column('user_id')
