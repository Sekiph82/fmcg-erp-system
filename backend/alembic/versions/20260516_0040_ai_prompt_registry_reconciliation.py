"""AI Prompt Registry reconciliation (GAP-024C)

Revision ID: 20260516_0040
Revises: 20260516_0030
Create Date: 2026-05-16 11:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260516_0040"
down_revision = "20260516_0030"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    from alembic import context
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if not _has_table("ai_prompts"):
        op.create_table(
            "ai_prompts",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("version", sa.Integer, nullable=False, server_default="1"),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("module", sa.String(50), nullable=True),
            sa.Column("prompt_type", sa.String(50), nullable=False, server_default="system"),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("variables", sa.JSON, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("created_by", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("key", "version", name="uq_ai_prompts_key_version"),
        )
        op.create_index("ix_ai_prompts_key_active", "ai_prompts", ["key", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_ai_prompts_key_active", table_name="ai_prompts")
    op.drop_table("ai_prompts")
