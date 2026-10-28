"""store expected process yield against BOM input base quantity

Revision ID: 20261028_0019
Revises: 20261028_0018
Create Date: 2026-10-28
"""
from alembic import op


revision = "20261028_0019"
down_revision = "20261028_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'advanced_boms'
                  AND column_name = 'expected_process_yield_pct'
            ) THEN
                ALTER TABLE public.advanced_boms
                    ADD COLUMN expected_process_yield_pct NUMERIC(8, 4);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.advanced_boms'::regclass
                  AND conname = 'ck_advanced_bom_expected_process_yield_nonnegative'
            ) THEN
                ALTER TABLE public.advanced_boms
                    ADD CONSTRAINT ck_advanced_bom_expected_process_yield_nonnegative
                    CHECK (
                        expected_process_yield_pct IS NULL
                        OR expected_process_yield_pct >= 0
                    );
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.advanced_boms
            DROP CONSTRAINT IF EXISTS ck_advanced_bom_expected_process_yield_nonnegative,
            DROP COLUMN IF EXISTS expected_process_yield_pct
        """
    )
