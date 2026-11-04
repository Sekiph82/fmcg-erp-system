"""Link subcontracting orders to canonical production work orders.

Revision ID: 20261104_0008
Revises: 20261104_0007
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0008"
down_revision = "20261104_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subcontract_orders",
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_subcontract_orders_work_order",
        "subcontract_orders",
        "work_orders",
        ["work_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_subcontract_orders_work_order_id",
        "subcontract_orders",
        ["work_order_id"],
        unique=True,
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM subcontract_orders WHERE work_order_id IS NOT NULL) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: subcontract-to-work-order links would be destroyed';
            END IF;
        END
        $$;
        """
    )
    op.drop_index("ix_subcontract_orders_work_order_id", table_name="subcontract_orders")
    op.drop_constraint("fk_subcontract_orders_work_order", "subcontract_orders", type_="foreignkey")
    op.drop_column("subcontract_orders", "work_order_id")
