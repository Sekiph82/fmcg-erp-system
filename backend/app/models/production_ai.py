"""
Production AI Intelligence Layer — Data Models
───────────────────────────────────────────────
Four tables that store the outputs of all AI agents:

  ai_predictions    – Agent 1: completion time, output qty, delay risk
  ai_anomalies      – Agent 2: detected deviations / alerts
  ai_suggestions    – Agent 3/4/5: optimization, recipe, cost suggestions
  ai_model_metrics  – Tracks agent accuracy over time (prediction vs actual)
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class AgentType(str, enum.Enum):
    PREDICTION   = "PREDICTION"
    ANOMALY      = "ANOMALY"
    OPTIMIZATION = "OPTIMIZATION"
    RECIPE       = "RECIPE"
    COST         = "COST"
    MAINTENANCE  = "MAINTENANCE"


class AnomalySeverity(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class AnomalyType(str, enum.Enum):
    MATERIAL_OVERUSE    = "material_overuse"
    MATERIAL_UNDERUSE   = "material_underuse"
    EFFICIENCY_DROP     = "efficiency_drop"
    EXCESSIVE_DOWNTIME  = "excessive_downtime"
    WASTE_SPIKE         = "waste_spike"
    QC_FAIL_SPIKE       = "qc_fail_spike"
    COST_OVERRUN        = "cost_overrun"
    CYCLE_TIME_DEVIATION = "cycle_time_deviation"


class SuggestionType(str, enum.Enum):
    BATCH_OPTIMIZATION  = "batch_optimization"
    SCHEDULING          = "scheduling"
    RESOURCE_ALLOCATION = "resource_allocation"
    RECIPE_ADJUSTMENT   = "recipe_adjustment"
    MATERIAL_SUBSTITUTION = "material_substitution"
    COST_REDUCTION      = "cost_reduction"
    MAINTENANCE_ACTION  = "maintenance_action"


class SuggestionStatus(str, enum.Enum):
    PENDING  = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED  = "applied"
    EXPIRED  = "expired"


# ── 1. AI Predictions ─────────────────────────────────────────────────────────

class ProductionPrediction(Base, TimestampMixin):
    """
    Agent 1 — Production Prediction Engine output.
    One record per prediction run per production order.
    Multiple records for the same order accumulate over time (track history).
    """
    __tablename__ = "production_ai_predictions"
    __table_args__ = (
        Index("ix_ai_pred_order",   "production_order_id"),
        Index("ix_ai_pred_created", "created_at"),
    )

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_no            = Column(String(50), unique=True, nullable=False, index=True)

    # Source
    production_order_id      = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False)
    agent_type               = Column(Enum(AgentType), nullable=False, default=AgentType.PREDICTION)

    # Prediction outputs
    predicted_completion_at  = Column(DateTime(timezone=True), nullable=True)
    predicted_output_qty     = Column(Numeric(14, 3), nullable=True)
    predicted_output_uom     = Column(String(20), nullable=True, default="KG")
    delay_risk_pct           = Column(Numeric(6, 2), nullable=True)    # 0–100
    efficiency_forecast_pct  = Column(Numeric(6, 2), nullable=True)    # predicted efficiency
    historical_sample_size   = Column(Integer, nullable=True)          # how many past orders used

    # Quality metrics
    confidence_score         = Column(Numeric(5, 4), nullable=False, default=0.5)  # 0–1
    explanation              = Column(Text, nullable=False)

    # Status tracking (GREEN / YELLOW / RED)
    risk_level               = Column(String(20), nullable=True)       # GREEN / YELLOW / RED

    # Outcome tracking (filled after order completes for accuracy measurement)
    actual_completion_at     = Column(DateTime(timezone=True), nullable=True)
    actual_output_qty        = Column(Numeric(14, 3), nullable=True)
    was_delayed              = Column(Boolean, nullable=True)
    prediction_error_pct     = Column(Numeric(8, 3), nullable=True)   # |predicted-actual|/actual*100

    production_order         = relationship("ProductionOrder")


# ── 2. AI Anomalies ───────────────────────────────────────────────────────────

class ProductionAnomaly(Base, TimestampMixin):
    """
    Agent 2 — Anomaly Detection Engine output.
    One record per detected anomaly event.
    """
    __tablename__ = "production_ai_anomalies"
    __table_args__ = (
        Index("ix_ai_anom_order",    "production_order_id"),
        Index("ix_ai_anom_type",     "anomaly_type"),
        Index("ix_ai_anom_severity", "severity"),
        Index("ix_ai_anom_resolved", "is_resolved"),
        Index("ix_ai_anom_created",  "created_at"),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anomaly_no           = Column(String(50), unique=True, nullable=False, index=True)

    # Source
    production_order_id  = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    work_center_id       = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)

    # Anomaly details
    anomaly_type         = Column(Enum(AnomalyType), nullable=False)
    severity             = Column(Enum(AnomalySeverity), nullable=False, default=AnomalySeverity.MEDIUM)
    affected_area        = Column(String(255), nullable=True)
    affected_material    = Column(String(255), nullable=True)
    deviation_pct        = Column(Numeric(8, 3), nullable=True)
    actual_value         = Column(Numeric(14, 4), nullable=True)
    expected_value       = Column(Numeric(14, 4), nullable=True)
    baseline_source      = Column(String(255), nullable=True)   # e.g. "last 10 similar orders"

    # AI quality
    confidence_score     = Column(Numeric(5, 4), nullable=False, default=0.7)
    explanation          = Column(Text, nullable=False)

    # Resolution
    is_resolved          = Column(Boolean, nullable=False, default=False)
    resolved_at          = Column(DateTime(timezone=True), nullable=True)
    resolved_by          = Column(String(255), nullable=True)
    resolution_notes     = Column(Text, nullable=True)

    production_order     = relationship("ProductionOrder")
    work_center          = relationship("WorkCenter")


# ── 3. AI Suggestions ─────────────────────────────────────────────────────────

class ProductionSuggestion(Base, TimestampMixin):
    """
    Agent 3/4/5 — Optimization, Recipe Improvement, Cost Optimization outputs.
    Users can accept or reject suggestions.
    """
    __tablename__ = "production_ai_suggestions"
    __table_args__ = (
        Index("ix_ai_sug_type",    "suggestion_type"),
        Index("ix_ai_sug_status",  "status"),
        Index("ix_ai_sug_product", "product_id"),
        Index("ix_ai_sug_recipe",  "recipe_id"),
    )

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_no              = Column(String(50), unique=True, nullable=False, index=True)

    # Source
    agent_type                 = Column(Enum(AgentType), nullable=False)
    suggestion_type            = Column(Enum(SuggestionType, name="ai_suggestiontype"), nullable=False)
    production_order_id        = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    product_id                 = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    recipe_id                  = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    work_center_id             = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)

    # Suggestion content
    issue_detected             = Column(Text, nullable=False)
    suggested_change           = Column(Text, nullable=False)
    current_value              = Column(Numeric(18, 4), nullable=True)
    recommended_value          = Column(Numeric(18, 4), nullable=True)
    value_unit                 = Column(String(50), nullable=True)

    # Expected impact
    expected_efficiency_gain_pct = Column(Numeric(8, 3), nullable=True)
    expected_cost_reduction_pct  = Column(Numeric(8, 3), nullable=True)
    expected_quality_improvement = Column(Text, nullable=True)
    estimated_kes_saving         = Column(Numeric(18, 4), nullable=True)

    # AI quality
    confidence_score           = Column(Numeric(5, 4), nullable=False, default=0.7)
    explanation                = Column(Text, nullable=False)
    supporting_data            = Column(Text, nullable=True)   # JSON-encoded context

    # Lifecycle
    status                     = Column(Enum(SuggestionStatus, name="ai_suggestionstatus"), nullable=False, default=SuggestionStatus.PENDING)
    expires_at                 = Column(DateTime(timezone=True), nullable=True)
    actioned_by                = Column(String(255), nullable=True)
    actioned_at                = Column(DateTime(timezone=True), nullable=True)
    rejection_reason           = Column(Text, nullable=True)

    production_order           = relationship("ProductionOrder")
    product                    = relationship("Product")
    recipe                     = relationship("Recipe")
    work_center                = relationship("WorkCenter")


# ── 4. AI Model Metrics ───────────────────────────────────────────────────────

class ProductionAIMetrics(Base, TimestampMixin):
    """
    Tracks per-agent prediction accuracy over time.
    Updated whenever an order completes and actual values are known.
    """
    __tablename__ = "production_ai_model_metrics"
    __table_args__ = (
        UniqueConstraint("agent_type", "metric_date", name="uq_ai_metrics_agent_date"),
        Index("ix_ai_metrics_date", "metric_date"),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type            = Column(Enum(AgentType), nullable=False)
    metric_date           = Column(Date, nullable=False)

    # Volume
    predictions_made      = Column(Integer, nullable=False, default=0)
    anomalies_detected    = Column(Integer, nullable=False, default=0)
    suggestions_generated = Column(Integer, nullable=False, default=0)
    suggestions_accepted  = Column(Integer, nullable=False, default=0)
    suggestions_rejected  = Column(Integer, nullable=False, default=0)

    # Prediction accuracy (Agent 1)
    avg_completion_error_pct = Column(Numeric(8, 3), nullable=True)  # |pred-actual|/actual avg
    avg_qty_error_pct        = Column(Numeric(8, 3), nullable=True)
    delay_precision          = Column(Numeric(5, 4), nullable=True)  # TP/(TP+FP)
    delay_recall             = Column(Numeric(5, 4), nullable=True)  # TP/(TP+FN)

    # Anomaly accuracy (Agent 2)
    anomaly_true_positives   = Column(Integer, nullable=True)
    anomaly_false_positives  = Column(Integer, nullable=True)

    # Overall agent health score
    agent_accuracy_score     = Column(Numeric(5, 4), nullable=True)  # 0–1

    notes                    = Column(Text, nullable=True)
