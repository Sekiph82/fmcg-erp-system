"""post landed-cost actual variances without rewriting original postings

Revision ID: 20261029_0041
Revises: 20261029_0040
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261029_0041"
down_revision = "20261029_0040"
branch_labels = None
depends_on = None


TABLE = "lc_line_actuals"
POSTINGS = "lc_actual_variance_postings"
MARKER = "Added by Alembic revision 20261029_0041"
COLUMNS = {
    "actual_amount_base": (sa.Numeric(14, 4), f"{MARKER}; actual source amount translated at the saved landed-cost line rate"),
    "variance_amount_base": (sa.Numeric(14, 4), f"{MARKER}; actual base amount less the immutable original posted allocation"),
    "variance_status": (sa.String(length=20), f"{MARKER}; RECORDED, PENDING, POSTED, or NOT_REQUIRED"),
    "posting_error": (sa.Text(), f"{MARKER}; bounded reconciliation detail for a failed variance posting"),
    "posted_at": (sa.DateTime(), f"{MARKER}; successful actual-variance posting timestamp"),
}


def _column_comment(bind, table, column):
    return bind.execute(sa.text(
        "SELECT col_description((quote_ident(current_schema()) || '.' || quote_ident(:table))::regclass, ordinal_position) "
        "FROM information_schema.columns WHERE table_schema = current_schema() "
        "AND table_name = :table AND column_name = :column"
    ), {"table": table, "column": column}).scalar_one_or_none()


def _ensure_column(bind, name, column_type, comment):
    columns = {item["name"]: item for item in sa.inspect(bind).get_columns(TABLE)}
    if name not in columns:
        op.add_column(TABLE, sa.Column(name, column_type, nullable=True, comment=comment))
        return
    existing = columns[name]
    if not existing["nullable"] or not isinstance(existing["type"], type(column_type)):
        raise RuntimeError(f"Refusing to adopt unexpected {TABLE}.{name} definition")
    if _column_comment(bind, TABLE, name) != comment:
        raise RuntimeError(f"Refusing to adopt {TABLE}.{name} without the expected ownership marker")


def _posting_table_shape(bind):
    inspector = sa.inspect(bind)
    columns = {item["name"]: item for item in inspector.get_columns(POSTINGS)}
    expected_names = {
        "id", "actual_id", "allocation_line_id", "variance_amount_base", "posting_batch_id",
        "journal_entry_id", "accounting_status", "posting_error", "posted_at", "created_at", "updated_at",
    }
    if set(columns) != expected_names:
        return False
    types = {
        "id": sa.Uuid,
        "actual_id": sa.Uuid,
        "allocation_line_id": sa.Uuid,
        "variance_amount_base": sa.Numeric,
        "posting_batch_id": sa.Uuid,
        "journal_entry_id": sa.Uuid,
        "posting_error": sa.Text,
        "posted_at": sa.DateTime,
        "created_at": sa.DateTime,
        "updated_at": sa.DateTime,
    }
    for name, expected_type in types.items():
        if not isinstance(columns[name]["type"], expected_type):
            return False
    amount_type = columns["variance_amount_base"]["type"]
    if amount_type.precision != 14 or amount_type.scale != 4:
        return False
    status_type = columns["accounting_status"]["type"]
    if getattr(status_type, "name", None) != "operational_posting_status":
        return False
    for name in ("created_at", "updated_at"):
        if not getattr(columns[name]["type"], "timezone", False):
            return False
    required = {"id", "actual_id", "allocation_line_id", "variance_amount_base", "created_at", "updated_at"}
    if any(columns[name]["nullable"] for name in required):
        return False
    if any(not columns[name]["nullable"] for name in expected_names - required):
        return False
    if inspector.get_pk_constraint(POSTINGS).get("constrained_columns") != ["id"]:
        return False
    unique = inspector.get_unique_constraints(POSTINGS)
    if len(unique) != 1 or not any(
        item.get("name") == "uq_lc_actual_variance_allocation"
        and item.get("column_names") == ["actual_id", "allocation_line_id"]
        for item in unique
    ):
        return False
    expected_fks = {
        ("actual_id", "lc_line_actuals", "id", "CASCADE"),
        ("allocation_line_id", "lc_allocation_lines", "id", "RESTRICT"),
        ("posting_batch_id", "accounting_posting_batches", "id", "SET NULL"),
        ("journal_entry_id", "journal_entries", "id", "SET NULL"),
    }
    raw_fks = inspector.get_foreign_keys(POSTINGS)
    if len(raw_fks) != 4 or any(
        len(fk["constrained_columns"]) != 1 or len(fk["referred_columns"]) != 1
        for fk in raw_fks
    ):
        return False
    actual_fks = {
        (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0],
         (fk.get("options") or {}).get("ondelete", "").upper())
        for fk in raw_fks
    }
    if len(actual_fks) != len(raw_fks) or actual_fks != expected_fks:
        return False
    unique_names = {item.get("name") for item in unique}
    indexes = {
        item["name"]: item.get("column_names")
        for item in inspector.get_indexes(POSTINGS)
        if item["name"] not in unique_names and item.get("duplicates_constraint") is None
    }
    expected_indexes = {
        "ix_lc_actual_variance_postings_batch_id": ["posting_batch_id"],
        "ix_lc_actual_variance_postings_journal_id": ["journal_entry_id"],
        "ix_lc_actual_variance_postings_status": ["accounting_status"],
    }
    if indexes != expected_indexes:
        return False
    comment = inspector.get_table_comment(POSTINGS).get("text")
    return comment == MARKER


def _ensure_postings_table(bind):
    if sa.inspect(bind).has_table(POSTINGS):
        if not _posting_table_shape(bind):
            raise RuntimeError(f"Refusing to adopt an incompatible {POSTINGS} table")
        return

    op.create_table(
        POSTINGS,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actual_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_line_id", sa.Uuid(), nullable=False),
        sa.Column("variance_amount_base", sa.Numeric(14, 4), nullable=False),
        sa.Column("posting_batch_id", sa.Uuid(), nullable=True),
        sa.Column("journal_entry_id", sa.Uuid(), nullable=True),
        sa.Column("accounting_status", postgresql.ENUM(
            "PENDING", "POSTED", "FAILED", "REVERSED", "NOT_REQUIRED",
            name="operational_posting_status", create_type=False,
        ), nullable=True),
        sa.Column("posting_error", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_lc_actual_variance_postings"),
        sa.UniqueConstraint("actual_id", "allocation_line_id", name="uq_lc_actual_variance_allocation"),
        sa.ForeignKeyConstraint(["actual_id"], ["lc_line_actuals.id"], name="fk_lc_actual_variance_actual", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["allocation_line_id"], ["lc_allocation_lines.id"], name="fk_lc_actual_variance_allocation", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["posting_batch_id"], ["accounting_posting_batches.id"], name="fk_lc_actual_variance_batch", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], name="fk_lc_actual_variance_journal", ondelete="SET NULL"),
        comment=MARKER,
    )
    op.create_index("ix_lc_actual_variance_postings_batch_id", POSTINGS, ["posting_batch_id"])
    op.create_index("ix_lc_actual_variance_postings_journal_id", POSTINGS, ["journal_entry_id"])
    op.create_index("ix_lc_actual_variance_postings_status", POSTINGS, ["accounting_status"])
    if not _posting_table_shape(bind):
        raise RuntimeError(f"Created {POSTINGS} table does not match the expected posting schema")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE):
        raise RuntimeError(f"Required {TABLE} table is missing before landed-cost variance posting")
    for name, (column_type, comment) in COLUMNS.items():
        _ensure_column(bind, name, column_type, comment)
    _ensure_postings_table(bind)

    bind.execute(sa.text(f"""
        UPDATE {TABLE} AS actual
        SET actual_amount_base = round(actual.amount_fc * COALESCE(line.exchange_rate, 1), 4),
            variance_amount_base = round(
                actual.amount_fc * COALESCE(line.exchange_rate, 1)
                - COALESCE((
                    SELECT SUM(allocation.allocated_amount)
                    FROM lc_allocation_lines AS allocation
                    WHERE allocation.header_id = header.id
                      AND allocation.lc_line_id = line.id
                      AND allocation.is_posted IS TRUE
                ), line.amount_base),
                4
            ),
            variance_status = CASE
                WHEN header.status <> 'POSTED' THEN 'RECORDED'
                WHEN round(
                    actual.amount_fc * COALESCE(line.exchange_rate, 1)
                    - COALESCE((
                        SELECT SUM(allocation.allocated_amount)
                        FROM lc_allocation_lines AS allocation
                        WHERE allocation.header_id = header.id
                          AND allocation.lc_line_id = line.id
                          AND allocation.is_posted IS TRUE
                    ), line.amount_base),
                    4
                ) = 0 THEN 'NOT_REQUIRED'
                ELSE 'PENDING'
            END
        FROM lc_lines AS line
        JOIN lc_headers AS header ON header.id = line.header_id
        WHERE actual.lc_line_id = line.id
          AND (actual.variance_status IS NULL OR actual.actual_amount_base IS NULL OR actual.variance_amount_base IS NULL)
    """))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(POSTINGS):
        has_rows = bind.execute(sa.text(f'SELECT EXISTS (SELECT 1 FROM "{POSTINGS}")')).scalar_one()
        if has_rows:
            raise RuntimeError("Refusing to discard landed-cost actual variance posting evidence")
        op.drop_index("ix_lc_actual_variance_postings_status", table_name=POSTINGS)
        op.drop_index("ix_lc_actual_variance_postings_journal_id", table_name=POSTINGS)
        op.drop_index("ix_lc_actual_variance_postings_batch_id", table_name=POSTINGS)
        op.drop_table(POSTINGS)
    if inspector.has_table(TABLE):
        has_reconciliations = bind.execute(sa.text(
            f'SELECT EXISTS (SELECT 1 FROM "{TABLE}" WHERE actual_amount_base IS NOT NULL '
            "OR variance_amount_base IS NOT NULL OR variance_status IS NOT NULL OR posted_at IS NOT NULL)"
        )).scalar_one()
        if has_reconciliations:
            raise RuntimeError("Refusing to discard landed-cost actual variance reconciliation metadata")
        for name in reversed(list(COLUMNS)):
            if name in {item["name"] for item in sa.inspect(bind).get_columns(TABLE)}:
                op.drop_column(TABLE, name)
