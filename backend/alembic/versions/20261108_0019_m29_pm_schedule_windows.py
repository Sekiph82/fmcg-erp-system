"""Link maintenance assets and explicit PM windows to production schedules."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0019"
down_revision = "20261108_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    if "work_center_id" not in asset_columns:
        op.add_column("assets", sa.Column("work_center_id", postgresql.UUID(as_uuid=True), nullable=True))
    asset_fks = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("assets")}
    if "fk_assets_work_center_id_work_centers" not in asset_fks:
        op.create_foreign_key(
            "fk_assets_work_center_id_work_centers",
            "assets",
            "work_centers",
            ["work_center_id"],
            ["id"],
            ondelete="SET NULL",
        )
    asset_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("assets")}
    if "ix_assets_work_center_id" not in asset_indexes:
        op.create_index("ix_assets_work_center_id", "assets", ["work_center_id"])

    pm_columns = {column["name"] for column in sa.inspect(bind).get_columns("pm_work_orders")}
    if "window_start" not in pm_columns:
        op.add_column("pm_work_orders", sa.Column("window_start", sa.DateTime(timezone=True), nullable=True))
    if "window_end" not in pm_columns:
        op.add_column("pm_work_orders", sa.Column("window_end", sa.DateTime(timezone=True), nullable=True))
    pm_checks = {constraint["name"] for constraint in sa.inspect(bind).get_check_constraints("pm_work_orders")}
    if "ck_pm_work_orders_window_order" not in pm_checks:
        op.create_check_constraint(
            "ck_pm_work_orders_window_order",
            "pm_work_orders",
            "(window_start IS NULL AND window_end IS NULL) OR "
            "(window_start IS NOT NULL AND window_end IS NOT NULL AND window_end > window_start)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    pm_checks = {constraint["name"] for constraint in sa.inspect(bind).get_check_constraints("pm_work_orders")}
    if "ck_pm_work_orders_window_order" in pm_checks:
        op.drop_constraint("ck_pm_work_orders_window_order", "pm_work_orders", type_="check")
    pm_columns = {column["name"] for column in sa.inspect(bind).get_columns("pm_work_orders")}
    if "window_end" in pm_columns:
        op.drop_column("pm_work_orders", "window_end")
    if "window_start" in pm_columns:
        op.drop_column("pm_work_orders", "window_start")

    asset_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("assets")}
    if "ix_assets_work_center_id" in asset_indexes:
        op.drop_index("ix_assets_work_center_id", table_name="assets")
    asset_fks = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("assets")}
    if "fk_assets_work_center_id_work_centers" in asset_fks:
        op.drop_constraint("fk_assets_work_center_id_work_centers", "assets", type_="foreignkey")
    asset_columns = {column["name"] for column in sa.inspect(bind).get_columns("assets")}
    if "work_center_id" in asset_columns:
        op.drop_column("assets", "work_center_id")
