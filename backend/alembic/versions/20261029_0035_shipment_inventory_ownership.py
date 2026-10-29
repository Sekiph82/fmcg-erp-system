"""track evidence-backed inventory ownership for shipment PO links

Revision ID: 20261029_0035
Revises: 20261029_0034
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0035"
down_revision = "20261029_0034"
branch_labels = None
depends_on = None


OWNER_COLUMN = "inventory_owner_status"
OWNER_CONSTRAINT = "ck_shipment_po_links_inventory_owner_status"
EVENT_TABLE = "shipment_ownership_events"
COLUMN_MARKER = "added by Alembic revision 20261029_0035"
TABLE_MARKER = "created by Alembic revision 20261029_0035"
EVENT_CONSTRAINTS = (
    "ck_shipment_ownership_events_previous_owner",
    "ck_shipment_ownership_events_new_owner",
)


def _column_exists(bind, table: str, column: str) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :table AND column_name = :column"
    ), {"table": table, "column": column}).first())


def _constraint_exists(bind, table: str, constraint: str) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conrelid = to_regclass(:table) AND conname = :constraint"
    ), {"table": table, "constraint": constraint}).first())


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "shipment_po_links", OWNER_COLUMN):
        op.add_column(
            "shipment_po_links",
            sa.Column(OWNER_COLUMN, sa.String(24), nullable=False, server_default="UNCONFIRMED"),
        )
        op.execute(
            f"COMMENT ON COLUMN shipment_po_links.{OWNER_COLUMN} IS '{COLUMN_MARKER}'"
        )
    if not _constraint_exists(bind, "shipment_po_links", OWNER_CONSTRAINT):
        op.create_check_constraint(
            OWNER_CONSTRAINT,
            "shipment_po_links",
            f"{OWNER_COLUMN} IN ('UNCONFIRMED', 'SUPPLIER_OWNED', 'BUYER_OWNED')",
        )
        op.execute(
            f"COMMENT ON CONSTRAINT {OWNER_CONSTRAINT} ON shipment_po_links IS '{COLUMN_MARKER}'"
        )

    table_exists = bind.execute(sa.text(
        "SELECT to_regclass(:table)"
    ), {"table": EVENT_TABLE}).scalar_one_or_none() is not None
    if not table_exists:
        op.create_table(
            EVENT_TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("shipment_po_link_id", sa.Uuid(), nullable=False),
            sa.Column("previous_owner", sa.String(24), nullable=False),
            sa.Column("new_owner", sa.String(24), nullable=False),
            sa.Column("source_reference", sa.String(200), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("changed_by_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "previous_owner IN ('UNCONFIRMED', 'SUPPLIER_OWNED', 'BUYER_OWNED')",
                name=EVENT_CONSTRAINTS[0],
            ),
            sa.CheckConstraint(
                "new_owner IN ('SUPPLIER_OWNED', 'BUYER_OWNED')",
                name=EVENT_CONSTRAINTS[1],
            ),
            sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["shipment_po_link_id"], ["shipment_po_links.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_shipment_ownership_events_shipment_po_link_id",
            EVENT_TABLE,
            ["shipment_po_link_id"],
        )
        op.execute(f"COMMENT ON TABLE {EVENT_TABLE} IS '{TABLE_MARKER}'")
    else:
        for constraint, condition in (
            (EVENT_CONSTRAINTS[0], "previous_owner IN ('UNCONFIRMED', 'SUPPLIER_OWNED', 'BUYER_OWNED')"),
            (EVENT_CONSTRAINTS[1], "new_owner IN ('SUPPLIER_OWNED', 'BUYER_OWNED')"),
        ):
            if not _constraint_exists(bind, EVENT_TABLE, constraint):
                op.create_check_constraint(constraint, EVENT_TABLE, condition)

    op.execute("""
        CREATE OR REPLACE FUNCTION reject_shipment_ownership_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'shipment ownership events are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute(f"""
        CREATE TRIGGER shipment_ownership_events_no_update_delete
        BEFORE UPDATE OR DELETE ON {EVENT_TABLE}
        FOR EACH ROW EXECUTE FUNCTION reject_shipment_ownership_event_mutation()
    """)
    op.execute(f"""
        CREATE TRIGGER shipment_ownership_events_no_truncate
        BEFORE TRUNCATE ON {EVENT_TABLE}
        FOR EACH STATEMENT EXECUTE FUNCTION reject_shipment_ownership_event_mutation()
    """)


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(f"DROP TRIGGER IF EXISTS shipment_ownership_events_no_truncate ON {EVENT_TABLE}")
    op.execute(f"DROP TRIGGER IF EXISTS shipment_ownership_events_no_update_delete ON {EVENT_TABLE}")
    op.execute("DROP FUNCTION IF EXISTS reject_shipment_ownership_event_mutation()")

    if bind.execute(sa.text("SELECT to_regclass(:table)"), {"table": EVENT_TABLE}).scalar_one_or_none():
        marker = bind.execute(
            sa.text("SELECT obj_description(to_regclass(:table), 'pg_class')"),
            {"table": EVENT_TABLE},
        ).scalar_one_or_none()
        if marker == TABLE_MARKER:
            if bind.execute(sa.text(f"SELECT 1 FROM {EVENT_TABLE} LIMIT 1")).first():
                raise RuntimeError("Cannot downgrade shipment ownership while its audit events still exist.")
            op.drop_table(EVENT_TABLE)

    if _constraint_exists(bind, "shipment_po_links", OWNER_CONSTRAINT):
        constraint_marker = bind.execute(sa.text(
            "SELECT obj_description(oid, 'pg_constraint') FROM pg_constraint "
            "WHERE conrelid = to_regclass('shipment_po_links') AND conname = :name"
        ), {"name": OWNER_CONSTRAINT}).scalar_one_or_none()
        if constraint_marker == COLUMN_MARKER:
            op.drop_constraint(OWNER_CONSTRAINT, "shipment_po_links", type_="check")

    if _column_exists(bind, "shipment_po_links", OWNER_COLUMN):
        marker = bind.execute(sa.text(
            "SELECT col_description(attrelid, attnum) FROM pg_attribute "
            "WHERE attrelid = to_regclass('shipment_po_links') AND attname = :column "
            "AND NOT attisdropped"
        ), {"column": OWNER_COLUMN}).scalar_one_or_none()
        if marker == COLUMN_MARKER:
            op.drop_column("shipment_po_links", OWNER_COLUMN)
