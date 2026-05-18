"""OTP delivery: expand challenge_code column to store bcrypt hash

Revision ID: 20260518_0001
Revises: 20260516_0060
Create Date: 2026-05-18

Expands two_fa_sessions.challenge_code from String(10) to String(255)
so it can store a bcrypt hash instead of a plaintext OTP.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260518_0001"
down_revision = "20260516_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "two_fa_sessions",
        "challenge_code",
        existing_type=sa.String(10),
        type_=sa.String(255),
        existing_nullable=True,
        postgresql_using="challenge_code::varchar(255)",
    )


def downgrade() -> None:
    op.alter_column(
        "two_fa_sessions",
        "challenge_code",
        existing_type=sa.String(255),
        type_=sa.String(10),
        existing_nullable=True,
        postgresql_using="left(challenge_code, 10)::varchar(10)",
    )
