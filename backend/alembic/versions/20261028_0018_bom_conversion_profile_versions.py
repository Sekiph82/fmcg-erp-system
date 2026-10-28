"""add conversion profile versions and inclusive effective-date windows

Revision ID: 20261028_0018
Revises: 20261028_0017
Create Date: 2026-10-28
"""
from alembic import op


revision = "20261028_0018"
down_revision = "20261028_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'bom_conversion_profiles'
                  AND column_name = 'version_no'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles
                    ADD COLUMN version_no VARCHAR(20) NOT NULL DEFAULT '1.0';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'bom_conversion_profiles'
                  AND column_name = 'effective_from'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles ADD COLUMN effective_from DATE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'bom_conversion_profiles'
                  AND column_name = 'effective_to'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles ADD COLUMN effective_to DATE;
            END IF;

            UPDATE public.bom_conversion_profiles
                SET version_no = '1.0'
                WHERE version_no IS NULL OR btrim(version_no) = '';
            ALTER TABLE public.bom_conversion_profiles
                ALTER COLUMN version_no SET DEFAULT '1.0',
                ALTER COLUMN version_no SET NOT NULL,
                DROP CONSTRAINT IF EXISTS uq_bom_conversion_profiles_profile_code;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_conversion_profiles'::regclass
                  AND conname = 'uq_bom_conversion_profile_code_version'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles
                    ADD CONSTRAINT uq_bom_conversion_profile_code_version
                    UNIQUE (profile_code, version_no);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_conversion_profiles'::regclass
                  AND conname = 'ck_bom_conversion_profile_version_not_blank'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles
                    ADD CONSTRAINT ck_bom_conversion_profile_version_not_blank
                    CHECK (version_no ~ '[^[:space:]]');
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_conversion_profiles'::regclass
                  AND conname = 'ck_bom_conversion_profile_effective_window'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles
                    ADD CONSTRAINT ck_bom_conversion_profile_effective_window
                    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from);
            END IF;
        END;
        $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS public.ix_bom_conversion_profiles_profile_code")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bom_conversion_profiles_profile_code "
        "ON public.bom_conversion_profiles (profile_code)"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM public.bom_conversion_profiles
                GROUP BY profile_code HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade conversion profile versions while a profile_code has multiple versions';
            END IF;
            ALTER TABLE public.bom_conversion_profiles
                DROP CONSTRAINT IF EXISTS ck_bom_conversion_profile_effective_window,
                DROP CONSTRAINT IF EXISTS ck_bom_conversion_profile_version_not_blank,
                DROP CONSTRAINT IF EXISTS uq_bom_conversion_profile_code_version;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'public.bom_conversion_profiles'::regclass
                  AND conname = 'uq_bom_conversion_profiles_profile_code'
            ) THEN
                ALTER TABLE public.bom_conversion_profiles
                    ADD CONSTRAINT uq_bom_conversion_profiles_profile_code UNIQUE (profile_code);
            END IF;
        END;
        $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS public.ix_bom_conversion_profiles_profile_code")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_bom_conversion_profiles_profile_code "
        "ON public.bom_conversion_profiles (profile_code)"
    )
    op.execute(
        """
        ALTER TABLE public.bom_conversion_profiles
            DROP COLUMN IF EXISTS effective_to,
            DROP COLUMN IF EXISTS effective_from,
            DROP COLUMN IF EXISTS version_no
        """
    )
