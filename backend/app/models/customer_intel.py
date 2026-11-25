"""M45 customer intelligence: buyer intent (T004), churn model (T005), health score (T006).

Scores are computed from first-party ERP/CRM data (orders, invoices, tickets, NPS, e-mail engagement, quote views,
consented website visits). Only settings, trained model parameters, alerts and daily health snapshots are stored.
"""
import uuid

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CISetting(Base):
    """Configurable weights/thresholds per area ("intent", "health", "churn"); defaults live in the service."""
    __tablename__ = "ci_settings"

    key        = Column(String(20), primary_key=True)
    value      = Column(JSON, nullable=False)
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CIModel(Base):
    """A locally trained churn model (logistic regression on synthetic or real history) with its validation metrics."""
    __tablename__ = "ci_models"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind        = Column(String(10), nullable=False, default="CHURN")
    params      = Column(JSON, nullable=False)        # features, mean, std, coef, intercept
    metrics     = Column(JSON, nullable=False)        # auc, brier, calibration, baseline, n_train, n_valid, split date
    status      = Column(String(10), nullable=False, default="ACTIVE")   # ACTIVE | RETIRED
    trained_by  = Column(String(100), nullable=True)
    trained_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CIAlert(Base):
    """Intent spike / low health / high churn risk for one customer; one per kind and customer per cool-down window."""
    __tablename__ = "ci_alerts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind            = Column(String(10), nullable=False)          # INTENT | HEALTH | CHURN
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    score           = Column(Float, nullable=False)
    reasons         = Column(JSON, nullable=False)
    owner_user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)


class CIHealthSnapshot(Base):
    __tablename__ = "ci_health_snapshots"
    __table_args__ = (UniqueConstraint("customer_id", "day", name="uq_ci_health_snapshot_day"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    day         = Column(Date, nullable=False)
    score       = Column(Integer, nullable=True)                  # NULL = not enough data
    components  = Column(JSON, nullable=False)
