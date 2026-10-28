"""add batch-specific BOM substitution approvals

Revision ID: 20261028_0022
Revises: 20261028_0021
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261028_0022"
down_revision = "20261028_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bom_substitution_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("substitute_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy", sa.String(30), nullable=False),
        sa.Column("target_qty", sa.Numeric(14, 4), nullable=False),
        sa.Column("substitute_qty", sa.Numeric(14, 4), nullable=False),
        sa.Column("context_reference", sa.String(120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("shortage_evidence_reference", sa.String(255), nullable=True),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requester_email", sa.String(255), nullable=False),
        sa.Column("requester_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_qty > 0", name="ck_bom_substitution_request_target_qty_positive"),
        sa.CheckConstraint("substitute_qty > 0", name="ck_bom_substitution_request_substitute_qty_positive"),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED')", name="ck_bom_substitution_request_status"),
        sa.ForeignKeyConstraint(["bom_line_id"], ["advanced_bom_lines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bom_id"], ["advanced_boms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["substitute_id"], ["bom_substitutes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bom_substitution_requests_bom_line_id", "bom_substitution_requests", ["bom_line_id"])
    op.create_index("ix_bom_substitution_requests_bom_id", "bom_substitution_requests", ["bom_id"])
    op.create_index("ix_bom_substitution_requests_substitute_id", "bom_substitution_requests", ["substitute_id"])
    op.create_index("ix_bom_substitution_requests_status", "bom_substitution_requests", ["status"])

    op.create_table(
        "bom_substitution_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_role", sa.String(20), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("actor_name", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("approver_role IN ('PLANNER', 'QUALITY')", name="ck_bom_substitution_decision_role"),
        sa.CheckConstraint("decision IN ('APPROVED', 'REJECTED')", name="ck_bom_substitution_decision_value"),
        sa.ForeignKeyConstraint(["request_id"], ["bom_substitution_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "approver_role", name="uq_bom_substitution_decision_role"),
    )
    op.create_index("ix_bom_substitution_decisions_request_id", "bom_substitution_decisions", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_bom_substitution_decisions_request_id", table_name="bom_substitution_decisions")
    op.drop_table("bom_substitution_decisions")
    op.drop_index("ix_bom_substitution_requests_status", table_name="bom_substitution_requests")
    op.drop_index("ix_bom_substitution_requests_substitute_id", table_name="bom_substitution_requests")
    op.drop_index("ix_bom_substitution_requests_bom_id", table_name="bom_substitution_requests")
    op.drop_index("ix_bom_substitution_requests_bom_line_id", table_name="bom_substitution_requests")
    op.drop_table("bom_substitution_requests")
