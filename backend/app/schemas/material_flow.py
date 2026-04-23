from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.material_flow import (
    FlowType, FlowStatus, FlowMode, StageType, QualityStatus,
    MovementReason, ReservationStatus, TankStatus, ReconciliationStatus,
    MFAIAgentType, MFAIRecStatus,
)


# ── Stage ─────────────────────────────────────────────────────────────────────

class FlowStageCreate(BaseModel):
    stage_code: str
    stage_name: str
    stage_type: StageType
    plant_id: Optional[str] = None
    warehouse_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    quality_default_status: QualityStatus = QualityStatus.QUARANTINE
    sequence_no: int = 0
    active_flag: bool = True
    notes: Optional[str] = None


class FlowStageOut(FlowStageCreate):
    id: UUID
    warehouse_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Flow Transaction ──────────────────────────────────────────────────────────

class FlowLineCreate(BaseModel):
    line_no: int = 1
    item_type: str = "material"
    material_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    batch_id: Optional[str] = None
    quantity: Decimal
    uom: str = "KG"
    source_warehouse_id: Optional[UUID] = None
    source_location_id: Optional[UUID] = None
    source_stage_id: Optional[UUID] = None
    destination_warehouse_id: Optional[UUID] = None
    destination_location_id: Optional[UUID] = None
    destination_stage_id: Optional[UUID] = None
    quality_status: QualityStatus = QualityStatus.RELEASED
    movement_reason: MovementReason = MovementReason.PRODUCTION_ISSUE
    reservation_flag: bool = False
    issue_flag: bool = False
    consumption_flag: bool = False
    return_flag: bool = False
    scrap_flag: bool = False
    rework_flag: bool = False
    reference_line_id: Optional[UUID] = None
    notes: Optional[str] = None


class FlowLineOut(FlowLineCreate):
    id: UUID
    transaction_id: UUID
    material_name: Optional[str] = None
    product_name: Optional[str] = None
    lot_number: Optional[str] = None
    source_stage_name: Optional[str] = None
    destination_stage_name: Optional[str] = None

    class Config:
        from_attributes = True


class FlowTransactionCreate(BaseModel):
    flow_type: FlowType
    flow_mode: FlowMode = FlowMode.ONE_STEP
    production_order_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    source_document_type: Optional[str] = None
    source_document_id: Optional[UUID] = None
    transaction_datetime: Optional[datetime] = None
    plant_id: Optional[str] = None
    notes: Optional[str] = None
    lines: List[FlowLineCreate] = Field(default_factory=list)


class FlowTransactionOut(BaseModel):
    id: UUID
    flow_no: str
    flow_type: FlowType
    flow_mode: FlowMode
    status: FlowStatus
    production_order_id: Optional[UUID] = None
    transaction_datetime: datetime
    plant_id: Optional[str] = None
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    notes: Optional[str] = None
    lines: List[FlowLineOut] = []

    class Config:
        from_attributes = True


class FlowTransactionApprove(BaseModel):
    notes: Optional[str] = None


# ── Reservation ───────────────────────────────────────────────────────────────

class ReservationLineCreate(BaseModel):
    line_no: int = 1
    item_type: str = "material"
    material_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    warehouse_id: UUID
    quantity_required: Decimal
    uom: str = "KG"
    quality_status_required: QualityStatus = QualityStatus.RELEASED
    lot_fixed: bool = False
    notes: Optional[str] = None


class ReservationLineOut(ReservationLineCreate):
    id: UUID
    reservation_id: UUID
    quantity_reserved: Decimal = Decimal("0")
    quantity_issued: Decimal = Decimal("0")
    fefo_lot_candidate: Optional[str] = None
    material_name: Optional[str] = None
    lot_number: Optional[str] = None

    class Config:
        from_attributes = True


class ReservationCreate(BaseModel):
    production_order_id: UUID
    work_order_id: Optional[UUID] = None
    expiry_datetime: Optional[datetime] = None
    notes: Optional[str] = None
    lines: List[ReservationLineCreate] = Field(default_factory=list)


class ReservationOut(BaseModel):
    id: UUID
    reservation_no: str
    production_order_id: UUID
    status: ReservationStatus
    expiry_datetime: Optional[datetime] = None
    lines: List[ReservationLineOut] = []

    class Config:
        from_attributes = True


# ── Consumption ───────────────────────────────────────────────────────────────

class ConsumptionCreate(BaseModel):
    production_order_id: UUID
    work_order_id: Optional[UUID] = None
    item_type: str = "material"
    material_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    quantity_consumed: Decimal
    quantity_returned: Decimal = Decimal("0")
    quantity_scrapped: Decimal = Decimal("0")
    uom: str = "KG"
    stage_id: Optional[UUID] = None
    notes: Optional[str] = None


class ConsumptionOut(ConsumptionCreate):
    id: UUID
    quantity_issued: Decimal
    quantity_variance: Decimal
    variance_pct: Optional[Decimal] = None
    bom_quantity: Optional[Decimal] = None
    consumed_at: Optional[datetime] = None
    material_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Prepared Lot ──────────────────────────────────────────────────────────────

