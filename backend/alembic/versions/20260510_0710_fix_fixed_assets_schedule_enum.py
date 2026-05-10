"""fix fixed asset depreciation schedule enum type

Revision ID: 20260510_0710
Revises: 20260510_0700
Create Date: 2026-05-10 07:10:00
"""
from alembic import op


revision = "20260510_0710"
down_revision = "20260510_0700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assets_schedulestatus') THEN
                CREATE TYPE assets_schedulestatus AS ENUM ('PLANNED', 'POSTED', 'REVERSED', 'ADJUSTED');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER TABLE fa_depreciation_schedules
        ALTER COLUMN schedule_status DROP DEFAULT,
        ALTER COLUMN schedule_status TYPE assets_schedulestatus
        USING CASE schedule_status::text
            WHEN 'PLANNED' THEN 'PLANNED'::assets_schedulestatus
            WHEN 'POSTED' THEN 'POSTED'::assets_schedulestatus
            WHEN 'REVERSED' THEN 'REVERSED'::assets_schedulestatus
            WHEN 'ADJUSTED' THEN 'ADJUSTED'::assets_schedulestatus
            ELSE 'PLANNED'::assets_schedulestatus
        END,
        ALTER COLUMN schedule_status SET DEFAULT 'PLANNED'::assets_schedulestatus;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE fa_depreciation_schedules
        ALTER COLUMN schedule_status DROP DEFAULT,
        ALTER COLUMN schedule_status TYPE schedulestatus
        USING CASE schedule_status::text
            WHEN 'PLANNED' THEN 'PLANNED'::schedulestatus
            ELSE 'COMPLETED'::schedulestatus
        END,
        ALTER COLUMN schedule_status SET DEFAULT 'PLANNED'::schedulestatus;
        """
    )
