"""Add append-only calibration certificate history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0023"
down_revision = "20261108_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "instrument_calibration_events" not in inspector.get_table_names():
        op.create_table(
            "instrument_calibration_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("instrument_calibration_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("calibration_date", sa.Date(), nullable=False),
            sa.Column("calibration_interval_days", sa.Integer(), nullable=False),
            sa.Column("next_calibration_due", sa.Date(), nullable=False),
            sa.Column("calibration_authority", sa.String(length=200), nullable=False),
            sa.Column("certificate_ref", sa.String(length=200), nullable=False),
            sa.Column("result", sa.String(length=10), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("recorded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "calibration_interval_days > 0",
                name="ck_instrument_calibration_event_interval_positive",
            ),
            sa.CheckConstraint(
                "result IN ('PASS', 'FAIL')",
                name="ck_instrument_calibration_event_result",
            ),
            sa.ForeignKeyConstraint(
                ["instrument_calibration_id"],
                ["instrument_calibrations.id"],
                name="fk_instrument_calibration_events_instrument_id",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["recorded_by_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("instrument_calibration_events")}
    index_name = "ix_instrument_calibration_events_instrument_calibration_id"
    if index_name not in indexes:
        op.create_index(
            index_name,
            "instrument_calibration_events",
            ["instrument_calibration_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "instrument_calibration_events" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("instrument_calibration_events")}
    index_name = "ix_instrument_calibration_events_instrument_calibration_id"
    if index_name in indexes:
        op.drop_index(index_name, table_name="instrument_calibration_events")
    op.drop_table("instrument_calibration_events")
