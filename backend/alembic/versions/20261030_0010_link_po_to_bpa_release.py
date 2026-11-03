"""Link BPA release purchase orders to their source agreement.

Revision ID: 20261030_0010
Revises: 20261030_0009
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0010"
down_revision = "20261030_0009"
branch_labels = None
depends_on = None

TABLE = "purchase_orders"
COLUMN = "bpa_id"
FK = "fk_purchase_orders_bpa_id_blanket_purchase_agreements"
INDEX = "ix_purchase_orders_bpa_id"
OWNERSHIP = "po_bpa_release_migration_ownership"


def _inspector():
    return sa.inspect(op.get_bind())


def _column():
    return next((item for item in _inspector().get_columns(TABLE) if item["name"] == COLUMN), None)


def _validate_column() -> None:
    item = _column()
    if item is None or not isinstance(item["type"], postgresql.UUID) or not item["nullable"]:
        raise RuntimeError("Existing purchase_orders.bpa_id is incompatible; refusing to adopt it.")


def _matching_fk():
    return next((
        item for item in _inspector().get_foreign_keys(TABLE)
        if item["constrained_columns"] == [COLUMN]
        and item["referred_table"] == "blanket_purchase_agreements"
        and item["referred_columns"] == ["id"]
        and (item.get("options") or {}).get("ondelete", "").upper() == "RESTRICT"
    ), None)


def _has_index() -> bool:
    item = next((index for index in _inspector().get_indexes(TABLE) if index["name"] == INDEX), None)
    if item is None:
        return False
    options = item.get("dialect_options") or {}
    compatible = (
        item.get("column_names") == [COLUMN]
        and not item.get("unique", False)
        and options.get("postgresql_where") is None
        and options.get("postgresql_using") in (None, "btree")
    )
    if not compatible:
        raise RuntimeError(f"Existing index {INDEX} has an incompatible definition.")
    return True


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table(TABLE) or not inspector.has_table("blanket_purchase_agreements"):
        raise RuntimeError("BPA release link requires the existing purchase order and agreement tables.")
    if inspector.has_table(OWNERSHIP):
        raise RuntimeError(f"Unexpected pre-existing migration ownership table {OWNERSHIP}.")

    column_created = _column() is None
    if column_created:
        op.add_column(TABLE, sa.Column(COLUMN, postgresql.UUID(as_uuid=True), nullable=True))
    else:
        _validate_column()

    fk_created = _matching_fk() is None
    if fk_created:
        if any(COLUMN in item["constrained_columns"] for item in _inspector().get_foreign_keys(TABLE)):
            raise RuntimeError("Existing BPA purchase-order foreign key has an incompatible definition.")
        op.create_foreign_key(FK, TABLE, "blanket_purchase_agreements", [COLUMN], ["id"], ondelete="RESTRICT")

    index_created = not _has_index()
    if index_created:
        if INDEX in {item["name"] for item in _inspector().get_indexes(TABLE)}:
            raise RuntimeError(f"Existing index {INDEX} has an incompatible definition.")
        op.create_index(INDEX, TABLE, [COLUMN], unique=False)

    op.create_table(
        OWNERSHIP,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("column_created", sa.Boolean(), nullable=False),
        sa.Column("fk_created", sa.Boolean(), nullable=False),
        sa.Column("index_created", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id = 1", name=f"ck_{OWNERSHIP}_singleton"),
    )
    op.bulk_insert(
        sa.table(OWNERSHIP,
            sa.column("id", sa.Integer()),
            sa.column("column_created", sa.Boolean()),
            sa.column("fk_created", sa.Boolean()),
            sa.column("index_created", sa.Boolean()),
        ),
        [{"id": 1, "column_created": column_created, "fk_created": fk_created, "index_created": index_created}],
    )


def downgrade() -> None:
    if not _inspector().has_table(OWNERSHIP):
        raise RuntimeError("Cannot safely downgrade without the BPA release ownership record.")
    ownership_rows = op.get_bind().execute(sa.text(
        f"SELECT id, column_created, fk_created, index_created FROM {OWNERSHIP} ORDER BY id"
    )).mappings().all()
    if len(ownership_rows) != 1 or ownership_rows[0]["id"] != 1:
        raise RuntimeError("BPA release migration ownership record is invalid.")
    ownership = ownership_rows[0]

    if ownership["column_created"] or ownership["fk_created"] or ownership["index_created"]:
        op.get_bind().execute(sa.text(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE"))

    if ownership["column_created"]:
        if not _column():
            raise RuntimeError("Migration-owned purchase_orders.bpa_id is missing; refusing downgrade.")
        if op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE {COLUMN} IS NOT NULL")).scalar_one():
            raise RuntimeError("Refusing to remove purchase_orders.bpa_id while BPA release orders still reference it.")
    if ownership["index_created"]:
        if not _has_index():
            raise RuntimeError("Migration-owned BPA release index is missing; refusing downgrade.")
        op.drop_index(INDEX, table_name=TABLE)
    if ownership["fk_created"]:
        foreign_key = _matching_fk()
        if not foreign_key:
            raise RuntimeError("Migration-owned BPA release foreign key is missing; refusing downgrade.")
        op.drop_constraint(foreign_key["name"], TABLE, type_="foreignkey")
    if ownership["column_created"]:
        _validate_column()
        op.drop_column(TABLE, COLUMN)
    op.drop_table(OWNERSHIP)
