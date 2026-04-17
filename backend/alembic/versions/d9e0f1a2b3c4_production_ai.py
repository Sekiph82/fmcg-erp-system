"""production_ai_intelligence

Creates 4 AI intelligence tables for the Production Module:

  ai_predictions    – Agent 1: completion time, output qty, delay risk per order
  ai_anomalies      – Agent 2: detected deviations and alerts
  ai_suggestions    – Agent 3/4/5: optimization, recipe, cost suggestions
  ai_model_metrics  – Per-agent accuracy tracking over time

Revision ID: d9e0f1a2b3c4
Revises:     c8d9e0f1a2b3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision       = "d9e0f1a2b3c4"
down_revision  = "c8d9e0f1a2b3"
branch_labels  = None
depends_on     = None

# Enum names (must match SQLAlchemy model exactly)
agent_type_enum     = sa.Enum("PREDICTION","ANOMALY","OPTIMIZATION","RECIPE","COST","MAINTENANCE", name="agenttype")
anomaly_sev_enum    = sa.Enum("low","medium","high","critical",                                     name="anomalyseverity")
anomaly_type_enum   = sa.Enum("material_overuse","material_underuse","efficiency_drop",
                               "excessive_downtime","waste_spike","qc_fail_spike",
                               "cost_overrun","cycle_time_deviation",                               name="anomalytype")
suggestion_type_enum = sa.Enum("batch_optimization","scheduling","resource_allocation",
                                "recipe_adjustment","material_substitution",
                                "cost_reduction","maintenance_action",                             name="suggestiontype")
suggestion_status_enum = sa.Enum("pending","accepted","rejected","applied","expired",              name="suggestionstatus")


def upgrade() -> None:
    # ── ai_predictions ────────────────────────────────────────────────────────
    agent_type_enum.create(op.get_bind(), checkfirst=True)
    anomaly_sev_enum.create(op.get_bind(), checkfirst=True)
    anomaly_type_enum.create(op.get_bind(), checkfirst=True)
    suggestion_type_enum.create(op.get_bind(), checkfirst=True)
    suggestion_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_predictions",
        sa.Column("id",                      postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prediction_no",           sa.String(50),  nullable=False, unique=True),
        sa.Column("production_order_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type",              agent_type_enum,  nullable=False),
        sa.Column("predicted_completion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("predicted_output_qty",    sa.Numeric(14, 3), nullable=True),
        sa.Column("predicted_output_uom",    sa.String(20),  nullable=True),
        sa.Column("delay_risk_pct",          sa.Numeric(6, 2),  nullable=True),
        sa.Column("efficiency_forecast_pct", sa.Numeric(6, 2),  nullable=True),
        sa.Column("historical_sample_size",  sa.Integer,    nullable=True),
        sa.Column("confidence_score",        sa.Numeric(5, 4), nullable=False),
        sa.Column("explanation",             sa.Text,       nullable=False),
        sa.Column("risk_level",              sa.String(20), nullable=True),
        sa.Column("actual_completion_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_output_qty",       sa.Numeric(14, 3), nullable=True),
        sa.Column("was_delayed",             sa.Boolean,    nullable=True),
        sa.Column("prediction_error_pct",    sa.Numeric(8, 3),  nullable=True),
        sa.Column("created_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",              sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_pred_order",   "ai_predictions", ["production_order_id"])
    op.create_index("ix_ai_pred_created", "ai_predictions", ["created_at"])

    # ── ai_anomalies ──────────────────────────────────────────────────────────
    op.create_table(
        "ai_anomalies",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("anomaly_no",          sa.String(50),  nullable=False, unique=True),
        sa.Column("production_order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_center_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("work_centers.id",      ondelete="SET NULL"), nullable=True),
        sa.Column("anomaly_type",        anomaly_type_enum, nullable=False),
        sa.Column("severity",            anomaly_sev_enum,  nullable=False),
        sa.Column("affected_area",       sa.String(255), nullable=True),
        sa.Column("affected_material",   sa.String(255), nullable=True),
        sa.Column("deviation_pct",       sa.Numeric(8, 3),  nullable=True),
        sa.Column("actual_value",        sa.Numeric(14, 4), nullable=True),
        sa.Column("expected_value",      sa.Numeric(14, 4), nullable=True),
        sa.Column("baseline_source",     sa.String(255), nullable=True),
        sa.Column("confidence_score",    sa.Numeric(5, 4),  nullable=False),
        sa.Column("explanation",         sa.Text,        nullable=False),
        sa.Column("is_resolved",         sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("resolved_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by",         sa.String(255), nullable=True),
        sa.Column("resolution_notes",    sa.Text,        nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_anom_order",    "ai_anomalies", ["production_order_id"])
    op.create_index("ix_ai_anom_type",     "ai_anomalies", ["anomaly_type"])
    op.create_index("ix_ai_anom_severity", "ai_anomalies", ["severity"])
    op.create_index("ix_ai_anom_resolved", "ai_anomalies", ["is_resolved"])
    op.create_index("ix_ai_anom_created",  "ai_anomalies", ["created_at"])

    # ── ai_suggestions ────────────────────────────────────────────────────────
    op.create_table(
        "ai_suggestions",
        sa.Column("id",                          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("suggestion_no",               sa.String(50),  nullable=False, unique=True),
        sa.Column("agent_type",                  agent_type_enum,      nullable=False),
        sa.Column("suggestion_type",             suggestion_type_enum, nullable=False),
        sa.Column("production_order_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id",                  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id",   ondelete="SET NULL"), nullable=True),
        sa.Column("recipe_id",                   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("recipes.id",    ondelete="SET NULL"), nullable=True),
        sa.Column("work_center_id",              postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("issue_detected",              sa.Text,        nullable=False),
        sa.Column("suggested_change",            sa.Text,        nullable=False),
        sa.Column("current_value",               sa.Numeric(18, 4), nullable=True),
        sa.Column("recommended_value",           sa.Numeric(18, 4), nullable=True),
        sa.Column("value_unit",                  sa.String(50),  nullable=True),
        sa.Column("expected_efficiency_gain_pct",sa.Numeric(8, 3),  nullable=True),
        sa.Column("expected_cost_reduction_pct", sa.Numeric(8, 3),  nullable=True),
        sa.Column("expected_quality_improvement",sa.Text,        nullable=True),
        sa.Column("estimated_kes_saving",        sa.Numeric(18, 4), nullable=True),
        sa.Column("confidence_score",            sa.Numeric(5, 4),  nullable=False),
        sa.Column("explanation",                 sa.Text,        nullable=False),
        sa.Column("supporting_data",             sa.Text,        nullable=True),
        sa.Column("status",                      suggestion_status_enum, nullable=False),
        sa.Column("expires_at",                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("actioned_by",                 sa.String(255), nullable=True),
        sa.Column("actioned_at",                 sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason",            sa.Text,        nullable=True),
        sa.Column("created_at",                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",                  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_sug_type",    "ai_suggestions", ["suggestion_type"])
    op.create_index("ix_ai_sug_status",  "ai_suggestions", ["status"])
    op.create_index("ix_ai_sug_product", "ai_suggestions", ["product_id"])
    op.create_index("ix_ai_sug_recipe",  "ai_suggestions", ["recipe_id"])

    # ── ai_model_metrics ──────────────────────────────────────────────────────
    op.create_table(
        "ai_model_metrics",
        sa.Column("id",                       postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type",               agent_type_enum, nullable=False),
        sa.Column("metric_date",              sa.Date,         nullable=False),
        sa.Column("predictions_made",         sa.Integer,      nullable=False, server_default="0"),
        sa.Column("anomalies_detected",       sa.Integer,      nullable=False, server_default="0"),
        sa.Column("suggestions_generated",    sa.Integer,      nullable=False, server_default="0"),
        sa.Column("suggestions_accepted",     sa.Integer,      nullable=False, server_default="0"),
        sa.Column("suggestions_rejected",     sa.Integer,      nullable=False, server_default="0"),
        sa.Column("avg_completion_error_pct", sa.Numeric(8, 3), nullable=True),
        sa.Column("avg_qty_error_pct",        sa.Numeric(8, 3), nullable=True),
        sa.Column("delay_precision",          sa.Numeric(5, 4), nullable=True),
        sa.Column("delay_recall",             sa.Numeric(5, 4), nullable=True),
        sa.Column("anomaly_true_positives",   sa.Integer,      nullable=True),
        sa.Column("anomaly_false_positives",  sa.Integer,      nullable=True),
        sa.Column("agent_accuracy_score",     sa.Numeric(5, 4), nullable=True),
        sa.Column("notes",                    sa.Text,         nullable=True),
        sa.Column("created_at",               sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",               sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("agent_type", "metric_date", name="uq_ai_metrics_agent_date"),
    )
    op.create_index("ix_ai_metrics_date", "ai_model_metrics", ["metric_date"])


def downgrade() -> None:
    op.drop_table("ai_model_metrics")
    op.drop_table("ai_suggestions")
    op.drop_table("ai_anomalies")
    op.drop_table("ai_predictions")

    suggestion_status_enum.drop(op.get_bind(), checkfirst=True)
    suggestion_type_enum.drop(op.get_bind(), checkfirst=True)
    anomaly_type_enum.drop(op.get_bind(), checkfirst=True)
    anomaly_sev_enum.drop(op.get_bind(), checkfirst=True)
    agent_type_enum.drop(op.get_bind(), checkfirst=True)
