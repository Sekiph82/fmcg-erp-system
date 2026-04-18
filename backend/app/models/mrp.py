import uuid
import enum
from datetime import date
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class ForecastModelType(str, enum.Enum):
    MOVING_AVG          = "MOVING_AVG"
    WEIGHTED_MOVING_AVG = "WEIGHTED_MOVING_AVG"
    EXPONENTIAL_SMOOTHING = "EXPONENTIAL_SMOOTHING"
    SEASONAL            = "SEASONAL"
    PROPHET             = "PROPHET"   # AI-ready stub


class PeriodType(str, enum.Enum):
    DAILY   = "DAILY"
    WEEKLY  = "WEEKLY"
    MONTHLY = "MONTHLY"


class ForecastStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    APPROVED = "APPROVED"
    LOCKED   = "LOCKED"


class MRPRunStatus(str, enum.Enum):
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"


class MRPTrigger(str, enum.Enum):
    MANUAL    = "MANUAL"
    SCHEDULED = "SCHEDULED"
    AI        = "AI"


class SuggestionType(str, enum.Enum):
    PRODUCTION   = "PRODUCTION"
    PROCUREMENT  = "PROCUREMENT"


class SuggestionStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    CONVERTED = "CONVERTED"


# ── Demand Forecast ──────────────────────────────────────────────────────────

class DemandForecast(Base, TimestampMixin):
    __tablename__ = "demand_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "period_type", "start_date", "forecast_model",
            name="uq_demand_forecast",
        ),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"),
                             nullable=False, index=True)
    warehouse_id    = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"),
                             nullable=True, index=True)
    forecast_model  = Column(Enum(ForecastModelType), nullable=False,
                             default=ForecastModelType.EXPONENTIAL_SMOOTHING)
    period_type     = Column(Enum(PeriodType), nullable=False, default=PeriodType.MONTHLY)
    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=False)
    status          = Column(Enum(ForecastStatus), nullable=False, default=ForecastStatus.DRAFT)
    is_approved     = Column(Boolean, default=False, nullable=False)
    model_params    = Column(JSON, nullable=True)       # {"alpha": 0.3, "periods": 6, ...}
    mape            = Column(Numeric(7, 3), nullable=True)   # Mean Absolute Percentage Error %
    notes           = Column(Text, nullable=True)
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at     = Column(DateTime(timezone=True), nullable=True)

    product   = relationship("Product")
    warehouse = relationship("Warehouse")
    creator   = relationship("User", foreign_keys=[created_by])
    approver  = relationship("User", foreign_keys=[approved_by])
    lines     = relationship(
        "DemandForecastLine",
        back_populates="forecast",
        cascade="all, delete-orphan",
        order_by="DemandForecastLine.period_date",
    )


