"""record accepted receipt volume for volume-based landed-cost allocation

Revision ID: 20261029_0038
Revises: 20261029_0037
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
import re


revision = "20261029_0038"
down_revision = "20261029_0037"
branch_labels = None
depends_on = None


TABLE = "grn_lines"
COLUMN = "accepted_volume_m3"
CONSTRAINT = "ck_grn_lines_accepted_volume_positive"
MARKER = "added by Alembic revision 20261029_0038"
ALLOCATION_TABLE = "lc_allocation_lines"
ALLOCATION_VOLUME = "received_volume"


def _table_exists(bind) -> bool:
    return bind.execute(
        sa.text("SELECT to_regclass(:table)"), {"table": TABLE}
    ).scalar_one_or_none() is not None


def _column_marker(bind):
    return bind.execute(sa.text(
        "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
        "FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :table AND column_name = :column"
    ), {"table": TABLE, "column": COLUMN}).scalar_one_or_none()


def _constraint_marker(bind):
    return bind.execute(sa.text(
        "SELECT obj_description(oid, 'pg_constraint') FROM pg_constraint "
        "WHERE conrelid = to_regclass(:table) AND conname = :constraint"
    ), {"table": TABLE, "constraint": CONSTRAINT}).scalar_one_or_none()


def _constraint_exists(bind) -> bool:
    return bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conrelid = to_regclass(:table) AND conname = :constraint"
    ), {"table": TABLE, "constraint": CONSTRAINT}).first() is not None


def _constraint_definition(bind):
    return bind.execute(sa.text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = to_regclass(:table) AND conname = :constraint"
    ), {"table": TABLE, "constraint": CONSTRAINT}).scalar_one_or_none()


def _normalized_volume_check(definition: str) -> str:
    compact = re.sub(r"[\s()]+", "", definition.lower())
    return compact.replace("::numeric", "")


def _allocation_volume_marker(bind):
    return bind.execute(sa.text(
        "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
        "FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :table AND column_name = :column"
    ), {"table": ALLOCATION_TABLE, "column": ALLOCATION_VOLUME}).scalar_one_or_none()


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind):
        raise RuntimeError("Cannot add accepted volume because grn_lines is missing")

    inspected = sa.inspect(bind)
    columns = {column["name"]: column for column in inspected.get_columns(TABLE)}
    if COLUMN not in columns:
        op.add_column(TABLE, sa.Column(COLUMN, sa.Numeric(14, 6), nullable=True))
        op.execute(f"COMMENT ON COLUMN {TABLE}.{COLUMN} IS '{MARKER}'")
    else:
        column = columns[COLUMN]
        column_type = column["type"]
        if (
            not isinstance(column_type, sa.Numeric)
            or column_type.precision != 14
            or column_type.scale != 6
            or not column["nullable"]
            or column.get("default") is not None
            or _column_marker(bind) not in (None, MARKER)
        ):
            raise RuntimeError("Existing grn_lines.accepted_volume_m3 is not owned by this migration")

    if _constraint_exists(bind):
        definition = _constraint_definition(bind) or ""
        if (
            _constraint_marker(bind) not in (None, MARKER)
            or _normalized_volume_check(definition)
            != "checkaccepted_volume_m3isnulloraccepted_volume_m3>0"
        ):
            raise RuntimeError("Existing accepted-volume constraint is not owned by this migration")
    else:
        op.create_check_constraint(
            CONSTRAINT,
            TABLE,
            f"{COLUMN} IS NULL OR {COLUMN} > 0",
        )
        op.execute(f"COMMENT ON CONSTRAINT {CONSTRAINT} ON {TABLE} IS '{MARKER}'")

    if bind.execute(
        sa.text("SELECT to_regclass(:table)"), {"table": ALLOCATION_TABLE}
    ).scalar_one_or_none() is None:
        raise RuntimeError("Cannot preserve allocation volume because lc_allocation_lines is missing")
    allocation_columns = {
        column["name"]: column
        for column in inspected.get_columns(ALLOCATION_TABLE)
    }
    if ALLOCATION_VOLUME not in allocation_columns:
        raise RuntimeError("Cannot preserve allocation volume because lc_allocation_lines.received_volume is missing")
    allocation_volume = allocation_columns[ALLOCATION_VOLUME]
    allocation_type = allocation_volume["type"]
    if not isinstance(allocation_type, sa.Numeric) or allocation_type.precision != 14 or not allocation_volume["nullable"]:
        raise RuntimeError("Existing landed-cost allocation volume has an unexpected shape")
    if allocation_type.scale == 3:
        if _allocation_volume_marker(bind) not in (None, MARKER):
            raise RuntimeError("Existing landed-cost allocation volume is owned by another migration")
        op.alter_column(
            ALLOCATION_TABLE,
            ALLOCATION_VOLUME,
            existing_type=sa.Numeric(14, 3),
            type_=sa.Numeric(14, 6),
            existing_nullable=True,
        )
        op.execute(f"COMMENT ON COLUMN {ALLOCATION_TABLE}.{ALLOCATION_VOLUME} IS '{MARKER}'")
    elif allocation_type.scale != 6 or _allocation_volume_marker(bind) not in (None, MARKER):
        raise RuntimeError("Existing landed-cost allocation volume is not safely compatible")


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind):
        return

    if _constraint_exists(bind):
        if _constraint_marker(bind) == MARKER:
            op.drop_constraint(CONSTRAINT, TABLE, type_="check")

    columns = {column["name"]: column for column in sa.inspect(bind).get_columns(TABLE)}
    if COLUMN in columns and _column_marker(bind) == MARKER:
        if bind.execute(sa.text(f"SELECT 1 FROM {TABLE} WHERE {COLUMN} IS NOT NULL LIMIT 1")).first():
            raise RuntimeError("Cannot remove accepted receipt volume while measurements exist")
        op.drop_column(TABLE, COLUMN)

    allocation_columns = {column["name"]: column for column in sa.inspect(bind).get_columns(ALLOCATION_TABLE)}
    if ALLOCATION_VOLUME in allocation_columns and _allocation_volume_marker(bind) == MARKER:
        if bind.execute(sa.text(
            f"SELECT 1 FROM {ALLOCATION_TABLE} WHERE {ALLOCATION_VOLUME} IS NOT NULL "
            f"AND {ALLOCATION_VOLUME} <> round({ALLOCATION_VOLUME}, 3) LIMIT 1"
        )).first():
            raise RuntimeError("Cannot reduce landed-cost volume precision while sub-millilitre values exist")
        op.alter_column(
            ALLOCATION_TABLE,
            ALLOCATION_VOLUME,
            existing_type=sa.Numeric(14, 6),
            type_=sa.Numeric(14, 3),
            existing_nullable=True,
        )
        op.execute(f"COMMENT ON COLUMN {ALLOCATION_TABLE}.{ALLOCATION_VOLUME} IS NULL")
