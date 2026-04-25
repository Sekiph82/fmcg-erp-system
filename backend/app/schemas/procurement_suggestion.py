"""Pydantic v2 schemas for the Procurement Suggestion Engine."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.procurement_suggestion import (
    PSAIAgentType, PSGroupStatus, PSRunStatus,
    PSSuggestionStatus, PSUrgencyLevel, SupplierItemPriority,
)


# ── SupplierItemPrice ─────────────────────────────────────────────────────────

class SupplierItemPriceCreate(BaseModel):
    supplier_id:       uuid.UUID
    material_id:       uuid.UUID
    unit_price:        Decimal
    currency:          str = "KES"
    moq:               Decimal = Decimal("1")
    pack_size:         Optional[Decimal] = None
    lead_time_days:    int = 0
    buffer_days:       int = 0
    customs_days:      int = 0
    priority:          SupplierItemPriority = SupplierItemPriority.PRIMARY
    reliability_score: Optional[Decimal] = None
    contract_no:       Optional[str] = None
    is_active:         bool = True
    valid_from:        Optional[date] = None
    valid_to:          Optional[date] = None
    notes:             Optional[str] = None


class SupplierItemPriceUpdate(BaseModel):
    unit_price:        Optional[Decimal] = None
    currency:          Optional[str] = None
    moq:               Optional[Decimal] = None
    pack_size:         Optional[Decimal] = None
    lead_time_days:    Optional[int] = None
    buffer_days:       Optional[int] = None
    customs_days:      Optional[int] = None
    priority:          Optional[SupplierItemPriority] = None
    reliability_score: Optional[Decimal] = None
    contract_no:       Optional[str] = None
    is_active:         Optional[bool] = None
    valid_from:        Optional[date] = None
    valid_to:          Optional[date] = None
    notes:             Optional[str] = None


class SupplierItemPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    supplier_id:       uuid.UUID
    material_id:       uuid.UUID
    unit_price:        Decimal
    currency:          str
    moq:               Decimal
    pack_size:         Optional[Decimal]
    lead_time_days:    int
    buffer_days:       int
    customs_days:      int
    priority:          SupplierItemPriority
    reliability_score: Optional[Decimal]
    contract_no:       Optional[str]
    is_active:         bool
    valid_from:        Optional[date]
    valid_to:          Optional[date]
    notes:             Optional[str]
    created_at:        Optional[datetime]

    supplier_name: Optional[str] = None
    material_name: Optional[str] = None
    material_code: Optional[str] = None


# ── Run ───────────────────────────────────────────────────────────────────────

class PSRunCreate(BaseModel):
    warehouse_id:          Optional[uuid.UUID] = None
    mrp_run_id:            Optional[uuid.UUID] = None
    planning_horizon_days: int = 90
    include_safety_stock:  bool = True
    include_reorder_point: bool = True
    currency:              str = "KES"
    notes:                 Optional[str] = None


class PSRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    uuid.UUID
    run_no:                str
    suggestion_date:       date
    warehouse_id:          Optional[uuid.UUID]
    mrp_run_id:            Optional[uuid.UUID]
    status:                PSRunStatus
    planning_horizon_days: int
    include_safety_stock:  bool
    include_reorder_point: bool
    suggestion_count:      Optional[int]
    total_estimated_cost:  Optional[Decimal]
    currency:              str
    error_message:         Optional[str]
    started_at:            Optional[datetime]
    completed_at:          Optional[datetime]
    created_by:            Optional[uuid.UUID]
    notes:                 Optional[str]
    created_at:            Optional[datetime]

    warehouse_name: Optional[str] = None
    mrp_run_no:     Optional[str] = None


# ── Suggestion Line ───────────────────────────────────────────────────────────

class PSLineUpdate(BaseModel):
    supplier_id:       Optional[uuid.UUID] = None
    adjusted_order_qty: Optional[Decimal] = None
    required_date:     Optional[date] = None
    urgency_level:     Optional[PSUrgencyLevel] = None
    status:            Optional[PSSuggestionStatus] = None
    notes:             Optional[str] = None


class PSLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                      uuid.UUID
    run_id:                  uuid.UUID
    material_id:             uuid.UUID
    uom:                     Optional[str]
    required_qty:            Decimal
    available_qty:           Decimal
    shortage_qty:            Decimal
    safety_stock_qty:        Decimal
    reorder_point_qty:       Decimal
    incoming_po_qty:         Decimal
    supplier_id:             Optional[uuid.UUID]
    alternative_supplier_ids: Optional[Any]
    supplier_price:          Optional[Decimal]
    currency:                str
    moq:                     Optional[Decimal]
    pack_size:               Optional[Decimal]
    adjusted_order_qty:      Decimal
    estimated_total_cost:    Optional[Decimal]
    lead_time_days:          Optional[int]
    buffer_days:             int
    required_date:           Optional[date]
    suggested_order_date:    Optional[date]
    urgency_level:           PSUrgencyLevel
    risk_flag:               bool
    risk_notes:              Optional[str]
    recommendation_score:    Optional[Decimal]
    status:                  PSSuggestionStatus
    mrp_suggestion_id:       Optional[uuid.UUID]
    group_id:                Optional[uuid.UUID]
    converted_pr_id:         Optional[uuid.UUID]
    notes:                   Optional[str]
    created_at:              Optional[datetime]

    material_name:    Optional[str] = None
    material_code:    Optional[str] = None
    supplier_name:    Optional[str] = None


# ── Group ─────────────────────────────────────────────────────────────────────

class PSGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   uuid.UUID
    run_id:               uuid.UUID
    supplier_id:          uuid.UUID
    group_no:             Optional[str]
    target_delivery_date: Optional[date]
    line_count:           int
    total_estimated_cost: Optional[Decimal]
    currency:             str
    status:               PSGroupStatus
    converted_pr_id:      Optional[uuid.UUID]
    notes:                Optional[str]
    created_at:           Optional[datetime]

    supplier_name: Optional[str] = None
    lines:         List[PSLineOut] = []


# ── Convert group → PR ────────────────────────────────────────────────────────

class ConvertGroupToPRRequest(BaseModel):
    group_id:      uuid.UUID
    required_date: date
    notes:         Optional[str] = None


# ── AI Recommendation ─────────────────────────────────────────────────────────

class PSAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    run_id:           uuid.UUID
    agent_type:       PSAIAgentType
    material_id:      Optional[uuid.UUID]
    supplier_id:      Optional[uuid.UUID]
    title:            str
    recommendation:   str
    rationale:        Optional[str]
    potential_saving: Optional[Decimal]
    priority:         int
    is_actioned:      bool
    action_notes:     Optional[str]
    created_at:       Optional[datetime]

    material_name: Optional[str] = None
    supplier_name: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class PSDashboard(BaseModel):
    total_runs:           int
    latest_run_no:        Optional[str]
    latest_run_status:    Optional[str]
    open_suggestions:     int
    critical_suggestions: int
    high_suggestions:     int
    risk_flagged:         int
    total_estimated_cost: Decimal
    approved_count:       int
    converted_count:      int
    supplier_count:       int
    supplier_items_count: int
    ai_recs_count:        int


# ── Supplier compare (for a material) ────────────────────────────────────────

class SupplierCompareRow(BaseModel):
    supplier_id:       uuid.UUID
    supplier_name:     str
    supplier_code:     str
    priority:          str
    unit_price:        Decimal
    currency:          str
    moq:               Decimal
    lead_time_days:    int
    total_lead_days:   int  # lead + buffer + customs
    reliability_score: Optional[Decimal]
    contract_no:       Optional[str]
    performance_score: Optional[Decimal]
    is_preferred:      bool
    score:             Decimal  # composite selection score 0-100


class SupplierCompareResult(BaseModel):
    material_id:   uuid.UUID
    material_name: str
    material_code: str
    suppliers:     List[SupplierCompareRow]
    recommended_supplier_id: Optional[uuid.UUID]


# ── Shortage report row ───────────────────────────────────────────────────────

class ShortageReportRow(BaseModel):
    material_id:       uuid.UUID
    material_code:     str
    material_name:     str
    uom:               Optional[str]
    available_qty:     Decimal
    required_qty:      Decimal
    shortage_qty:      Decimal
    safety_stock_qty:  Decimal
    reorder_point_qty: Decimal
    urgency_level:     str
    risk_flag:         bool
    suggested_order_date: Optional[date]
    required_date:     Optional[date]
    supplier_name:     Optional[str]
    estimated_cost:    Optional[Decimal]
