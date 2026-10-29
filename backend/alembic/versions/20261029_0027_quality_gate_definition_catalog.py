"""add configurable quality gate definitions

Revision ID: 20261029_0027
Revises: 20261029_0026
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261029_0027"
down_revision = "20261029_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_gate_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("gate_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_event", sa.String(length=50), nullable=False),
        sa.Column("target_module", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_quality_gate_definitions_code_not_blank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_quality_gate_definitions_name_not_blank"),
        sa.CheckConstraint("length(trim(gate_type)) > 0", name="ck_quality_gate_definitions_type_not_blank"),
        sa.CheckConstraint("length(trim(trigger_event)) > 0", name="ck_quality_gate_definitions_trigger_not_blank"),
        sa.CheckConstraint("length(trim(target_module)) > 0", name="ck_quality_gate_definitions_module_not_blank"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_quality_gate_definitions_code"),
    )
    op.create_index("ix_quality_gate_definitions_gate_type", "quality_gate_definitions", ["gate_type"])
    op.create_index("ix_quality_gate_definitions_trigger_event", "quality_gate_definitions", ["trigger_event"])
    op.create_index("ix_quality_gate_definitions_target_module", "quality_gate_definitions", ["target_module"])


def downgrade() -> None:
    op.drop_index("ix_quality_gate_definitions_target_module", table_name="quality_gate_definitions")
    op.drop_index("ix_quality_gate_definitions_trigger_event", table_name="quality_gate_definitions")
    op.drop_index("ix_quality_gate_definitions_gate_type", table_name="quality_gate_definitions")
    op.drop_table("quality_gate_definitions")
