"""
Advanced Production Module Models
──────────────────────────────────
11 sub-modules for full factory-level operational control:

  1. Work Centers         – machines, lines, capacities
  2. Routing              – step-by-step production flow per product
  3. Work Orders          – executable operations from production orders
  4. Production Schedule  – machine-level scheduling with shift support
  5. Shifts               – shift definitions and assignments
  6. Time Tracking        – actual vs planned time per work order
  7. Downtime Events      – machine downtime with categories
  8. QC Inspections       – inline and final quality checks
  9. Waste & Yield        – expected vs actual consumption + loss calculation
 10. Batch / Lot Tracking – full traceability per production order
 11. Labor Tracking       – operator-level work logging
 12. OEE Records          – daily machine efficiency metrics (stored)
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer, Float,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class WorkCenterType(str, enum.Enum):
    MACHINE  = "MACHINE"
    LINE     = "LINE"
    CELL     = "CELL"
    MANUAL   = "MANUAL"

class WorkCenterStatus(str, enum.Enum):
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    MAINTENANCE = "maintenance"

class WorkOrderStatus(str, enum.Enum):
    PLANNED     = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"
    ON_HOLD     = "on_hold"

class ScheduleStatus(str, enum.Enum):
    PLANNED    = "planned"
    CONFIRMED  = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"

class SchedulePriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"

class DowntimeCategory(str, enum.Enum):
    PLANNED   = "planned"
    UNPLANNED = "unplanned"
    EXTERNAL  = "external"

class QCInspectionType(str, enum.Enum):
    INLINE = "inline"
    FINAL  = "final"
    INPUT  = "input"

class AdvQCStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED  = "pass"
    FAILED  = "fail"
    ON_HOLD = "on_hold"

class QCResultValue(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"

class WasteType(str, enum.Enum):
    MATERIAL  = "MATERIAL"
    PRODUCT   = "PRODUCT"
    PACKAGING = "PACKAGING"

class WasteCategory(str, enum.Enum):
    NORMAL   = "normal"
    ABNORMAL = "abnormal"

class BatchLotStatus(str, enum.Enum):
    QUARANTINE = "quarantine"
    RELEASED   = "released"
    REJECTED   = "rejected"
    CONSUMED   = "consumed"

class LaborActivityType(str, enum.Enum):
    SETUP      = "setup"
    PRODUCTION = "production"
    QC         = "qc"
    CLEANING   = "cleaning"
    OTHER      = "other"

class TimeTrackingCategory(str, enum.Enum):
    PRODUCTIVE = "productive"
    IDLE       = "idle"
    SETUP      = "setup"
    CLEANING   = "cleaning"
    DOWNTIME   = "downtime"


# ── 1. Work Centers ────────────────────────────────────────────────────────────

class WorkCenter(Base, TimestampMixin):
    """Physical machine / production line / manual work cell."""
    __tablename__ = "work_centers"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_center_id      = Column(String(50), unique=True, nullable=False, index=True)
    name                = Column(String(255), nullable=False)
    type                = Column(Enum(WorkCenterType), nullable=False, default=WorkCenterType.MACHINE)
    capacity            = Column(Numeric(14, 3), nullable=True)       # capacity value (e.g. 2000)
    capacity_uom        = Column(String(20), nullable=True)            # e.g. "L", "KG", "units/hr"
    location            = Column(String(255), nullable=True)
    department          = Column(String(100), nullable=True)
    setup_time_min        = Column(Integer, nullable=True, default=0)    # standard setup minutes
    ideal_cycle_time_sec  = Column(Numeric(10, 3), nullable=True)       # for OEE performance calc
    labor_rate_per_hour   = Column(Numeric(14, 4), nullable=True)       # KES/hr operator labor
    machine_cost_per_hour = Column(Numeric(14, 4), nullable=True)       # KES/hr machine cost
    status                = Column(Enum(WorkCenterStatus), nullable=False, default=WorkCenterStatus.ACTIVE)
    notes                 = Column(Text, nullable=True)

    # Relationships
    routing_steps  = relationship("RoutingStep", back_populates="work_center", cascade="all, delete-orphan")
    work_orders    = relationship("WorkOrder", back_populates="work_center")
    schedules      = relationship("ProductionSchedule", back_populates="work_center")
    downtime_events = relationship("DowntimeEvent", back_populates="work_center", cascade="all, delete-orphan")
    oee_records    = relationship("OEERecord", back_populates="work_center", cascade="all, delete-orphan")


# ── 2. Routing ─────────────────────────────────────────────────────────────────

class Routing(Base, TimestampMixin):
    """Production routing: ordered set of operations per product."""
    __tablename__ = "routings"
    __table_args__ = (
        UniqueConstraint("routing_id", name="uq_routing_code"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routing_id = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    version    = Column(Integer, nullable=False, default=1)
    name       = Column(String(255), nullable=True)
    is_active  = Column(Boolean, nullable=False, default=True)
    notes      = Column(Text, nullable=True)

    product = relationship("Product")
    steps   = relationship(
        "RoutingStep",
        back_populates="routing",
        cascade="all, delete-orphan",
        order_by="RoutingStep.step_number",
    )


class RoutingStep(Base, TimestampMixin):
    """Single operation step within a routing."""
    __tablename__ = "routing_steps"
    __table_args__ = (
        UniqueConstraint("routing_id", "step_number", name="uq_routing_step"),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routing_id            = Column(UUID(as_uuid=True), ForeignKey("routings.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number           = Column(Integer, nullable=False)
    operation             = Column(String(255), nullable=False)       # e.g. "Mixing", "Filling"
    work_center_id        = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="RESTRICT"), nullable=False)
    standard_time_minutes = Column(Integer, nullable=False, default=0)
    setup_time_minutes    = Column(Integer, nullable=True, default=0)
    is_parallel           = Column(Boolean, nullable=False, default=False)
    notes                 = Column(Text, nullable=True)

    routing     = relationship("Routing", back_populates="steps")
    work_center = relationship("WorkCenter", back_populates="routing_steps")


# ── 3. Work Orders ─────────────────────────────────────────────────────────────

class WorkOrder(Base, TimestampMixin):
    """Executable operation derived from a production order."""
    __tablename__ = "work_orders"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id       = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    routing_step_id     = Column(UUID(as_uuid=True), ForeignKey("routing_steps.id", ondelete="SET NULL"), nullable=True)
    work_center_id      = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="RESTRICT"), nullable=False)
    operation           = Column(String(255), nullable=False)
    operator            = Column(String(255), nullable=True)          # free-text operator name
    status              = Column(Enum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.PLANNED)
    planned_quantity    = Column(Numeric(14, 3), nullable=True)
    actual_quantity     = Column(Numeric(14, 3), nullable=True)
    start_time          = Column(DateTime(timezone=True), nullable=True)
    end_time            = Column(DateTime(timezone=True), nullable=True)
    planned_start       = Column(DateTime(timezone=True), nullable=True)
    planned_end         = Column(DateTime(timezone=True), nullable=True)
    notes               = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder")
    routing_step     = relationship("RoutingStep")
    work_center      = relationship("WorkCenter", back_populates="work_orders")
    time_entries     = relationship("TimeTracking", back_populates="work_order", cascade="all, delete-orphan")
    labor_logs       = relationship("LaborLog", back_populates="work_order", cascade="all, delete-orphan")


# ── 4. Production Scheduling ───────────────────────────────────────────────────

class Shift(Base, TimestampMixin):
    """Shift definition (Shift A, Night Shift, etc.)."""
    __tablename__ = "shifts"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_code     = Column(String(50), unique=True, nullable=False, index=True)
    name           = Column(String(255), nullable=False)
    start_time_str = Column(String(8), nullable=False)   # "08:00" HH:MM
    end_time_str   = Column(String(8), nullable=False)   # "16:00" HH:MM
    duration_hours = Column(Numeric(4, 2), nullable=False)
    is_active      = Column(Boolean, nullable=False, default=True)
    notes          = Column(Text, nullable=True)

    schedules = relationship("ProductionSchedule", back_populates="shift")
    oee_records = relationship("OEERecord", back_populates="shift")


class ProductionSchedule(Base, TimestampMixin):
    """Machine-level production schedule entry."""
    __tablename__ = "production_schedules"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id         = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    work_center_id      = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="RESTRICT"), nullable=False, index=True)
    shift_id            = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    shift_name          = Column(String(100), nullable=True)           # denormalized for CSV import
    start_time          = Column(DateTime(timezone=True), nullable=False)
    end_time            = Column(DateTime(timezone=True), nullable=False)
    status              = Column(Enum(ScheduleStatus), nullable=False, default=ScheduleStatus.PLANNED)
    priority            = Column(Enum(SchedulePriority), nullable=False, default=SchedulePriority.MEDIUM)
    conflict_flag       = Column(Boolean, nullable=False, default=False)
    notes               = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder")
    work_center      = relationship("WorkCenter", back_populates="schedules")
    shift            = relationship("Shift", back_populates="schedules")


# ── 5. Time Tracking ───────────────────────────────────────────────────────────

class TimeTracking(Base, TimestampMixin):
    """Actual vs planned production time per work order."""
    __tablename__ = "time_tracking"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id                = Column(String(50), unique=True, nullable=False, index=True)
    work_order_id         = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    actual_start          = Column(DateTime(timezone=True), nullable=False)
    actual_end            = Column(DateTime(timezone=True), nullable=True)
    duration_actual_min   = Column(Integer, nullable=True)            # computed
    duration_planned_min  = Column(Integer, nullable=True)
    downtime_minutes      = Column(Integer, nullable=True, default=0)
    category              = Column(Enum(TimeTrackingCategory), nullable=False, default=TimeTrackingCategory.PRODUCTIVE)
    reason                = Column(String(500), nullable=True)        # delay or downtime reason
    efficiency_pct        = Column(Numeric(6, 2), nullable=True)      # planned/actual * 100
    notes                 = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", back_populates="time_entries")


# ── 6. Downtime Events ─────────────────────────────────────────────────────────

class DowntimeEvent(Base, TimestampMixin):
    """Machine-level downtime event (more granular than DowntimeLog)."""
    __tablename__ = "downtime_events"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    downtime_id     = Column(String(50), unique=True, nullable=False, index=True)
    work_center_id  = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="RESTRICT"), nullable=False, index=True)
    work_order_id   = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id      = Column(String(100), nullable=True)              # free-text machine code
    start_time      = Column(DateTime(timezone=True), nullable=False)
    end_time        = Column(DateTime(timezone=True), nullable=True)
    duration_min    = Column(Integer, nullable=True)                  # auto-calculated on close
    reason          = Column(String(500), nullable=False)
    category        = Column(Enum(DowntimeCategory), nullable=False, default=DowntimeCategory.UNPLANNED)
    reported_by     = Column(String(255), nullable=True)
    impact_units    = Column(Integer, nullable=True)                  # units lost due to downtime
    notes           = Column(Text, nullable=True)

    work_center = relationship("WorkCenter", back_populates="downtime_events")
    work_order  = relationship("WorkOrder")


# ── 7. QC Inspections ──────────────────────────────────────────────────────────

class AdvQCInspection(Base, TimestampMixin):
    """Quality control inspection record (inline or final) for advanced production."""
    __tablename__ = "adv_qc_inspections"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    qc_id               = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    inspection_type     = Column(Enum(QCInspectionType), nullable=False, default=QCInspectionType.INLINE)
    status              = Column(Enum(AdvQCStatus), nullable=False, default=AdvQCStatus.PENDING)
    checked_by          = Column(String(255), nullable=True)
    inspected_at        = Column(DateTime(timezone=True), nullable=True)
    batch_ref           = Column(String(100), nullable=True)
    notes               = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder")
    work_order       = relationship("WorkOrder")
    results          = relationship(
        "AdvQCResult",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )


class AdvQCResult(Base, TimestampMixin):
    """Individual QC parameter test result for advanced production."""
    __tablename__ = "adv_qc_results"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id  = Column(UUID(as_uuid=True), ForeignKey("adv_qc_inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    test_type      = Column(String(100), nullable=False)              # e.g. "pH", "viscosity"
    actual_value   = Column(Numeric(14, 4), nullable=True)
    min_value      = Column(Numeric(14, 4), nullable=True)
    max_value      = Column(Numeric(14, 4), nullable=True)
    unit           = Column(String(50), nullable=True)                # e.g. "pH", "cP", "%"
    result         = Column(Enum(QCResultValue), nullable=False, default=QCResultValue.PASS)
    notes          = Column(Text, nullable=True)

    inspection = relationship("AdvQCInspection", back_populates="results")


# ── 8. Waste & Yield Tracking ──────────────────────────────────────────────────

class WasteRecord(Base, TimestampMixin):
    """Waste and yield tracking per production order / work order."""
    __tablename__ = "waste_records"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_id            = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    work_order_id       = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    material_id         = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    material_code       = Column(String(100), nullable=True)          # denormalized for CSV
    waste_type          = Column(Enum(WasteType), nullable=False, default=WasteType.MATERIAL)
    waste_category      = Column(Enum(WasteCategory), nullable=False, default=WasteCategory.NORMAL)
    expected_qty        = Column(Numeric(14, 4), nullable=False)
    actual_qty          = Column(Numeric(14, 4), nullable=False)
    loss_qty            = Column(Numeric(14, 4), nullable=False, default=0)   # expected - actual
    loss_pct            = Column(Numeric(6, 3), nullable=True)                # loss / expected * 100
    uom                 = Column(String(20), nullable=True, default="KG")
    reason              = Column(String(500), nullable=True)
    is_anomaly          = Column(Boolean, nullable=False, default=False)       # auto-flagged
    notes               = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder")
    work_order       = relationship("WorkOrder")
    material         = relationship("Material")


# ── 9. Batch / Lot Tracking ────────────────────────────────────────────────────

class BatchLot(Base, TimestampMixin):
    """Full traceability record for a production batch / lot."""
    __tablename__ = "batch_lots"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id            = Column(String(100), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_sku         = Column(String(100), nullable=True)          # denormalized for CSV
    quantity            = Column(Numeric(14, 3), nullable=False)
    uom                 = Column(String(20), nullable=False, default="KG")
    manufacture_date    = Column(Date, nullable=True)
    expiry_date         = Column(Date, nullable=True)
    status              = Column(Enum(BatchLotStatus), nullable=False, default=BatchLotStatus.QUARANTINE)
    traceability_code   = Column(String(255), nullable=True, index=True)
    warehouse_id        = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    quarantine_reason   = Column(String(500), nullable=True)
    released_by         = Column(String(255), nullable=True)
    notes               = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder")
    product          = relationship("Product")
    warehouse        = relationship("Warehouse")


# ── 10. Labor Tracking ─────────────────────────────────────────────────────────

class LaborLog(Base, TimestampMixin):
    """Operator-level work logging per work order."""
    __tablename__ = "labor_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    labor_id        = Column(String(50), unique=True, nullable=False, index=True)
    work_order_id   = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id     = Column(UUID(as_uuid=True), nullable=True)        # no FK — use hr_employees if needed
    employee_code   = Column(String(50), nullable=True)               # denormalized for CSV
    operator_name   = Column(String(255), nullable=True)
    start_time      = Column(DateTime(timezone=True), nullable=True)
    end_time        = Column(DateTime(timezone=True), nullable=True)
    hours_worked    = Column(Numeric(6, 2), nullable=True)
    role            = Column(String(100), nullable=True)              # e.g. "operator", "supervisor"
    activity_type   = Column(Enum(LaborActivityType), nullable=False, default=LaborActivityType.PRODUCTION)
    pieces_produced = Column(Integer, nullable=True)
    notes           = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", back_populates="labor_logs")


# ── 11. OEE Records ────────────────────────────────────────────────────────────

class OEERecord(Base, TimestampMixin):
    """Daily stored OEE metrics per work center / shift."""
    __tablename__ = "oee_records"
    __table_args__ = (
        UniqueConstraint("work_center_id", "record_date", "shift_id", name="uq_oee_center_date_shift"),
        Index("ix_oee_record_date", "record_date"),
    )

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oee_id                      = Column(String(50), unique=True, nullable=False, index=True)
    work_center_id              = Column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="RESTRICT"), nullable=False, index=True)
    machine_id                  = Column(String(100), nullable=True)  # denormalized / free-text ref
    shift_id                    = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    record_date                 = Column(Date, nullable=False)
    planned_production_time_min = Column(Integer, nullable=False)
    actual_production_time_min  = Column(Integer, nullable=True)
    downtime_min                = Column(Integer, nullable=True, default=0)
    ideal_cycle_time_sec        = Column(Numeric(10, 3), nullable=True)
    total_units_produced        = Column(Integer, nullable=True, default=0)
    good_units_produced         = Column(Integer, nullable=True, default=0)
    # KPIs (auto-calculated, stored for fast dashboard queries)
    availability                = Column(Numeric(6, 4), nullable=True)   # 0.0 – 1.0
    performance                 = Column(Numeric(6, 4), nullable=True)   # 0.0 – 1.0
    quality                     = Column(Numeric(6, 4), nullable=True)   # 0.0 – 1.0
    oee_score                   = Column(Numeric(6, 4), nullable=True)   # availability × performance × quality
    # Anomaly flags
    is_low_oee                  = Column(Boolean, nullable=False, default=False)   # OEE < 0.65
    is_high_downtime            = Column(Boolean, nullable=False, default=False)   # downtime > 20 % of planned
    notes                       = Column(Text, nullable=True)

    work_center = relationship("WorkCenter", back_populates="oee_records")
    shift       = relationship("Shift", back_populates="oee_records")
