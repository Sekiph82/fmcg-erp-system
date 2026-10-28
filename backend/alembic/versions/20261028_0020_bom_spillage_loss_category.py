"""add a distinct spillage yield/loss category

Revision ID: 20261028_0020
Revises: 20261028_0019
Create Date: 2026-10-28
"""
from alembic import op


revision = "20261028_0020"
down_revision = "20261028_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing filling and packaging-reject categories remain distinct; spillage
    # is added without changing or reclassifying existing loss rows.
    op.execute("ALTER TYPE losscategory ADD VALUE IF NOT EXISTS 'SPILLAGE'")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_yield_configs'::regclass
                  AND conname = 'ck_bom_yield_config_standard_pct_nonnegative'
            ) THEN
                ALTER TABLE public.bom_yield_configs
                    ADD CONSTRAINT ck_bom_yield_config_standard_pct_nonnegative
                    CHECK (standard_pct <> 'NaN'::numeric AND standard_pct >= 0);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_yield_configs'::regclass
                  AND conname = 'ck_bom_yield_config_max_allowable_pct_nonnegative'
            ) THEN
                ALTER TABLE public.bom_yield_configs
                    ADD CONSTRAINT ck_bom_yield_config_max_allowable_pct_nonnegative
                    CHECK (
                        max_allowable_pct IS NULL
                        OR (max_allowable_pct <> 'NaN'::numeric AND max_allowable_pct >= 0)
                    );
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL cannot remove an enum label in place. Keep SPILLAGE as an
    # unused-compatible label rather than risk rewriting existing loss records.
    op.execute(
        "ALTER TABLE public.bom_yield_configs "
        "DROP CONSTRAINT IF EXISTS ck_bom_yield_config_max_allowable_pct_nonnegative"
    )
    op.execute(
        "ALTER TABLE public.bom_yield_configs "
        "DROP CONSTRAINT IF EXISTS ck_bom_yield_config_standard_pct_nonnegative"
    )
