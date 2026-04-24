import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class FlowType(str, enum.Enum):
    RAW_ISSUE = "RAW_ISSUE"
    PKG_ISSUE = "PKG_ISSUE"
    CONSUMABLE_ISSUE = "CONSUMABLE_ISSUE"
    WEIGHING_TRANSFER = "WEIGHING_TRANSFER"
    STAGE_TRANSFER = "STAGE_TRANSFER"
    INTERMEDIATE_CREATE = "INTERMEDIATE_CREATE"
    BULK_TRANSFER = "BULK_TRANSFER"
    TANK_FILL = "TANK_FILL"
    TANK_TRANSFER = "TANK_TRANSFER"
    LINE_TRANSFER = "LINE_TRANSFER"
    FG_RECEIPT = "FG_RECEIPT"
    RETURN = "RETURN"
    REVERSAL = "REVERSAL"
    SCRAP = "SCRAP"
    REWORK = "REWORK"
    RECONCILIATION = "RECONCILIATION"


class FlowStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"
    CANCELLED = "CANCELLED"


class StageType(str, enum.Enum):
    RAW_WAREHOUSE = "RAW_WAREHOUSE"
    QUARANTINE_RAW = "QUARANTINE_RAW"
    WEIGHING_ROOM = "WEIGHING_ROOM"
    STAGED_LINE = "STAGED_LINE"
    MIXING = "MIXING"
    PREMIX = "PREMIX"
    INTERMEDIATE_HOLD = "INTERMEDIATE_HOLD"
    BULK_TANK = "BULK_TANK"
    QC_HOLD_TANK = "QC_HOLD_TANK"
    RELEASED_BULK = "RELEASED_BULK"
    FILLING_STAGING = "FILLING_STAGING"
    PACKAGING_STAGING = "PACKAGING_STAGING"
    SECONDARY_PACKING = "SECONDARY_PACKING"
    PALLETIZATION = "PALLETIZATION"
    FG_QUARANTINE = "FG_QUARANTINE"
    FG_RELEASED = "FG_RELEASED"
    REWORK_HOLDING = "REWORK_HOLDING"
    SCRAP_HOLDING = "SCRAP_HOLDING"
    TRANSIT = "TRANSIT"


class QualityStatus(str, enum.Enum):
    QUARANTINE = "QUARANTINE"
    PENDING_INSPECTION = "PENDING_INSPECTION"
    RELEASED = "RELEASED"
    QC_HOLD = "QC_HOLD"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    REWORK_PENDING = "REWORK_PENDING"


class MovementReason(str, enum.Enum):
    PRODUCTION_ISSUE = "PRODUCTION_ISSUE"
    STAGED_ISSUE = "STAGED_ISSUE"
    WEIGHING_TRANSFER = "WEIGHING_TRANSFER"
    INTERMEDIATE_TRANSFER = "INTERMEDIATE_TRANSFER"
    BULK_TRANSFER = "BULK_TRANSFER"
    FG_RECEIPT = "FG_RECEIPT"
    RETURN_UNUSED = "RETURN_UNUSED"
    RETURN_FROM_REWORK = "RETURN_FROM_REWORK"
    REVERSAL = "REVERSAL"
    SCRAP = "SCRAP"
    REWORK_ROUTING = "REWORK_ROUTING"
    QC_RELEASE = "QC_RELEASE"
    QC_HOLD = "QC_HOLD"
    RECONCILIATION = "RECONCILIATION"
    MANUAL = "MANUAL"


class FlowMode(str, enum.Enum):
    ONE_STEP = "ONE_STEP"
    TWO_STEP = "TWO_STEP"
    THREE_STEP = "THREE_STEP"
    MULTI_STAGE = "MULTI_STAGE"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    FULLY_ISSUED = "FULLY_ISSUED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class TankStatus(str, enum.Enum):
    EMPTY = "EMPTY"
    FILLING = "FILLING"
    FULL = "FULL"
    IN_USE = "IN_USE"
    QC_HOLD = "QC_HOLD"
    CLEANING = "CLEANING"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class ReconciliationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"


class MFAIAgentType(str, enum.Enum):
    VARIANCE_ANALYZER = "VARIANCE_ANALYZER"
    FLOW_OPTIMIZER = "FLOW_OPTIMIZER"
    RISK_MONITOR = "RISK_MONITOR"


class MFAIRecStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


# ── Stage Configuration ───────────────────────────────────────────────────────

class FlowStage(Base, TimestampMixin):
    __tablename__ = "flow_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_code = Column(String(50), unique=True, nullable=False, index=True)
    stage_name = Column(String(200), nullable=False)
    stage_type = Column(Enum(StageType), nullable=False)
    plant_id = Column(String(50), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    quality_default_status = Column(Enum(QualityStatus), nullable=False, default=QualityStatus.QUARANTINE)
    sequence_no = Column(Integer, nullable=False, default=0)
    active_flag = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])


# ── Material Flow Transaction Header ─────────────────────────────────────────

