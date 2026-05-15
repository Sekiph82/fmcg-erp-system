"""Add APS planning tables.

Revision ID: 20260514_0010
Revises: 20260511_0040
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0010"
down_revision = "20260511_0040"
branch_labels = None
depends_on = None


scenario_status = sa.Enum("DRAFT", "ACTIVE", "LOCKED", "ARCHIVED", name="scenariostatus")
scenario_mode = sa.Enum("FINITE", "INFINITE", name="scenariomode")
op_queue_status = sa.Enum(
    "PENDING",
    "SCHEDULED",
    "IN_PROGRESS",
    "COMPLETED",
    "BLOCKED",
    "SKIPPED",
    name="opqueuestatus",
)
capacity_slot_type = sa.Enum("AVAILABLE", "ALLOCATED", "BLOCKED", "CHANGEOVER", name="capacityslottype")
bottleneck_severity = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="bottleneckseverity")
planning_agent_type = sa.Enum(
    "CAPACITY_OPTIMIZER",
    "SEQUENCING_OPTIMIZER",
    "DISRUPTION_PREDICTOR",
    name="planningagenttype",
)
planning_rec_status = sa.Enum("PENDING", "ACCEPTED", "REJECTED", name="planningrecstatus")
simulation_status = sa.Enum("DRAFT", "COMPUTED", "PUBLISHED", "DISCARDED", name="simulationstatus")


def upgrade() -> None:
    op.create_table(
        "planning_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_no", sa.String(50), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", scenario_status, nullable=False, server_default="DRAFT"),
        sa.Column("mode", scenario_mode, nullable=False, server_default="FINITE"),
        sa.Column("horizon_start", sa.Date(), nullable=True),
        sa.Column("horizon_end", sa.Date(), nullable=True),
        sa.Column("mps_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_ops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_ops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_ops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_utilization_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("total_changeover_hrs", sa.Numeric(10, 2), nullable=True),
        sa.Column("bottleneck_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scenario_no", name="uq_planning_scenarios_scenario_no"),
    )
    op.create_index("ix_planning_scenarios_scenario_no", "planning_scenarios", ["scenario_no"])
    op.create_index("ix_planning_scenarios_status", "planning_scenarios", ["status"])

    op.create_table(
        "resource_calendars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("work_center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("available_hours", sa.Numeric(6, 2), nullable=False, server_default="8.0"),
        sa.Column("shift_1_start", sa.String(8), nullable=True),
        sa.Column("shift_1_end", sa.String(8), nullable=True),
        sa.Column("shift_2_start", sa.String(8), nullable=True),
        sa.Column("shift_2_end", sa.String(8), nullable=True),
        sa.Column("shift_3_start", sa.String(8), nullable=True),
        sa.Column("shift_3_end", sa.String(8), nullable=True),
        sa.Column("is_holiday", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_maintenance", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("work_center_id", "calendar_date", name="uq_rescal_wc_date"),
    )
    op.create_index("ix_resource_calendars_calendar_date", "resource_calendars", ["calendar_date"])
    op.create_index("ix_resource_calendars_work_center_id", "resource_calendars", ["work_center_id"])

    op.create_table(
        "operation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("op_no", sa.String(50), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mps_line_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_lines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("production_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("routing_step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routing_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_code", sa.String(100), nullable=True),
        sa.Column("work_center_name", sa.String(255), nullable=True),
        sa.Column("step_name", sa.String(255), nullable=True),
        sa.Column("planned_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("rate_per_hour", sa.Numeric(10, 3), nullable=True),
        sa.Column("setup_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cleanup_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changeover_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", op_queue_status, nullable=False, server_default="PENDING"),
        sa.Column("is_critical_path", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("predecessor_ids", sa.JSON(), nullable=True),
        sa.Column("block_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_operation_queue_op_no", "operation_queue", ["op_no"])
    op.create_index("ix_operation_queue_scenario_id", "operation_queue", ["scenario_id"])
    op.create_index("ix_operation_queue_status", "operation_queue", ["status"])
    op.create_index("ix_operation_queue_work_center_id", "operation_queue", ["work_center_id"])
    op.create_index("ix_operation_queue_scheduled_start", "operation_queue", ["scheduled_start"])

    op.create_table(
        "capacity_load_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_center_name", sa.String(255), nullable=True),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("slot_hour", sa.Integer(), nullable=True),
        sa.Column("available_hours", sa.Numeric(6, 2), nullable=False, server_default="8.0"),
        sa.Column("allocated_hours", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("changeover_hours", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("utilization_pct", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("is_overloaded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("overload_hours", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("slot_type", capacity_slot_type, nullable=False, server_default="AVAILABLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scenario_id", "work_center_id", "slot_date", "slot_hour", name="uq_load_snap_wc_slot"),
    )
    op.create_index("ix_capacity_load_snapshots_scenario_id", "capacity_load_snapshots", ["scenario_id"])
    op.create_index("ix_capacity_load_snapshots_slot_date", "capacity_load_snapshots", ["slot_date"])
    op.create_index("ix_capacity_load_snapshots_work_center_id", "capacity_load_snapshots", ["work_center_id"])

    op.create_table(
        "changeover_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("work_center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_centers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_family", sa.String(50), nullable=False),
        sa.Column("to_family", sa.String(50), nullable=False),
        sa.Column("changeover_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("work_center_id", "from_family", "to_family", name="uq_changeover_wc_families"),
    )
    op.create_index("ix_changeover_matrix_work_center_id", "changeover_matrix", ["work_center_id"])

    op.create_table(
        "planning_bottlenecks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_center_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_center_name", sa.String(255), nullable=True),
        sa.Column("severity", bottleneck_severity, nullable=False, server_default="MEDIUM"),
        sa.Column("peak_utilization_pct", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("overloaded_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_overload_hrs", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("blocked_op_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_planning_bottlenecks_scenario_id", "planning_bottlenecks", ["scenario_id"])
    op.create_index("ix_planning_bottlenecks_work_center_id", "planning_bottlenecks", ["work_center_id"])

    op.create_table(
        "planning_ai_recs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", planning_agent_type, nullable=False),
        sa.Column("status", planning_rec_status, nullable=False, server_default="PENDING"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("affected_op_ids", sa.JSON(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("actioned_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_planning_ai_recs_scenario_id", "planning_ai_recs", ["scenario_id"])
    op.create_index("ix_planning_ai_recs_status", "planning_ai_recs", ["status"])

    op.create_table(
        "planning_simulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sim_no", sa.String(50), nullable=False),
        sa.Column("sim_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("planning_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", simulation_status, nullable=False, server_default="DRAFT"),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("ops_rescheduled", sa.Integer(), nullable=True),
        sa.Column("ops_delayed", sa.Integer(), nullable=True),
        sa.Column("utilization_delta", sa.Numeric(6, 2), nullable=True),
        sa.Column("changeover_delta_hrs", sa.Numeric(8, 2), nullable=True),
        sa.Column("throughput_delta_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sim_no", name="uq_planning_simulations_sim_no"),
    )
    op.create_index("ix_planning_simulations_scenario_id", "planning_simulations", ["scenario_id"])
    op.create_index("ix_planning_simulations_sim_no", "planning_simulations", ["sim_no"])


def downgrade() -> None:
    op.drop_index("ix_planning_simulations_sim_no", table_name="planning_simulations")
    op.drop_index("ix_planning_simulations_scenario_id", table_name="planning_simulations")
    op.drop_table("planning_simulations")

    op.drop_index("ix_planning_ai_recs_status", table_name="planning_ai_recs")
    op.drop_index("ix_planning_ai_recs_scenario_id", table_name="planning_ai_recs")
    op.drop_table("planning_ai_recs")

    op.drop_index("ix_planning_bottlenecks_work_center_id", table_name="planning_bottlenecks")
    op.drop_index("ix_planning_bottlenecks_scenario_id", table_name="planning_bottlenecks")
    op.drop_table("planning_bottlenecks")

    op.drop_index("ix_changeover_matrix_work_center_id", table_name="changeover_matrix")
    op.drop_table("changeover_matrix")

    op.drop_index("ix_capacity_load_snapshots_work_center_id", table_name="capacity_load_snapshots")
    op.drop_index("ix_capacity_load_snapshots_slot_date", table_name="capacity_load_snapshots")
    op.drop_index("ix_capacity_load_snapshots_scenario_id", table_name="capacity_load_snapshots")
    op.drop_table("capacity_load_snapshots")

    op.drop_index("ix_operation_queue_scheduled_start", table_name="operation_queue")
    op.drop_index("ix_operation_queue_work_center_id", table_name="operation_queue")
    op.drop_index("ix_operation_queue_status", table_name="operation_queue")
    op.drop_index("ix_operation_queue_scenario_id", table_name="operation_queue")
    op.drop_index("ix_operation_queue_op_no", table_name="operation_queue")
    op.drop_table("operation_queue")

    op.drop_index("ix_resource_calendars_work_center_id", table_name="resource_calendars")
    op.drop_index("ix_resource_calendars_calendar_date", table_name="resource_calendars")
    op.drop_table("resource_calendars")

    op.drop_index("ix_planning_scenarios_status", table_name="planning_scenarios")
    op.drop_index("ix_planning_scenarios_scenario_no", table_name="planning_scenarios")
    op.drop_table("planning_scenarios")

    simulation_status.drop(op.get_bind(), checkfirst=True)
    planning_rec_status.drop(op.get_bind(), checkfirst=True)
    planning_agent_type.drop(op.get_bind(), checkfirst=True)
    bottleneck_severity.drop(op.get_bind(), checkfirst=True)
    capacity_slot_type.drop(op.get_bind(), checkfirst=True)
    op_queue_status.drop(op.get_bind(), checkfirst=True)
    scenario_mode.drop(op.get_bind(), checkfirst=True)
    scenario_status.drop(op.get_bind(), checkfirst=True)
