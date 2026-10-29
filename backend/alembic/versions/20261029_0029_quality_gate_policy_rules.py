"""add quality gate severity, mandatory, and waiver safeguards

Revision ID: 20261029_0029
Revises: 20261029_0028
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0029"
down_revision = "20261029_0028"
branch_labels = None
depends_on = None


def _add_check_if_missing(name: str, expression: str) -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint "
            "WHERE conname = :name AND conrelid = to_regclass(:table_name))"
        ),
        {"name": name, "table_name": "quality_gate_definitions"},
    ).scalar_one()
    if not exists:
        op.create_check_constraint(name, "quality_gate_definitions", expression)


def upgrade() -> None:
    op.add_column(
        "quality_gate_definitions",
        sa.Column("severity", sa.String(length=16), server_default="MEDIUM", nullable=False),
    )
    op.add_column(
        "quality_gate_definitions",
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "quality_gate_definitions",
        sa.Column("waiver_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "quality_gate_definitions",
        sa.Column("waiver_reason_required", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "quality_gate_definitions",
        sa.Column("waiver_approval_required", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    _add_check_if_missing(
        "ck_quality_gate_definitions_severity",
        "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
    )
    _add_check_if_missing(
        "ck_quality_gate_definitions_critical_policy",
        "severity != 'CRITICAL' OR (is_mandatory AND NOT waiver_allowed)",
    )
    _add_check_if_missing(
        "ck_quality_gate_definitions_waiver_safeguards",
        "NOT waiver_allowed OR (waiver_reason_required AND waiver_approval_required)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_quality_gate_definitions_waiver_safeguards", "quality_gate_definitions", type_="check"
    )
    op.drop_constraint(
        "ck_quality_gate_definitions_critical_policy", "quality_gate_definitions", type_="check"
    )
    op.drop_constraint("ck_quality_gate_definitions_severity", "quality_gate_definitions", type_="check")
    op.drop_column("quality_gate_definitions", "waiver_approval_required")
    op.drop_column("quality_gate_definitions", "waiver_reason_required")
    op.drop_column("quality_gate_definitions", "waiver_allowed")
    op.drop_column("quality_gate_definitions", "is_mandatory")
    op.drop_column("quality_gate_definitions", "severity")
