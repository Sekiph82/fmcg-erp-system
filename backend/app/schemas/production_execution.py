from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Work Order ─────────────────────────────────────────────────────────────────

class ExecWorkOrderCreate(BaseModel):
    step_name: str
    step_sequence: int
    planned_qty: Decimal
    setup_time_planned: Decimal = Decimal("0")
    run_time_planned: Decimal = Decimal("0")
    cleanup_time_planned: Decimal = Decimal("0")
    work_center_id: Optional[UUID] = None
    operation_code: Optional[str] = None
    section_id: Optional[str] = None
    line_id: Optional[str] = None
    qc_required_flag: bool = False
    dependency_work_order_id: Optional[UUID] = None
    notes: Optional[str] = None


class ExecWorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_order_id: UUID
    operation_code: Optional[str]
    step_sequence: int
    step_name: str
    work_center_id: Optional[UUID]
    section_id: Optional[str]
    line_id: Optional[str]
    machine_id: Optional[UUID]
    assigned_operator_id: Optional[UUID]
    planned_qty: Decimal
    completed_qty: Decimal
    scrap_qty: Decimal
    rework_qty: Decimal
    setup_time_planned: Decimal
    run_time_planned: Decimal
    cleanup_time_planned: Decimal
    setup_time_actual: Optional[Decimal]
    run_time_actual: Optional[Decimal]
    cleanup_time_actual: Optional[Decimal]
    dependency_work_order_id: Optional[UUID]
    qc_required_flag: bool
    qc_passed: Optional[bool]
    scrap_category: Optional[str]
    scrap_reason: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class CompleteWorkOrderRequest(BaseModel):
    completed_qty: Decimal
    scrap_qty: Decimal = Decimal("0")
    rework_qty: Decimal = Decimal("0")
    setup_time_actual: Optional[Decimal] = None
    run_time_actual: Optional[Decimal] = None
    cleanup_time_actual: Optional[Decimal] = None
    scrap_category: Optional[str] = None
    scrap_reason: Optional[str] = None
    qc_passed: Optional[bool] = None
    notes: Optional[str] = None


# ── Material ───────────────────────────────────────────────────────────────────

class ExecOrderMaterialCreate(BaseModel):
    item_type: str = "MATERIAL"
    item_id: Optional[UUID] = None
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    required_qty: Decimal
    uom: str
    work_order_id: Optional[UUID] = None
    unit_cost: Optional[Decimal] = None


class IssueReturnMaterialRequest(BaseModel):
    material_id: UUID
    qty: Decimal
    lot_no: Optional[str] = None
    action: str  # "issue" or "return"


class ExecOrderMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_order_id: UUID
    work_order_id: Optional[UUID]
    item_type: str
    item_id: Optional[UUID]
    item_name: Optional[str]
    item_code: Optional[str]
    required_qty: Decimal
    reserved_qty: Decimal
    issued_qty: Decimal
    consumed_qty: Decimal
    returned_qty: Decimal
    scrapped_qty: Decimal
    uom: str
    status: str
    lot_numbers: Optional[list]
    unit_cost: Optional[Decimal]
    extended_cost: Optional[Decimal]


# ── Genealogy ──────────────────────────────────────────────────────────────────

class BatchGenealogyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_order_id: UUID
    input_lot_no: Optional[str]
    input_item_name: Optional[str]
    input_qty: Optional[Decimal]
    input_uom: Optional[str]
    input_supplier: Optional[str]
    output_lot_no: Optional[str]
    output_item_name: Optional[str]
    output_qty: Optional[Decimal]
    output_uom: Optional[str]
    link_type: str
    created_at: datetime


class GenealogyNode(BaseModel):
    order_id: str
    order_no: str
    batch_no: Optional[str]
    product_name: Optional[str]
    planned_qty: Decimal
    completed_qty: Decimal
    status: str
    is_rework: bool
    is_split: bool
    input_lots: List[BatchGenealogyOut]
    children: List["GenealogyNode"] = []

GenealogyNode.model_rebuild()


class GenealogyResult(BaseModel):
    root: GenealogyNode
    all_input_lots: List[str]
    all_output_lots: List[str]
    depth: int


