"""govern Advanced BOM version identifiers and effective date windows

Revision ID: 20261029_0026
Revises: 20261029_0025
Create Date: 2026-10-29
"""
from alembic import op


revision = "20261029_0026"
down_revision = "20261029_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The squashed baseline may already create these model checks. Keep the
    # legacy-upgrade path idempotent, matching the recipe governance migration.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.advanced_boms'::regclass
                  AND conname = 'ck_advanced_boms_version_not_blank'
            ) THEN
                ALTER TABLE public.advanced_boms
                    ADD CONSTRAINT ck_advanced_boms_version_not_blank
                    CHECK (version_no ~ '[^[:space:]]');
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.advanced_boms'::regclass
                  AND conname = 'ck_advanced_boms_revision_not_blank'
            ) THEN
                ALTER TABLE public.advanced_boms
                    ADD CONSTRAINT ck_advanced_boms_revision_not_blank
                    CHECK (revision_no ~ '[^[:space:]]');
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.advanced_boms'::regclass
                  AND conname = 'ck_advanced_boms_effective_window'
            ) THEN
                ALTER TABLE public.advanced_boms
                    ADD CONSTRAINT ck_advanced_boms_effective_window
                    CHECK (
                        effective_to IS NULL
                        OR effective_from IS NULL
                        OR effective_to >= effective_from
                    );
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.advanced_boms DROP CONSTRAINT IF EXISTS ck_advanced_boms_effective_window")
    op.execute("ALTER TABLE public.advanced_boms DROP CONSTRAINT IF EXISTS ck_advanced_boms_revision_not_blank")
    op.execute("ALTER TABLE public.advanced_boms DROP CONSTRAINT IF EXISTS ck_advanced_boms_version_not_blank")
