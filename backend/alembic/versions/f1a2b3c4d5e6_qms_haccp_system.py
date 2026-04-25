"""QMS + HACCP / Food Safety System

Creates all Quality Management System and HACCP tables:
  qc_parameters, qc_templates, qc_template_parameters,
  qc_inspections, qc_test_results,
  haccp_hazard_analyses, critical_control_points, ccp_monitoring_logs,
  corrective_actions, corrective_action_steps,
  qc_deviations, lot_quality_statuses,
  allergen_validation_records, qms_ai_recommendations

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-04-25
"""
from __future__ import annotations
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── QC Parameters (master) ────────────────────────────────────────────────
    op.create_table(
        "qc_parameters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parameter_type", sa.String(20), nullable=False, server_default="NUMERIC"),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("min_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("max_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("expected_value", sa.String(200), nullable=True),
        sa.Column("is_critical", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("applicable_types", sa.String(100), nullable=False, server_default="ALL"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── QC Templates ──────────────────────────────────────────────────────────
    op.create_table(
        "qc_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("qc_type", sa.String(30), nullable=False),
        sa.Column("qc_sub_type", sa.String(50), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_category", sa.String(100), nullable=True),
        sa.Column("sampling_method", sa.String(30), nullable=False, server_default="FIXED"),
        sa.Column("sample_size", sa.Numeric(10, 3), nullable=True),
        sa.Column("sample_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("sampling_frequency", sa.Integer, nullable=True),
        sa.Column("sampling_interval_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_ccp_template", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("blocks_progression", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("release_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qc_templates_product_id", "qc_templates", ["product_id"])
    op.create_index("ix_qc_templates_material_id", "qc_templates", ["material_id"])

    # ── QC Template Parameters ────────────────────────────────────────────────
    op.create_table(
        "qc_template_parameters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("qc_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("qc_parameters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        sa.Column("parameter_type", sa.String(20), nullable=False, server_default="NUMERIC"),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("target_value", sa.String(200), nullable=True),
        sa.Column("min_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("max_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("is_critical", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_ccp_parameter", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qc_template_parameters_template_id", "qc_template_parameters", ["template_id"])

    # ── QC Inspections ────────────────────────────────────────────────────────
    op.create_table(
        "qc_inspections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("inspection_no", sa.String(50), nullable=False, unique=True),
        sa.Column("qc_type", sa.String(30), nullable=False),
        sa.Column("qc_sub_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("qc_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grn_id", UUID(as_uuid=True), sa.ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grn_line_id", UUID(as_uuid=True), sa.ForeignKey("grn_lines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_order_id", UUID(as_uuid=True), nullable=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("batch_no", sa.String(100), nullable=True),
        sa.Column("sample_size", sa.Numeric(10, 3), nullable=True),
        sa.Column("sample_unit", sa.String(20), nullable=True),
        sa.Column("inspection_date", sa.Date, nullable=False),
        sa.Column("inspector_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("blocks_progression", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("release_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("hold_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("decision", sa.String(30), nullable=True),
        sa.Column("decided_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column("rework_candidate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("quarantine_applied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qc_inspections_inspection_no", "qc_inspections", ["inspection_no"])

    # ── QC Test Results ───────────────────────────────────────────────────────
    op.create_table(
        "qc_test_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("inspection_id", UUID(as_uuid=True), sa.ForeignKey("qc_inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("qc_parameters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        sa.Column("parameter_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("numeric_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("text_value", sa.Text, nullable=True),
        sa.Column("boolean_value", sa.Boolean, nullable=True),
        sa.Column("min_spec", sa.Numeric(14, 4), nullable=True),
        sa.Column("max_spec", sa.Numeric(14, 4), nullable=True),
        sa.Column("expected_text", sa.String(200), nullable=True),
        sa.Column("is_passed", sa.Boolean, nullable=True),
        sa.Column("is_critical", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tested_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qc_test_results_inspection_id", "qc_test_results", ["inspection_id"])

    # ── Corrective Actions (must precede CCP monitoring log and deviations) ──
    op.create_table(
        "corrective_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ca_no", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("trigger_type", sa.String(50), nullable=True),
        sa.Column("trigger_id", UUID(as_uuid=True), nullable=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("root_cause_analysis", sa.Text, nullable=True),
        sa.Column("effectiveness_check", sa.Text, nullable=True),
        sa.Column("preventive_measures", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_corrective_actions_ca_no", "corrective_actions", ["ca_no"])

    # ── Corrective Action Steps ───────────────────────────────────────────────
    op.create_table(
        "corrective_action_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("corrective_action_id", UUID(as_uuid=True), sa.ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_no", sa.Integer, nullable=False),
        sa.Column("step_description", sa.Text, nullable=False),
        sa.Column("assigned_to_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_corrective_action_steps_ca_id", "corrective_action_steps", ["corrective_action_id"])

    # ── Critical Control Points (must precede hazard_analyses and ccp_monitoring_logs) ──
    op.create_table(
        "critical_control_points",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ccp_no", sa.String(50), nullable=False, unique=True),
        sa.Column("ccp_name", sa.String(200), nullable=False),
        sa.Column("process_step", sa.String(200), nullable=False),
        sa.Column("hazard_type", sa.String(30), nullable=False),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        sa.Column("parameter_unit", sa.String(30), nullable=True),
        sa.Column("critical_limit_min", sa.Numeric(14, 4), nullable=True),
        sa.Column("critical_limit_max", sa.Numeric(14, 4), nullable=True),
        sa.Column("critical_limit_description", sa.Text, nullable=True),
        sa.Column("monitoring_method", sa.String(200), nullable=False),
        sa.Column("monitoring_frequency", sa.String(100), nullable=False),
        sa.Column("monitoring_frequency_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("corrective_action_description", sa.Text, nullable=False),
        sa.Column("responsible_role", sa.String(100), nullable=True),
        sa.Column("responsible_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verification_method", sa.Text, nullable=True),
        sa.Column("verification_frequency", sa.String(100), nullable=True),
        sa.Column("record_keeping", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("allergen_related", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cleaning_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_critical_control_points_ccp_no", "critical_control_points", ["ccp_no"])

    # ── CCP Monitoring Logs ───────────────────────────────────────────────────
    op.create_table(
        "ccp_monitoring_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ccp_id", UUID(as_uuid=True), sa.ForeignKey("critical_control_points.id", ondelete="CASCADE"), nullable=False),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_order_id", UUID(as_uuid=True), nullable=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("monitoring_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("recorded_text", sa.String(200), nullable=True),
        sa.Column("is_within_limits", sa.Boolean, nullable=False),
        sa.Column("is_violation", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deviation_amount", sa.Numeric(14, 4), nullable=True),
        sa.Column("recorded_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corrective_action_taken", sa.Text, nullable=True),
        sa.Column("corrective_action_id", UUID(as_uuid=True), sa.ForeignKey("corrective_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("process_blocked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ccp_monitoring_logs_ccp_id", "ccp_monitoring_logs", ["ccp_id"])
    op.create_index("ix_ccp_monitoring_logs_monitoring_datetime", "ccp_monitoring_logs", ["monitoring_datetime"])

    # ── HACCP Hazard Analyses ─────────────────────────────────────────────────
    op.create_table(
        "haccp_hazard_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("hazard_no", sa.String(50), nullable=False, unique=True),
        sa.Column("process_step", sa.String(200), nullable=False),
        sa.Column("hazard_type", sa.String(30), nullable=False),
        sa.Column("hazard_description", sa.Text, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("likelihood_score", sa.Integer, nullable=True),
        sa.Column("severity_score", sa.Integer, nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("control_measure", sa.Text, nullable=False),
        sa.Column("is_ccp", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ccp_id", UUID(as_uuid=True), sa.ForeignKey("critical_control_points.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_haccp_hazard_analyses_hazard_no", "haccp_hazard_analyses", ["hazard_no"])

    # ── QC Deviations ─────────────────────────────────────────────────────────
    op.create_table(
        "qc_deviations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("deviation_no", sa.String(50), nullable=False, unique=True),
        sa.Column("inspection_id", UUID(as_uuid=True), sa.ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deviation_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("immediate_action", sa.Text, nullable=True),
        sa.Column("affected_quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("affected_uom", sa.String(20), nullable=True),
        sa.Column("reported_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corrective_action_id", UUID(as_uuid=True), sa.ForeignKey("corrective_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qc_deviations_deviation_no", "qc_deviations", ["deviation_no"])

    # ── Lot Quality Statuses ──────────────────────────────────────────────────
    op.create_table(
        "lot_quality_statuses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("qc_status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("release_status", sa.String(30), nullable=False, server_default="UNRELEASED"),
        sa.Column("hold_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("quarantine_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("quarantine_location", sa.String(200), nullable=True),
        sa.Column("hold_reason", sa.Text, nullable=True),
        sa.Column("last_inspection_id", UUID(as_uuid=True), sa.ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("released_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_notes", sa.Text, nullable=True),
        sa.Column("fefo_eligible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("shipment_eligible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("allergen_cleared", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lot_quality_statuses_lot_id", "lot_quality_statuses", ["lot_id"])

    # ── Allergen Validation Records ───────────────────────────────────────────
    op.create_table(
        "allergen_validation_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("validation_no", sa.String(50), nullable=False, unique=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("allergens_present", sa.String(500), nullable=True),
        sa.Column("cleaning_method", sa.Text, nullable=True),
        sa.Column("cleaning_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_passed", sa.Boolean, nullable=True),
        sa.Column("validated_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("swab_test_result", sa.String(100), nullable=True),
        sa.Column("evidence_notes", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_allergen_validation_records_validation_no", "allergen_validation_records", ["validation_no"])

    # ── QMS AI Recommendations ────────────────────────────────────────────────
    op.create_table(
        "qms_ai_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("inspection_id", UUID(as_uuid=True), sa.ForeignKey("qc_inspections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ccp_id", UUID(as_uuid=True), sa.ForeignKey("critical_control_points.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deviation_id", UUID(as_uuid=True), sa.ForeignKey("qc_deviations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("priority_score", sa.Integer, nullable=True),
        sa.Column("reviewed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qms_ai_recommendations_agent_type", "qms_ai_recommendations", ["agent_type"])


def downgrade() -> None:
    op.drop_table("qms_ai_recommendations")
    op.drop_table("allergen_validation_records")
    op.drop_table("lot_quality_statuses")
    op.drop_table("qc_deviations")
    op.drop_table("haccp_hazard_analyses")
    op.drop_table("ccp_monitoring_logs")
    op.drop_table("critical_control_points")
    op.drop_table("corrective_action_steps")
    op.drop_table("corrective_actions")
    op.drop_table("qc_test_results")
    op.drop_table("qc_inspections")
    op.drop_table("qc_template_parameters")
    op.drop_table("qc_templates")
    op.drop_table("qc_parameters")
