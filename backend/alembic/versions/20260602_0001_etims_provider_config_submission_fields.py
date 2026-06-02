"""eTIMS provider config model + submission tracking fields (TASK-005.1A)

Adds:
  - EtimsProviderConfig table (provider/integrator adapter config)
  - New columns to etims_submissions (provider tracking, payload snapshots, timing)
  - New ETimsStatus enum values: DRAFT, READY, RETRY_PENDING, CANCELLED, ERROR
  - Index on etims_submissions.status
  - Index on etims_submissions.provider_reference

Safety:
  - production_execution_allowed defaults to FALSE on all provider config rows
  - is_demo_mode defaults to TRUE on all provider config rows
  - Additive only — no existing columns dropped or renamed

Revision ID: 20260602_0001
Revises: 20260518_0001
Create Date: 2026-06-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260602_0001"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend ETimsStatus enum ────────────────────────────────────────────
    # ALTER TYPE ADD VALUE requires PostgreSQL 9.1+; IF NOT EXISTS requires 9.3+.
    # In PostgreSQL < 12 this statement cannot run inside a transaction.
    # The squashed_baseline (20260517_0000) creates the type as "etimsstatus".
    # If the DB is PG 12+ (recommended), this runs safely within the transaction.
    new_etims_values = ("DRAFT", "READY", "RETRY_PENDING", "CANCELLED", "ERROR")
    for value in new_etims_values:
        op.execute(sa.text(f"ALTER TYPE etimsstatus ADD VALUE IF NOT EXISTS '{value}'"))

    # ── 2. Add new columns to etims_submissions ───────────────────────────────
    op.add_column("etims_submissions",
        sa.Column("provider_name", sa.String(100), nullable=True))
    op.add_column("etims_submissions",
        sa.Column("provider_reference", sa.String(200), nullable=True))
    op.add_column("etims_submissions",
        sa.Column("environment", sa.String(50), nullable=True))
    op.add_column("etims_submissions",
        sa.Column("request_payload", sa.JSON, nullable=True))
    op.add_column("etims_submissions",
        sa.Column("response_payload", sa.JSON, nullable=True))
    op.add_column("etims_submissions",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("etims_submissions",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("etims_submissions",
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("etims_submissions",
        sa.Column("error_code", sa.String(50), nullable=True))

    # ── 3. Add indexes on etims_submissions ───────────────────────────────────
    op.create_index("ix_etims_submissions_status",
                    "etims_submissions", ["status"], unique=False)
    op.create_index("ix_etims_submissions_provider_reference",
                    "etims_submissions", ["provider_reference"], unique=False)

    # ── 4. Create etims_provider_configs table ────────────────────────────────
    op.create_table(
        "etims_provider_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("branch_id", sa.String(100), nullable=True),
        sa.Column("device_serial", sa.String(100), nullable=True),
        sa.Column("taxpayer_pin", sa.String(50), nullable=True),
        sa.Column("client_id", sa.String(200), nullable=True),
        sa.Column("secret_ref", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_demo_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("production_execution_allowed", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider_name", "environment",
                            name="uq_etims_provider_env"),
    )
    op.create_index("ix_etims_provider_configs_provider_name",
                    "etims_provider_configs", ["provider_name"], unique=False)
    op.create_index("ix_etims_provider_configs_is_active",
                    "etims_provider_configs", ["is_active"], unique=False)


def downgrade() -> None:
    # Drop etims_provider_configs
    op.drop_index("ix_etims_provider_configs_is_active",
                  table_name="etims_provider_configs")
    op.drop_index("ix_etims_provider_configs_provider_name",
                  table_name="etims_provider_configs")
    op.drop_table("etims_provider_configs")

    # Drop indexes on etims_submissions
    op.drop_index("ix_etims_submissions_provider_reference",
                  table_name="etims_submissions")
    op.drop_index("ix_etims_submissions_status",
                  table_name="etims_submissions")

    # Drop new columns from etims_submissions
    for col in ("error_code", "attempt_count", "last_attempt_at", "accepted_at",
                "response_payload", "request_payload", "environment",
                "provider_reference", "provider_name"):
        op.drop_column("etims_submissions", col)

    # NOTE: PostgreSQL does not support removing enum values.
    # The new ETimsStatus values (DRAFT, READY, RETRY_PENDING, CANCELLED, ERROR)
    # cannot be removed from the "etimsstatus" type without recreating it.
    # Leaving enum type unchanged on downgrade — safe as long as no rows use new values.