class MaterialFlowTransaction(Base, TimestampMixin):
    __tablename__ = "material_flow_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_no = Column(String(50), unique=True, nullable=False, index=True)
    flow_type = Column(Enum(FlowType), nullable=False)
    flow_mode = Column(Enum(FlowMode), nullable=False, default=FlowMode.ONE_STEP)
    status = Column(Enum(FlowStatus), nullable=False, default=FlowStatus.DRAFT)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True)
    source_document_type = Column(String(50), nullable=True)
    source_document_id = Column(UUID(as_uuid=True), nullable=True)
    transaction_datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    plant_id = Column(String(50), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    lines = relationship("MaterialFlowLine", back_populates="transaction", cascade="all, delete-orphan", order_by="MaterialFlowLine.line_no")
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])


# ── Material Flow Line ────────────────────────────────────────────────────────

class MaterialFlowLine(Base, TimestampMixin):
    __tablename__ = "material_flow_lines"
    __table_args__ = (
        UniqueConstraint("transaction_id", "line_no", name="uq_mfl_line_no"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("material_flow_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)

    item_type = Column(String(20), nullable=False, default="material")  # material / product
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)
    batch_id = Column(String(100), nullable=True)

    quantity = Column(Numeric(14, 3), nullable=False)
    uom = Column(String(20), nullable=False, default="KG")

    source_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    source_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    source_stage_id = Column(UUID(as_uuid=True), ForeignKey("flow_stages.id", ondelete="SET NULL"), nullable=True)

    destination_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True)
    destination_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    destination_stage_id = Column(UUID(as_uuid=True), ForeignKey("flow_stages.id", ondelete="SET NULL"), nullable=True)

    quality_status = Column(Enum(QualityStatus), nullable=False, default=QualityStatus.RELEASED)
    movement_reason = Column(Enum(MovementReason), nullable=False, default=MovementReason.PRODUCTION_ISSUE)

    reservation_flag = Column(Boolean, default=False, nullable=False)
    issue_flag = Column(Boolean, default=False, nullable=False)
    consumption_flag = Column(Boolean, default=False, nullable=False)
    return_flag = Column(Boolean, default=False, nullable=False)
    scrap_flag = Column(Boolean, default=False, nullable=False)
    rework_flag = Column(Boolean, default=False, nullable=False)

    reference_line_id = Column(UUID(as_uuid=True), ForeignKey("material_flow_lines.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    transaction = relationship("MaterialFlowTransaction", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])
    product = relationship("Product", foreign_keys=[product_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])
    source_stage = relationship("FlowStage", foreign_keys=[source_stage_id])
    destination_stage = relationship("FlowStage", foreign_keys=[destination_stage_id])
    reference_line = relationship("MaterialFlowLine", remote_side=[id], foreign_keys=[reference_line_id])


# ── Material Reservation ──────────────────────────────────────────────────────

class MaterialReservation(Base, TimestampMixin):
    __tablename__ = "material_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_no = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.ACTIVE)
    expiry_datetime = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    lines = relationship("MaterialReservationLine", back_populates="reservation", cascade="all, delete-orphan")
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    creator = relationship("User", foreign_keys=[created_by])


class MaterialReservationLine(Base, TimestampMixin):
    __tablename__ = "material_reservation_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey("material_reservations.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)

    item_type = Column(String(20), nullable=False, default="material")
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)

    quantity_required = Column(Numeric(14, 3), nullable=False)
    quantity_reserved = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_issued = Column(Numeric(14, 3), nullable=False, default=0)
    uom = Column(String(20), nullable=False, default="KG")
    quality_status_required = Column(Enum(QualityStatus), nullable=False, default=QualityStatus.RELEASED)
    fefo_lot_candidate = Column(String(100), nullable=True)
    lot_fixed = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    reservation = relationship("MaterialReservation", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])
    product = relationship("Product", foreign_keys=[product_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])


# ── Progressive Consumption Tracking ─────────────────────────────────────────

