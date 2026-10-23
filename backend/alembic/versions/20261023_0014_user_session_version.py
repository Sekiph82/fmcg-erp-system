"""add user-wide authentication session version

Revision ID: 20261023_0014
Revises: 20261023_0013
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "20261023_0014"
down_revision = "20261023_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_session_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "auth_session_version")
