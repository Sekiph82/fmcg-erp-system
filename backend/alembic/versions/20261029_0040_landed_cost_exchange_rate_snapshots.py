"""snapshot dated finance exchange rates on landed-cost documents

Revision ID: 20261029_0040
Revises: 20261029_0039
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0040"
down_revision = "20261029_0039"
branch_labels = None
depends_on = None


TABLES = ("lc_headers", "lc_lines")
MARKER = "Added by Alembic revision 20261029_0040"
RATE_ID_FKS = {
    "lc_headers": "fk_lc_headers_exchange_rate_id_exchange_rates",
    "lc_lines": "fk_lc_lines_exchange_rate_id_exchange_rates",
}
COLUMNS = {
    "exchange_rate_id": (sa.Uuid(), f"{MARKER}; exact finance rate row used for this snapshot"),
    "exchange_rate_date": (sa.Date(), f"{MARKER}; effective rate date, null for legacy unknowns"),
    "exchange_rate_source": (sa.String(length=20), f"{MARKER}; source copied with the rate snapshot"),
}


def _columns(bind, table):
    return {item["name"]: item for item in sa.inspect(bind).get_columns(table)}


def _ensure_column(bind, table, name, column_type, comment):
    columns = _columns(bind, table)
    if name not in columns:
        op.add_column(table, sa.Column(name, column_type, nullable=True, comment=comment))
        return
    existing = columns[name]
    if not isinstance(existing["type"], type(column_type)) or not existing["nullable"]:
        raise RuntimeError(f"Refusing to adopt unexpected {table}.{name} definition")
    remarks = bind.execute(sa.text(
        "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
        "FROM information_schema.columns WHERE table_schema = current_schema() "
        "AND table_name = :table AND column_name = :column"
    ), {"table": table, "column": name}).scalar_one_or_none()
    if remarks != comment:
        raise RuntimeError(f"Refusing to adopt {table}.{name} without the expected ownership marker")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    missing_tables = [table for table in TABLES if not inspector.has_table(table)]
    if missing_tables:
        raise RuntimeError(f"Required landed-cost table(s) are missing: {', '.join(missing_tables)}")
    if not inspector.has_table("exchange_rates"):
        raise RuntimeError("Finance exchange_rates table is required before landed-cost FX snapshots")

    for table in TABLES:
        for name, (column_type, comment) in COLUMNS.items():
            _ensure_column(bind, table, name, column_type, comment)
        fks = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table)}
        fk_name = RATE_ID_FKS[table]
        if fk_name not in fks:
            op.create_foreign_key(
                fk_name, table, "exchange_rates", ["exchange_rate_id"], ["id"], ondelete="SET NULL",
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in TABLES:
        if not inspector.has_table(table):
            continue
        columns = _columns(bind, table)
        if "exchange_rate_id" in columns:
            has_links = bind.execute(sa.text(
                f'SELECT EXISTS (SELECT 1 FROM "{table}" WHERE exchange_rate_id IS NOT NULL)'
            )).scalar_one()
            if has_links:
                raise RuntimeError(f"Refusing to discard saved Finance rate links in {table}")
        if "exchange_rate_date" in columns or "exchange_rate_source" in columns:
            names = [name for name in ("exchange_rate_date", "exchange_rate_source") if name in columns]
            predicates = " OR ".join(f'"{name}" IS NOT NULL' for name in names)
            has_snapshots = bind.execute(sa.text(
                f'SELECT EXISTS (SELECT 1 FROM "{table}" WHERE {predicates})'
            )).scalar_one()
            if has_snapshots:
                raise RuntimeError(f"Refusing to discard saved rate provenance in {table}")
        fk_name = RATE_ID_FKS[table]
        fks = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table)}
        if fk_name in fks:
            op.drop_constraint(fk_name, table, type_="foreignkey")
        current = _columns(bind, table)
        for name in reversed(tuple(COLUMNS)):
            if name not in current:
                continue
            remarks = bind.execute(sa.text(
                "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
                "FROM information_schema.columns WHERE table_schema = current_schema() "
                "AND table_name = :table AND column_name = :column"
            ), {"table": table, "column": name}).scalar_one_or_none()
            if remarks != COLUMNS[name][1]:
                raise RuntimeError(f"Refusing to drop unowned {table}.{name}")
            op.drop_column(table, name)
