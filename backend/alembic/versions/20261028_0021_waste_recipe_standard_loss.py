"""snapshot recipe standard loss on waste records

Revision ID: 20261028_0021
Revises: 20261028_0020
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = "20261028_0021"
down_revision = "20261028_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "waste_records",
        sa.Column("standard_loss_pct", sa.Numeric(6, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("waste_records", "standard_loss_pct")