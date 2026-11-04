"""Record partial production-order completion and linked backorders.

Revision ID: 20261104_0006
Revises: 20261104_0005
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0006"
down_revision = "20261104_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM production_orders
                WHERE actual_quantity IS NOT NULL
                  AND (actual_quantity <= 0 OR actual_quantity > planned_quantity)
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce partial-completion quantities: existing actual quantities are outside (0, planned_quantity]';
            END IF;
            IF EXISTS (
                SELECT 1 FROM work_orders
                WHERE actual_quantity IS NOT NULL
                  AND (actual_quantity <= 0 OR (planned_quantity IS NOT NULL AND actual_quantity > planned_quantity))
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce work-order quantity limits: existing actual quantities are outside (0, planned_quantity]';
            END IF;
        END
        $$;
        """
    )
    op.add_column(
        "production_orders",
        sa.Column("backorder_of_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "production_orders",
        sa.Column(
            "backordered_quantity",
            sa.Numeric(14, 3),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_production_orders_backorder_of",
        "production_orders",
        "production_orders",
        ["backorder_of_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_production_orders_backorder_of_id",
        "production_orders",
        ["backorder_of_id"],
    )
    op.create_check_constraint(
        "ck_production_orders_backordered_quantity_range",
        "production_orders",
        "backordered_quantity >= 0 AND backordered_quantity <= planned_quantity",
    )
    op.create_check_constraint(
        "ck_production_orders_actual_quantity_range",
        "production_orders",
        "actual_quantity IS NULL OR (actual_quantity > 0 AND actual_quantity <= planned_quantity)",
    )
    op.create_check_constraint(
        "ck_work_orders_actual_quantity_range",
        "work_orders",
        "actual_quantity IS NULL OR (actual_quantity > 0 AND (planned_quantity IS NULL OR actual_quantity <= planned_quantity))",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM production_orders
                WHERE backorder_of_id IS NOT NULL OR backordered_quantity > 0
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: production-order backorder lineage would be destroyed';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint(
        "ck_work_orders_actual_quantity_range",
        "work_orders",
        type_="check",
    )
    op.drop_constraint(
        "ck_production_orders_actual_quantity_range",
        "production_orders",
        type_="check",
    )
    op.drop_constraint(
        "ck_production_orders_backordered_quantity_range",
        "production_orders",
        type_="check",
    )
    op.drop_index("ix_production_orders_backorder_of_id", table_name="production_orders")
    op.drop_constraint(
        "fk_production_orders_backorder_of",
        "production_orders",
        type_="foreignkey",
    )
    op.drop_column("production_orders", "backordered_quantity")
    op.drop_column("production_orders", "backorder_of_id")
