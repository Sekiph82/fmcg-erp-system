"""Track canonical work-order rework without losing operation quantity lineage.

Revision ID: 20261104_0007
Revises: 20261104_0006
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0007"
down_revision = "20261104_0006"
branch_labels = None
depends_on = None


def _create_check_constraint_if_missing(name: str, table: str, expression: str) -> None:
    # The squashed fresh-database baseline may already include current-model checks.
    existing = sa.inspect(op.get_bind()).get_check_constraints(table)
    if any(constraint.get("name") == name for constraint in existing):
        return
    op.create_check_constraint(name, table, expression)


def upgrade() -> None:
    op.add_column(
        "work_orders",
        sa.Column("rework_quantity", sa.Numeric(14, 3), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "work_orders",
        sa.Column("rework_of_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("work_orders", sa.Column("rework_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_work_orders_rework_of",
        "work_orders",
        "work_orders",
        ["rework_of_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_work_orders_rework_of_id", "work_orders", ["rework_of_id"])
    _create_check_constraint_if_missing(
        "ck_work_orders_rework_quantity_range",
        "work_orders",
        "rework_quantity >= 0 AND (planned_quantity IS NULL OR rework_quantity <= planned_quantity) "
        "AND (actual_quantity IS NULL OR rework_quantity <= actual_quantity)",
    )
    _create_check_constraint_if_missing(
        "ck_work_orders_rework_not_self",
        "work_orders",
        "rework_of_id IS NULL OR rework_of_id <> id",
    )
    _create_check_constraint_if_missing(
        "ck_work_orders_rework_reason_required",
        "work_orders",
        "(rework_of_id IS NULL AND rework_reason IS NULL) OR "
        "(rework_of_id IS NOT NULL AND rework_reason IS NOT NULL AND length(trim(rework_reason)) > 0)",
    )
    op.drop_constraint("ck_work_order_genealogy_action", "production_work_order_genealogy", type_="check")
    op.create_check_constraint(
        "ck_work_order_genealogy_action",
        "production_work_order_genealogy",
        "action IN ('SPLIT', 'MERGE', 'REWORK')",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM work_orders
                WHERE rework_of_id IS NOT NULL OR rework_quantity > 0 OR rework_reason IS NOT NULL
            ) OR EXISTS (
                SELECT 1 FROM production_work_order_genealogy WHERE action = 'REWORK'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: canonical work-order rework lineage or quantities would be destroyed';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint("ck_work_order_genealogy_action", "production_work_order_genealogy", type_="check")
    op.create_check_constraint(
        "ck_work_order_genealogy_action",
        "production_work_order_genealogy",
        "action IN ('SPLIT', 'MERGE')",
    )
    op.drop_constraint("ck_work_orders_rework_reason_required", "work_orders", type_="check")
    op.drop_constraint("ck_work_orders_rework_not_self", "work_orders", type_="check")
    op.drop_constraint("ck_work_orders_rework_quantity_range", "work_orders", type_="check")
    op.drop_index("ix_work_orders_rework_of_id", table_name="work_orders")
    op.drop_constraint("fk_work_orders_rework_of", "work_orders", type_="foreignkey")
    op.drop_column("work_orders", "rework_reason")
    op.drop_column("work_orders", "rework_of_id")
    op.drop_column("work_orders", "rework_quantity")
