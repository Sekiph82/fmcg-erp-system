"""maintenance predictive reconciliation

Revision ID: 20260516_0030
Revises: 20260516_0020
Create Date: 2026-05-16 08:00:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260516_0030"
down_revision = "20260516_0020"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _create_enum(name: str, *values: str) -> None:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)


def _enum(name: str, *values: str):
    return postgresql.ENUM(*values, name=name, create_type=False)


def _drop_enum(name: str) -> None:
    op.execute(f"DROP TYPE IF EXISTS {name}")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    ]


def _create_enums() -> None:
    _create_enum("assetstatus", "ACTIVE", "IDLE", "UNDER_MAINTENANCE", "DECOMMISSIONED")
    _create_enum("pmfrequency", "DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "BIANNUAL", "ANNUAL")
    _create_enum("pmstatus", "PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE", "SKIPPED")
    _create_enum("breakdownseverity", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    _create_enum("breakdownstatus", "OPEN", "IN_REPAIR", "RESOLVED")
    _create_enum("maintenancepredictionstatus", "OPEN", "REVIEWED", "WORK_ORDER_CREATED", "DISMISSED")
    _create_enum("maintenancepredictionrisk", "LOW", "MEDIUM", "HIGH", "CRITICAL")


def _create_maintenance_tables() -> None:
    if context.is_offline_mode() or not _has_table("assets"):
        op.create_table(
            "assets",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("asset_no", sa.String(50), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("asset_type", sa.String(100), nullable=True),
            sa.Column("line", sa.String(100), nullable=True),
            sa.Column("serial_no", sa.String(100), nullable=True),
            sa.Column("manufacturer", sa.String(255), nullable=True),
            sa.Column("model", sa.String(255), nullable=True),
            sa.Column("install_date", sa.Date(), nullable=True),
            sa.Column("warranty_expiry", sa.Date(), nullable=True),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("status", _enum("assetstatus", "ACTIVE", "IDLE", "UNDER_MAINTENANCE", "DECOMMISSIONED"), nullable=False, server_default="ACTIVE"),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint("asset_no", name="uq_assets_asset_no"),
        )

    _create_index_once("ix_assets_asset_no", "assets", ["asset_no"])
    _create_index_once("ix_assets_line", "assets", ["line"])

    if context.is_offline_mode() or not _has_table("pm_plans"):
        op.create_table(
            "pm_plans",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("asset_id", UUID, nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("frequency", _enum("pmfrequency", "DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "BIANNUAL", "ANNUAL"), nullable=False, server_default="MONTHLY"),
            sa.Column("interval_days", sa.Integer(), nullable=True),
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("checklist", sa.Text(), nullable=True),
            sa.Column("assigned_to", sa.String(255), nullable=True),
            sa.Column("last_completed_date", sa.Date(), nullable=True),
            sa.Column("next_due_date", sa.Date(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        )

    _create_index_once("ix_pm_plans_asset_id", "pm_plans", ["asset_id"])
    _create_index_once("ix_pm_plans_next_due_date", "pm_plans", ["next_due_date"])

    if context.is_offline_mode() or not _has_table("pm_work_orders"):
        op.create_table(
            "pm_work_orders",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("wo_no", sa.String(50), nullable=False),
            sa.Column("plan_id", UUID, nullable=False),
            sa.Column("scheduled_date", sa.Date(), nullable=False),
            sa.Column("status", _enum("pmstatus", "PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE", "SKIPPED"), nullable=False, server_default="PENDING"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("technician", sa.String(255), nullable=True),
            sa.Column("checklist_notes", sa.Text(), nullable=True),
            sa.Column("completed_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["plan_id"], ["pm_plans.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["completed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("wo_no", name="uq_pm_work_orders_wo_no"),
        )

    _create_index_once("ix_pm_work_orders_wo_no", "pm_work_orders", ["wo_no"])
    _create_index_once("ix_pm_work_orders_plan_id", "pm_work_orders", ["plan_id"])

    if context.is_offline_mode() or not _has_table("breakdown_records"):
        op.create_table(
            "breakdown_records",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("breakdown_no", sa.String(50), nullable=False),
            sa.Column("asset_id", UUID, nullable=False),
            sa.Column("production_order_id", UUID, nullable=True),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("downtime_minutes", sa.Integer(), nullable=True),
            sa.Column("reason", sa.String(500), nullable=False),
            sa.Column("root_cause", sa.Text(), nullable=True),
            sa.Column("severity", _enum("breakdownseverity", "LOW", "MEDIUM", "HIGH", "CRITICAL"), nullable=False, server_default="MEDIUM"),
            sa.Column("status", _enum("breakdownstatus", "OPEN", "IN_REPAIR", "RESOLVED"), nullable=False, server_default="OPEN"),
            sa.Column("corrective_action", sa.Text(), nullable=True),
            sa.Column("reported_by_id", UUID, nullable=True),
            sa.Column("resolved_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["production_order_id"], ["production_orders.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("breakdown_no", name="uq_breakdown_records_no"),
        )

    _create_index_once("ix_breakdown_records_breakdown_no", "breakdown_records", ["breakdown_no"])
    _create_index_once("ix_breakdown_records_asset_id", "breakdown_records", ["asset_id"])
    _create_index_once("ix_breakdown_records_production_order_id", "breakdown_records", ["production_order_id"])

    if context.is_offline_mode() or not _has_table("spare_parts"):
        op.create_table(
            "spare_parts",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("part_no", sa.String(100), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
            sa.Column("material_id", UUID, nullable=True),
            sa.Column("current_stock", sa.Numeric(16, 4), nullable=False, server_default="0"),
            sa.Column("reorder_level", sa.Numeric(16, 4), nullable=True),
            sa.Column("unit_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("supplier", sa.String(255), nullable=True),
            sa.Column("lead_time_days", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_timestamps(),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("part_no", name="uq_spare_parts_part_no"),
        )

    _create_index_once("ix_spare_parts_part_no", "spare_parts", ["part_no"])

    if context.is_offline_mode() or not _has_table("spare_part_usages"):
        op.create_table(
            "spare_part_usages",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("spare_part_id", UUID, nullable=False),
            sa.Column("asset_id", UUID, nullable=False),
            sa.Column("breakdown_id", UUID, nullable=True),
            sa.Column("pm_work_order_id", UUID, nullable=True),
            sa.Column("quantity_used", sa.Numeric(16, 4), nullable=False),
            sa.Column("unit_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("used_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["spare_part_id"], ["spare_parts.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["breakdown_id"], ["breakdown_records.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["pm_work_order_id"], ["pm_work_orders.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["used_by_id"], ["users.id"], ondelete="SET NULL"),
        )

    if context.is_offline_mode() or not _has_table("maintenance_predictions"):
        op.create_table(
            "maintenance_predictions",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("asset_id", UUID, nullable=True),
            sa.Column("machine_id", sa.String(100), nullable=False),
            sa.Column("machine_name", sa.String(255), nullable=True),
            sa.Column("predicted_failure_date", sa.Date(), nullable=False),
            sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("risk_level", _enum("maintenancepredictionrisk", "LOW", "MEDIUM", "HIGH", "CRITICAL"), nullable=False, server_default="MEDIUM"),
            sa.Column("failure_mode", sa.String(200), nullable=False),
            sa.Column("recommended_action", sa.Text(), nullable=False),
            sa.Column("evidence_summary", sa.Text(), nullable=True),
            sa.Column("source_metrics", sa.JSON(), nullable=True),
            sa.Column("status", _enum("maintenancepredictionstatus", "OPEN", "REVIEWED", "WORK_ORDER_CREATED", "DISMISSED"), nullable=False, server_default="OPEN"),
            sa.Column("generated_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by", sa.String(200), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        )

    _create_index_once("ix_maintenance_predictions_asset_id", "maintenance_predictions", ["asset_id"])
    _create_index_once("ix_maintenance_predictions_machine_id", "maintenance_predictions", ["machine_id"])
    _create_index_once("ix_maintenance_predictions_predicted_failure_date", "maintenance_predictions", ["predicted_failure_date"])
    _create_index_once("ix_maintenance_predictions_risk_level", "maintenance_predictions", ["risk_level"])
    _create_index_once("ix_maintenance_predictions_status", "maintenance_predictions", ["status"])


def upgrade() -> None:
    _create_enums()
    _create_maintenance_tables()


def downgrade() -> None:
    for table_name in (
        "maintenance_predictions",
        "spare_part_usages",
        "spare_parts",
        "breakdown_records",
        "pm_work_orders",
        "pm_plans",
        "assets",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)

    for enum_name in (
        "maintenancepredictionrisk",
        "maintenancepredictionstatus",
        "breakdownstatus",
        "breakdownseverity",
        "pmstatus",
        "pmfrequency",
        "assetstatus",
    ):
        _drop_enum(enum_name)
