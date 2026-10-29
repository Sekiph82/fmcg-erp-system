"""link quality gates to required QC specifications

Revision ID: 20261029_0028
Revises: 20261029_0027
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261029_0028"
down_revision = "20261029_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_gate_required_templates",
        sa.Column("gate_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qc_template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_definition_id"], ["quality_gate_definitions.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["qc_template_id"], ["qc_templates.id"], ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("gate_definition_id", "qc_template_id"),
    )
    op.create_index(
        "ix_quality_gate_required_templates_qc_template_id",
        "quality_gate_required_templates",
        ["qc_template_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quality_gate_required_templates_qc_template_id",
        table_name="quality_gate_required_templates",
    )
    op.drop_table("quality_gate_required_templates")
