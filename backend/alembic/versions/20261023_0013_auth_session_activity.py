"""track auth session activity for inactivity expiry

Revision ID: 20261023_0013
Revises: 20261023_0012
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "20261023_0013"
down_revision = "20261023_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_refresh_tokens",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE auth_refresh_tokens AS token
        SET last_activity_at = family.last_activity_at
        FROM (
            SELECT family_id, MAX(created_at) AS last_activity_at
            FROM auth_refresh_tokens
            GROUP BY family_id
        ) AS family
        WHERE token.family_id = family.family_id
        """
    )
    op.alter_column(
        "auth_refresh_tokens",
        "last_activity_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def downgrade() -> None:
    op.drop_column("auth_refresh_tokens", "last_activity_at")