class ProductionConsumption(Base, TimestampMixin):
    __tablename__ = "production_consumptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True)
    flow_line_id = Column(UUID(as_uuid=True), ForeignKey("material_flow_lines.id", ondelete="SET NULL"), nullable=True)

    item_type = Column(String(20), nullable=False, default="material")
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)

    quantity_issued = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_consumed = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_returned = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_scrapped = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_variance = Column(Numeric(14, 3), nullable=False, default=0)
    uom = Column(String(20), nullable=False, default="KG")

    bom_quantity = Column(Numeric(14, 3), nullable=True)
    variance_pct = Column(Numeric(7, 3), nullable=True)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("flow_stages.id", ondelete="SET NULL"), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    material = relationship("Material", foreign_keys=[material_id])
    product = relationship("Product", foreign_keys=[product_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    stage = relationship("FlowStage", foreign_keys=[stage_id])
    operator = relationship("User", foreign_keys=[operator_id])


# ── Prepared / Weighed Lot ────────────────────────────────────────────────────

class PreparedLot(Base, TimestampMixin):
    __tablename__ = "prepared_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prepared_lot_no = Column(String(100), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    source_lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False)

    target_quantity = Column(Numeric(14, 3), nullable=False)
    actual_quantity = Column(Numeric(14, 3), nullable=True)
    uom = Column(String(20), nullable=False, default="KG")
    tolerance_pct = Column(Numeric(5, 2), nullable=True)
    over_weigh = Column(Boolean, default=False, nullable=False)
    under_weigh = Column(Boolean, default=False, nullable=False)

    weighing_stage_id = Column(UUID(as_uuid=True), ForeignKey("flow_stages.id", ondelete="SET NULL"), nullable=True)
    weighed_at = Column(DateTime(timezone=True), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quality_status = Column(Enum(QualityStatus), nullable=False, default=QualityStatus.RELEASED)
    consumed = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    source_lot = relationship("Lot", foreign_keys=[source_lot_id])
    material = relationship("Material", foreign_keys=[material_id])
    weighing_stage = relationship("FlowStage", foreign_keys=[weighing_stage_id])
    operator = relationship("User", foreign_keys=[operator_id])


# ── Tank / Container Occupancy ────────────────────────────────────────────────

class TankOccupancy(Base, TimestampMixin):
    __tablename__ = "tank_occupancies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tank_code = Column(String(50), nullable=False, index=True)
    tank_name = Column(String(200), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("flow_stages.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    capacity_max = Column(Numeric(14, 3), nullable=True)
    uom = Column(String(20), nullable=False, default="KG")

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True)
    batch_id = Column(String(100), nullable=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    quantity_current = Column(Numeric(14, 3), nullable=False, default=0)
    quantity_reserved = Column(Numeric(14, 3), nullable=False, default=0)
    quality_status = Column(Enum(QualityStatus), nullable=False, default=QualityStatus.QUARANTINE)
    tank_status = Column(Enum(TankStatus), nullable=False, default=TankStatus.EMPTY)
    fill_datetime = Column(DateTime(timezone=True), nullable=True)
    release_datetime = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    stage = relationship("FlowStage", foreign_keys=[stage_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    product = relationship("Product", foreign_keys=[product_id])
    material = relationship("Material", foreign_keys=[material_id])
    lot = relationship("Lot", foreign_keys=[lot_id])
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])


# ── Batch Reconciliation ──────────────────────────────────────────────────────

class BatchReconciliation(Base, TimestampMixin):
    __tablename__ = "batch_reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_no = Column(String(50), unique=True, nullable=False, index=True)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(ReconciliationStatus, name="batchreconciliationstatus"), nullable=False, default=ReconciliationStatus.OPEN)

    total_issued = Column(Numeric(14, 3), nullable=False, default=0)
    total_consumed = Column(Numeric(14, 3), nullable=False, default=0)
    total_returned = Column(Numeric(14, 3), nullable=False, default=0)
    total_scrapped = Column(Numeric(14, 3), nullable=False, default=0)
    total_variance = Column(Numeric(14, 3), nullable=False, default=0)
    variance_pct = Column(Numeric(7, 3), nullable=True)

    output_planned = Column(Numeric(14, 3), nullable=True)
    output_actual = Column(Numeric(14, 3), nullable=True)
    output_variance = Column(Numeric(14, 3), nullable=True)

    variance_reason = Column(Text, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    lines = relationship("BatchReconciliationLine", back_populates="reconciliation", cascade="all, delete-orphan")
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    approver = relationship("User", foreign_keys=[approved_by])


class BatchReconciliationLine(Base, TimestampMixin):
    __tablename__ = "batch_reconciliation_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey("batch_reconciliations.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)

    item_type = Column(String(20), nullable=False, default="material")
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)

    bom_quantity = Column(Numeric(14, 3), nullable=True)
    issued_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    consumed_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    returned_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    scrapped_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    variance_quantity = Column(Numeric(14, 3), nullable=False, default=0)
    variance_pct = Column(Numeric(7, 3), nullable=True)
    uom = Column(String(20), nullable=False, default="KG")
    variance_reason = Column(Text, nullable=True)
    cost_impact = Column(Numeric(14, 4), nullable=True)
    notes = Column(Text, nullable=True)

    reconciliation = relationship("BatchReconciliation", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])
    product = relationship("Product", foreign_keys=[product_id])


# ── AI Recommendations ────────────────────────────────────────────────────────

class MFAIRecommendation(Base, TimestampMixin):
    __tablename__ = "mf_ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(MFAIAgentType), nullable=False)
    status = Column(Enum(MFAIRecStatus), nullable=False, default=MFAIRecStatus.PENDING)
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    confidence_score = Column(Numeric(5, 2), nullable=True)
    estimated_impact = Column(Text, nullable=True)

    actioned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actioned_at = Column(DateTime(timezone=True), nullable=True)
    action_notes = Column(Text, nullable=True)

    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    actioned_user = relationship("User", foreign_keys=[actioned_by])