class PreparedLotCreate(BaseModel):
    production_order_id: Optional[UUID] = None
    source_lot_id: Optional[UUID] = None
    material_id: UUID
    target_quantity: Decimal
    uom: str = "KG"
    tolerance_pct: Optional[Decimal] = None
    weighing_stage_id: Optional[UUID] = None
    notes: Optional[str] = None


class PreparedLotWeigh(BaseModel):
    actual_quantity: Decimal
    operator_id: Optional[UUID] = None
    notes: Optional[str] = None


class PreparedLotOut(PreparedLotCreate):
    id: UUID
    prepared_lot_no: str
    actual_quantity: Optional[Decimal] = None
    over_weigh: bool = False
    under_weigh: bool = False
    quality_status: QualityStatus = QualityStatus.RELEASED
    consumed: bool = False
    weighed_at: Optional[datetime] = None
    material_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Tank Occupancy ────────────────────────────────────────────────────────────

class TankCreate(BaseModel):
    tank_code: str
    tank_name: str
    stage_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    capacity_max: Optional[Decimal] = None
    uom: str = "KG"
    notes: Optional[str] = None


class TankUpdate(BaseModel):
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    batch_id: Optional[str] = None
    production_order_id: Optional[UUID] = None
    quantity_current: Optional[Decimal] = None
    quantity_reserved: Optional[Decimal] = None
    quality_status: Optional[QualityStatus] = None
    tank_status: Optional[TankStatus] = None
    notes: Optional[str] = None


class TankOut(BaseModel):
    id: UUID
    tank_code: str
    tank_name: str
    stage_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    capacity_max: Optional[Decimal] = None
    uom: str
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    batch_id: Optional[str] = None
    production_order_id: Optional[UUID] = None
    quantity_current: Decimal
    quantity_reserved: Decimal
    quality_status: QualityStatus
    tank_status: TankStatus
    fill_datetime: Optional[datetime] = None
    release_datetime: Optional[datetime] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None
    material_name: Optional[str] = None
    fill_pct: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ── Reconciliation ────────────────────────────────────────────────────────────

class ReconciliationLineOut(BaseModel):
    id: UUID
    line_no: int
    item_type: str
    material_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    bom_quantity: Optional[Decimal] = None
    issued_quantity: Decimal
    consumed_quantity: Decimal
    returned_quantity: Decimal
    scrapped_quantity: Decimal
    variance_quantity: Decimal
    variance_pct: Optional[Decimal] = None
    uom: str
    variance_reason: Optional[str] = None
    cost_impact: Optional[Decimal] = None
    material_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReconciliationOut(BaseModel):
    id: UUID
    reconciliation_no: str
    production_order_id: UUID
    status: ReconciliationStatus
    total_issued: Decimal
    total_consumed: Decimal
    total_returned: Decimal
    total_scrapped: Decimal
    total_variance: Decimal
    variance_pct: Optional[Decimal] = None
    output_planned: Optional[Decimal] = None
    output_actual: Optional[Decimal] = None
    output_variance: Optional[Decimal] = None
    variance_reason: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    lines: List[ReconciliationLineOut] = []

    class Config:
        from_attributes = True


class ReconciliationApprove(BaseModel):
    variance_reason: Optional[str] = None
    notes: Optional[str] = None


# ── AI Recommendations ────────────────────────────────────────────────────────

class MFAIRecOut(BaseModel):
    id: UUID
    agent_type: MFAIAgentType
    status: MFAIRecStatus
    production_order_id: Optional[UUID] = None
    title: str
    description: str
    severity: str
    confidence_score: Optional[Decimal] = None
    estimated_impact: Optional[str] = None
    actioned_by: Optional[UUID] = None
    actioned_at: Optional[datetime] = None
    action_notes: Optional[str] = None

    class Config:
        from_attributes = True


class MFAIRecAction(BaseModel):
    status: MFAIRecStatus
    notes: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class MFDashboard(BaseModel):
    total_flows_today: int = 0
    total_issued_today: Decimal = Decimal("0")
    active_reservations: int = 0
    open_reconciliations: int = 0
    tanks_in_use: int = 0
    tanks_qc_hold: int = 0
    pending_ai_recs: int = 0
    total_wip_quantity: Decimal = Decimal("0")
    recent_flows: List[FlowTransactionOut] = []
    ai_recommendations: List[MFAIRecOut] = []


# ── Reports ───────────────────────────────────────────────────────────────────

class FlowHistoryFilter(BaseModel):
    production_order_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    stage_id: Optional[UUID] = None
    flow_type: Optional[FlowType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class VarianceReportRow(BaseModel):
    production_order_id: UUID
    order_no: str
    material_id: Optional[UUID] = None
    material_name: Optional[str] = None
    bom_quantity: Optional[Decimal] = None
    issued_quantity: Decimal
    consumed_quantity: Decimal
    returned_quantity: Decimal
    variance_quantity: Decimal
    variance_pct: Optional[Decimal] = None
    uom: str
