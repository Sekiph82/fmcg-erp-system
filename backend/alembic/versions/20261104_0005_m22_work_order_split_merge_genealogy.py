"""Add immutable work-order split/merge lineage.

Revision ID: 20261104_0005
Revises: 20261104_0004
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0005"
down_revision = "20261104_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A split creates several successors for one routing step. Keep the route-step
    # FK restrictive, but replace the earlier one-row uniqueness assumption.
    op.drop_constraint(
        "uq_work_order_route_step_per_parent",
        "work_orders",
        type_="unique",
    )
    op.create_table(
        "production_work_order_genealogy",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("source_work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transferred_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("action IN ('SPLIT', 'MERGE')", name="ck_work_order_genealogy_action"),
        sa.CheckConstraint(
            "source_work_order_id <> result_work_order_id",
            name="ck_work_order_genealogy_not_self",
        ),
        sa.CheckConstraint(
            "transferred_quantity > 0",
            name="ck_work_order_genealogy_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["source_work_order_id"],
            ["work_orders.id"],
            name="fk_work_order_genealogy_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["result_work_order_id"],
            ["work_orders.id"],
            name="fk_work_order_genealogy_result",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_work_order_genealogy_actor",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_production_work_order_genealogy"),
        sa.UniqueConstraint(
            "operation_id",
            "source_work_order_id",
            "result_work_order_id",
            name="uq_work_order_genealogy_operation_edge",
        ),
    )
    op.create_index(
        "ix_work_order_genealogy_operation",
        "production_work_order_genealogy",
        ["operation_id"],
    )
    op.create_index(
        "ix_work_order_genealogy_source_created",
        "production_work_order_genealogy",
        ["source_work_order_id", "created_at"],
    )
    op.create_index(
        "ix_work_order_genealogy_result_created",
        "production_work_order_genealogy",
        ["result_work_order_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION public.prevent_production_work_order_genealogy_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Production work-order genealogy is append-only'
                USING ERRCODE = '23514',
                      CONSTRAINT = 'ck_work_order_genealogy_append_only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_work_order_genealogy_append_only
            BEFORE UPDATE OR DELETE ON public.production_work_order_genealogy
            FOR EACH ROW EXECUTE FUNCTION public.prevent_production_work_order_genealogy_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_work_order_genealogy_no_truncate
            BEFORE TRUNCATE ON public.production_work_order_genealogy
            FOR EACH STATEMENT EXECUTE FUNCTION public.prevent_production_work_order_genealogy_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM production_work_order_genealogy) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: work-order split/merge genealogy would be destroyed';
            END IF;
            IF EXISTS (
                SELECT 1
                FROM work_orders
                WHERE routing_step_id IS NOT NULL
                GROUP BY production_order_id, routing_step_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: split work orders share a production-order/routing-step pair';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_work_order_genealogy_no_truncate ON public.production_work_order_genealogy"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_work_order_genealogy_append_only ON public.production_work_order_genealogy"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS public.prevent_production_work_order_genealogy_mutation()"
    )
    op.drop_index("ix_work_order_genealogy_result_created", table_name="production_work_order_genealogy")
    op.drop_index("ix_work_order_genealogy_source_created", table_name="production_work_order_genealogy")
    op.drop_index("ix_work_order_genealogy_operation", table_name="production_work_order_genealogy")
    op.drop_table("production_work_order_genealogy")
    op.create_unique_constraint(
        "uq_work_order_route_step_per_parent",
        "work_orders",
        ["production_order_id", "routing_step_id"],
    )
