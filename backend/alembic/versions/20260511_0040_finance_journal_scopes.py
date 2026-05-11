"""Add scoped access fields to finance journals.

Revision ID: 20260511_0040
Revises: 20260511_0030
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260511_0040"
down_revision = "20260511_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("journal_entries", sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("journal_entries", sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key(
        "fk_journal_entries_company_id",
        "journal_entries",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_journal_entries_branch_id",
        "journal_entries",
        "branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_journal_entries_cost_center_id",
        "journal_entries",
        "cost_centers",
        ["cost_center_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_journal_entries_company_id", "journal_entries", ["company_id"])
    op.create_index("ix_journal_entries_branch_id", "journal_entries", ["branch_id"])
    op.create_index("ix_journal_entries_cost_center_id", "journal_entries", ["cost_center_id"])


def downgrade() -> None:
    op.drop_index("ix_journal_entries_cost_center_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_branch_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_company_id", table_name="journal_entries")
    op.drop_constraint("fk_journal_entries_cost_center_id", "journal_entries", type_="foreignkey")
    op.drop_constraint("fk_journal_entries_branch_id", "journal_entries", type_="foreignkey")
    op.drop_constraint("fk_journal_entries_company_id", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "cost_center_id")
    op.drop_column("journal_entries", "branch_id")
    op.drop_column("journal_entries", "company_id")
