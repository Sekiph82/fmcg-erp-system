"""Record production-order approval before release.

Revision ID: 20261104_0002
Revises: 20261104_0001
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0002"
down_revision = "20261104_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_orders",
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "production_orders",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_production_orders_approved_by_users",
        "production_orders",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "exec_production_orders",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exec_production_orders", "approved_at")
    op.drop_constraint(
        "fk_production_orders_approved_by_users",
        "production_orders",
        type_="foreignkey",
    )
    op.drop_column("production_orders", "approved_at")
    op.drop_column("production_orders", "approved_by")
