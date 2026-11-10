"""Persist operator session context on shop-floor activity and downtime records.

Revision ID: 20261104_0010
Revises: 20261104_0009
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0010"
down_revision = "20261104_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sf_activity_logs",
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sf_activity_logs_shift_id_shifts",
        "sf_activity_logs",
        "shifts",
        ["shift_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "sf_downtime_logs",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sf_downtime_logs_session_id_sf_sessions",
        "sf_downtime_logs",
        "sf_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "sf_downtime_logs",
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sf_downtime_logs_shift_id_shifts",
        "sf_downtime_logs",
        "shifts",
        ["shift_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sf_downtime_logs_shift_id_shifts",
        "sf_downtime_logs",
        type_="foreignkey",
    )
    op.drop_column("sf_downtime_logs", "shift_id")
    op.drop_constraint(
        "fk_sf_downtime_logs_session_id_sf_sessions",
        "sf_downtime_logs",
        type_="foreignkey",
    )
    op.drop_column("sf_downtime_logs", "session_id")
    op.drop_constraint(
        "fk_sf_activity_logs_shift_id_shifts",
        "sf_activity_logs",
        type_="foreignkey",
    )
    op.drop_column("sf_activity_logs", "shift_id")
