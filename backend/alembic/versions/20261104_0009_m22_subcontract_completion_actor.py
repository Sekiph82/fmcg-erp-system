"""Record the authenticated actor who completes a subcontracting order.

Revision ID: 20261104_0009
Revises: 20261104_0008
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0009"
down_revision = "20261104_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subcontract_orders",
        sa.Column("completed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_subcontract_orders_completed_by",
        "subcontract_orders",
        "users",
        ["completed_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_subcontract_orders_completed_by",
        "subcontract_orders",
        type_="foreignkey",
    )
    op.drop_column("subcontract_orders", "completed_by_id")
