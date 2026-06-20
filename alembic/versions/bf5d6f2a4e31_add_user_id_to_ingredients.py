"""add_user_id_to_ingredients

Revision ID: bf5d6f2a4e31
Revises: a36ce9c7da17
Create Date: 2026-06-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf5d6f2a4e31'
down_revision: Union[str, None] = 'a36ce9c7da17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_ingredients_user_id_users',
            'users',
            ['user_id'],
            ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.drop_constraint('fk_ingredients_user_id_users', type_='foreignkey')
        batch_op.drop_column('user_id')
