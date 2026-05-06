from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.traceability import (
    TraceEventType, TraceItemStage, GenealogyRelType,
    RecallType, RecallTrigger, RecallSeverity, RecallStatus,
    RecallActionType, RecallActionStatus, RecallRiskStatus,
    TRRecAIAgentType, TRRecAIRecStatus,
    RecallAudience,
)


class _Base(BaseModel):
    model_config = {"from_attributes": True}


# ── Traceability Events ───────────────────────────────────────────────────────

class TraceEventLineCreate(BaseModel):
    product_id:   Optional[UUID] = None
    material_id:  Optional[UUID] = None
    source_lot_id: Optional[UUID] = None
    child_lot_id:  Optional[UUID] = None
    quantity:      Decimal
    uom:           Optional[str] = None
    source_stage:  Optional[TraceItemStage] = None
    dest_stage:    Optional[TraceItemStage] = None
    source_location_id: Optional[UUID] = None
    dest_location_id:   Optional[UUID] = None
    quality_status: Optional[str] = None
    movement_reason: Optional[str] = None
    linked_customer_id: Optional[UUID] = None
    linked_shipment_id: Optional[UUID] = None
    linked_supplier_id: Optional[UUID] = None
    linked_grn_id:      Optional[UUID] = None
    notes: Optional[str] = None

class TraceEventCreate(BaseModel):
    trace_event_type:    TraceEventType
    event_datetime:      datetime
    reference_number:    Optional[str] = None
    source_document_type: Optional[str] = None
    source_document_id:  Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    work_order_id:       Optional[UUID] = None
    plant_id:            Optional[str]  = None
    warehouse_id:        Optional[UUID] = None
    performed_by_id:     Optional[UUID] = None
    approved_by_id:      Optional[UUID] = None
    recall_id:           Optional[UUID] = None
    notes:               Optional[str]  = None
    lines:               List[TraceEventLineCreate] = Field(default_factory=list)

class TraceEventLineOut(_Base):
    id:            UUID
    event_id:      UUID
    product_id:    Optional[UUID]
    material_id:   Optional[UUID]
    source_lot_id: Optional[UUID]
    child_lot_id:  Optional[UUID]
    quantity:      Decimal
    uom:           Optional[str]
    source_stage:  Optional[TraceItemStage]
    dest_stage:    Optional[TraceItemStage]
    quality_status: Optional[str]
    movement_reason: Optional[str]
    linked_customer_id: Optional[UUID]
    linked_shipment_id: Optional[UUID]
    linked_supplier_id: Optional[UUID]
    linked_grn_id:      Optional[UUID]
    notes:         Optional[str]
    created_at:    datetime

class TraceEventOut(_Base):
    id:                  UUID
    trace_event_type:    TraceEventType
    event_datetime:      datetime
    reference_number:    Optional[str]
    source_document_type: Optional[str]
    source_document_id:  Optional[UUID]
    production_order_id: Optional[UUID]
    warehouse_id:        Optional[UUID]
    performed_by_id:     Optional[UUID]
    recall_id:           Optional[UUID]
    notes:               Optional[str]
    lines:               List[TraceEventLineOut]
    created_at:          datetime


# ── Genealogy Link ────────────────────────────────────────────────────────────

class GenealogyLinkCreate(BaseModel):
    parent_lot_id:       UUID
    child_lot_id:        UUID
    relationship_type:   GenealogyRelType
    source_document_type: Optional[str] = None
    source_document_id:  Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    quantity_linked:     Optional[Decimal] = None
    uom:                 Optional[str]  = None
    parent_stage:        Optional[TraceItemStage] = None
    child_stage:         Optional[TraceItemStage] = None
    notes:               Optional[str]  = None

class GenealogyLinkOut(_Base):
    id:                  UUID
    parent_lot_id:       UUID
    child_lot_id:        UUID
    relationship_type:   GenealogyRelType
    source_document_type: Optional[str]
    source_document_id:  Optional[UUID]
    production_order_id: Optional[UUID]
    quantity_linked:     Optional[Decimal]
    uom:                 Optional[str]
    parent_stage:        Optional[TraceItemStage]
    child_stage:         Optional[TraceItemStage]
    notes:               Optional[str]
    created_at:          datetime


