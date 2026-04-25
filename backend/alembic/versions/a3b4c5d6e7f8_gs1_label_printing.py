"""GS1 Barcode + Label Printing System

Creates all GS1 and label printing tables:
  gs1_company_configs, gs1_label_templates, product_gs1_configs,
  gs1_lot_barcode_records, gs1_sscc_pallets, gs1_sscc_pallet_lots,
  gs1_label_print_jobs, gs1_label_print_job_items, gs1_ai_recommendations

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-04-25
"""
from __future__ import annotations
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── GS1 Company Config ────────────────────────────────────────────────────
    op.create_table(
        "gs1_company_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("gs1_company_prefix", sa.String(12), nullable=False, unique=True),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column("extension_digit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sscc_serial_counter", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── GS1 Label Templates (must precede product_gs1_configs) ───────────────
    op.create_table(
        "gs1_label_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("packaging_level", sa.String(20), nullable=True),
        sa.Column("template_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("width_mm", sa.Numeric(6, 1), nullable=True),
        sa.Column("height_mm", sa.Numeric(6, 1), nullable=True),
        sa.Column("fields", sa.JSON, nullable=True),
        sa.Column("html_template", sa.Text, nullable=True),
        sa.Column("css_styles", sa.Text, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Product GS1 Config ────────────────────────────────────────────────────
    op.create_table(
        "product_gs1_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_config_id", UUID(as_uuid=True), sa.ForeignKey("gs1_company_configs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("gtin", sa.String(14), nullable=True, unique=True),
        sa.Column("barcode_type", sa.String(30), nullable=False, server_default="EAN13"),
        sa.Column("packaging_level", sa.String(20), nullable=False, server_default="UNIT"),
        sa.Column("label_template_id", UUID(as_uuid=True), sa.ForeignKey("gs1_label_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gs1_company_prefix", sa.String(12), nullable=True),
        sa.Column("requires_serialization", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("requires_lot_tracking", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requires_expiry_tracking", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("units_per_inner_pack", sa.Integer, nullable=True),
        sa.Column("inner_packs_per_carton", sa.Integer, nullable=True),
        sa.Column("cartons_per_pallet", sa.Integer, nullable=True),
        sa.Column("carton_gtin", sa.String(14), nullable=True),
        sa.Column("pallet_gtin", sa.String(14), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", name="uq_product_gs1"),
    )
    op.create_index("ix_product_gs1_configs_product_id", "product_gs1_configs", ["product_id"])
    op.create_index("ix_product_gs1_configs_gtin", "product_gs1_configs", ["gtin"])

    # ── Lot Barcode Records ───────────────────────────────────────────────────
    op.create_table(
        "gs1_lot_barcode_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_config_id", UUID(as_uuid=True), sa.ForeignKey("product_gs1_configs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("gtin", sa.String(14), nullable=False),
        sa.Column("lot_number", sa.String(100), nullable=False),
        sa.Column("production_date", sa.Date, nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("barcode_type", sa.String(30), nullable=False),
        sa.Column("gs1_ai_string", sa.Text, nullable=False),
        sa.Column("gs1_raw_string", sa.Text, nullable=True),
        sa.Column("qr_payload", sa.Text, nullable=True),
        sa.Column("barcode_image_b64", sa.Text, nullable=True),
        sa.Column("qr_image_b64", sa.Text, nullable=True),
        sa.Column("is_printed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("printed_at", sa.DateTime, nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("packaging_level", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gs1_lot_barcode_records_product_config_id", "gs1_lot_barcode_records", ["product_config_id"])
    op.create_index("ix_gs1_lot_barcode_records_lot_id", "gs1_lot_barcode_records", ["lot_id"])

    # ── SSCC Pallets ──────────────────────────────────────────────────────────
    op.create_table(
        "gs1_sscc_pallets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_config_id", UUID(as_uuid=True), sa.ForeignKey("gs1_company_configs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sscc_code", sa.String(18), nullable=False, unique=True),
        sa.Column("extension_digit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("company_prefix", sa.String(12), nullable=False),
        sa.Column("serial_reference", sa.String(9), nullable=False),
        sa.Column("check_digit", sa.Integer, nullable=False),
        sa.Column("pallet_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("warehouse_location", sa.String(200), nullable=True),
        sa.Column("shipment_reference", sa.String(200), nullable=True),
        sa.Column("sscc_image_b64", sa.Text, nullable=True),
        sa.Column("label_printed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("label_printed_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gs1_sscc_pallets_sscc_code", "gs1_sscc_pallets", ["sscc_code"])
    op.create_index("ix_gs1_sscc_pallets_pallet_id", "gs1_sscc_pallets", ["pallet_id"])

    # ── SSCC Pallet Lots (link table) ─────────────────────────────────────────
    op.create_table(
        "gs1_sscc_pallet_lots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sscc_id", UUID(as_uuid=True), sa.ForeignKey("gs1_sscc_pallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_barcode_id", UUID(as_uuid=True), sa.ForeignKey("gs1_lot_barcode_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("packaging_level", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gs1_sscc_pallet_lots_sscc_id", "gs1_sscc_pallet_lots", ["sscc_id"])

    # ── Label Print Jobs ──────────────────────────────────────────────────────
    op.create_table(
        "gs1_label_print_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_no", sa.String(50), nullable=False, unique=True),
        sa.Column("trigger", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("gs1_label_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("printed_by", sa.String(200), nullable=True),
        sa.Column("printed_at", sa.DateTime, nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("printer_name", sa.String(200), nullable=True),
        sa.Column("print_data", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gs1_label_print_jobs_job_no", "gs1_label_print_jobs", ["job_no"])

    # ── Label Print Job Items ─────────────────────────────────────────────────
    op.create_table(
        "gs1_label_print_job_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("gs1_label_print_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_barcode_id", UUID(as_uuid=True), sa.ForeignKey("gs1_lot_barcode_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sscc_id", UUID(as_uuid=True), sa.ForeignKey("gs1_sscc_pallets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("copies", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gs1_label_print_job_items_job_id", "gs1_label_print_job_items", ["job_id"])

    # ── GS1 AI Recommendations ────────────────────────────────────────────────
    op.create_table(
        "gs1_ai_recommendations",
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
    op.drop_table("gs1_ai_recommendations")
    op.drop_table("gs1_label_print_job_items")
    op.drop_table("gs1_label_print_jobs")
    op.drop_table("gs1_sscc_pallet_lots")
    op.drop_table("gs1_sscc_pallets")
    op.drop_table("gs1_lot_barcode_records")
    op.drop_table("product_gs1_configs")
    op.drop_table("gs1_label_templates")
    op.drop_table("gs1_company_configs")
