"""Preserve canonical routing-step identity on production work orders.

Revision ID: 20261104_0004
Revises: 20261104_0003
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20261104_0004"
down_revision = "20261104_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM work_orders wo
                JOIN production_orders po ON po.id = wo.production_order_id
                JOIN routing_steps rs ON rs.id = wo.routing_step_id
                JOIN routings r ON r.id = rs.routing_id
                WHERE wo.routing_step_id IS NOT NULL
                  AND (
                      po.product_id <> r.product_id
                      OR wo.work_center_id <> rs.work_center_id
                      OR wo.operation <> rs.operation
                  )
            ) THEN
                RAISE EXCEPTION
                    'Cannot preserve routing identity: existing work orders disagree with their routing product, operation, or work center';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM work_orders
                WHERE routing_step_id IS NOT NULL
                GROUP BY production_order_id, routing_step_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce one work order per routing step: duplicate production-order/routing-step links exist';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint(
        "work_orders_routing_step_id_fkey",
        "work_orders",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_work_orders_routing_step_id_routing_steps",
        "work_orders",
        "routing_steps",
        ["routing_step_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_work_order_route_step_per_parent",
        "work_orders",
        ["production_order_id", "routing_step_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_work_order_route_step_per_parent",
        "work_orders",
        type_="unique",
    )
    op.drop_constraint(
        "fk_work_orders_routing_step_id_routing_steps",
        "work_orders",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "work_orders_routing_step_id_fkey",
        "work_orders",
        "routing_steps",
        ["routing_step_id"],
        ["id"],
        ondelete="SET NULL",
    )
