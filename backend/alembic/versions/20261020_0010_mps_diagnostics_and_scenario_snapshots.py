"""Persist reproducible MPS constraint and what-if evidence."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261020_0010"
down_revision = "20261019_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mps_line_diagnostics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mps_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_lines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version", sa.String(40), nullable=False),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("run_id", "line_id", name="uq_mps_diag_run_line"),
    )
    op.create_index("ix_mps_diag_plan_run", "mps_line_diagnostics", ["mps_id", "run_id"])

    op.create_table(
        "mps_scenario_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_whatif_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_version", sa.String(40), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scenario_id", "snapshot_version", name="uq_mps_scenario_snapshot_version"),
    )
    op.create_index("ix_mps_scenario_snapshot_created", "mps_scenario_snapshots", ["scenario_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_mps_scenario_snapshot_created", table_name="mps_scenario_snapshots")
    op.drop_table("mps_scenario_snapshots")
    op.drop_index("ix_mps_diag_plan_run", table_name="mps_line_diagnostics")
    op.drop_table("mps_line_diagnostics")
