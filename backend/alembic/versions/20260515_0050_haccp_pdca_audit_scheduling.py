"""haccp pdca audit scheduling

Revision ID: 20260515_0050
Revises: 20260515_0030
Create Date: 2026-05-15 14:00:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "20260515_0050"
down_revision = "20260515_0030"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def upgrade() -> None:
    # corrective_actions: PDCA cycle closure timestamp
    _add_column_once(
        "corrective_actions",
        sa.Column("pdca_closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # qms_audit_checklists: scheduling support
    _add_column_once(
        "qms_audit_checklists",
        sa.Column("scheduled_date", sa.Date, nullable=True),
    )
    _add_column_once(
        "qms_audit_checklists",
        sa.Column("recurrence_days", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    if _has_table("qms_audit_checklists"):
        cols = _columns("qms_audit_checklists")
        if "recurrence_days" in cols:
            op.drop_column("qms_audit_checklists", "recurrence_days")
        if "scheduled_date" in cols:
            op.drop_column("qms_audit_checklists", "scheduled_date")
    if _has_table("corrective_actions"):
        if "pdca_closed_at" in _columns("corrective_actions"):
            op.drop_column("corrective_actions", "pdca_closed_at")