# ── Genealogy Tree Nodes ──────────────────────────────────────────────────────

class GenealogyNode(BaseModel):
    lot_id:     UUID
    lot_number: str
    stage:      Optional[TraceItemStage]
    quantity:   Optional[Decimal]
    rel_type:   Optional[GenealogyRelType]
    children:   List["GenealogyNode"] = Field(default_factory=list)
    parents:    List["GenealogyNode"] = Field(default_factory=list)

GenealogyNode.model_rebuild()

class GenealogyTree(BaseModel):
    root_lot_id:  UUID
    root_lot_number: str
    direction:   str  # "forward" | "backward" | "both"
    depth:       int
    nodes:       List[GenealogyNode]
    edges:       List[Dict[str, Any]]   # [{source, target, rel_type, qty}]
    lot_count:   int
    stage_summary: Dict[str, int]

class TraceabilitySearchRequest(BaseModel):
    lot_number:        Optional[str] = None
    batch_number:      Optional[str] = None
    product_id:        Optional[UUID] = None
    material_id:       Optional[UUID] = None
    supplier_id:       Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    customer_id:       Optional[UUID] = None
    shipment_reference: Optional[str] = None
    date_from:         Optional[date] = None
    date_to:           Optional[date] = None

class TraceabilitySearchResult(BaseModel):
    lot_id:       Optional[UUID]
    lot_number:   Optional[str]
    batch_number: Optional[str]
    item_name:    Optional[str]
    stage:        Optional[TraceItemStage]
    events:       List[TraceEventOut]
    genealogy_link_count: int
    has_recall:   bool

class ForwardTraceResult(BaseModel):
    root_lot_id:   UUID
    affected_lots: List[Dict[str, Any]]
    affected_shipments: List[Dict[str, Any]]
    affected_customers: List[Dict[str, Any]]
    qty_in_stock:  Decimal
    qty_shipped:   Decimal
    qty_returned:  Decimal
    qty_scrapped:  Decimal
    qty_quarantined: Decimal
    qty_reworked:  Decimal
    total_affected_qty: Decimal

class BackwardTraceResult(BaseModel):
    root_lot_id:   UUID
    source_lots:   List[Dict[str, Any]]
    production_orders: List[Dict[str, Any]]
    suppliers:     List[Dict[str, Any]]
    grns:          List[Dict[str, Any]]
    qc_events:     List[Dict[str, Any]]
    genealogy_depth: int


# ── Recall ────────────────────────────────────────────────────────────────────

class RecallCreate(BaseModel):
    recall_type:     RecallType
    recall_reason:   str
    trigger_source:  RecallTrigger
    severity_level:  RecallSeverity = RecallSeverity.medium
    source_lot_id:   Optional[UUID] = None
    source_product_id: Optional[UUID] = None
    source_material_id: Optional[UUID] = None
    source_supplier_id: Optional[UUID] = None
    initiated_by_id: Optional[UUID] = None
    target_market:   Optional[str] = None
    country_scope:   Optional[str] = None
    product_scope_notes: Optional[str] = None
    linked_qc_case_id:  Optional[UUID] = None
    linked_complaint_id: Optional[UUID] = None
    notes:           Optional[str] = None

class RecallStatusUpdate(BaseModel):
    status:         RecallStatus
    approved_by_id: Optional[UUID] = None
    notes:          Optional[str] = None

class RecallScopeLineOut(_Base):
    id:               UUID
    recall_id:        UUID
    affected_item_id: Optional[UUID]
    affected_material_id: Optional[UUID]
    affected_lot_id:  Optional[UUID]
    affected_warehouse_id: Optional[UUID]
    affected_qty_total:      Decimal
    affected_qty_in_stock:   Decimal
    affected_qty_in_transit: Decimal
    affected_qty_shipped:    Decimal
    affected_qty_returned:   Decimal
    affected_qty_quarantined: Decimal
    affected_qty_scrapped:   Decimal
    affected_qty_reworked:   Decimal
    affected_customer_count: int
    risk_status:      RecallRiskStatus
    action_status:    RecallActionStatus
    hold_placed:      bool
    hold_placed_at:   Optional[datetime]
    notes:            Optional[str]
    created_at:       datetime

