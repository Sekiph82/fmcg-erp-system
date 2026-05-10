"""add user must_change_password flag

Revision ID: 20260510_0700
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-10 07:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260510_0700"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
