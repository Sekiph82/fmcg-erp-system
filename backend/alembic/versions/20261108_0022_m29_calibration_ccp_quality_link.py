"""Link CCP monitoring records to calibration instruments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0022"
down_revision = "20261108_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("ccp_monitoring_logs")}
    if "instrument_calibration_id" not in columns:
        op.add_column(
            "ccp_monitoring_logs",
            sa.Column("instrument_calibration_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "calibration_status_at_record" not in columns:
        op.add_column(
            "ccp_monitoring_logs",
            sa.Column("calibration_status_at_record", sa.String(length=30), nullable=True),
        )
    if "calibration_instrument_code_at_record" not in columns:
        op.add_column(
            "ccp_monitoring_logs",
            sa.Column("calibration_instrument_code_at_record", sa.String(length=50), nullable=True),
        )

    foreign_keys = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("ccp_monitoring_logs")}
    fk_name = "fk_ccp_monitoring_logs_instrument_calibration_id_instrument_calibrations"
    if fk_name not in foreign_keys:
        op.create_foreign_key(
            fk_name,
            "ccp_monitoring_logs",
            "instrument_calibrations",
            ["instrument_calibration_id"],
            ["id"],
            ondelete="SET NULL",
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("ccp_monitoring_logs")}
    if "ix_ccp_monitoring_logs_instrument_calibration_id" not in indexes:
        op.create_index(
            "ix_ccp_monitoring_logs_instrument_calibration_id",
            "ccp_monitoring_logs",
            ["instrument_calibration_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("ccp_monitoring_logs")}
    if "ix_ccp_monitoring_logs_instrument_calibration_id" in indexes:
        op.drop_index("ix_ccp_monitoring_logs_instrument_calibration_id", table_name="ccp_monitoring_logs")

    foreign_keys = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("ccp_monitoring_logs")}
    fk_name = "fk_ccp_monitoring_logs_instrument_calibration_id_instrument_calibrations"
    if fk_name in foreign_keys:
        op.drop_constraint(fk_name, "ccp_monitoring_logs", type_="foreignkey")

    columns = {column["name"] for column in sa.inspect(bind).get_columns("ccp_monitoring_logs")}
    if "calibration_instrument_code_at_record" in columns:
        op.drop_column("ccp_monitoring_logs", "calibration_instrument_code_at_record")
    if "calibration_status_at_record" in columns:
        op.drop_column("ccp_monitoring_logs", "calibration_status_at_record")
    if "instrument_calibration_id" in columns:
        op.drop_column("ccp_monitoring_logs", "instrument_calibration_id")