class RecallActionCreate(BaseModel):
    action_type:        RecallActionType
    target_entity_type: Optional[str] = None
    target_entity_id:   Optional[UUID] = None
    target_description: Optional[str] = None
    assigned_to_id:     Optional[UUID] = None
    due_date:           Optional[date] = None
    notes:              Optional[str] = None

class RecallActionComplete(BaseModel):
    completed_by_id: UUID
    evidence_note:   Optional[str] = None

class RecallActionOut(_Base):
    id:                UUID
    recall_id:         UUID
    action_type:       RecallActionType
    status:            RecallActionStatus
    target_entity_type: Optional[str]
    target_entity_id:   Optional[UUID]
    target_description: Optional[str]
    assigned_to_id:     Optional[UUID]
    due_date:           Optional[date]
    completed_at:       Optional[datetime]
    completed_by_id:    Optional[UUID]
    evidence_note:      Optional[str]
    notes:              Optional[str]
    created_at:         datetime

class RecallCustomerImpactOut(_Base):
    id:                UUID
    recall_id:         UUID
    customer_id:       Optional[UUID]
    customer_name:     Optional[str]
    contact_info:      Optional[str]
    country_code:      Optional[str]
    channel:           Optional[str]
    affected_lot_id:   Optional[UUID]
    shipment_reference: Optional[str]
    delivery_date:     Optional[date]
    qty_delivered:     Optional[Decimal]
    qty_remaining_open: Optional[Decimal]
    notification_sent: bool
    notification_sent_at: Optional[datetime]
    return_requested:  bool
    return_confirmed:  bool
    qty_returned:      Optional[Decimal]
    priority_rank:     Optional[int]
    risk_level:        Optional[RecallRiskStatus]
    notes:             Optional[str]
    created_at:        datetime

class RecallReturnCreate(BaseModel):
    customer_id:     Optional[UUID] = None
    lot_id:          Optional[UUID] = None
    qty_requested:   Optional[Decimal] = None
    qty_confirmed:   Optional[Decimal] = None
    qty_received:    Optional[Decimal] = None
    qty_destroyed_at_customer: Optional[Decimal] = None
    qty_quarantined_on_return: Optional[Decimal] = None
    qty_reworked:    Optional[Decimal] = None
    qty_written_off: Optional[Decimal] = None
    return_date:     Optional[date] = None
    return_ref:      Optional[str]  = None
    return_refused:  bool = False
    evidence_notes:  Optional[str]  = None

class RecallReturnOut(_Base):
    id:              UUID
    recall_id:       UUID
    customer_id:     Optional[UUID]
    lot_id:          Optional[UUID]
    qty_requested:   Optional[Decimal]
    qty_confirmed:   Optional[Decimal]
    qty_received:    Optional[Decimal]
    qty_destroyed_at_customer: Optional[Decimal]
    qty_quarantined_on_return: Optional[Decimal]
    qty_reworked:    Optional[Decimal]
    qty_written_off: Optional[Decimal]
    return_date:     Optional[date]
    return_ref:      Optional[str]
    discrepancy:     Optional[Decimal]
    return_refused:  bool
    follow_up_required: bool
    evidence_notes:  Optional[str]
    created_at:      datetime

class RecallHeaderOut(_Base):
    id:                  UUID
    recall_no:           str
    recall_type:         RecallType
    recall_reason:       str
    trigger_source:      RecallTrigger
    severity_level:      RecallSeverity
    status:              RecallStatus
    initiation_datetime: datetime
    initiated_by_id:     Optional[UUID]
    approved_by_id:      Optional[UUID]
    approved_at:         Optional[datetime]
    source_lot_id:       Optional[UUID]
    source_product_id:   Optional[UUID]
    source_material_id:  Optional[UUID]
    source_supplier_id:  Optional[UUID]
    target_market:       Optional[str]
    country_scope:       Optional[str]
    product_scope_notes: Optional[str]
    scope_calculated_at: Optional[datetime]
    contained_at:        Optional[datetime]
    completed_at:        Optional[datetime]
    closed_at:           Optional[datetime]
    total_affected_qty:  Optional[Decimal]
    total_affected_customers: Optional[int]
    recovery_pct:        Optional[Decimal]
    effectiveness_score: Optional[Decimal]
    time_to_trace_hours: Optional[Decimal]
    time_to_contain_hours: Optional[Decimal]
    notes:               Optional[str]
    created_at:          datetime
    updated_at:          datetime

