"""Link material issues to exact reservation and stock rows.

Revision ID: 20261108_0014
Revises: 20261108_0013
Create Date: 2026-11-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0014"
down_revision = "20261108_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_reservation_lines",
        sa.Column("source_stock_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reservation_line_source_stock",
        "material_reservation_lines",
        "stocks",
        ["source_stock_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_material_reservation_lines_source_stock_id",
        "material_reservation_lines",
        ["source_stock_id"],
    )

    op.add_column(
        "material_flow_lines",
        sa.Column("reservation_line_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_material_flow_line_reservation_line",
        "material_flow_lines",
        "material_reservation_lines",
        ["reservation_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_material_flow_lines_reservation_line_id",
        "material_flow_lines",
        ["reservation_line_id"],
    )

    op.add_column(
        "material_flow_transactions",
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "uq_material_flow_transactions_idempotency_key",
        "material_flow_transactions",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_material_flow_transactions_idempotency_key", table_name="material_flow_transactions")
    op.drop_column("material_flow_transactions", "idempotency_key")

    op.drop_index("ix_material_flow_lines_reservation_line_id", table_name="material_flow_lines")
    op.drop_constraint("fk_material_flow_line_reservation_line", "material_flow_lines", type_="foreignkey")
    op.drop_column("material_flow_lines", "reservation_line_id")

    op.drop_index("ix_material_reservation_lines_source_stock_id", table_name="material_reservation_lines")
    op.drop_constraint("fk_reservation_line_source_stock", "material_reservation_lines", type_="foreignkey")
    op.drop_column("material_reservation_lines", "source_stock_id")
