"""add versioned quality gate definitions with inclusive effective dates

Revision ID: 20261029_0030
Revises: 20261029_0029
Create Date: 2026-10-29
"""
from alembic import op


revision = "20261029_0030"
down_revision = "20261029_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'quality_gate_definitions'
                  AND column_name = 'version'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'quality_gate_definitions'
                  AND column_name = 'effective_from'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD COLUMN effective_from DATE NOT NULL DEFAULT CURRENT_DATE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'quality_gate_definitions'
                  AND column_name = 'effective_to'
            ) THEN
                ALTER TABLE public.quality_gate_definitions ADD COLUMN effective_to DATE;
            END IF;

            UPDATE public.quality_gate_definitions
                SET version = 1 WHERE version IS NULL OR version < 1;
            ALTER TABLE public.quality_gate_definitions
                ALTER COLUMN version SET DEFAULT 1,
                ALTER COLUMN version SET NOT NULL,
                ALTER COLUMN effective_from SET DEFAULT CURRENT_DATE,
                ALTER COLUMN effective_from SET NOT NULL,
                DROP CONSTRAINT IF EXISTS uq_quality_gate_definitions_code,
                DROP CONSTRAINT IF EXISTS quality_gate_definitions_code_key;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.quality_gate_definitions'::regclass
                  AND conname = 'uq_quality_gate_definitions_code_version'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD CONSTRAINT uq_quality_gate_definitions_code_version UNIQUE (code, version);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.quality_gate_definitions'::regclass
                  AND conname = 'ck_quality_gate_definitions_version_positive'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD CONSTRAINT ck_quality_gate_definitions_version_positive CHECK (version >= 1);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.quality_gate_definitions'::regclass
                  AND conname = 'ck_quality_gate_definitions_effective_window'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD CONSTRAINT ck_quality_gate_definitions_effective_window
                    CHECK (effective_to IS NULL OR effective_to >= effective_from);
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM public.quality_gate_definitions
                GROUP BY code HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade quality gate versions while a code has multiple versions';
            END IF;
            ALTER TABLE public.quality_gate_definitions
                DROP CONSTRAINT IF EXISTS ck_quality_gate_definitions_effective_window,
                DROP CONSTRAINT IF EXISTS ck_quality_gate_definitions_version_positive,
                DROP CONSTRAINT IF EXISTS uq_quality_gate_definitions_code_version;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.quality_gate_definitions'::regclass
                  AND conname = 'uq_quality_gate_definitions_code'
            ) THEN
                ALTER TABLE public.quality_gate_definitions
                    ADD CONSTRAINT uq_quality_gate_definitions_code UNIQUE (code);
            END IF;
            ALTER TABLE public.quality_gate_definitions
                DROP COLUMN IF EXISTS effective_to,
                DROP COLUMN IF EXISTS effective_from,
                DROP COLUMN IF EXISTS version;
        END;
        $$;
        """
    )
