"""Add dated quantity price breaks to blanket purchase agreements.

Revision ID: 20261030_0009
Revises: 20261030_0008
Create Date: 2026-10-30
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0009"
down_revision = "20261030_0008"
branch_labels = None
depends_on = None

TABLE = "blanket_agreement_price_breaks"
OWNERSHIP_TABLE = "bpa_price_break_migration_ownership"
INDEXES = {
    "ix_bpa_price_break_agreement_effective": ("agreement_id", "effective_from", "effective_to"),
    "ix_bpa_price_break_agreement_min": ("agreement_id", "min_quantity"),
}
CHECKS = {
    "ck_bpa_price_break_min_quantity_positive": "min_quantity > 0 AND min_quantity < 'Infinity'::numeric",
    "ck_bpa_price_break_unit_price_positive": "unit_price > 0 AND unit_price < 'Infinity'::numeric",
    "ck_bpa_price_break_validity_order": "effective_to >= effective_from",
}


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _normalize(expression: str) -> str:
    value = expression.lower().replace('"', "").replace("'", "")
    value = re.sub(r"::[a-z_][a-z0-9_]*", "", value)
    return re.sub(r"[\s()]", "", value)


def _validate_table() -> None:
    inspector = _inspector()
    columns = {item["name"]: item for item in inspector.get_columns(TABLE)}
    expected = {
        "id", "agreement_id", "min_quantity", "unit_price", "effective_from",
        "effective_to", "notes", "created_at", "updated_at",
    }
    if set(columns) != expected:
        raise RuntimeError(f"Existing {TABLE} has an incompatible column set.")

    for name in ("id", "agreement_id"):
        if not isinstance(columns[name]["type"], postgresql.UUID) or columns[name]["nullable"]:
            raise RuntimeError(f"Existing {TABLE}.{name} must be a non-null PostgreSQL UUID.")
    for name, precision_scale in (("min_quantity", (14, 3)), ("unit_price", (14, 4))):
        kind = columns[name]["type"]
        if not isinstance(kind, sa.Numeric) or (kind.precision, kind.scale) != precision_scale or columns[name]["nullable"]:
            raise RuntimeError(f"Existing {TABLE}.{name} has incompatible numeric shape.")
    for name in ("effective_from", "effective_to"):
        if not isinstance(columns[name]["type"], sa.Date) or columns[name]["nullable"]:
            raise RuntimeError(f"Existing {TABLE}.{name} must be a required DATE.")
    if not isinstance(columns["notes"]["type"], sa.String) or columns["notes"]["type"].length != 500 or not columns["notes"]["nullable"]:
        raise RuntimeError(f"Existing {TABLE}.notes must be nullable VARCHAR(500).")
    for name in ("created_at", "updated_at"):
        kind = columns[name]["type"]
        if not isinstance(kind, sa.DateTime) or not kind.timezone or columns[name]["nullable"]:
            raise RuntimeError(f"Existing {TABLE}.{name} must be a required timezone-aware timestamp.")

    checks = {item["name"]: _normalize(item["sqltext"] or "") for item in inspector.get_check_constraints(TABLE)}
    check_fragments = {
        "ck_bpa_price_break_min_quantity_positive": ("min_quantity>0", "min_quantity<infinity"),
        "ck_bpa_price_break_unit_price_positive": ("unit_price>0", "unit_price<infinity"),
        "ck_bpa_price_break_validity_order": ("effective_to>=effective_from",),
    }
    for name, fragments in check_fragments.items():
        if not checks.get(name) or any(fragment not in checks[name] for fragment in fragments):
            raise RuntimeError(f"Existing {TABLE} is missing compatible constraint {name}.")
    if tuple(inspector.get_pk_constraint(TABLE).get("constrained_columns") or []) != ("id",):
        raise RuntimeError(f"Existing {TABLE} has an incompatible primary key.")
    foreign_keys = {
        (tuple(item["constrained_columns"] or []), item["referred_table"], tuple(item["referred_columns"] or []), (item.get("options") or {}).get("ondelete", "").upper())
        for item in inspector.get_foreign_keys(TABLE)
    }
    if (("agreement_id",), "blanket_purchase_agreements", ("id",), "CASCADE") not in foreign_keys:
        raise RuntimeError(f"Existing {TABLE} is missing its agreement cascade foreign key.")
    indexes = {item["name"]: tuple(item["column_names"] or []) for item in inspector.get_indexes(TABLE)}
    for name, columns_expected in INDEXES.items():
        if indexes.get(name) != columns_expected:
            raise RuntimeError(f"Existing {TABLE} is missing compatible index {name}.")


def _validate_ownership_table() -> bool:
    inspector = _inspector()
    columns = {item["name"]: item for item in inspector.get_columns(OWNERSHIP_TABLE)}
    if set(columns) != {"id", "created_here"}:
        raise RuntimeError("Existing BPA price-break ownership record has an incompatible column set.")
    if not isinstance(columns["id"]["type"], sa.SmallInteger) or columns["id"]["nullable"]:
        raise RuntimeError("BPA price-break ownership id must be a required SMALLINT.")
    if not isinstance(columns["created_here"]["type"], sa.Boolean) or columns["created_here"]["nullable"]:
        raise RuntimeError("BPA price-break ownership created_here must be a required BOOLEAN.")
    if tuple(inspector.get_pk_constraint(OWNERSHIP_TABLE).get("constrained_columns") or []) != ("id",):
        raise RuntimeError("BPA price-break ownership record has an incompatible primary key.")
    checks = {
        item["name"]: _normalize(item["sqltext"] or "")
        for item in inspector.get_check_constraints(OWNERSHIP_TABLE)
    }
    if checks.get("ck_bpa_price_break_ownership_singleton") != "id=1":
        raise RuntimeError("BPA price-break ownership record is missing its singleton constraint.")
    rows = op.get_bind().execute(sa.text(f"SELECT id, created_here FROM {OWNERSHIP_TABLE}")).all()
    if len(rows) != 1 or rows[0].id != 1 or not isinstance(rows[0].created_here, bool):
        raise RuntimeError("BPA price-break ownership record must contain exactly one valid row.")
    return rows[0].created_here


def upgrade() -> None:
    inspector = _inspector()
    created_here = not inspector.has_table(TABLE)
    if created_here:
        op.create_table(
            TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("agreement_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("min_quantity", sa.Numeric(14, 3), nullable=False),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=False),
            sa.Column("notes", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("min_quantity > 0 AND min_quantity < 'Infinity'::numeric", name="ck_bpa_price_break_min_quantity_positive"),
            sa.CheckConstraint("unit_price > 0 AND unit_price < 'Infinity'::numeric", name="ck_bpa_price_break_unit_price_positive"),
            sa.CheckConstraint("effective_to >= effective_from", name="ck_bpa_price_break_validity_order"),
            sa.ForeignKeyConstraint(["agreement_id"], ["blanket_purchase_agreements.id"], name="fk_bpa_price_break_agreement_id", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name="pk_blanket_agreement_price_breaks"),
        )
    inspector = _inspector()
    present_indexes = {item["name"] for item in inspector.get_indexes(TABLE)}
    if "ix_bpa_price_break_agreement_effective" not in present_indexes:
        op.create_index("ix_bpa_price_break_agreement_effective", TABLE, ["agreement_id", "effective_from", "effective_to"])
    if "ix_bpa_price_break_agreement_min" not in present_indexes:
        op.create_index("ix_bpa_price_break_agreement_min", TABLE, ["agreement_id", "min_quantity"])
    _validate_table()

    if not _has_table(OWNERSHIP_TABLE):
        op.create_table(
            OWNERSHIP_TABLE,
            sa.Column("id", sa.SmallInteger(), primary_key=True),
            sa.Column("created_here", sa.Boolean(), nullable=False),
            sa.CheckConstraint("id = 1", name="ck_bpa_price_break_ownership_singleton"),
        )
        op.execute(
            sa.text(f"INSERT INTO {OWNERSHIP_TABLE} (id, created_here) VALUES (1, :created_here)")
            .bindparams(created_here=created_here)
        )
    else:
        _validate_ownership_table()


def downgrade() -> None:
    if not _has_table(OWNERSHIP_TABLE):
        raise RuntimeError("Refusing BPA price-break downgrade without its migration ownership record.")
    if not _has_table(TABLE):
        raise RuntimeError("Refusing BPA price-break downgrade because the owned table is missing.")
    _validate_table()
    created_here = _validate_ownership_table()
    if created_here:
        op.get_bind().execute(sa.text(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE"))
        count = op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        if count:
            raise RuntimeError("Refusing to drop BPA price-break rows during downgrade.")
        op.drop_table(TABLE)
    op.drop_table(OWNERSHIP_TABLE)
