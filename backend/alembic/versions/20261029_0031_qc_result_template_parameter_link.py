"""link QC results to their exact template parameter

Revision ID: 20261029_0031
Revises: 20261029_0030
Create Date: 2026-10-29
"""
from alembic import op


revision = "20261029_0031"
down_revision = "20261029_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.qc_test_results') IS NULL THEN
                RAISE EXCEPTION 'qc_test_results is required before linking QC template parameters';
            END IF;
            IF to_regclass('public.qc_template_parameters') IS NULL THEN
                RAISE EXCEPTION 'qc_template_parameters is required before linking QC results';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'qc_test_results'
                  AND column_name = 'template_parameter_id'
            ) THEN
                ALTER TABLE public.qc_test_results
                    ADD COLUMN template_parameter_id UUID
                    REFERENCES public.qc_template_parameters(id) ON DELETE SET NULL;
            END IF;
            CREATE INDEX IF NOT EXISTS ix_qc_test_results_template_parameter_id
                ON public.qc_test_results (template_parameter_id);
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM public.qc_test_results WHERE template_parameter_id IS NOT NULL) THEN
                RAISE EXCEPTION 'Cannot remove QC template parameter links while QC results reference them';
            END IF;
            DROP INDEX IF EXISTS public.ix_qc_test_results_template_parameter_id;
            ALTER TABLE public.qc_test_results DROP COLUMN IF EXISTS template_parameter_id;
        END;
        $$;
        """
    )
