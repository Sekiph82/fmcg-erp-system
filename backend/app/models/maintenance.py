import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class AssetStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


class PMFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BIANNUAL = "BIANNUAL"
    ANNUAL = "ANNUAL"


class PMStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    SKIPPED = "SKIPPED"


class BreakdownSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BreakdownStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REPAIR = "IN_REPAIR"
    RESOLVED = "RESOLVED"


class MaintenancePredictionStatus(str, enum.Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    WORK_ORDER_CREATED = "WORK_ORDER_CREATED"
    DISMISSED = "DISMISSED"


class MaintenancePredictionRisk(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Asset Register ─────────────────────────────────────────────────────────────

class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    asset_type = Column(String(100), nullable=True)          # e.g. Mixer, Filler, Conveyor
    line = Column(String(100), nullable=True, index=True)    # production line
    serial_no = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    install_date = Column(Date, nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(Enum(AssetStatus, name="assetstatus"), nullable=False, default=AssetStatus.ACTIVE)
    notes = Column(Text, nullable=True)

    pm_plans = relationship("PMPlan", back_populates="asset", cascade="all, delete-orphan")
    breakdowns = relationship("BreakdownRecord", back_populates="asset", cascade="all, delete-orphan")
    spare_usages = relationship("SparePartUsage", back_populates="asset", cascade="all, delete-orphan")
    predictions = relationship("MaintenancePrediction", back_populates="asset", cascade="all, delete-orphan")


# ── Preventive Maintenance Plans ───────────────────────────────────────────────

class PMPlan(Base, TimestampMixin):
    __tablename__ = "pm_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(Enum(PMFrequency), nullable=False, default=PMFrequency.MONTHLY)
    interval_days = Column(Integer, nullable=True)           # custom interval override
    estimated_duration_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    checklist = Column(Text, nullable=True)                  # newline-separated checklist items
    assigned_to = Column(String(255), nullable=True)         # technician name / team
    last_completed_date = Column(Date, nullable=True)
    next_due_date = Column(Date, nullable=True, index=True)

    asset = relationship("Asset", back_populates="pm_plans")
    work_orders = relationship("PMWorkOrder", back_populates="plan", cascade="all, delete-orphan")


class PMWorkOrder(Base, TimestampMixin):
    __tablename__ = "pm_work_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wo_no = Column(String(50), unique=True, nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("pm_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    status = Column(Enum(PMStatus), nullable=False, default=PMStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    technician = Column(String(255), nullable=True)
    checklist_notes = Column(Text, nullable=True)            # completion notes per item
    completed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    plan = relationship("PMPlan", back_populates="work_orders")
    completed_by = relationship("User")


# ── Breakdown Records ──────────────────────────────────────────────────────────

class BreakdownRecord(Base, TimestampMixin):
    __tablename__ = "breakdown_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    breakdown_no = Column(String(50), unique=True, nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    downtime_minutes = Column(Integer, nullable=True)
    reason = Column(String(500), nullable=False)
    root_cause = Column(Text, nullable=True)
    severity = Column(Enum(BreakdownSeverity), nullable=False, default=BreakdownSeverity.MEDIUM)
    status = Column(Enum(BreakdownStatus), nullable=False, default=BreakdownStatus.OPEN)
    corrective_action = Column(Text, nullable=True)
    reported_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    asset = relationship("Asset", back_populates="breakdowns")
    production_order = relationship("ProductionOrder")
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    spare_usages = relationship("SparePartUsage", back_populates="breakdown", cascade="all, delete-orphan")


# ── Spare Parts Inventory Link ─────────────────────────────────────────────────

class SparePart(Base, TimestampMixin):
    """Spare part master — optionally linked to a Material record."""
    __tablename__ = "spare_parts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    part_no = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(20), nullable=False, default="pcs")
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    current_stock = Column(Numeric(16, 4), nullable=False, default=0)
    reorder_level = Column(Numeric(16, 4), nullable=True)
    unit_cost = Column(Numeric(16, 4), nullable=True)
    supplier = Column(String(255), nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    material = relationship("Material")
    usages = relationship("SparePartUsage", back_populates="spare_part")


class SparePartUsage(Base, TimestampMixin):
    """Records consumption of a spare part for a breakdown or PM work order."""
    __tablename__ = "spare_part_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spare_part_id = Column(UUID(as_uuid=True), ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    breakdown_id = Column(UUID(as_uuid=True), ForeignKey("breakdown_records.id", ondelete="SET NULL"), nullable=True)
    pm_work_order_id = Column(UUID(as_uuid=True), ForeignKey("pm_work_orders.id", ondelete="SET NULL"), nullable=True)
    quantity_used = Column(Numeric(16, 4), nullable=False)
    unit_cost = Column(Numeric(16, 4), nullable=True)
    notes = Column(Text, nullable=True)
    used_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    spare_part = relationship("SparePart", back_populates="usages")
    asset = relationship("Asset", back_populates="spare_usages")
    breakdown = relationship("BreakdownRecord", back_populates="spare_usages")
    pm_work_order = relationship("PMWorkOrder")
    used_by = relationship("User")


# Predictive Maintenance

class MaintenancePrediction(Base, TimestampMixin):
    """Rule-based machine failure prediction from IoT trends and maintenance history."""
    __tablename__ = "maintenance_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id = Column(String(100), nullable=False, index=True)
    machine_name = Column(String(255), nullable=True)
    predicted_failure_date = Column(Date, nullable=False, index=True)
    confidence = Column(Numeric(5, 4), nullable=False, default=0)
    risk_level = Column(Enum(MaintenancePredictionRisk), nullable=False, default=MaintenancePredictionRisk.MEDIUM, index=True)
    failure_mode = Column(String(200), nullable=False)
    recommended_action = Column(Text, nullable=False)
    evidence_summary = Column(Text, nullable=True)
    source_metrics = Column(JSON, nullable=True)
    status = Column(Enum(MaintenancePredictionStatus), nullable=False, default=MaintenancePredictionStatus.OPEN, index=True)
    generated_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    asset = relationship("Asset", back_populates="predictions")
