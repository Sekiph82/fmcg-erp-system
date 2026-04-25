"""Allergen + Nutrition Management System

Creates all allergen and nutrition management tables:
  allergen_masters, material_allergen_profiles, material_allergen_lines,
  nutrition_profiles, nutrition_profile_lines,
  product_allergen_summaries, product_nutrition_summaries,
  allergen_change_logs, product_serving_configs, an_ai_recommendations

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-04-25
"""
from __future__ import annotations
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Allergen Master ───────────────────────────────────────────────────────
    op.create_table(
        "allergen_masters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("allergen_code", sa.String(50), nullable=False, unique=True),
        sa.Column("allergen_name", sa.String(200), nullable=False),
        sa.Column("regulatory_name", sa.String(300), nullable=True),
        sa.Column("category", sa.String(20), nullable=False, server_default="MAJOR"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_allergen_masters_allergen_code", "allergen_masters", ["allergen_code"])

    # ── Material Allergen Profiles ────────────────────────────────────────────
    op.create_table(
        "material_allergen_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allergen_present_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("allergen_may_contain_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cross_contact_risk_level", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("supplier_allergen_statement_ref", sa.String(500), nullable=True),
        sa.Column("allergen_review_date", sa.Date, nullable=True),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("material_id", name="uq_mat_allergen_profile"),
    )
    op.create_index("ix_material_allergen_profiles_material_id", "material_allergen_profiles", ["material_id"])

    # ── Material Allergen Lines ───────────────────────────────────────────────
    op.create_table(
        "material_allergen_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("material_allergen_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allergen_id", UUID(as_uuid=True), sa.ForeignKey("allergen_masters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("presence_type", sa.String(30), nullable=False, server_default="CONTAINS"),
        sa.Column("concentration_note", sa.String(500), nullable=True),
        sa.Column("declaration_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("critical_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_material_allergen_lines_profile_id", "material_allergen_lines", ["profile_id"])
    op.create_index("ix_material_allergen_lines_allergen_id", "material_allergen_lines", ["allergen_id"])

    # ── Nutrition Profiles ────────────────────────────────────────────────────
    op.create_table(
        "nutrition_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("basis_type", sa.String(20), nullable=False, server_default="PER_100G"),
        sa.Column("density_factor", sa.Numeric(8, 4), nullable=True),
        sa.Column("moisture_factor", sa.Numeric(8, 4), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_nutrition_profiles_material_id", "nutrition_profiles", ["material_id"])
    op.create_index("ix_nutrition_profiles_product_id", "nutrition_profiles", ["product_id"])

    # ── Nutrition Profile Lines ───────────────────────────────────────────────
    op.create_table(
        "nutrition_profile_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("nutrition_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nutrient_code", sa.String(50), nullable=False),
        sa.Column("nutrient_name", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
        sa.Column("value", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="MANUAL"),
        sa.Column("approved_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("review_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("profile_id", "nutrient_code", name="uq_nutrition_line"),
    )
    op.create_index("ix_nutrition_profile_lines_profile_id", "nutrition_profile_lines", ["profile_id"])

    # ── Product Allergen Summaries ────────────────────────────────────────────
    op.create_table(
        "product_allergen_summaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("bom_version", sa.String(20), nullable=True),
        sa.Column("contains_allergens", sa.JSON, nullable=True),
        sa.Column("may_contain_allergens", sa.JSON, nullable=True),
        sa.Column("declaration_required", sa.JSON, nullable=True),
        sa.Column("cross_contact_risk", sa.String(20), nullable=True, server_default="NONE"),
        sa.Column("label_statement", sa.Text, nullable=True),
        sa.Column("may_contain_statement", sa.Text, nullable=True),
        sa.Column("last_calculated_at", sa.DateTime, nullable=True),
        sa.Column("calculation_source", sa.String(50), nullable=True),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", name="uq_prod_allergen_summary"),
    )
    op.create_index("ix_product_allergen_summaries_product_id", "product_allergen_summaries", ["product_id"])

    # ── Product Nutrition Summaries ───────────────────────────────────────────
    op.create_table(
        "product_nutrition_summaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("bom_version", sa.String(20), nullable=True),
        sa.Column("serving_size_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("serving_size_uom", sa.String(20), nullable=True, server_default="g"),
        sa.Column("servings_per_pack", sa.Numeric(8, 2), nullable=True),
        sa.Column("label_basis_type", sa.String(20), nullable=False, server_default="PER_100G"),
        sa.Column("nutrition_per_100g", sa.JSON, nullable=True),
        sa.Column("nutrition_per_100ml", sa.JSON, nullable=True),
        sa.Column("nutrition_per_serving", sa.JSON, nullable=True),
        sa.Column("nutrition_per_unit", sa.JSON, nullable=True),
        sa.Column("last_calculated_at", sa.DateTime, nullable=True),
        sa.Column("calculation_source", sa.String(50), nullable=True),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", name="uq_prod_nutrition_summary"),
    )
    op.create_index("ix_product_nutrition_summaries_product_id", "product_nutrition_summaries", ["product_id"])

    # ── Allergen Change Logs ──────────────────────────────────────────────────
    op.create_table(
        "allergen_change_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("bom_version_from", sa.String(20), nullable=True),
        sa.Column("bom_version_to", sa.String(20), nullable=True),
        sa.Column("allergen_id", UUID(as_uuid=True), sa.ForeignKey("allergen_masters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("old_value", sa.String(200), nullable=True),
        sa.Column("new_value", sa.String(200), nullable=True),
        sa.Column("detected_at", sa.DateTime, nullable=True),
        sa.Column("requires_label_review", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requires_qc_review", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requires_haccp_review", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("requires_cleaning_validation", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("label_review_done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("qc_review_done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_allergen_change_logs_product_id", "allergen_change_logs", ["product_id"])

    # ── Product Serving Configs ───────────────────────────────────────────────
    op.create_table(
        "product_serving_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("serving_size_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("serving_size_uom", sa.String(20), nullable=True, server_default="g"),
        sa.Column("servings_per_pack", sa.Numeric(8, 2), nullable=True),
        sa.Column("label_basis_type", sa.String(20), nullable=False, server_default="PER_100G"),
        sa.Column("market_profile", sa.String(100), nullable=True),
        sa.Column("rounding_profile", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", name="uq_prod_serving_config"),
    )

    # ── AN AI Recommendations ─────────────────────────────────────────────────
    op.create_table(
        "an_ai_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("affected_entity_type", sa.String(100), nullable=True),
        sa.Column("affected_entity_id", sa.String(100), nullable=True),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("agent_metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("an_ai_recommendations")
    op.drop_table("product_serving_configs")
    op.drop_table("allergen_change_logs")
    op.drop_table("product_nutrition_summaries")
    op.drop_table("product_allergen_summaries")
    op.drop_table("nutrition_profile_lines")
    op.drop_table("nutrition_profiles")
    op.drop_table("material_allergen_lines")
    op.drop_table("material_allergen_profiles")
    op.drop_table("allergen_masters")
