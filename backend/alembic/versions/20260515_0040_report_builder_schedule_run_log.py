"""report builder schedule run log

Revision ID: 20260515_0040
Revises: 20260515_0030
Create Date: 2026-05-15 14:30:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0040"
down_revision = "20260515_0030"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def upgrade() -> None:
    if not _has_table("rb_schedule_run_log"):
        op.create_table(
            "rb_schedule_run_log",
            sa.Column("run_id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "schedule_id",
                UUID,
                sa.ForeignKey("rb_report_schedules.schedule_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "report_id",
                UUID,
                sa.ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            # status: running / success / failed / skipped
            sa.Column("status", sa.String(20), nullable=False, server_default="running"),
            sa.Column("row_count", sa.Integer, nullable=True),
            sa.Column("export_format", sa.String(10), nullable=True),
            # JSON list of email addresses that were notified
            sa.Column("recipients_sent", sa.Text, nullable=True),
            sa.Column("error_message", sa.Text, nullable=True),
        )
        op.create_index(
            "ix_rb_schedule_run_log_schedule_id",
            "rb_schedule_run_log",
            ["schedule_id"],
        )
        op.create_index(
            "ix_rb_schedule_run_log_started_at",
            "rb_schedule_run_log",
            ["started_at"],
        )


def downgrade() -> None:
    op.drop_table("rb_schedule_run_log")