class RecallDetail(RecallHeaderOut):
    scope_lines:     List[RecallScopeLineOut]
    actions:         List[RecallActionOut]
    customer_impacts: List[RecallCustomerImpactOut]
    returns:         List[RecallReturnOut]
    ai_recs:         List["TRRecAIRecommendationOut"]

class RecallRegulatoryReport(BaseModel):
    recall_no:           str
    recall_type:         RecallType
    severity_level:      RecallSeverity
    trigger_source:      RecallTrigger
    initiation_datetime: datetime
    recall_reason:       str
    source_lot_number:   Optional[str]
    total_affected_qty:  Optional[Decimal]
    total_affected_customers: Optional[int]
    affected_lots:       List[str]
    affected_markets:    str
    actions_taken:       List[str]
    recovery_pct:        Optional[Decimal]
    time_to_trace_hours: Optional[Decimal]
    time_to_contain_hours: Optional[Decimal]
    status:              RecallStatus
    summary_narrative:   str

class RecallDashboard(BaseModel):
    total_recalls:       int
    active_recalls:      int
    critical_recalls:    int
    completed_recalls:   int
    avg_time_to_trace_h: Optional[Decimal]
    avg_recovery_pct:    Optional[Decimal]
    recent_recalls:      List[RecallHeaderOut]
    pending_actions:     int
    open_scope_lines:    int


# ── AI ────────────────────────────────────────────────────────────────────────

class TRRecAIRecReview(BaseModel):
    status:         TRRecAIRecStatus
    reviewed_by_id: UUID
    review_note:    Optional[str] = None

class TRRecAIRecommendationOut(_Base):
    id:              UUID
    agent_type:      TRRecAIAgentType
    status:          TRRecAIRecStatus
    recall_id:       Optional[UUID]
    lot_id:          Optional[UUID]
    customer_id:     Optional[UUID]
    warehouse_id:    Optional[UUID]
    title:           str
    explanation:     str
    recommendation:  str
    confidence_score: Optional[Decimal]
    priority_score:  Optional[int]
    reviewed_by_id:  Optional[UUID]
    reviewed_at:     Optional[datetime]
    review_note:     Optional[str]
    created_at:      datetime

RecallDetail.model_rebuild()


# ── Communication Templates ───────────────────────────────────────────────────

class RecallTemplateCreate(BaseModel):
    name:          str
    audience:      RecallAudience
    recall_type:   Optional[str]  = None
    severity_level: Optional[str] = None
    subject:       str
    body:          str
    channel:       str = "EMAIL"
    language:      str = "en"


class RecallTemplateUpdate(BaseModel):
    name:          Optional[str] = None
    subject:       Optional[str] = None
    body:          Optional[str] = None
    channel:       Optional[str] = None
    is_active:     Optional[bool] = None


class RecallTemplateOut(_Base):
    id:            UUID
    name:          str
    audience:      RecallAudience
    recall_type:   Optional[str]
    severity_level: Optional[str]
    subject:       str
    body:          str
    channel:       str
    language:      str
    is_active:     bool
    created_at:    datetime


# ── Status Audit Log ──────────────────────────────────────────────────────────

class RecallStatusLogOut(_Base):
    id:            UUID
    recall_id:     UUID
    from_status:   Optional[str]
    to_status:     str
    changed_by_id: Optional[UUID]
    changed_by_name: Optional[str] = None
    changed_at:    datetime
    reason:        Optional[str]
    system_note:   Optional[str]


# ── Evidence Attachments ──────────────────────────────────────────────────────

class RecallEvidenceCreate(BaseModel):
    title:         str
    description:   Optional[str] = None
    file_url:      Optional[str] = None
    file_name:     Optional[str] = None
    file_type:     Optional[str] = None
    evidence_type: Optional[str] = None


class RecallEvidenceOut(_Base):
    id:            UUID
    recall_id:     UUID
    title:         str
    description:   Optional[str]
    file_url:      Optional[str]
    file_name:     Optional[str]
    file_type:     Optional[str]
    evidence_type: Optional[str]
    uploaded_by_id: Optional[UUID]
    created_at:    datetime
