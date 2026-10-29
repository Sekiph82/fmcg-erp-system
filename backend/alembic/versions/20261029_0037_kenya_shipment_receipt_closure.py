"""record immutable Kenya warehouse receipt closure against posted GRNs

Revision ID: 20261029_0037
Revises: 20261029_0036
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0037"
down_revision = "20261029_0036"
branch_labels = None
depends_on = None


HEADER = "shipment_receipt_closures"
LINES = "shipment_receipt_closure_grns"
HEADER_MARKER = "created by Alembic revision 20261029_0037"
LINES_MARKER = "created by Alembic revision 20261029_0037"
LINES_INDEX = "ix_shipment_receipt_closure_grns_closure_id"
INDEX_MARKER = "added by Alembic revision 20261029_0037"
FUNCTION_MARKER = "created by Alembic revision 20261029_0037"
TRIGGER_MARKER = "created by Alembic revision 20261029_0037"


def _table_exists(bind, name: str) -> bool:
    return bind.execute(sa.text("SELECT to_regclass(:name)"), {"name": name}).scalar_one_or_none() is not None


def _table_marker(bind, name: str):
    return bind.execute(
        sa.text("SELECT obj_description(to_regclass(:name), 'pg_class')"),
        {"name": name},
    ).scalar_one_or_none()


def _has_rows(bind, name: str) -> bool:
    return bool(bind.execute(sa.text(f"SELECT 1 FROM {name} LIMIT 1")).first())


def _index_exists(bind) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = :name"
    ), {"name": LINES_INDEX}).first())


def _index_marker(bind):
    return bind.execute(sa.text(
        "SELECT obj_description(to_regclass(:name), 'pg_class')"
    ), {"name": LINES_INDEX}).scalar_one_or_none()


def _function_marker(bind):
    return bind.execute(sa.text(
        "SELECT obj_description(p.oid, 'pg_proc') FROM pg_proc AS p "
        "JOIN pg_namespace AS n ON n.oid = p.pronamespace "
        "WHERE n.nspname = current_schema() "
        "AND p.proname = 'reject_shipment_receipt_closure_mutation' "
        "AND pg_get_function_identity_arguments(p.oid) = ''"
    )).scalar_one_or_none()


def _trigger_marker(bind, table: str, trigger: str):
    return bind.execute(sa.text(
        "SELECT obj_description(t.oid, 'pg_trigger') "
        "FROM pg_trigger AS t JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = current_schema() AND c.relname = :table "
        "AND t.tgname = :trigger AND NOT t.tgisinternal"
    ), {"table": table, "trigger": trigger}).scalar_one_or_none()


def _user_triggers(bind, table: str):
    return list(bind.execute(sa.text(
        "SELECT t.tgname FROM pg_trigger AS t "
        "JOIN pg_class AS c ON c.oid = t.tgrelid "
        "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
        "WHERE n.nspname = current_schema() AND c.relname = :table AND NOT t.tgisinternal"
    ), {"table": table}).scalars().all())


def _table_shape_matches(bind, table: str) -> bool:
    inspector = sa.inspect(bind)
    expected = {
        HEADER: {
            "columns": {"id", "shipment_id", "closed_at", "closed_by_id", "created_at", "updated_at"},
            "types": {
                "id": sa.Uuid, "shipment_id": sa.Uuid, "closed_at": sa.DateTime,
                "closed_by_id": sa.Uuid, "created_at": sa.DateTime, "updated_at": sa.DateTime,
            },
            "timezone_columns": {"closed_at", "created_at", "updated_at"},
            "unique_column": "shipment_id",
            "foreign_keys": {"shipment_id": "intl_shipments", "closed_by_id": "users"},
        },
        LINES: {
            "columns": {"id", "closure_id", "grn_id", "received_date", "created_at", "updated_at"},
            "types": {
                "id": sa.Uuid, "closure_id": sa.Uuid, "grn_id": sa.Uuid,
                "received_date": sa.Date, "created_at": sa.DateTime, "updated_at": sa.DateTime,
            },
            "timezone_columns": {"created_at", "updated_at"},
            "unique_column": "grn_id",
            "foreign_keys": {"closure_id": HEADER, "grn_id": "goods_receipts"},
        },
    }[table]
    inspected_columns = {column["name"]: column for column in inspector.get_columns(table)}
    columns = set(inspected_columns)
    primary_key = set(inspector.get_pk_constraint(table).get("constrained_columns") or ())
    uniques = {
        tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints(table)
    }
    foreign_keys = {
        tuple(foreign_key.get("constrained_columns") or ()): (
            foreign_key.get("referred_table"),
            tuple(foreign_key.get("referred_columns") or ()),
            (foreign_key.get("options") or {}).get("ondelete", "").upper(),
        )
        for foreign_key in inspector.get_foreign_keys(table)
    }
    expected_foreign_keys = {
        (column,): (target, ("id",), "RESTRICT")
        for column, target in expected["foreign_keys"].items()
    }
    types_match = all(
        isinstance(inspected_columns[name]["type"], expected_type)
        for name, expected_type in expected["types"].items()
    )
    timezone_match = all(
        bool(getattr(inspected_columns[name]["type"], "timezone", False))
        == (name in expected["timezone_columns"])
        for name in expected["types"]
        if isinstance(inspected_columns[name]["type"], sa.DateTime)
    )
    defaults_match = all(
        bool(inspected_columns[name].get("default")) == (name in {"created_at", "updated_at"})
        and (
            name not in {"created_at", "updated_at"}
            or "now()" in str(inspected_columns[name].get("default")).lower()
        )
        for name in expected["columns"]
    )
    nullable_match = all(not inspected_columns[name]["nullable"] for name in expected["columns"])
    return (
        columns == expected["columns"]
        and types_match
        and timezone_match
        and defaults_match
        and nullable_match
        and primary_key == {"id"}
        and (expected["unique_column"],) in uniques
        and all(foreign_keys.get(columns) == target for columns, target in expected_foreign_keys.items())
    )


def upgrade() -> None:
    bind = op.get_bind()
    for table, marker in ((HEADER, HEADER_MARKER), (LINES, LINES_MARKER)):
        if _table_exists(bind, table):
            current_marker = _table_marker(bind, table)
            if current_marker not in (None, marker) or not _table_shape_matches(bind, table):
                raise RuntimeError(f"Refusing to modify an unowned or incompatible table {table}.")
            if current_marker is None and _has_rows(bind, table):
                raise RuntimeError(f"Refusing to adopt non-empty unmarked table {table}.")
            if current_marker is None and _user_triggers(bind, table):
                raise RuntimeError(f"Refusing to adopt unmarked table {table} with existing triggers.")
    if not _table_exists(bind, HEADER):
        op.create_table(
            HEADER,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("shipment_id", sa.Uuid(), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_by_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("shipment_id", name="uq_shipment_receipt_closures_shipment"),
            sa.ForeignKeyConstraint(["shipment_id"], ["intl_shipments.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"], ondelete="RESTRICT"),
        )
        op.execute(f"COMMENT ON TABLE {HEADER} IS '{HEADER_MARKER}'")

    if not _table_exists(bind, LINES):
        op.create_table(
            LINES,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("closure_id", sa.Uuid(), nullable=False),
            sa.Column("grn_id", sa.Uuid(), nullable=False),
            sa.Column("received_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("grn_id", name="uq_shipment_receipt_closure_grns_grn"),
            sa.ForeignKeyConstraint(["closure_id"], [f"{HEADER}.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["grn_id"], ["goods_receipts.id"], ondelete="RESTRICT"),
        )
        op.execute(f"COMMENT ON TABLE {LINES} IS '{LINES_MARKER}'")
    for table, marker in ((HEADER, HEADER_MARKER), (LINES, LINES_MARKER)):
        if _table_marker(bind, table) is None:
            op.execute(f"COMMENT ON TABLE {table} IS '{marker}'")

    if _index_exists(bind):
        index = next((item for item in sa.inspect(bind).get_indexes(LINES) if item["name"] == LINES_INDEX), None)
        if index is None or index.get("column_names") != ["closure_id"] or index.get("unique"):
            raise RuntimeError(f"Refusing to reuse incompatible index {LINES_INDEX}.")
        if _index_marker(bind) not in (None, INDEX_MARKER):
            raise RuntimeError(f"Refusing to reuse unowned index {LINES_INDEX}.")
        if _index_marker(bind) is None and _has_rows(bind, HEADER):
            raise RuntimeError(f"Refusing to adopt unmarked index {LINES_INDEX} after receipt evidence exists.")
    if not _index_exists(bind):
        op.create_index(LINES_INDEX, LINES, ["closure_id"])
        op.execute(f"COMMENT ON INDEX {LINES_INDEX} IS '{INDEX_MARKER}'")

    function_name = "reject_shipment_receipt_closure_mutation()"
    function_exists = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_proc AS p "
        "JOIN pg_namespace AS n ON n.oid = p.pronamespace "
        "WHERE n.nspname = current_schema() "
        "AND p.proname = 'reject_shipment_receipt_closure_mutation' "
        "AND pg_get_function_identity_arguments(p.oid) = '')"
    )).scalar_one()
    if function_exists and _function_marker(bind) != FUNCTION_MARKER:
        raise RuntimeError("Refusing to replace an unowned receipt-closure trigger function.")
    if not function_exists:
        op.execute("""
            CREATE FUNCTION reject_shipment_receipt_closure_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'shipment receipt closures are append-only'
                    USING ERRCODE = '23514';
            END;
            $$ LANGUAGE plpgsql
        """)
        op.execute(
            "COMMENT ON FUNCTION reject_shipment_receipt_closure_mutation() "
            f"IS '{FUNCTION_MARKER}'"
        )
    for table in (HEADER, LINES):
        for suffix, event, level in (
            ("no_update_delete", "BEFORE UPDATE OR DELETE", "FOR EACH ROW"),
            ("no_truncate", "BEFORE TRUNCATE", "FOR EACH STATEMENT"),
        ):
            trigger = f"{table}_{suffix}"
            marker = _trigger_marker(bind, table, trigger)
            if marker not in (None, TRIGGER_MARKER):
                raise RuntimeError(f"Refusing to replace unowned trigger {trigger} on {table}.")
            if marker == TRIGGER_MARKER:
                op.execute(f"DROP TRIGGER {trigger} ON {table}")
            op.execute(f"""
                CREATE TRIGGER {trigger}
                {event} ON {table}
                {level} EXECUTE FUNCTION reject_shipment_receipt_closure_mutation()
            """)
            op.execute(f"COMMENT ON TRIGGER {trigger} ON {table} IS '{TRIGGER_MARKER}'")


def downgrade() -> None:
    bind = op.get_bind()
    header_owned = _table_exists(bind, HEADER) and _table_marker(bind, HEADER) == HEADER_MARKER
    lines_owned = _table_exists(bind, LINES) and _table_marker(bind, LINES) == LINES_MARKER
    if (header_owned and _has_rows(bind, HEADER)) or (lines_owned and _has_rows(bind, LINES)):
        raise RuntimeError("Cannot downgrade Kenya receipt closure while closure evidence exists.")

    for table, owned in ((LINES, lines_owned), (HEADER, header_owned)):
        if owned:
            op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_no_update_delete ON {table}")
            op.drop_table(table)

    if _index_exists(bind) and not lines_owned:
        marker = bind.execute(sa.text(
            "SELECT obj_description(to_regclass(:name), 'pg_class')"
        ), {"name": LINES_INDEX}).scalar_one_or_none()
        if marker == INDEX_MARKER:
            op.drop_index(LINES_INDEX, table_name=LINES)

    if (header_owned or lines_owned) and _function_marker(bind) == FUNCTION_MARKER:
        op.execute("DROP FUNCTION IF EXISTS reject_shipment_receipt_closure_mutation()")
