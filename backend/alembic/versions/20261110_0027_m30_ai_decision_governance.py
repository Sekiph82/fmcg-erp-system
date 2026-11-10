"""M30: AI decision governance tables (type registry, approval policy, provider config, decision log)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261110_0027"
down_revision = "20261108_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    domain_enum = postgresql.ENUM(
        "PRODUCTION_SCHEDULE", "PROCUREMENT_ORDER", "MAINTENANCE_ACTION",
        "PRICING_ADJUSTMENT", "INVENTORY_REORDER", "QUALITY_DISPOSITION",
        "RESOURCE_ALLOCATION", "GENERAL",
        name="aidecisiondomain", create_type=True,
    )
    risk_tier_enum = postgresql.ENUM(
        "LOW", "MEDIUM", "HIGH", "CRITICAL",
        name="airisktier", create_type=True,
    )
    decision_status_enum = postgresql.ENUM(
        "PENDING_APPROVAL", "APPROVED", "REJECTED", "EXECUTING",
        "EXECUTED", "ROLLED_BACK", "EXPIRED", "AUTO_APPROVED",
        name="aidecisionstatus", create_type=True,
    )
    domain_enum.create(op.get_bind(), checkfirst=True)
    risk_tier_enum.create(op.get_bind(), checkfirst=True)
    decision_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_decision_type_registry",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.Enum("PRODUCTION_SCHEDULE", "PROCUREMENT_ORDER", "MAINTENANCE_ACTION",
                                    "PRICING_ADJUSTMENT", "INVENTORY_REORDER", "QUALITY_DISPOSITION",
                                    "RESOURCE_ALLOCATION", "GENERAL", name="aidecisiondomain"),
                  nullable=False, unique=True),
        sa.Column("default_risk_tier", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="airisktier"),
                  nullable=False, server_default="MEDIUM"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("example_actions", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_decision_type_registry_domain", "ai_decision_type_registry", ["domain"])

    op.create_table(
        "ai_approval_policies",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("risk_tier", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="airisktier"),
                  nullable=False, unique=True),
        sa.Column("requires_human_approval", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("auto_approve_min_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("required_approver_role", sa.String(100), nullable=True),
        sa.Column("approval_timeout_hours", sa.Integer, nullable=True, server_default="24"),
        sa.Column("escalation_hours", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_approval_policies_risk_tier", "ai_approval_policies", ["risk_tier"])

    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.Enum("anthropic", "openai", "gemini", "mock", "auto", name="aiprovider"),
                  nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("capability_flags", sa.JSON, nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("cost_per_1k_input_tokens", sa.Numeric(10, 6), nullable=True),
        sa.Column("cost_per_1k_output_tokens", sa.Numeric(10, 6), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_provider_configs_provider", "ai_provider_configs", ["provider"])

    op.create_table(
        "ai_decision_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("domain", sa.Enum("PRODUCTION_SCHEDULE", "PROCUREMENT_ORDER", "MAINTENANCE_ACTION",
                                    "PRICING_ADJUSTMENT", "INVENTORY_REORDER", "QUALITY_DISPOSITION",
                                    "RESOURCE_ALLOCATION", "GENERAL", name="aidecisiondomain"),
                  nullable=False),
        sa.Column("risk_tier", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="airisktier"),
                  nullable=False),
        sa.Column("provider_config_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("ai_provider_configs.id", ondelete="SET NULL"), nullable=True),
        # Observe → Decide
        sa.Column("observation_payload", sa.JSON, nullable=True),
        sa.Column("constraint_violations", sa.JSON, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("alternatives", sa.JSON, nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("evidence", sa.JSON, nullable=True),
        # Simulate → Approve → Execute
        sa.Column("predicted_kpis", sa.JSON, nullable=True),
        sa.Column("simulation_data", sa.JSON, nullable=True),
        sa.Column("status", sa.Enum("PENDING_APPROVAL", "APPROVED", "REJECTED", "EXECUTING",
                                    "EXECUTED", "ROLLED_BACK", "EXPIRED", "AUTO_APPROVED",
                                    name="aidecisionstatus"),
                  nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("requires_approval", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("approved_by_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("rejected_by_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime, nullable=True),
        sa.Column("execution_result", sa.JSON, nullable=True),
        sa.Column("rolled_back_at", sa.DateTime, nullable=True),
        sa.Column("rollback_reason", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        # Learn
        sa.Column("actual_kpis", sa.JSON, nullable=True),
        sa.Column("acceptance_reason", sa.Text, nullable=True),
        sa.Column("kpi_feedback", sa.JSON, nullable=True),
        sa.Column("outcome_recorded_at", sa.DateTime, nullable=True),
        # Audit
        sa.Column("initiated_by_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_decision_logs_domain", "ai_decision_logs", ["domain"])
    op.create_index("ix_ai_decision_logs_risk_tier", "ai_decision_logs", ["risk_tier"])
    op.create_index("ix_ai_decision_logs_status", "ai_decision_logs", ["status"])
    op.create_index("ix_ai_decision_logs_idempotency_key", "ai_decision_logs", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("ai_decision_logs")
    op.drop_table("ai_provider_configs")
    op.drop_table("ai_approval_policies")
    op.drop_table("ai_decision_type_registry")
    op.execute("DROP TYPE IF EXISTS aidecisionstatus")
    op.execute("DROP TYPE IF EXISTS airisktier")
    op.execute("DROP TYPE IF EXISTS aidecisiondomain")
