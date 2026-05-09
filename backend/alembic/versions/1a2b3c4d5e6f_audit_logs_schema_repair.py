"""audit_logs_schema_repair

Revision ID: 1a2b3c4d5e6f
Revises: f1a2b3c4e5d6
Create Date: 2026-05-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1a2b3c4d5e6f"
down_revision = "f1a2b3c4e5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("actor_name", sa.String(255), nullable=True))
    op.add_column("audit_logs", sa.Column("session_id", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column("audit_logs", sa.Column("module", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("before_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("after_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("row_hash", sa.String(64), nullable=True))
    op.create_index("ix_audit_logs_session_id", "audit_logs", ["session_id"])
    op.create_index("ix_audit_logs_module", "audit_logs", ["module"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_module", table_name="audit_logs")
    op.drop_index("ix_audit_logs_session_id", table_name="audit_logs")
    op.drop_column("audit_logs", "row_hash")
    op.drop_column("audit_logs", "after_value")
    op.drop_column("audit_logs", "before_value")
    op.drop_column("audit_logs", "module")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "session_id")
    op.drop_column("audit_logs", "actor_name")
