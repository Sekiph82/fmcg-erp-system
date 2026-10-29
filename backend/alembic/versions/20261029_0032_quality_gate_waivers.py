"""add auditable quality gate waiver approval records

Revision ID: 20261029_0032
Revises: 20261029_0031
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20261029_0032"
down_revision = "20261029_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_gate_waivers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("waiver_no", sa.String(50), nullable=False),
        sa.Column("gate_definition_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deviation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("requested_by_id", UUID(as_uuid=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gate_definition_id"], ["quality_gate_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deviation_id"], ["qc_deviations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "scope_type IN ('GRN_LINE', 'PRODUCTION_ORDER', 'LOT', 'SHIPMENT_LINE')",
            name="ck_quality_gate_waivers_scope_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'REVOKED')",
            name="ck_quality_gate_waivers_status",
        ),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_quality_gate_waivers_reason_not_blank"),
        sa.CheckConstraint(
            "(status = 'PENDING' AND decided_by_id IS NULL AND decided_at IS NULL AND expires_at IS NULL) "
            "OR (status = 'APPROVED' AND decided_by_id IS NOT NULL AND decided_at IS NOT NULL AND expires_at > decided_at) "
            "OR (status IN ('REJECTED', 'REVOKED') AND decided_by_id IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_quality_gate_waivers_decision_state",
        ),
        sa.CheckConstraint(
            "(status = 'REVOKED' AND revoked_by_id IS NOT NULL AND revoked_at IS NOT NULL) "
            "OR (status != 'REVOKED' AND revoked_by_id IS NULL AND revoked_at IS NULL)",
            name="ck_quality_gate_waivers_revocation_state",
        ),
    )
    op.create_index("ix_quality_gate_waivers_waiver_no", "quality_gate_waivers", ["waiver_no"], unique=True)
    op.create_index(
        "ix_quality_gate_waivers_active_scope",
        "quality_gate_waivers",
        ["gate_definition_id", "scope_type", "scope_id", "status"],
    )
    op.create_index(
        "uq_quality_gate_waivers_pending_scope",
        "quality_gate_waivers",
        ["gate_definition_id", "scope_type", "scope_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index("uq_quality_gate_waivers_pending_scope", table_name="quality_gate_waivers")
    op.drop_index("ix_quality_gate_waivers_active_scope", table_name="quality_gate_waivers")
    op.drop_index("ix_quality_gate_waivers_waiver_no", table_name="quality_gate_waivers")
    op.drop_table("quality_gate_waivers")
