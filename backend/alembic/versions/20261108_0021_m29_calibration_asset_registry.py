"""Link QMS calibration instruments to the maintenance asset register."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0021"
down_revision = "20261108_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("instrument_calibrations")}
    if "asset_id" not in columns:
        op.add_column(
            "instrument_calibrations",
            sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    foreign_keys = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("instrument_calibrations")}
    if "fk_instrument_calibrations_asset_id_assets" not in foreign_keys:
        op.create_foreign_key(
            "fk_instrument_calibrations_asset_id_assets",
            "instrument_calibrations",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="SET NULL",
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("instrument_calibrations")}
    if "ix_instrument_calibrations_asset_id" not in indexes:
        op.create_index("ix_instrument_calibrations_asset_id", "instrument_calibrations", ["asset_id"])

    checks = {check["name"] for check in sa.inspect(bind).get_check_constraints("instrument_calibrations")}
    if "ck_instrument_calibration_interval_positive" not in checks:
        invalid_rows = bind.execute(
            sa.text("SELECT count(*) FROM instrument_calibrations WHERE calibration_interval_days <= 0")
        ).scalar_one()
        if invalid_rows:
            raise RuntimeError(
                "Cannot enforce positive calibration intervals: existing instrument_calibrations rows contain "
                f"{invalid_rows} invalid interval(s). Correct those records before retrying this migration."
            )
        op.create_check_constraint(
            "ck_instrument_calibration_interval_positive",
            "instrument_calibrations",
            "calibration_interval_days > 0",
        )


def downgrade() -> None:
    bind = op.get_bind()
    checks = {check["name"] for check in sa.inspect(bind).get_check_constraints("instrument_calibrations")}
    if "ck_instrument_calibration_interval_positive" in checks:
        op.drop_constraint("ck_instrument_calibration_interval_positive", "instrument_calibrations", type_="check")

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("instrument_calibrations")}
    if "ix_instrument_calibrations_asset_id" in indexes:
        op.drop_index("ix_instrument_calibrations_asset_id", table_name="instrument_calibrations")

    foreign_keys = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("instrument_calibrations")}
    if "fk_instrument_calibrations_asset_id_assets" in foreign_keys:
        op.drop_constraint("fk_instrument_calibrations_asset_id_assets", "instrument_calibrations", type_="foreignkey")

    columns = {column["name"] for column in sa.inspect(bind).get_columns("instrument_calibrations")}
    if "asset_id" in columns:
        op.drop_column("instrument_calibrations", "asset_id")
