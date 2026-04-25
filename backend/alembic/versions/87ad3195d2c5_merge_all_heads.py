"""merge_all_heads

Revision ID: 87ad3195d2c5
Revises: a0b1c2d3e4f5, b4c5d6e7f8a9, d4e5f6a7b8cc
Create Date: 2026-04-25 08:30:53.507257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '87ad3195d2c5'
down_revision: Union[str, None] = ('a0b1c2d3e4f5', 'b4c5d6e7f8a9', 'd4e5f6a7b8cc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