# ── Production Order ───────────────────────────────────────────────────────────

class ProdExecOrderCreate(BaseModel):
    product_id: Optional[UUID] = None
    bom_id: Optional[UUID] = None
    routing_id: Optional[UUID] = None
    product_name: Optional[str] = None
    bom_code: Optional[str] = None
    planned_qty: Decimal
    uom: str = "KG"
    batch_no: Optional[str] = None
    source_type: str = "MANUAL"
    source_document_id: Optional[UUID] = None
    priority: int = 5
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    plant_id: Optional[str] = None
    section_id: Optional[str] = None
    line_id: Optional[str] = None
    preferred_machine_id: Optional[UUID] = None
    remarks: Optional[str] = None


class ProdExecOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_no: str
    product_id: Optional[UUID]
    product_name: Optional[str]
    bom_id: Optional[UUID]
    bom_code: Optional[str]
    planned_qty: Decimal
    completed_qty: Decimal
    scrap_qty: Decimal
    uom: str
    batch_no: Optional[str]
    source_type: str
    priority: int
    planned_start: Optional[datetime]
    planned_end: Optional[datetime]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    status: str
    is_rework: bool
    is_split: bool
    parent_order_id: Optional[UUID]
    total_actual_cost: Decimal
    cost_per_uom: Optional[Decimal]
    created_at: datetime
    updated_at: datetime


class ProdExecOrderOut(ProdExecOrderSummary):
    routing_id: Optional[UUID]
    plant_id: Optional[str]
    section_id: Optional[str]
    line_id: Optional[str]
    preferred_machine_id: Optional[UUID]
    planned_material_cost: Decimal
    actual_material_cost: Decimal
    planned_labor_cost: Decimal
    actual_labor_cost: Decimal
    overhead_cost: Decimal
    rework_qty: Decimal
    rework_reason: Optional[str]
    remarks: Optional[str]
    approved_by: Optional[UUID]
    work_orders: List[ExecWorkOrderOut] = []
    materials: List[ExecOrderMaterialOut] = []


# ── Action Requests ────────────────────────────────────────────────────────────

class CompleteOrderRequest(BaseModel):
    completed_qty: Decimal
    scrap_qty: Decimal = Decimal("0")
    remarks: Optional[str] = None


class SplitOrderRequest(BaseModel):
    split_qtys: List[Decimal]
    reason: Optional[str] = None


class MergeOrdersRequest(BaseModel):
    order_ids: List[UUID]
    reason: Optional[str] = None


class ReworkOrderRequest(BaseModel):
    qty: Decimal
    reason: str


class AddGenealogyRequest(BaseModel):
    input_lot_no: Optional[str] = None
    input_item_name: Optional[str] = None
    input_qty: Optional[Decimal] = None
    input_uom: Optional[str] = None
    input_supplier: Optional[str] = None
    output_lot_no: Optional[str] = None
    output_item_name: Optional[str] = None
    output_qty: Optional[Decimal] = None
    output_uom: Optional[str] = None
    link_type: str = "INPUT_OUTPUT"


# ── AI ─────────────────────────────────────────────────────────────────────────

class ExecAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_order_id: UUID
    agent_type: str
    status: str
    title: str
    explanation: Optional[str]
    impact_summary: Optional[str]
    confidence_score: Optional[Decimal]
    actioned_at: Optional[datetime]
    created_at: datetime


# ── Dashboard ──────────────────────────────────────────────────────────────────

class ExecDashboard(BaseModel):
    total_orders: int
    draft_orders: int
    released_orders: int
    in_progress_orders: int
    completed_today: int
    delayed_orders: int
    total_work_orders: int
    pending_work_orders: int
    active_work_orders: int
    total_scrap_qty: float
    pending_ai_recs: int
    by_status: dict
    recent_orders: List[ProdExecOrderSummary]


# ── Batch Record ───────────────────────────────────────────────────────────────

class BatchRecord(BaseModel):
    order: ProdExecOrderOut
    work_orders: List[ExecWorkOrderOut]
    materials: List[ExecOrderMaterialOut]
    genealogy: List[BatchGenealogyOut]
    generated_at: datetime
