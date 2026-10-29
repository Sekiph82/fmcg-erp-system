"""persist append-only quality gate evaluation history

Revision ID: 20261029_0033
Revises: 20261029_0032
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20261029_0033"
down_revision = "20261029_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_gate_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("evaluation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_module", sa.String(50), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("gate_definition_id", UUID(as_uuid=True), nullable=True),
        sa.Column("gate_code", sa.String(50), nullable=False),
        sa.Column("gate_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=False),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("business_id", UUID(as_uuid=True), nullable=False),
        sa.Column("required_template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("required_template_name", sa.String(200), nullable=True),
        sa.Column("inspection_id", UUID(as_uuid=True), nullable=True),
        sa.Column("waiver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("evaluated_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "result IN ('PASS', 'BLOCKED', 'WAIVED', 'NO_GATE')",
            name="ck_quality_gate_audit_events_result",
        ),
        sa.CheckConstraint(
            "scope_type IN ('GRN_LINE', 'PRODUCTION_ORDER', 'LOT', 'SHIPMENT_LINE', 'QC_INSPECTION', 'SHIPMENT')",
            name="ck_quality_gate_audit_events_scope_type",
        ),
        sa.CheckConstraint("gate_version >= 0", name="ck_quality_gate_audit_events_gate_version"),
    )
    op.create_index(
        "ix_quality_gate_audit_events_scope_time", "quality_gate_audit_events",
        ["scope_type", "scope_id", "evaluated_at"],
    )
    op.create_index(
        "ix_quality_gate_audit_events_business_time", "quality_gate_audit_events",
        ["business_type", "business_id", "evaluated_at"],
    )
    op.create_index(
        "ix_quality_gate_audit_events_gate_time", "quality_gate_audit_events",
        ["gate_code", "gate_version", "evaluated_at"],
    )
    op.create_index(
        "ix_quality_gate_audit_events_evaluation_id", "quality_gate_audit_events", ["evaluation_id"]
    )
    op.create_index(
        "ix_quality_gate_audit_events_evaluated_at", "quality_gate_audit_events", ["evaluated_at"]
    )
    op.execute("""
        CREATE FUNCTION prevent_quality_gate_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'quality_gate_audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_quality_gate_audit_events_append_only
        BEFORE UPDATE OR DELETE ON quality_gate_audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_quality_gate_audit_event_mutation()
    """)
    op.execute("""
        CREATE TRIGGER trg_quality_gate_audit_events_no_truncate
        BEFORE TRUNCATE ON quality_gate_audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION prevent_quality_gate_audit_event_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_quality_gate_audit_events_append_only ON quality_gate_audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_quality_gate_audit_events_no_truncate ON quality_gate_audit_events")
    op.execute("DROP FUNCTION IF EXISTS prevent_quality_gate_audit_event_mutation()")
    op.drop_index("ix_quality_gate_audit_events_evaluated_at", table_name="quality_gate_audit_events")
    op.drop_index("ix_quality_gate_audit_events_evaluation_id", table_name="quality_gate_audit_events")
    op.drop_index("ix_quality_gate_audit_events_gate_time", table_name="quality_gate_audit_events")
    op.drop_index("ix_quality_gate_audit_events_business_time", table_name="quality_gate_audit_events")
    op.drop_index("ix_quality_gate_audit_events_scope_time", table_name="quality_gate_audit_events")
    op.drop_table("quality_gate_audit_events")
