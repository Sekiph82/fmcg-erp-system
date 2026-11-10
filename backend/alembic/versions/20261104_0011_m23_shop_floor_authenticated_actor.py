"""Persist authenticated ERP actors for shop-floor sessions and decisions.

Revision ID: 20261104_0011
Revises: 20261104_0010
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0011"
down_revision = "20261104_0010"
branch_labels = None
depends_on = None


_ACTOR_COLUMNS = (
    ("sf_sessions", "authenticated_user_id"),
    ("sf_activity_logs", "actor_user_id"),
    ("sf_downtime_logs", "created_by_user_id"),
    ("sf_downtime_logs", "closed_by_user_id"),
    ("sf_shift_handovers", "created_by_user_id"),
    ("sf_shift_handovers", "approved_by_user_id"),
    ("sf_supervisor_overrides", "actor_user_id"),
    ("sf_ai_recs", "actioned_by_user_id"),
)


def upgrade() -> None:
    for table, column in _ACTOR_COLUMNS:
        op.add_column(table, sa.Column(column, postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_{column}_users",
            table,
            "users",
            [column],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table, column in reversed(_ACTOR_COLUMNS):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.drop_constraint(f"fk_{table}_{column}_users", table, type_="foreignkey")
        op.drop_column(table, column)
