"""track estimated and actual landed-cost line amounts

Revision ID: 20261029_0039
Revises: 20261029_0038
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0039"
down_revision = "20261029_0038"
branch_labels = None
depends_on = None


LINE_TABLE = "lc_lines"
ACTUAL_TABLE = "lc_line_actuals"
ESTIMATE_COLUMN = "estimated_amount_fc"
MARKER = "added by Alembic revision 20261029_0039"


def _table_exists(bind, table: str) -> bool:
    return bind.execute(sa.text("SELECT to_regclass(:table)"), {"table": table}).scalar_one_or_none() is not None


def _column_marker(bind, table: str, column: str):
    return bind.execute(sa.text(
        "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
        "FROM information_schema.columns WHERE table_schema = current_schema() "
        "AND table_name = :table AND column_name = :column"
    ), {"table": table, "column": column}).scalar_one_or_none()


def _actual_table_shape(bind) -> bool:
    columns = {column["name"]: column for column in sa.inspect(bind).get_columns(ACTUAL_TABLE)}
    expected = {"id", "lc_line_id", "amount_fc", "source_reference", "recorded_by_id", "recorded_at"}
    if set(columns) != expected:
        return False
    types = {
        "id": sa.Uuid,
        "lc_line_id": sa.Uuid,
        "amount_fc": sa.Numeric,
        "source_reference": sa.String,
        "recorded_by_id": sa.Uuid,
        "recorded_at": sa.DateTime,
    }
    for name, expected_type in types.items():
        if not isinstance(columns[name]["type"], expected_type):
            return False
    if columns["amount_fc"]["type"].precision != 14 or columns["amount_fc"]["type"].scale != 4:
        return False
    if columns["source_reference"]["type"].length != 200:
        return False
    if columns["lc_line_id"]["nullable"] or columns["amount_fc"]["nullable"] or columns["source_reference"]["nullable"]:
        return False
    if columns["recorded_at"]["nullable"] or not columns["recorded_by_id"]["nullable"]:
        return False
    if not getattr(columns["recorded_at"]["type"], "timezone", False):
        return False
    primary_key = sa.inspect(bind).get_pk_constraint(ACTUAL_TABLE)
    if primary_key.get("constrained_columns") != ["id"]:
        return False

    constraints = sa.inspect(bind).get_unique_constraints(ACTUAL_TABLE)
    unique_line = any(
        item.get("name") == "uq_lc_line_actuals_lc_line_id" and item.get("column_names") == ["lc_line_id"]
        for item in constraints
    )
    foreign_keys = sa.inspect(bind).get_foreign_keys(ACTUAL_TABLE)
    expected_fks = {
        ("lc_line_id", "lc_lines", "id", "CASCADE"),
        ("recorded_by_id", "users", "id", "SET NULL"),
    }
    actual_fks = {
        (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0],
         (fk.get("options") or {}).get("ondelete", "").upper())
        for fk in foreign_keys if len(fk["constrained_columns"]) == 1 and len(fk["referred_columns"]) == 1
    }
    return unique_line and expected_fks <= actual_fks


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, LINE_TABLE) or not _table_exists(bind, "users"):
        raise RuntimeError("Cannot add landed-cost actual tracking because lc_lines or users is missing")

    columns = {column["name"]: column for column in sa.inspect(bind).get_columns(LINE_TABLE)}
    if "amount_fc" not in columns:
        raise RuntimeError("Cannot backfill estimated landed cost because lc_lines.amount_fc is missing")

    if ESTIMATE_COLUMN not in columns:
        op.add_column(LINE_TABLE, sa.Column(ESTIMATE_COLUMN, sa.Numeric(14, 4), nullable=True))
        op.execute(f"COMMENT ON COLUMN {LINE_TABLE}.{ESTIMATE_COLUMN} IS '{MARKER}'")
        op.execute(f"UPDATE {LINE_TABLE} SET {ESTIMATE_COLUMN} = amount_fc WHERE {ESTIMATE_COLUMN} IS NULL")
    else:
        column = columns[ESTIMATE_COLUMN]
        data_type = column["type"]
        if (
            not isinstance(data_type, sa.Numeric)
            or data_type.precision != 14
            or data_type.scale != 4
            or not column["nullable"]
            or column.get("default") is not None
            or _column_marker(bind, LINE_TABLE, ESTIMATE_COLUMN) not in (None, MARKER)
        ):
            raise RuntimeError("Existing lc_lines.estimated_amount_fc is not safely compatible")
        op.execute(f"UPDATE {LINE_TABLE} SET {ESTIMATE_COLUMN} = amount_fc WHERE {ESTIMATE_COLUMN} IS NULL")

    if not _table_exists(bind, ACTUAL_TABLE):
        op.create_table(
            ACTUAL_TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("lc_line_id", sa.Uuid(), nullable=False),
            sa.Column("amount_fc", sa.Numeric(14, 4), nullable=False),
            sa.Column("source_reference", sa.String(200), nullable=False),
            sa.Column("recorded_by_id", sa.Uuid(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["lc_line_id"], ["lc_lines.id"], name="fk_lc_line_actuals_lc_line_id_lc_lines", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], name="fk_lc_line_actuals_recorded_by_id_users", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name="pk_lc_line_actuals"),
            sa.UniqueConstraint("lc_line_id", name="uq_lc_line_actuals_lc_line_id"),
        )
        op.create_index("ix_lc_line_actuals_recorded_at", ACTUAL_TABLE, ["recorded_at"])
        op.execute(f"COMMENT ON TABLE {ACTUAL_TABLE} IS '{MARKER}'")
    elif not _actual_table_shape(bind):
        raise RuntimeError("Existing lc_line_actuals is not safely compatible; refusing to adopt or overwrite it")


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, ACTUAL_TABLE):
        if bind.execute(sa.text(f"SELECT 1 FROM {ACTUAL_TABLE} LIMIT 1")).first():
            raise RuntimeError("Cannot remove landed-cost actual references while actual records exist")
        marker = bind.execute(sa.text(
            "SELECT obj_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, 'pg_class')"
        ), {"table": ACTUAL_TABLE}).scalar_one_or_none()
        if marker == MARKER:
            op.drop_table(ACTUAL_TABLE)

    if _table_exists(bind, LINE_TABLE):
        columns = {column["name"]: column for column in sa.inspect(bind).get_columns(LINE_TABLE)}
        if ESTIMATE_COLUMN in columns and _column_marker(bind, LINE_TABLE, ESTIMATE_COLUMN) == MARKER:
            if bind.execute(sa.text(
                f"SELECT 1 FROM {LINE_TABLE} WHERE {ESTIMATE_COLUMN} IS DISTINCT FROM amount_fc LIMIT 1"
            )).first():
                raise RuntimeError("Cannot remove distinct landed-cost estimates while estimate/actual differences exist")
            op.drop_column(LINE_TABLE, ESTIMATE_COLUMN)
