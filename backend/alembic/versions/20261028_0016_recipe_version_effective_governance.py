"""govern recipe version identifiers and effective date windows

Revision ID: 20261028_0016
Revises: 20261027_0015
Create Date: 2026-10-28
"""
from alembic import op


revision = "20261028_0016"
down_revision = "20261027_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The squashed baseline may already have created these model constraints.
    # The guards keep both baseline-first and legacy-upgrade paths idempotent.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.recipes'::regclass
                  AND conname = 'ck_recipes_version_not_blank'
            ) THEN
                ALTER TABLE public.recipes
                    ADD CONSTRAINT ck_recipes_version_not_blank
                    CHECK (version ~ '[^[:space:]]');
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.recipes'::regclass
                  AND conname = 'ck_recipes_effective_window'
            ) THEN
                ALTER TABLE public.recipes
                    ADD CONSTRAINT ck_recipes_effective_window
                    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from);
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.recipes DROP CONSTRAINT IF EXISTS ck_recipes_effective_window")
    op.execute("ALTER TABLE public.recipes DROP CONSTRAINT IF EXISTS ck_recipes_version_not_blank")
