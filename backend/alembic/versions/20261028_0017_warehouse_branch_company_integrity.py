"""Enforce warehouse branch/company ownership across master references.

Revision ID: 20261028_0017
Revises: 20261028_0016
Create Date: 2026-10-28
"""
from alembic import op


revision = "20261028_0017"
down_revision = "20261028_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires the referenced composite key to be explicitly unique.
    # The branch id is already the PK; this pair lets a warehouse reference the
    # branch only under its actual owning company.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.branches'::regclass
                  AND conname = 'uq_branches_id_company_id'
            ) THEN
                ALTER TABLE public.branches
                    ADD CONSTRAINT uq_branches_id_company_id UNIQUE (id, company_id);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.warehouses'::regclass
                  AND conname = 'fk_warehouses_branch_company'
            ) THEN
                ALTER TABLE public.warehouses
                    ADD CONSTRAINT fk_warehouses_branch_company
                    FOREIGN KEY (branch_id, company_id)
                    REFERENCES public.branches (id, company_id)
                    ON DELETE SET NULL (branch_id);
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.warehouses DROP CONSTRAINT IF EXISTS fk_warehouses_branch_company"
    )
    op.execute(
        "ALTER TABLE public.branches DROP CONSTRAINT IF EXISTS uq_branches_id_company_id"
    )
