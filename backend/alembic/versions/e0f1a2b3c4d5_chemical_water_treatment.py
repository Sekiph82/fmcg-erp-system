"""chemical_water_treatment

Creates water_treatment_chemicals master table and extends
treatment_chemical_records with comprehensive dosing, stock-movement,
lot-traceability, KPI, and anomaly-detection columns.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str         = "e0f1a2b3c4d5"
down_revision: Union[str, None] = "d9e0f1a2b3c4"
branch_labels = None
depends_on    = None

_TS = lambda: sa.DateTime(timezone=True)
_UUID = lambda: postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # ── 1. New enums ──────────────────────────────────────────────────────────

    chemical_category = postgresql.ENUM(
        "BOILER_TREATMENT", "OXYGEN_SCAVENGER", "ANTISCALANT",
        "CORROSION_INHIBITOR", "BIOCIDE", "COAGULANT", "FLOCCULANT",
        "PH_ADJUSTER", "NEUTRALIZER", "DEFOAMER", "CHLORINE",
        "DECHLORINATION", "BIO_NUTRIENT", "OTHER",
        name="chemicalcategory",
        create_type=True,
    )
    chemical_category.create(op.get_bind(), checkfirst=True)

    dosing_mode = postgresql.ENUM(
        "MANUAL", "AUTO",
        name="dosingmode",
        create_type=True,
    )
    dosing_mode.create(op.get_bind(), checkfirst=True)

    # ── 2. water_treatment_chemicals (master catalog) ─────────────────────────

    op.create_table(
        "water_treatment_chemicals",
        sa.Column("id",                _UUID(), nullable=False),
        sa.Column("chemical_code",     sa.String(50),  nullable=False),
        sa.Column("chemical_name",     sa.String(255), nullable=False),
        sa.Column("chemical_category", sa.String(30),  nullable=False),
        sa.Column("description",       sa.Text,        nullable=True),
        sa.Column("supplier_id",       _UUID(),        nullable=True),
        sa.Column("stock_uom",         sa.String(30),  nullable=False),
        sa.Column("dosing_uom",        sa.String(30),  nullable=False),
        sa.Column("unit_cost",         sa.Numeric(14, 6), nullable=True),
        sa.Column("target_dose_min",   sa.Numeric(12, 4), nullable=True),
        sa.Column("target_dose_max",   sa.Numeric(12, 4), nullable=True),
        sa.Column("low_stock_threshold", sa.Numeric(14, 4), nullable=True),
        sa.Column("material_id",       _UUID(),        nullable=True),
        sa.Column("is_active",         sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("notes",             sa.Text,        nullable=True),
        sa.Column("created_by_id",     _UUID(),        nullable=True),
        sa.Column("created_at", _TS(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _TS(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["supplier_id"],    ["suppliers.id"],  ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_id"],    ["materials.id"],  ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"],  ["users.id"],      ondelete="SET NULL"),
    )
    op.create_index("ix_wtc_chemical_code",     "water_treatment_chemicals", ["chemical_code"],     unique=True)
    op.create_index("ix_wtc_chemical_category", "water_treatment_chemicals", ["chemical_category"])
    op.create_index("ix_wtc_supplier_id",       "water_treatment_chemicals", ["supplier_id"])
    op.create_index("ix_wtc_is_active",         "water_treatment_chemicals", ["is_active"])

    # ── 3. Extend treatment_chemical_records ──────────────────────────────────

    op.add_column("treatment_chemical_records",
        sa.Column("date",              sa.Date,        nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("chemical_id",       _UUID(),        nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("chemical_code",     sa.String(50),  nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("chemical_category", sa.String(30),  nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("treatment_area",    sa.String(255), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("dosing_point",      sa.String(255), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("supplier_id",       _UUID(),        nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("batch_lot_no",      sa.String(100), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("unit_cost",         sa.Numeric(14, 6), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("stock_uom",         sa.String(30),  nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("dosing_uom",        sa.String(30),  nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("opening_stock",     sa.Numeric(14, 4), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("received_qty",      sa.Numeric(14, 4), nullable=True, server_default="0"))
    op.add_column("treatment_chemical_records",
        sa.Column("consumed_qty",      sa.Numeric(14, 4), nullable=True, server_default="0"))
    op.add_column("treatment_chemical_records",
        sa.Column("closing_stock",     sa.Numeric(14, 4), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("manual_or_auto_dose", sa.String(10), nullable=True, server_default="MANUAL"))
    op.add_column("treatment_chemical_records",
        sa.Column("related_meter_id",  _UUID(),        nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("water_treated_m3",  sa.Numeric(14, 3), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("steam_produced_ton", sa.Numeric(14, 3), nullable=True))
    op.add_column("treatment_chemical_records",
        sa.Column("overdose_flag",     sa.Boolean,     nullable=False, server_default="false"))
    op.add_column("treatment_chemical_records",
        sa.Column("underdose_flag",    sa.Boolean,     nullable=False, server_default="false"))
    op.add_column("treatment_chemical_records",
        sa.Column("inventory_synced",  sa.Boolean,     nullable=False, server_default="false"))

    # Foreign keys
    op.create_foreign_key(
        "fk_tcr_chemical_id",
        "treatment_chemical_records", "water_treatment_chemicals",
        ["chemical_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tcr_supplier_id",
        "treatment_chemical_records", "suppliers",
        ["supplier_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tcr_related_meter_id",
        "treatment_chemical_records", "utility_devices",
        ["related_meter_id"], ["id"], ondelete="SET NULL",
    )

    # Indexes on new columns
    op.create_index("ix_treatment_chemical_id",  "treatment_chemical_records", ["chemical_id"])
    op.create_index("ix_treatment_supplier_id",  "treatment_chemical_records", ["supplier_id"])
    op.create_index("ix_treatment_date",         "treatment_chemical_records", ["date"])
    op.create_index("ix_treatment_area",         "treatment_chemical_records", ["treatment_area"])
    op.create_index("ix_treatment_batch_lot_no", "treatment_chemical_records", ["batch_lot_no"])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index("ix_treatment_batch_lot_no",   "treatment_chemical_records")
    op.drop_index("ix_treatment_area",           "treatment_chemical_records")
    op.drop_index("ix_treatment_date",           "treatment_chemical_records")
    op.drop_index("ix_treatment_supplier_id",    "treatment_chemical_records")
    op.drop_index("ix_treatment_chemical_id",    "treatment_chemical_records")

    # Drop foreign keys
    op.drop_constraint("fk_tcr_related_meter_id",  "treatment_chemical_records", type_="foreignkey")
    op.drop_constraint("fk_tcr_supplier_id",        "treatment_chemical_records", type_="foreignkey")
    op.drop_constraint("fk_tcr_chemical_id",        "treatment_chemical_records", type_="foreignkey")

    # Drop added columns
    for col in [
        "inventory_synced", "underdose_flag", "overdose_flag",
        "steam_produced_ton", "water_treated_m3", "related_meter_id",
        "manual_or_auto_dose", "closing_stock", "consumed_qty", "received_qty",
        "opening_stock", "dosing_uom", "stock_uom", "unit_cost",
        "batch_lot_no", "supplier_id", "dosing_point", "treatment_area",
        "chemical_category", "chemical_code", "chemical_id", "date",
    ]:
        op.drop_column("treatment_chemical_records", col)

    # Drop master table
    op.drop_index("ix_wtc_is_active",         "water_treatment_chemicals")
    op.drop_index("ix_wtc_supplier_id",       "water_treatment_chemicals")
    op.drop_index("ix_wtc_chemical_category", "water_treatment_chemicals")
    op.drop_index("ix_wtc_chemical_code",     "water_treatment_chemicals")
    op.drop_table("water_treatment_chemicals")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS dosingmode")
    op.execute("DROP TYPE IF EXISTS chemicalcategory")
