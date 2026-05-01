from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, Numeric, Date, DateTime,
    Text, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PlanType(str, PyEnum):
    ABC = "abc"
    RANDOM = "random"
    LOCATION = "location"
    ITEM = "item"
    FREQUENCY = "frequency"


class PlanStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ABCClass(str, PyEnum):
    A = "A"
    B = "B"
    C = "C"


class AdjustmentStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"


class CycleCountPlan(Base, TimestampMixin):
    """Scheduling and strategy configuration for cycle counting."""
    __tablename__ = "cc_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan_type = Column(Enum(PlanType), nullable=False)
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT, nullable=False, index=True)
    frequency_days = Column(Integer, nullable=True)           # how often to count (days)
    abc_classes = Column(String(10), nullable=True)           # "A", "AB", "ABC"
    variance_tolerance_pct = Column(Numeric(5, 2), default=2.0, nullable=False)  # auto-approve threshold
    auto_approve_within_tolerance = Column(Boolean, default=True, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    tasks = relationship("CycleCountTask", back_populates="plan", cascade="all, delete-orphan")
    warehouse = relationship("Warehouse")


class CycleCountTask(Base, TimestampMixin):
    """One counting task: one item (or location) to count on a specific date."""
    __tablename__ = "cc_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no = Column(String(50), unique=True, nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("cc_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    abc_class = Column(Enum(ABCClass), nullable=True)
    scheduled_date = Column(Date, nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    plan = relationship("CycleCountPlan", back_populates="tasks")
    entries = relationship("CountEntry", back_populates="task", cascade="all, delete-orphan")
    warehouse = relationship("Warehouse")
    location = relationship("StorageLocation")
    product = relationship("Product")
    material = relationship("Material")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])


class CountEntry(Base, TimestampMixin):
    """Actual count result for one item in one task."""
    __tablename__ = "cc_count_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("cc_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    system_qty = Column(Numeric(14, 3), nullable=False)
    counted_qty = Column(Numeric(14, 3), nullable=False)
    variance_qty = Column(Numeric(14, 3), nullable=False)       # counted - system
    variance_pct = Column(Numeric(8, 4), nullable=True)         # abs(variance) / system * 100
    unit_cost = Column(Numeric(14, 4), nullable=True)
    variance_value = Column(Numeric(16, 4), nullable=True)      # variance_qty * unit_cost
    unit = Column(String(20), default="KG", nullable=False)
    within_tolerance = Column(Boolean, default=False, nullable=False)
    root_cause = Column(Text, nullable=True)
    counted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    counted_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("CycleCountTask", back_populates="entries")
    adjustment = relationship("CountAdjustment", back_populates="entry", uselist=False)
    counted_by = relationship("User", foreign_keys=[counted_by_id])


class CountAdjustment(Base, TimestampMixin):
    """Approval and stock posting record for a count entry variance."""
    __tablename__ = "cc_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("cc_count_entries.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(Enum(AdjustmentStatus), default=AdjustmentStatus.PENDING, nullable=False, index=True)
    adjustment_qty = Column(Numeric(14, 3), nullable=False)     # same as variance_qty
    adjustment_value = Column(Numeric(16, 4), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    posted_flag = Column(Boolean, default=False, nullable=False)
    stock_movement_ref = Column(String(100), nullable=True)     # reference to StockMovement
    notes = Column(Text, nullable=True)

    entry = relationship("CountEntry", back_populates="adjustment")
    approved_by = relationship("User", foreign_keys=[approved_by_id])


class ABCClassification(Base, TimestampMixin):
    """ABC class assignment per item per warehouse."""
    __tablename__ = "cc_abc_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=True)
    abc_class = Column(Enum(ABCClass), nullable=False)
    stock_value = Column(Numeric(16, 4), nullable=True)         # qty * unit_cost
    annual_movements = Column(Integer, nullable=True)           # movement count in last 12 months
    classification_date = Column(Date, nullable=False)
    count_frequency_days = Column(Integer, nullable=True)       # A=7, B=30, C=90
    notes = Column(Text, nullable=True)
