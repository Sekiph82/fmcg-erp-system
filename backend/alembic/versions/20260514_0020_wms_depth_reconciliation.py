"""Add WMS depth reconciliation tables.

Revision ID: 20260514_0020
Revises: 20260514_0010
Create Date: 2026-05-14 22:35:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260514_0020"
down_revision = "20260514_0010"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    if not _has_table(table_name):
        return set()
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    if not _has_table(table_name):
        return set()
    return {idx["name"] for idx in inspect(op.get_bind()).get_indexes(table_name)}


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if name not in _indexes(table_name):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


def _create_enum(name: str, *values: str) -> postgresql.ENUM:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)
    return enum


def _drop_enum(name: str) -> None:
    op.execute(f"DROP TYPE IF EXISTS {name}")


def upgrade() -> None:
    _create_enum("pickingtaskstatus", "PENDING", "IN_PROGRESS", "PICKED", "PACKED", "CANCELLED")
    _create_enum("packingstatus", "OPEN", "CLOSED")
    _create_enum("replenishmentstatus", "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED")
    _create_enum("wms_handling_unit_status", "OPEN", "CLOSED", "ON_HOLD", "SHIPPED", "CONSUMED", "VOID")
    _create_enum("wms_handling_unit_type", "PALLET", "CARTON", "TOTE", "CRATE", "CONTAINER")
    _create_enum("wms_pick_wave_status", "DRAFT", "RELEASED", "IN_PROGRESS", "PICKED", "CANCELLED", "CLOSED")

    if not _has_table("wms_handling_units"):
        op.create_table(
            "wms_handling_units",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("license_plate", sa.String(100), nullable=False),
            sa.Column("warehouse_id", UUID, nullable=False),
            sa.Column("location_id", UUID, nullable=True),
            sa.Column("parent_hu_id", UUID, nullable=True),
            sa.Column(
                "hu_type",
                postgresql.ENUM("PALLET", "CARTON", "TOTE", "CRATE", "CONTAINER", name="wms_handling_unit_type", create_type=False),
                nullable=False,
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "OPEN", "CLOSED", "ON_HOLD", "SHIPPED", "CONSUMED", "VOID",
                    name="wms_handling_unit_status",
                    create_type=False,
                ),
                nullable=False,
                server_default="OPEN",
            ),
            sa.Column("gross_weight_kg", sa.Numeric(12, 3), nullable=True),
            sa.Column("net_weight_kg", sa.Numeric(12, 3), nullable=True),
            sa.Column("volume_m3", sa.Numeric(12, 4), nullable=True),
            sa.Column("created_by_id", UUID, nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["location_id"], ["storage_locations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["parent_hu_id"], ["wms_handling_units.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("license_plate", name="uq_wms_handling_units_license_plate"),
        )
    _create_index_once("ix_wms_handling_units_warehouse_id", "wms_handling_units", ["warehouse_id"])
    _create_index_once("ix_wms_handling_units_location_id", "wms_handling_units", ["location_id"])
    _create_index_once("ix_wms_handling_units_parent_hu_id", "wms_handling_units", ["parent_hu_id"])
    _create_index_once("ix_wms_handling_units_status", "wms_handling_units", ["status"])

    if not _has_table("wms_handling_unit_items"):
        op.create_table(
            "wms_handling_unit_items",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("handling_unit_id", UUID, nullable=False),
            sa.Column("stock_type", postgresql.ENUM("PRODUCT", "MATERIAL", name="stocktype", create_type=False), nullable=False),
            sa.Column("product_id", UUID, nullable=True),
            sa.Column("material_id", UUID, nullable=True),
            sa.Column("lot_id", UUID, nullable=True),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["handling_unit_id"], ["wms_handling_units.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
            sa.CheckConstraint(
                "(stock_type = 'PRODUCT' AND product_id IS NOT NULL AND material_id IS NULL) OR "
                "(stock_type = 'MATERIAL' AND material_id IS NOT NULL AND product_id IS NULL)",
                name="ck_wms_hu_items_stock_type_item",
            ),
        )
    _create_index_once("ix_wms_handling_unit_items_handling_unit_id", "wms_handling_unit_items", ["handling_unit_id"])
    _create_index_once("ix_wms_handling_unit_items_product_id", "wms_handling_unit_items", ["product_id"])
    _create_index_once("ix_wms_handling_unit_items_material_id", "wms_handling_unit_items", ["material_id"])
    _create_index_once("ix_wms_handling_unit_items_lot_id", "wms_handling_unit_items", ["lot_id"])

    if not _has_table("wms_pick_waves"):
        op.create_table(
            "wms_pick_waves",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("wave_no", sa.String(50), nullable=False),
            sa.Column("warehouse_id", UUID, nullable=False),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "DRAFT", "RELEASED", "IN_PROGRESS", "PICKED", "CANCELLED", "CLOSED",
                    name="wms_pick_wave_status",
                    create_type=False,
                ),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("released_by_id", UUID, nullable=True),
            sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["released_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("wave_no", name="uq_wms_pick_waves_wave_no"),
        )
    _create_index_once("ix_wms_pick_waves_warehouse_id", "wms_pick_waves", ["warehouse_id"])
    _create_index_once("ix_wms_pick_waves_status", "wms_pick_waves", ["status"])
    _create_index_once("ix_wms_pick_waves_planned_start_at", "wms_pick_waves", ["planned_start_at"])

    if not _has_table("wms_picking_tasks"):
        op.create_table(
            "wms_picking_tasks",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("task_no", sa.String(50), nullable=False),
            sa.Column("warehouse_id", UUID, nullable=False),
            sa.Column("shipment_id", UUID, nullable=True),
            sa.Column("product_id", UUID, nullable=False),
            sa.Column("lot_id", UUID, nullable=True),
            sa.Column("from_location_id", UUID, nullable=True),
            sa.Column("wave_id", UUID, nullable=True),
            sa.Column("requested_qty", sa.Numeric(14, 3), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False, server_default="PCS"),
            sa.Column("picked_qty", sa.Numeric(14, 3), nullable=True),
            sa.Column("assigned_to_id", UUID, nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM("PENDING", "IN_PROGRESS", "PICKED", "PACKED", "CANCELLED", name="pickingtaskstatus", create_type=False),
                nullable=False,
                server_default="PENDING",
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("fefo_enforced", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["from_location_id"], ["storage_locations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["wave_id"], ["wms_pick_waves.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("task_no", name="uq_wms_picking_tasks_task_no"),
        )
    elif "wave_id" not in _columns("wms_picking_tasks"):
        op.add_column("wms_picking_tasks", sa.Column("wave_id", UUID, nullable=True))
        op.create_foreign_key(
            "fk_wms_picking_tasks_wave_id",
            "wms_picking_tasks",
            "wms_pick_waves",
            ["wave_id"],
            ["id"],
            ondelete="SET NULL",
        )
    _create_index_once("ix_wms_picking_tasks_warehouse_id", "wms_picking_tasks", ["warehouse_id"])
    _create_index_once("ix_wms_picking_tasks_status", "wms_picking_tasks", ["status"])
    _create_index_once("ix_wms_picking_tasks_wave_id", "wms_picking_tasks", ["wave_id"])
    _create_index_once("ix_wms_picking_tasks_assigned_to_id", "wms_picking_tasks", ["assigned_to_id"])

    if not _has_table("wms_packing_records"):
        op.create_table(
            "wms_packing_records",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("packing_no", sa.String(50), nullable=False),
            sa.Column("shipment_id", UUID, nullable=True),
            sa.Column("warehouse_id", UUID, nullable=False),
            sa.Column("box_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("pallet_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_weight_kg", sa.Numeric(10, 2), nullable=True),
            sa.Column("total_volume_m3", sa.Numeric(10, 4), nullable=True),
            sa.Column("carrier", sa.String(100), nullable=True),
            sa.Column("tracking_number", sa.String(100), nullable=True),
            sa.Column("status", postgresql.ENUM("OPEN", "CLOSED", name="packingstatus", create_type=False), nullable=False, server_default="OPEN"),
            sa.Column("packed_by_id", UUID, nullable=True),
            sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["packed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("packing_no", name="uq_wms_packing_records_packing_no"),
        )
    _create_index_once("ix_wms_packing_records_warehouse_id", "wms_packing_records", ["warehouse_id"])
    _create_index_once("ix_wms_packing_records_status", "wms_packing_records", ["status"])

    if not _has_table("wms_replenishment_tasks"):
        op.create_table(
            "wms_replenishment_tasks",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("task_no", sa.String(50), nullable=False),
            sa.Column("warehouse_id", UUID, nullable=False),
            sa.Column("location_id", UUID, nullable=False),
            sa.Column("product_id", UUID, nullable=True),
            sa.Column("material_id", UUID, nullable=True),
            sa.Column("current_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
            sa.Column("min_qty", sa.Numeric(14, 3), nullable=False),
            sa.Column("requested_qty", sa.Numeric(14, 3), nullable=False),
            sa.Column("fulfilled_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
            sa.Column("unit", sa.String(20), nullable=False, server_default="PCS"),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED",
                    name="replenishmentstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="PENDING",
            ),
            sa.Column("assigned_to_id", UUID, nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["location_id"], ["storage_locations.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("task_no", name="uq_wms_replenishment_tasks_task_no"),
        )
    _create_index_once("ix_wms_replenishment_tasks_warehouse_id", "wms_replenishment_tasks", ["warehouse_id"])
    _create_index_once("ix_wms_replenishment_tasks_location_id", "wms_replenishment_tasks", ["location_id"])
    _create_index_once("ix_wms_replenishment_tasks_status", "wms_replenishment_tasks", ["status"])

    stock_movement_cols = _columns("stock_movements")
    if "source_location_id" not in stock_movement_cols:
        op.add_column("stock_movements", sa.Column("source_location_id", UUID, nullable=True))
        op.create_foreign_key(
            "fk_stock_movements_source_location_id",
            "stock_movements",
            "storage_locations",
            ["source_location_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "destination_location_id" not in stock_movement_cols:
        op.add_column("stock_movements", sa.Column("destination_location_id", UUID, nullable=True))
        op.create_foreign_key(
            "fk_stock_movements_destination_location_id",
            "stock_movements",
            "storage_locations",
            ["destination_location_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "source_handling_unit_id" not in stock_movement_cols:
        op.add_column("stock_movements", sa.Column("source_handling_unit_id", UUID, nullable=True))
        op.create_foreign_key(
            "fk_stock_movements_source_handling_unit_id",
            "stock_movements",
            "wms_handling_units",
            ["source_handling_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "destination_handling_unit_id" not in stock_movement_cols:
        op.add_column("stock_movements", sa.Column("destination_handling_unit_id", UUID, nullable=True))
        op.create_foreign_key(
            "fk_stock_movements_destination_handling_unit_id",
            "stock_movements",
            "wms_handling_units",
            ["destination_handling_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )
    _create_index_once("ix_stock_movements_source_location_id", "stock_movements", ["source_location_id"])
    _create_index_once("ix_stock_movements_destination_location_id", "stock_movements", ["destination_location_id"])
    _create_index_once("ix_stock_movements_source_handling_unit_id", "stock_movements", ["source_handling_unit_id"])
    _create_index_once("ix_stock_movements_destination_handling_unit_id", "stock_movements", ["destination_handling_unit_id"])


def downgrade() -> None:
    if _has_table("stock_movements"):
        for index_name in (
            "ix_stock_movements_destination_handling_unit_id",
            "ix_stock_movements_source_handling_unit_id",
            "ix_stock_movements_destination_location_id",
            "ix_stock_movements_source_location_id",
        ):
            _drop_index_if_exists(index_name, "stock_movements")
        for constraint_name in (
            "fk_stock_movements_destination_handling_unit_id",
            "fk_stock_movements_source_handling_unit_id",
            "fk_stock_movements_destination_location_id",
            "fk_stock_movements_source_location_id",
        ):
            op.drop_constraint(constraint_name, "stock_movements", type_="foreignkey")
        for col_name in (
            "destination_handling_unit_id",
            "source_handling_unit_id",
            "destination_location_id",
            "source_location_id",
        ):
            if col_name in _columns("stock_movements"):
                op.drop_column("stock_movements", col_name)

    if _has_table("wms_picking_tasks") and "wave_id" in _columns("wms_picking_tasks"):
        _drop_index_if_exists("ix_wms_picking_tasks_wave_id", "wms_picking_tasks")
        op.drop_constraint("fk_wms_picking_tasks_wave_id", "wms_picking_tasks", type_="foreignkey")
        op.drop_column("wms_picking_tasks", "wave_id")

    for table_name in (
        "wms_replenishment_tasks",
        "wms_packing_records",
        "wms_picking_tasks",
        "wms_pick_waves",
        "wms_handling_unit_items",
        "wms_handling_units",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)

    for enum_name in (
        "wms_pick_wave_status",
        "wms_handling_unit_type",
        "wms_handling_unit_status",
        "replenishmentstatus",
        "packingstatus",
        "pickingtaskstatus",
    ):
        _drop_enum(enum_name)
