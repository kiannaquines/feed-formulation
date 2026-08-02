"""merge formulation timestamp and licensing branches

Revision ID: f0a7d6c4e921
Revises: 093a8297fd39, d40d94c9a812
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union


revision: str = "f0a7d6c4e921"
down_revision: Union[str, tuple[str, str], None] = (
    "093a8297fd39",
    "d40d94c9a812",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
