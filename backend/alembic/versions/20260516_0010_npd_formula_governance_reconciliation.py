"""npd formula governance reconciliation

Revision ID: 20260516_0010
Revises: 20260515_0040, 20260515_0060
Create Date: 2026-05-16 07:05:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260516_0010"
down_revision = ("20260515_0040", "20260515_0060")
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSON
JSONB = postgresql.JSONB


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return table_name in _inspector().get_table_names()


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


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


def _npd_timestamps(include_updated_at: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    ]
    if include_updated_at:
        columns.append(sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True))
    return columns


def _create_enums() -> None:
    _create_enum(
        "npdcategory",
        "NEW_PRODUCT",
        "LINE_EXTENSION",
        "REFORMULATION",
        "PACK_SIZE_CHANGE",
        "COST_REDUCTION",
    )
    _create_enum("npdstage", "IDEA", "CONCEPT", "DEVELOPMENT", "PILOT", "LAUNCH", "LAUNCHED", "CANCELLED")
    _create_enum("npdpilotbatchoutcome", "PASS", "FAIL", "CONDITIONAL", "IN_PROGRESS")
    _create_enum("recipestatus", "DRAFT", "APPROVED", "OBSOLETE")
    _create_enum("bomtype", "FORMULA", "INTERMEDIATE", "PACKAGING", "MULTILEVEL", "PHANTOM", "REWORK", "COPRODUCT")
    _create_enum("bomlifecycle", "DRAFT", "UNDER_REVIEW", "APPROVED", "RELEASED", "SUPERSEDED", "ARCHIVED")
    _create_enum("componenttype", "RAW", "INTERMEDIATE", "PACKAGING", "SERVICE", "CO_PRODUCT", "BY_PRODUCT", "UTILITY", "REWORK")
    _create_enum("itemlinktype", "PRODUCT", "MATERIAL")
    _create_enum("basistype", "PER_BATCH", "PER_UNIT", "PER_100KG", "PER_1000L", "PERCENTAGE", "FIXED")
    _create_enum("substitutionpolicy", "NO_SUB", "PLANNER_APPROVAL", "QA_APPROVAL", "BOTH_REQUIRED", "SHORTAGE_ONLY", "EMERGENCY_ONLY")
    _create_enum("losscategory", "PROCESS_LOSS", "EVAPORATION", "TRANSFER", "STARTUP", "SHUTDOWN", "FILLING", "PACKAGING_REJECT", "QC_REJECTION", "LINE_PURGE")
    _create_enum("bomagenttype", "FORMULA_ANALYZER", "PACKAGING_OPTIMIZER", "COMPLIANCE_CHECKER")
    _create_enum("bomrecstatus", "PENDING", "ACCEPTED", "REJECTED")


def _create_npd_tables() -> None:
    if context.is_offline_mode() or not _has_table("npd_projects"):
        op.create_table(
            "npd_projects",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("project_code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("category", _enum("npdcategory", "NEW_PRODUCT", "LINE_EXTENSION", "REFORMULATION", "PACK_SIZE_CHANGE", "COST_REDUCTION"), nullable=False),
            sa.Column("stage", _enum("npdstage", "IDEA", "CONCEPT", "DEVELOPMENT", "PILOT", "LAUNCH", "LAUNCHED", "CANCELLED"), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("target_launch_date", sa.Date(), nullable=True),
            sa.Column("estimated_cogs", sa.Numeric(14, 4), nullable=True),
            sa.Column("estimated_selling_price", sa.Numeric(14, 4), nullable=True),
            sa.Column("bom_recipe_id", sa.String(100), nullable=True),
            sa.Column("regulatory_checklist", JSONB, nullable=True),
            sa.Column("launch_readiness_checklist", JSONB, nullable=True),
            sa.Column("created_by", sa.String(200), nullable=True),
            sa.Column("brand", sa.String(200), nullable=True),
            sa.Column("target_market", sa.String(200), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_npd_timestamps(include_updated_at=True),
            sa.UniqueConstraint("project_code", name="uq_npd_projects_project_code"),
        )
    _create_index_once("ix_npd_projects_project_code", "npd_projects", ["project_code"], unique=True)

    if context.is_offline_mode() or not _has_table("npd_stage_gates"):
        op.create_table(
            "npd_stage_gates",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("project_id", UUID, nullable=False),
            sa.Column("stage", _enum("npdstage", "IDEA", "CONCEPT", "DEVELOPMENT", "PILOT", "LAUNCH", "LAUNCHED", "CANCELLED"), nullable=False),
            sa.Column("department", sa.String(100), nullable=False),
            sa.Column("approved_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("approved_by", sa.String(200), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_npd_timestamps(),
            sa.ForeignKeyConstraint(["project_id"], ["npd_projects.id"], ondelete="CASCADE"),
        )
    _create_index_once("ix_npd_stage_gates_project_id", "npd_stage_gates", ["project_id"])

    if context.is_offline_mode() or not _has_table("npd_pilot_batches"):
        op.create_table(
            "npd_pilot_batches",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("project_id", UUID, nullable=False),
            sa.Column("batch_ref", sa.String(100), nullable=False),
            sa.Column("batch_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("qty_produced", sa.Numeric(12, 3), nullable=True),
            sa.Column("uom", sa.String(20), nullable=False, server_default="KG"),
            sa.Column("actual_cogs", sa.Numeric(14, 4), nullable=True),
            sa.Column("outcome", _enum("npdpilotbatchoutcome", "PASS", "FAIL", "CONDITIONAL", "IN_PROGRESS"), nullable=False, server_default="IN_PROGRESS"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_npd_timestamps(),
            sa.ForeignKeyConstraint(["project_id"], ["npd_projects.id"], ondelete="CASCADE"),
        )
    _create_index_once("ix_npd_pilot_batches_project_id", "npd_pilot_batches", ["project_id"])


def _create_recipe_tables() -> None:
    if context.is_offline_mode() or not _has_table("recipes"):
        op.create_table(
            "recipes",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("product_id", UUID, nullable=False),
            sa.Column("version", sa.String(20), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", _enum("recipestatus", "DRAFT", "APPROVED", "OBSOLETE"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("created_by", UUID, nullable=True),
            sa.Column("approved_by", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("product_id", "version", name="uq_recipe_product_version"),
        )
    _create_index_once("ix_recipes_product_id", "recipes", ["product_id"])

    if context.is_offline_mode() or not _has_table("recipe_items"):
        op.create_table(
            "recipe_items",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("recipe_id", UUID, nullable=False),
            sa.Column("material_id", UUID, nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("loss_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("alternative_group", sa.String(50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("recipe_id", "line_no", name="uq_recipe_item_line"),
        )
    _create_index_once("ix_recipe_items_recipe_id", "recipe_items", ["recipe_id"])
    _create_index_once("ix_recipe_items_material_id", "recipe_items", ["material_id"])

    if context.is_offline_mode() or not _has_table("process_parameters"):
        op.create_table(
            "process_parameters",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("recipe_id", UUID, nullable=False),
            sa.Column("step_no", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(255), nullable=False),
            sa.Column("target_temperature", sa.Numeric(7, 2), nullable=True),
            sa.Column("target_ph", sa.Numeric(5, 2), nullable=True),
            sa.Column("target_viscosity", sa.Numeric(10, 2), nullable=True),
            sa.Column("mixing_time_minutes", sa.Integer(), nullable=True),
            sa.Column("rpm", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("recipe_id", "step_no", name="uq_process_param_step"),
        )
    _create_index_once("ix_process_parameters_recipe_id", "process_parameters", ["recipe_id"])


def _create_bom_tables() -> None:
    if context.is_offline_mode() or not _has_table("bom_substitute_groups"):
        op.create_table(
            "bom_substitute_groups",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("group_code", sa.String(50), nullable=False),
            sa.Column("group_name", sa.String(255), nullable=False),
            sa.Column("policy", _enum("substitutionpolicy", "NO_SUB", "PLANNER_APPROVAL", "QA_APPROVAL", "BOTH_REQUIRED", "SHORTAGE_ONLY", "EMERGENCY_ONLY"), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_timestamps(),
            sa.UniqueConstraint("group_code", name="uq_bom_substitute_groups_group_code"),
        )
    _create_index_once("ix_bom_substitute_groups_group_code", "bom_substitute_groups", ["group_code"], unique=True)

    if context.is_offline_mode() or not _has_table("advanced_boms"):
        op.create_table(
            "advanced_boms",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("bom_code", sa.String(80), nullable=False),
            sa.Column("bom_name", sa.String(255), nullable=False),
            sa.Column("bom_type", _enum("bomtype", "FORMULA", "INTERMEDIATE", "PACKAGING", "MULTILEVEL", "PHANTOM", "REWORK", "COPRODUCT"), nullable=False),
            sa.Column("product_id", UUID, nullable=True),
            sa.Column("product_name", sa.String(255), nullable=True),
            sa.Column("base_qty", sa.Numeric(14, 4), nullable=False, server_default="1000"),
            sa.Column("base_uom", sa.String(20), nullable=False, server_default="KG"),
            sa.Column("version_no", sa.String(20), nullable=False, server_default="1.0"),
            sa.Column("revision_no", sa.String(20), nullable=False, server_default="0"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("lifecycle", _enum("bomlifecycle", "DRAFT", "UNDER_REVIEW", "APPROVED", "RELEASED", "SUPERSEDED", "ARCHIVED"), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("created_by_id", UUID, nullable=True),
            sa.Column("reviewed_by_id", UUID, nullable=True),
            sa.Column("approved_by_id", UUID, nullable=True),
            sa.Column("released_by_id", UUID, nullable=True),
            sa.Column("linked_routing_id", UUID, nullable=True),
            sa.Column("linked_quality_spec_id", UUID, nullable=True),
            sa.Column("linked_label_profile_id", UUID, nullable=True),
            sa.Column("linked_compliance_profile_id", UUID, nullable=True),
            sa.Column("standard_batch_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("standard_cost_per_uom", sa.Numeric(16, 4), nullable=True),
            sa.Column("total_raw_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("total_packaging_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("by_product_credit", sa.Numeric(16, 4), nullable=True),
            sa.Column("costing_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("allergen_flags", JSON, nullable=True),
            sa.Column("nutrition_per_100g", JSON, nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["released_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("bom_code", name="uq_advanced_bom_code"),
        )
    _create_index_once("ix_advanced_boms_bom_code", "advanced_boms", ["bom_code"], unique=True)
    _create_index_once("ix_advanced_boms_bom_type", "advanced_boms", ["bom_type"])
    _create_index_once("ix_advanced_boms_product_id", "advanced_boms", ["product_id"])
    _create_index_once("ix_advanced_boms_lifecycle", "advanced_boms", ["lifecycle"])

    if context.is_offline_mode() or not _has_table("bom_substitutes"):
        op.create_table(
            "bom_substitutes",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("group_id", UUID, nullable=False),
            sa.Column("item_type", _enum("itemlinktype", "PRODUCT", "MATERIAL"), nullable=False),
            sa.Column("item_id", UUID, nullable=True),
            sa.Column("item_name", sa.String(255), nullable=True),
            sa.Column("item_code", sa.String(100), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("qty_ratio", sa.Numeric(8, 4), nullable=False, server_default="1.0"),
            sa.Column("cost_impact_pct", sa.Numeric(6, 2), nullable=True),
            sa.Column("quality_impact", sa.String(50), nullable=True),
            sa.Column("allergen_impact", sa.String(255), nullable=True),
            sa.Column("compliance_impact", sa.String(255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_timestamps(),
            sa.ForeignKeyConstraint(["group_id"], ["bom_substitute_groups.id"], ondelete="CASCADE"),
        )

    if context.is_offline_mode() or not _has_table("advanced_bom_lines"):
        op.create_table(
            "advanced_bom_lines",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("bom_id", UUID, nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("component_type", _enum("componenttype", "RAW", "INTERMEDIATE", "PACKAGING", "SERVICE", "CO_PRODUCT", "BY_PRODUCT", "UTILITY", "REWORK"), nullable=False),
            sa.Column("item_type", _enum("itemlinktype", "PRODUCT", "MATERIAL"), nullable=False),
            sa.Column("item_id", UUID, nullable=True),
            sa.Column("item_name", sa.String(255), nullable=True),
            sa.Column("item_code", sa.String(100), nullable=True),
            sa.Column("child_bom_id", UUID, nullable=True),
            sa.Column("required_qty", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("required_uom", sa.String(20), nullable=False, server_default="KG"),
            sa.Column("basis_type", _enum("basistype", "PER_BATCH", "PER_UNIT", "PER_100KG", "PER_1000L", "PERCENTAGE", "FIXED"), nullable=False),
            sa.Column("concentration_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("wastage_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
            sa.Column("process_loss_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
            sa.Column("yield_contribution_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("fixed_consumption", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("qc_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("allergen_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("nutrition_relevant", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("critical_component", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("substitute_group_id", UUID, nullable=True),
            sa.Column("substitution_policy", _enum("substitutionpolicy", "NO_SUB", "PLANNER_APPROVAL", "QA_APPROVAL", "BOTH_REQUIRED", "SHORTAGE_ONLY", "EMERGENCY_ONLY"), nullable=False),
            sa.Column("consumption_stage", sa.String(100), nullable=True),
            sa.Column("issue_stage", sa.String(100), nullable=True),
            sa.Column("allergen_types", JSON, nullable=True),
            sa.Column("traceability_level", sa.String(50), nullable=True),
            sa.Column("nutrition_data", JSON, nullable=True),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=True),
            sa.Column("extended_cost", sa.Numeric(16, 4), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["bom_id"], ["advanced_boms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["child_bom_id"], ["advanced_boms.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["substitute_group_id"], ["bom_substitute_groups.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("bom_id", "line_no", name="uq_adv_bom_line_no"),
        )
    _create_index_once("ix_advanced_bom_lines_bom_id", "advanced_bom_lines", ["bom_id"])

    if context.is_offline_mode() or not _has_table("bom_conversion_profiles"):
        op.create_table(
            "bom_conversion_profiles",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("profile_code", sa.String(80), nullable=False),
            sa.Column("profile_name", sa.String(255), nullable=False),
            sa.Column("source_product_id", UUID, nullable=True),
            sa.Column("source_product_name", sa.String(255), nullable=True),
            sa.Column("target_product_id", UUID, nullable=True),
            sa.Column("target_product_name", sa.String(255), nullable=True),
            sa.Column("theoretical_conversion_ratio", sa.Numeric(10, 6), nullable=False, server_default="1.0"),
            sa.Column("standard_fill_volume", sa.Numeric(14, 4), nullable=True),
            sa.Column("fill_volume_uom", sa.String(20), nullable=True),
            sa.Column("fill_tolerance_pct", sa.Numeric(5, 3), nullable=False, server_default="1.0"),
            sa.Column("density_g_per_ml", sa.Numeric(8, 4), nullable=True),
            sa.Column("startup_loss_pct", sa.Numeric(6, 3), nullable=False, server_default="0.5"),
            sa.Column("shutdown_loss_pct", sa.Numeric(6, 3), nullable=False, server_default="0.3"),
            sa.Column("packaging_reject_pct", sa.Numeric(6, 3), nullable=False, server_default="0.5"),
            sa.Column("residual_bulk_pct", sa.Numeric(6, 3), nullable=False, server_default="0.2"),
            sa.Column("line_purge_loss_pct", sa.Numeric(6, 3), nullable=False, server_default="0.1"),
            sa.Column("standard_expected_units", sa.Numeric(14, 0), nullable=True),
            sa.Column("realistic_expected_units", sa.Numeric(14, 0), nullable=True),
            sa.Column("linked_packaging_bom_id", UUID, nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["source_product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["target_product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["linked_packaging_bom_id"], ["advanced_boms.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("profile_code", name="uq_bom_conversion_profiles_profile_code"),
        )
    _create_index_once("ix_bom_conversion_profiles_profile_code", "bom_conversion_profiles", ["profile_code"], unique=True)

    if context.is_offline_mode() or not _has_table("bom_yield_configs"):
        op.create_table(
            "bom_yield_configs",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("bom_id", UUID, nullable=False),
            sa.Column("loss_category", _enum("losscategory", "PROCESS_LOSS", "EVAPORATION", "TRANSFER", "STARTUP", "SHUTDOWN", "FILLING", "PACKAGING_REJECT", "QC_REJECTION", "LINE_PURGE"), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("basis", sa.String(50), nullable=False, server_default="PCT_OF_INPUT"),
            sa.Column("standard_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
            sa.Column("max_allowable_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("cost_impact_flag", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["bom_id"], ["advanced_boms.id"], ondelete="CASCADE"),
        )

    if context.is_offline_mode() or not _has_table("bom_ai_recs"):
        op.create_table(
            "bom_ai_recs",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("bom_id", UUID, nullable=False),
            sa.Column("agent_type", _enum("bomagenttype", "FORMULA_ANALYZER", "PACKAGING_OPTIMIZER", "COMPLIANCE_CHECKER"), nullable=False),
            sa.Column("status", _enum("bomrecstatus", "PENDING", "ACCEPTED", "REJECTED"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("impact_summary", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Numeric(4, 2), nullable=True),
            sa.Column("payload", JSON, nullable=True),
            sa.Column("actioned_by_id", UUID, nullable=True),
            sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["bom_id"], ["advanced_boms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actioned_by_id"], ["users.id"], ondelete="SET NULL"),
        )


def upgrade() -> None:
    _create_enums()
    _create_npd_tables()
    _create_recipe_tables()
    _create_bom_tables()


def downgrade() -> None:
    for table_name, indexes in {
        "bom_conversion_profiles": ("ix_bom_conversion_profiles_profile_code",),
        "advanced_bom_lines": ("ix_advanced_bom_lines_bom_id",),
        "advanced_boms": ("ix_advanced_boms_lifecycle", "ix_advanced_boms_product_id", "ix_advanced_boms_bom_type", "ix_advanced_boms_bom_code"),
        "bom_substitute_groups": ("ix_bom_substitute_groups_group_code",),
        "process_parameters": ("ix_process_parameters_recipe_id",),
        "recipe_items": ("ix_recipe_items_material_id", "ix_recipe_items_recipe_id"),
        "recipes": ("ix_recipes_product_id",),
        "npd_pilot_batches": ("ix_npd_pilot_batches_project_id",),
        "npd_stage_gates": ("ix_npd_stage_gates_project_id",),
        "npd_projects": ("ix_npd_projects_project_code",),
    }.items():
        if _has_table(table_name):
            for index_name in indexes:
                _drop_index_if_exists(index_name, table_name)

    for table_name in (
        "bom_ai_recs",
        "bom_yield_configs",
        "bom_conversion_profiles",
        "advanced_bom_lines",
        "bom_substitutes",
        "advanced_boms",
        "bom_substitute_groups",
        "process_parameters",
        "recipe_items",
        "recipes",
        "npd_pilot_batches",
        "npd_stage_gates",
        "npd_projects",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)

    for enum_name in (
        "bomrecstatus",
        "bomagenttype",
        "losscategory",
        "substitutionpolicy",
        "basistype",
        "itemlinktype",
        "componenttype",
        "bomlifecycle",
        "bomtype",
        "recipestatus",
        "npdpilotbatchoutcome",
        "npdstage",
        "npdcategory",
    ):
        _drop_enum(enum_name)
