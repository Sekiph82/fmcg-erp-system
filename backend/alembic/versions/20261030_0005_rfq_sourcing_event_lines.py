"""Add multi-line sourcing-event requirements to the existing RFQ aggregate.

Revision ID: 20261030_0005
Revises: 20261030_0004
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0005"
down_revision = "20261030_0004"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> dict[str, dict]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    rfq_columns = _columns("rfq_requests")
    if not rfq_columns or "quantity" not in rfq_columns:
        raise RuntimeError("Expected the migration-managed rfq_requests baseline with a quantity column.")
    if not rfq_columns["quantity"]["nullable"]:
        op.alter_column(
            "rfq_requests",
            "quantity",
            existing_type=sa.Numeric(14, 3),
            nullable=True,
        )

    line_columns = _columns("rfq_request_lines")
    if not line_columns:
        op.create_table(
            "rfq_request_lines",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
            sa.Column("unit", sa.String(length=20), nullable=False),
            sa.Column("required_by", sa.Date(), nullable=True),
            sa.Column("notes", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("line_no > 0", name="ck_rfq_request_line_number_positive"),
            sa.CheckConstraint(
                "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')",
                name="ck_rfq_request_line_quantity_positive",
            ),
            sa.ForeignKeyConstraint(
                ["material_id"], ["materials.id"], name="fk_rfq_request_lines_material_id_materials", ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["product_id"], ["products.id"], name="fk_rfq_request_lines_product_id_products", ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["rfq_id"], ["rfq_requests.id"], name="fk_rfq_request_lines_rfq_id_rfq_requests", ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("rfq_id", "line_no", name="uq_rfq_request_line"),
        )
    else:
        required_columns = {
            "id", "rfq_id", "line_no", "material_id", "product_id", "description",
            "quantity", "unit", "required_by", "notes", "created_at", "updated_at",
        }
        if not required_columns.issubset(line_columns):
            raise RuntimeError("Existing rfq_request_lines table has an incompatible shape; refusing adoption.")
        if any(line_columns[name]["nullable"] for name in ("id", "rfq_id", "line_no", "quantity", "unit")):
            raise RuntimeError("Existing rfq_request_lines table has incompatible required-column nullability.")
        quantity_type = line_columns["quantity"]["type"]
        if not isinstance(quantity_type, sa.Numeric) or quantity_type.precision != 14 or quantity_type.scale != 3:
            raise RuntimeError("Existing rfq_request_lines.quantity must be NUMERIC(14, 3); refusing adoption.")
        inspector = sa.inspect(op.get_bind())
        constraints = inspector.get_check_constraints("rfq_request_lines")
        check_names = {
            "ck_rfq_request_line_number_positive",
            "ck_rfq_request_line_quantity_positive",
        }
        # Do not trust a matching constraint name: earlier/partial disposable or
        # interrupted setups may have installed weaker expressions under it.
        # Replacing these checks is data-preserving; PostgreSQL validates the
        # existing rows when each new constraint is added and aborts atomically
        # if any row violates the required sourcing-line invariants.
        for name in check_names.intersection(item.get("name") for item in constraints):
            op.drop_constraint(name, "rfq_request_lines", type_="check")
        op.create_check_constraint(
            "ck_rfq_request_line_number_positive",
            "rfq_request_lines",
            "line_no > 0",
        )
        op.create_check_constraint(
            "ck_rfq_request_line_quantity_positive",
            "rfq_request_lines",
            "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')",
        )
        unique_shapes = {
            tuple(item.get("column_names") or ())
            for item in inspector.get_unique_constraints("rfq_request_lines")
        }
        if ("rfq_id", "line_no") not in unique_shapes:
            raise RuntimeError("Existing rfq_request_lines table is missing unique event line numbering.")
        foreign_keys = inspector.get_foreign_keys("rfq_request_lines")
        required_foreign_keys = (
            (("rfq_id",), "rfq_requests", "CASCADE", "fk_rfq_request_lines_rfq_id_rfq_requests", "id"),
            (("material_id",), "materials", "SET NULL", "fk_rfq_request_lines_material_id_materials", "id"),
            (("product_id",), "products", "SET NULL", "fk_rfq_request_lines_product_id_products", "id"),
        )
        for columns, target_table, ondelete, constraint_name, target_column in required_foreign_keys:
            matches = [
                item for item in foreign_keys
                if tuple(item.get("constrained_columns") or ()) == columns
                and item.get("referred_table") == target_table
                and tuple(item.get("referred_columns") or ()) == (target_column,)
            ]
            if any((item.get("options") or {}).get("ondelete", "").upper() == ondelete for item in matches):
                continue
            if any(tuple(item.get("constrained_columns") or ()) == columns and item.get("referred_table") != target_table for item in foreign_keys):
                raise RuntimeError(f"Existing rfq_request_lines.{columns[0]} has an unexpected relationship; refusing adoption.")
            for item in matches:
                if not item.get("name"):
                    raise RuntimeError(f"Cannot safely replace unnamed foreign key on rfq_request_lines.{columns[0]}.")
                op.drop_constraint(item["name"], "rfq_request_lines", type_="foreignkey")
            op.create_foreign_key(
                constraint_name,
                "rfq_request_lines",
                target_table,
                list(columns),
                [target_column],
                ondelete=ondelete,
            )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("rfq_request_lines")}
    if "ix_rfq_request_lines_rfq_id" not in indexes:
        op.create_index("ix_rfq_request_lines_rfq_id", "rfq_request_lines", ["rfq_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("rfq_request_lines"):
        if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rfq_request_lines)")).scalar():
            raise RuntimeError("Cannot downgrade: sourcing-event line data would be destroyed.")
        op.drop_index("ix_rfq_request_lines_rfq_id", table_name="rfq_request_lines")
        op.drop_table("rfq_request_lines")

    rfq_columns = _columns("rfq_requests")
    if "quantity" in rfq_columns and rfq_columns["quantity"]["nullable"]:
        if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rfq_requests WHERE quantity IS NULL)")).scalar():
            raise RuntimeError("Cannot downgrade: multi-line sourcing events without a legacy quantity remain.")
        op.alter_column(
            "rfq_requests",
            "quantity",
            existing_type=sa.Numeric(14, 3),
            nullable=False,
        )