class DemandForecastLine(Base, TimestampMixin):
    __tablename__ = "demand_forecast_lines"
    __table_args__ = (
        UniqueConstraint("forecast_id", "period_date", name="uq_forecast_line_period"),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_id  = Column(UUID(as_uuid=True), ForeignKey("demand_forecasts.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    period_date  = Column(Date, nullable=False, index=True)
    forecast_qty = Column(Numeric(14, 3), nullable=False, default=0)
    adjusted_qty = Column(Numeric(14, 3), nullable=True)   # manual override
    actual_qty   = Column(Numeric(14, 3), nullable=True)   # back-filled from actuals
    error_pct    = Column(Numeric(7, 3), nullable=True)    # abs % error vs actual
    is_spike     = Column(Boolean, default=False, nullable=False)   # demand spike detected
    is_outlier   = Column(Boolean, default=False, nullable=False)   # statistical outlier
    notes        = Column(Text, nullable=True)

    forecast = relationship("DemandForecast", back_populates="lines")


# ── MRP Run ──────────────────────────────────────────────────────────────────

class MRPRun(Base, TimestampMixin):
    __tablename__ = "mrp_runs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_no                = Column(String(50), unique=True, nullable=False, index=True)
    run_date              = Column(Date, nullable=False)
    planning_horizon_days = Column(Integer, nullable=False, default=90)
    status                = Column(Enum(MRPRunStatus), nullable=False, default=MRPRunStatus.QUEUED)
    trigger               = Column(Enum(MRPTrigger), nullable=False, default=MRPTrigger.MANUAL)
    include_forecast      = Column(Boolean, default=True, nullable=False)
    include_safety_stock  = Column(Boolean, default=True, nullable=False)
    warehouse_id          = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"),
                                   nullable=True)
    error_message         = Column(Text, nullable=True)
    product_count         = Column(Integer, nullable=True)
    shortage_count        = Column(Integer, nullable=True)
    suggestion_count      = Column(Integer, nullable=True)
    started_at            = Column(DateTime(timezone=True), nullable=True)
    completed_at          = Column(DateTime(timezone=True), nullable=True)
    triggered_by_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                                   nullable=True)
    notes                 = Column(Text, nullable=True)

    triggered_by = relationship("User")
    warehouse    = relationship("Warehouse")
    results      = relationship("MRPResult", back_populates="run", cascade="all, delete-orphan")
    suggestions  = relationship("MRPSuggestion", back_populates="run", cascade="all, delete-orphan")


# ── MRP Result (one row per product per run) ─────────────────────────────────

class MRPResult(Base, TimestampMixin):
    __tablename__ = "mrp_results"
    __table_args__ = (
        UniqueConstraint("run_id", "product_id", name="uq_mrp_result"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id     = Column(UUID(as_uuid=True), ForeignKey("mrp_runs.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"),
                        nullable=False, index=True)

    # Demand breakdown
    so_demand_qty       = Column(Numeric(14, 3), default=0, nullable=False)
    forecast_demand_qty = Column(Numeric(14, 3), default=0, nullable=False)
    safety_stock_qty    = Column(Numeric(14, 3), default=0, nullable=False)
    gross_demand_qty    = Column(Numeric(14, 3), default=0, nullable=False)

    # Supply breakdown
    stock_on_hand_qty  = Column(Numeric(14, 3), default=0, nullable=False)
    incoming_po_qty    = Column(Numeric(14, 3), default=0, nullable=False)
    incoming_prod_qty  = Column(Numeric(14, 3), default=0, nullable=False)
    total_supply_qty   = Column(Numeric(14, 3), default=0, nullable=False)

    # Net
    net_requirement_qty     = Column(Numeric(14, 3), default=0, nullable=False)
    shortage_flag           = Column(Boolean, default=False, nullable=False)
    suggested_production_qty  = Column(Numeric(14, 3), nullable=True)
    suggested_procurement_qty = Column(Numeric(14, 3), nullable=True)

    run     = relationship("MRPRun", back_populates="results")
    product = relationship("Product")


# ── MRP Suggestion ───────────────────────────────────────────────────────────

class MRPSuggestion(Base, TimestampMixin):
    __tablename__ = "mrp_suggestions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id          = Column(UUID(as_uuid=True), ForeignKey("mrp_runs.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    suggestion_type = Column(Enum(SuggestionType), nullable=False)
    status          = Column(Enum(SuggestionStatus), nullable=False, default=SuggestionStatus.DRAFT)

    # What
    product_id  = Column(UUID(as_uuid=True), ForeignKey("products.id",   ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id",  ondelete="RESTRICT"), nullable=True)
    suggested_qty = Column(Numeric(14, 3), nullable=False)
    uom           = Column(String(20), nullable=True)

    # When
    required_date     = Column(Date, nullable=False)
    planned_start_date = Column(Date, nullable=True)

    # Context
    driver_product_id     = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"),
                                    nullable=True)
    net_requirement_qty   = Column(Numeric(14, 3), nullable=True)
    batch_size            = Column(Numeric(14, 3), nullable=True)
    moq                   = Column(Numeric(14, 3), nullable=True)
    preferred_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"),
                                    nullable=True)
    estimated_cost        = Column(Numeric(16, 4), nullable=True)

    # Conversion tracking
    converted_pr_id               = Column(UUID(as_uuid=True),
                                            ForeignKey("purchase_requisitions.id", ondelete="SET NULL"),
                                            nullable=True)
    converted_production_order_id = Column(UUID(as_uuid=True),
                                            ForeignKey("production_orders.id", ondelete="SET NULL"),
                                            nullable=True)

    rejection_reason = Column(Text, nullable=True)
    approved_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at      = Column(DateTime(timezone=True), nullable=True)
    notes            = Column(Text, nullable=True)

    run                = relationship("MRPRun", back_populates="suggestions")
    product            = relationship("Product", foreign_keys=[product_id])
    material           = relationship("Material", foreign_keys=[material_id])
    driver_product     = relationship("Product", foreign_keys=[driver_product_id])
    preferred_supplier = relationship("Supplier")
    approver           = relationship("User")
