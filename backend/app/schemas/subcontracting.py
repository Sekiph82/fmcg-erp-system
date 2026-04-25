"""Pydantic v2 schemas for the Subcontracting System."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.subcontracting import (
    SCAIAgentType, SCIssueStatus, SCOrderStatus,
    SCReceiptStatus, SCYieldStatus, ScrapReasonCode,
)


# ── SubcontractorLocation ─────────────────────────────────────────────────────

class SubcontractorLocationCreate(BaseModel):
    supplier_id:  uuid.UUID
    warehouse_id: uuid.UUID
    notes:        Optional[str] = None


class SubcontractorLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           uuid.UUID
    supplier_id:  uuid.UUID
    warehouse_id: uuid.UUID
    is_active:    bool
    notes:        Optional[str]
    created_at:   Optional[datetime]
    supplier_name:  Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None


# ── Order ─────────────────────────────────────────────────────────────────────

class SCOrderLineCreate(BaseModel):
    line_no:            int
    product_id:         Optional[uuid.UUID] = None
    material_id:        Optional[uuid.UUID] = None
    description:        Optional[str] = None
    quantity_ordered:   Decimal
    uom:                str = "KG"
    bom_id:             Optional[uuid.UUID] = None
    service_unit_cost:  Optional[Decimal] = None
    estimated_yield_pct: Optional[Decimal] = Decimal("100")
    notes:              Optional[str] = None


class SCOrderCreate(BaseModel):
    supplier_id:              uuid.UUID
    order_date:               date
    expected_completion_date: Optional[date] = None
    warehouse_id:             Optional[uuid.UUID] = None
    linked_po_id:             Optional[uuid.UUID] = None
    currency:                 str = "KES"
    remarks:                  Optional[str] = None
    lines:                    List[SCOrderLineCreate] = []


class SCOrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    order_id:            uuid.UUID
    line_no:             int
    product_id:          Optional[uuid.UUID]
    material_id:         Optional[uuid.UUID]
    description:         Optional[str]
    quantity_ordered:    Decimal
    quantity_received:   Decimal
    uom:                 str
    bom_id:              Optional[uuid.UUID]
    service_unit_cost:   Optional[Decimal]
    estimated_yield_pct: Optional[Decimal]
    notes:               Optional[str]
    product_name:  Optional[str] = None
    material_name: Optional[str] = None


class SCOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                       uuid.UUID
    order_no:                 str
    supplier_id:              uuid.UUID
    order_date:               date
    expected_completion_date: Optional[date]
    actual_completion_date:   Optional[date]
    status:                   SCOrderStatus
    linked_po_id:             Optional[uuid.UUID]
    warehouse_id:             Optional[uuid.UUID]
    subcontractor_location_id: Optional[uuid.UUID]
    total_material_cost:      Optional[Decimal]
    total_service_cost:       Optional[Decimal]
    total_wastage_cost:       Optional[Decimal]
    currency:                 str
    approved_by_id:           Optional[uuid.UUID]
    approved_at:              Optional[datetime]
    created_by_id:            Optional[uuid.UUID]
    remarks:                  Optional[str]
    created_at:               Optional[datetime]
    supplier_name:  Optional[str] = None
    warehouse_name: Optional[str] = None
    lines:          List[SCOrderLineOut] = []


# ── Material Issue ────────────────────────────────────────────────────────────

class SCIssueLineCreate(BaseModel):
    line_no:          int
    material_id:      uuid.UUID
    lot_id:           Optional[uuid.UUID] = None
    quantity_issued:  Decimal
    uom:              str = "KG"
    unit_cost:        Optional[Decimal] = None
    notes:            Optional[str] = None


class SCIssueCreate(BaseModel):
    order_id:   uuid.UUID
    issue_date: date
    notes:      Optional[str] = None
    lines:      List[SCIssueLineCreate] = []


class SCIssueLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    issue_id:          uuid.UUID
    line_no:           int
    material_id:       uuid.UUID
    lot_id:            Optional[uuid.UUID]
    quantity_issued:   Decimal
    quantity_returned: Decimal
    quantity_consumed: Decimal
    quantity_scrapped: Decimal
    uom:               str
    unit_cost:         Optional[Decimal]
    stock_movement_id: Optional[uuid.UUID]
    notes:             Optional[str]
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    lot_number:    Optional[str] = None


class SCIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          uuid.UUID
    issue_no:    str
    order_id:    uuid.UUID
    issue_date:  date
    status:      SCIssueStatus
    issued_by_id: Optional[uuid.UUID]
    notes:       Optional[str]
    created_at:  Optional[datetime]
    lines:       List[SCIssueLineOut] = []


# ── Receipt ───────────────────────────────────────────────────────────────────

class SCReceiptLineCreate(BaseModel):
    line_no:           int
    order_line_id:     Optional[uuid.UUID] = None
    product_id:        Optional[uuid.UUID] = None
    material_id:       Optional[uuid.UUID] = None
    quantity_received: Decimal
    quantity_accepted: Optional[Decimal] = None
    quantity_rejected: Decimal = Decimal("0")
    uom:               str = "KG"
    lot_number:        Optional[str] = None
    expiry_date:       Optional[date] = None
    unit_service_cost: Optional[Decimal] = None
    notes:             Optional[str] = None


class SCReceiptCreate(BaseModel):
    order_id:          uuid.UUID
    receipt_date:      date
    qc_inspection_id:  Optional[uuid.UUID] = None
    notes:             Optional[str] = None
    lines:             List[SCReceiptLineCreate] = []


class SCReceiptLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    receipt_id:        uuid.UUID
    order_line_id:     Optional[uuid.UUID]
    line_no:           int
    product_id:        Optional[uuid.UUID]
    material_id:       Optional[uuid.UUID]
    quantity_received: Decimal
    quantity_accepted: Decimal
    quantity_rejected: Decimal
    uom:               str
    lot_number:        Optional[str]
    expiry_date:       Optional[date]
    unit_service_cost: Optional[Decimal]
    stock_movement_id: Optional[uuid.UUID]
    notes:             Optional[str]
    product_name:  Optional[str] = None
    material_name: Optional[str] = None


class SCReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    receipt_no:       str
    order_id:         uuid.UUID
    receipt_date:     date
    status:           SCReceiptStatus
    received_by_id:   Optional[uuid.UUID]
    qc_inspection_id: Optional[uuid.UUID]
    notes:            Optional[str]
    created_at:       Optional[datetime]
    lines:            List[SCReceiptLineOut] = []


# ── Yield Record ──────────────────────────────────────────────────────────────

class SCYieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                      uuid.UUID
    order_id:                uuid.UUID
    order_line_id:           uuid.UUID
    total_material_issued:   Decimal
    expected_material_input: Optional[Decimal]
    quantity_ordered:        Decimal
    quantity_received:       Decimal
    expected_yield_pct:      Optional[Decimal]
    actual_yield_pct:        Optional[Decimal]
    yield_variance_pct:      Optional[Decimal]
    yield_status:            SCYieldStatus
    total_scrapped:          Decimal
    scrap_reason:            Optional[ScrapReasonCode]
    scrap_cost:              Optional[Decimal]
    material_variance_qty:   Optional[Decimal]
    material_variance_cost:  Optional[Decimal]
    is_abnormal:             bool
    notes:                   Optional[str]


# ── Performance ───────────────────────────────────────────────────────────────

class SCPerformanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    order_id:            uuid.UUID
    supplier_id:         uuid.UUID
    planned_completion:  Optional[date]
    actual_completion:   Optional[date]
    delay_days:          Optional[int]
    on_time:             Optional[bool]
    total_qty_ordered:   Decimal
    total_qty_received:  Decimal
    total_qty_rejected:  Decimal
    rejection_rate_pct:  Optional[Decimal]
    avg_yield_pct:       Optional[Decimal]
    budgeted_cost:       Optional[Decimal]
    actual_cost:         Optional[Decimal]
    cost_variance_pct:   Optional[Decimal]
    performance_score:   Optional[Decimal]
    notes:               Optional[str]
    supplier_name: Optional[str] = None
    order_no:      Optional[str] = None


# ── AI Rec ────────────────────────────────────────────────────────────────────

class SCAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    order_id:         Optional[uuid.UUID]
    supplier_id:      Optional[uuid.UUID]
    agent_type:       SCAIAgentType
    title:            str
    recommendation:   str
    rationale:        Optional[str]
    risk_level:       Optional[str]
    potential_saving: Optional[Decimal]
    priority:         int
    is_actioned:      bool
    action_notes:     Optional[str]
    created_at:       Optional[datetime]
    supplier_name: Optional[str] = None
    order_no:      Optional[str] = None


# ── Subcontractor Stock View ──────────────────────────────────────────────────

class SubcontractorStockRow(BaseModel):
    supplier_id:    uuid.UUID
    supplier_name:  str
    material_id:    uuid.UUID
    material_code:  str
    material_name:  str
    uom:            Optional[str]
    qty_issued:     Decimal
    qty_returned:   Decimal
    qty_consumed:   Decimal
    qty_scrapped:   Decimal
    qty_balance:    Decimal   # issued - returned - consumed - scrapped
    unit_cost:      Optional[Decimal]
    total_value:    Optional[Decimal]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class SCDashboard(BaseModel):
    total_orders:        int
    draft_orders:        int
    active_orders:       int
    completed_orders:    int
    overdue_orders:      int
    total_material_issued_value: Decimal
    avg_yield_pct:       Optional[Decimal]
    total_scrap_cost:    Decimal
    ai_recs_count:       int
    supplier_count:      int
    locations_count:     int
