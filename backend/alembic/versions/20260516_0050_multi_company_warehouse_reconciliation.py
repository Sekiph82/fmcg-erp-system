"""Multi-company warehouse reconciliation (GAP-025C)

Adds company_id and branch_id to warehouses for branch-level inventory isolation.
companies/branches/user_company_access tables already exist in the initial schema.

Revision ID: 20260516_0050
Revises: 20260516_0040
Create Date: 2026-05-16 12:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260516_0050"
down_revision = "20260516_0040"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    from alembic import context
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_column("warehouses", "company_id"):
        op.add_column(
            "warehouses",
            sa.Column(
                "company_id",
                UUID(as_uuid=True),
                sa.ForeignKey("companies.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_warehouses_company_id", "warehouses", ["company_id"])

    if not _has_column("warehouses", "branch_id"):
        op.add_column(
            "warehouses",
            sa.Column(
                "branch_id",
                UUID(as_uuid=True),
                sa.ForeignKey("branches.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    op.drop_index("ix_warehouses_company_id", table_name="warehouses")
    op.drop_column("warehouses", "branch_id")
    op.drop_column("warehouses", "company_id")
