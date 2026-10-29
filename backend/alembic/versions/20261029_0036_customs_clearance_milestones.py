"""add evidence-linked customs clearance status history

Revision ID: 20261029_0036
Revises: 20261029_0035
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0036"
down_revision = "20261029_0035"
branch_labels = None
depends_on = None


TABLE = "customs_clearance_milestones"
TABLE_MARKER = "created by Alembic revision 20261029_0036"
INDEX = "ix_customs_clearance_milestones_clearance_effective"
INDEX_MARKER = "added by Alembic revision 20261029_0036"
CONSTRAINTS = {
    "ck_customs_clearance_milestones_previous_status":
        "previous_status IN ('PENDING', 'DOCS_SUBMITTED', 'UNDER_REVIEW', 'EXAM_REQUESTED', 'DUTY_ASSESSED', 'DUTY_PAID', 'CLEARED', 'HELD')",
    "ck_customs_clearance_milestones_new_status":
        "new_status IN ('DOCS_SUBMITTED', 'UNDER_REVIEW', 'EXAM_REQUESTED', 'DUTY_ASSESSED', 'DUTY_PAID', 'CLEARED', 'HELD')",
    "ck_customs_clearance_milestones_source_reference":
        "length(trim(source_reference)) > 0",
}


def _table_exists(bind) -> bool:
    return bind.execute(sa.text("SELECT to_regclass(:table)"), {"table": TABLE}).scalar_one_or_none() is not None


def _constraint_exists(bind, name: str) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conrelid = to_regclass(:table) AND conname = :name"
    ), {"table": TABLE, "name": name}).first())


def _index_exists(bind) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = :name"
    ), {"name": INDEX}).first())


def _constraint_marker(bind, name: str):
    return bind.execute(sa.text(
        "SELECT obj_description(oid, 'pg_constraint') FROM pg_constraint "
        "WHERE conrelid = to_regclass(:table) AND conname = :name"
    ), {"table": TABLE, "name": name}).scalar_one_or_none()


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("clearance_id", sa.Uuid(), nullable=False),
            sa.Column("previous_status", sa.String(24), nullable=False),
            sa.Column("new_status", sa.String(24), nullable=False),
            sa.Column("source_reference", sa.String(200), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("changed_by_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["clearance_id"], ["customs_clearances.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="RESTRICT"),
        )
        op.execute(f"COMMENT ON TABLE {TABLE} IS '{TABLE_MARKER}'")

    for name, condition in CONSTRAINTS.items():
        if not _constraint_exists(bind, name):
            op.create_check_constraint(name, TABLE, condition)
            op.execute(f"COMMENT ON CONSTRAINT {name} ON {TABLE} IS '{INDEX_MARKER}'")

    if not _index_exists(bind):
        op.create_index(INDEX, TABLE, ["clearance_id", "effective_at", "created_at"])
        op.execute(f"COMMENT ON INDEX {INDEX} IS '{INDEX_MARKER}'")

    op.execute("""
        CREATE OR REPLACE FUNCTION reject_customs_clearance_milestone_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'customs clearance milestones are append-only'
                USING ERRCODE = '23514';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute(f"DROP TRIGGER IF EXISTS customs_clearance_milestones_no_update_delete ON {TABLE}")
    op.execute(f"DROP TRIGGER IF EXISTS customs_clearance_milestones_no_truncate ON {TABLE}")
    op.execute(f"""
        CREATE TRIGGER customs_clearance_milestones_no_update_delete
        BEFORE UPDATE OR DELETE ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION reject_customs_clearance_milestone_mutation()
    """)
    op.execute(f"""
        CREATE TRIGGER customs_clearance_milestones_no_truncate
        BEFORE TRUNCATE ON {TABLE}
        FOR EACH STATEMENT EXECUTE FUNCTION reject_customs_clearance_milestone_mutation()
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind):
        return
    marker = bind.execute(
        sa.text("SELECT obj_description(to_regclass(:table), 'pg_class')"),
        {"table": TABLE},
    ).scalar_one_or_none()
    if marker == TABLE_MARKER and bind.execute(sa.text(f"SELECT 1 FROM {TABLE} LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade customs clearance milestones while recorded history exists.")

    if marker == TABLE_MARKER:
        op.execute(f"DROP TRIGGER IF EXISTS customs_clearance_milestones_no_truncate ON {TABLE}")
        op.execute(f"DROP TRIGGER IF EXISTS customs_clearance_milestones_no_update_delete ON {TABLE}")
        op.execute("DROP FUNCTION IF EXISTS reject_customs_clearance_milestone_mutation()")

    for name in CONSTRAINTS:
        if _constraint_exists(bind, name) and _constraint_marker(bind, name) == INDEX_MARKER:
            op.drop_constraint(name, TABLE, type_="check")

    if _index_exists(bind):
        index_marker = bind.execute(sa.text(
            "SELECT obj_description(to_regclass(:name), 'pg_class')"
        ), {"name": INDEX}).scalar_one_or_none()
        if index_marker == INDEX_MARKER:
            op.drop_index(INDEX, table_name=TABLE)

    if marker == TABLE_MARKER:
        op.drop_table(TABLE)
