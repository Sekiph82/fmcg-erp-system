"""esg_intelligence_gap69

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-05-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
STATUSES = ["DRAFT", "ACTIVE", "UNDER_REVIEW", "ARCHIVED"]


def upgrade() -> None:
    risk_enum = postgresql.ENUM(*RISK_LEVELS, name="suppliersustainabilityrisk")
    status_enum = postgresql.ENUM(*STATUSES, name="suppliersustainabilitystatus")
    risk_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "esg_supplier_sustainability_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("assessment_period_start", sa.Date(), nullable=False),
        sa.Column("assessment_period_end", sa.Date(), nullable=False),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_level", sa.Enum(*RISK_LEVELS, name="suppliersustainabilityrisk"), nullable=False),
        sa.Column("status", sa.Enum(*STATUSES, name="suppliersustainabilitystatus"), nullable=False),
        sa.Column("emissions_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("energy_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("water_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("waste_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("compliance_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("labor_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("renewable_energy_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("has_ghg_disclosure", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_science_based_target", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("iso14001_certified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("wastewater_policy_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("audit_findings", sa.Text(), nullable=True),
        sa.Column("improvement_plan", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assessed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_esg_supplier_sustainability_scores_supplier_id", "esg_supplier_sustainability_scores", ["supplier_id"])
    op.create_index(
        "ix_esg_supplier_sustainability_period",
        "esg_supplier_sustainability_scores",
        ["assessment_period_start", "assessment_period_end"],
    )
    op.create_index(
        "ix_esg_supplier_sustainability_risk",
        "esg_supplier_sustainability_scores",
        ["risk_level", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_esg_supplier_sustainability_risk", table_name="esg_supplier_sustainability_scores")
    op.drop_index("ix_esg_supplier_sustainability_period", table_name="esg_supplier_sustainability_scores")
    op.drop_index("ix_esg_supplier_sustainability_scores_supplier_id", table_name="esg_supplier_sustainability_scores")
    op.drop_table("esg_supplier_sustainability_scores")
    op.execute("DROP TYPE IF EXISTS suppliersustainabilitystatus")
    op.execute("DROP TYPE IF EXISTS suppliersustainabilityrisk")
