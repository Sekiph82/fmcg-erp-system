"""MPS — Pydantic v2 schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field

from app.models.mps import (
    MPSPlanningMode, MPSCapacityMode, MPSStatus, MPSFeasibilityStatus,
    MPSAgentType, MPSRecType, MPSRecStatus, WhatIfStatus, MPSChangeType,
)


_CFG = ConfigDict(from_attributes=True)


# ── Plan ──────────────────────────────────────────────────────────────────────

class MPSPlanCreate(BaseModel):
    plan_name: str
    plant_code: Optional[str] = None
    planning_horizon_days: int = 90
    start_date: date
    end_date: date
    planning_mode: MPSPlanningMode = MPSPlanningMode.ASSISTED
    capacity_mode: MPSCapacityMode = MPSCapacityMode.FINITE
    mrp_run_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class MPSPlanOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    plan_no: str
    plan_name: str
    plant_code: Optional[str]
    planning_horizon_days: int
    start_date: date
    end_date: date
    planning_mode: MPSPlanningMode
    capacity_mode: MPSCapacityMode
    status: MPSStatus
    mrp_run_id: Optional[uuid.UUID]
    total_lines: int
    overloaded_lines: int
    feasible_lines: int
    locked_lines: int
    approved_at: Optional[datetime]
    released_at: Optional[datetime]
    created_by_id: Optional[uuid.UUID]
    approved_by_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class MPSPlanSummary(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    plan_no: str
    plan_name: str
    status: MPSStatus
    planning_mode: MPSPlanningMode
    capacity_mode: MPSCapacityMode
    start_date: date
    end_date: date
    total_lines: int
    overloaded_lines: int
    feasible_lines: int
    created_at: datetime


# ── Lines ──────────────────────────────────────────────────────────────────────

class MPSLineUpdate(BaseModel):
    """Planner-editable fields only. feasibility_status and is_locked are
    engine-controlled (set by capacity scheduling / regeneration) and must
    not be forgeable through a generic line PATCH — see M20.S01.T001 F4.
    Clearing an ON_HOLD line is an explicit, audited planner action."""
    planned_production_qty: Optional[Decimal] = None
    work_center_id: Optional[uuid.UUID] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    priority_score: Optional[Decimal] = None
    remarks: Optional[str] = None
    clear_hold: bool = False


class MPSLineOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    line_no: str
    mps_id: uuid.UUID
    product_id: uuid.UUID
    mrp_result_id: Optional[uuid.UUID]
    period_label: Optional[str]
    period_start: date
    period_end: date
    confirmed_demand_qty: Decimal
    forecast_qty: Decimal
    safety_stock_qty: Decimal
    net_requirement_qty: Decimal
    planned_production_qty: Decimal
    batch_size_qty: Optional[Decimal]
    num_batches: Optional[int]
    work_center_id: Optional[uuid.UUID]
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    required_hours: Optional[Decimal]
    campaign_id: Optional[uuid.UUID]
    priority_score: Decimal
    feasibility_status: MPSFeasibilityStatus
    overload_hours: Optional[Decimal]
    is_locked: bool
    remarks: Optional[str]
    production_order_id: Optional[uuid.UUID]
    # denormalized
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    work_center_name: Optional[str] = None


class MPSConstraintIssueOut(BaseModel):
    """One persisted, line-specific MPS constraint reason."""
    reason_code: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    provenance: str
    required_date: Optional[date] = None
    planned_quantity: Optional[Decimal] = None
    material_id: Optional[str] = None
    material_code: Optional[str] = None
    required_qty: Optional[Decimal] = None
    available_qty: Optional[Decimal] = None
    shortage_qty: Optional[Decimal] = None
    uom: Optional[str] = None
    lead_time_days: Optional[int] = None
    latest_order_date: Optional[date] = None
    substitution_policy: Optional[str] = None
    substitute_group_id: Optional[str] = None
    excluded_receipts: List[dict[str, str]] = Field(default_factory=list)
    message: Optional[str] = None
    bom_id: Optional[str] = None
    bom_ids: Optional[List[str]] = None
    recipe_id: Optional[str] = None
    recipe_ids: Optional[List[str]] = None
    work_center_id: Optional[str] = None
    capacity_uom: Optional[str] = None
    product_uom: Optional[str] = None
    capacity_date: Optional[date] = Field(default=None, alias="date")
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    dates: Optional[List[date]] = None
    required_hours: Optional[Decimal] = None
    available_hours: Optional[Decimal] = None
    downtime_hours: Optional[Decimal] = None
    overload_hours: Optional[Decimal] = None
    capacity_slot_id: Optional[uuid.UUID] = None
    capacity_slot_key: Optional[str] = None
    slot_required_hours: Optional[Decimal] = None
    net_available_hours: Optional[Decimal] = None
    affected_line_ids: List[uuid.UUID] = Field(default_factory=list)
    scenario_id: Optional[uuid.UUID] = None
    scenario_provenance: Optional[str] = None


class MPSLineConstraintDetailsOut(BaseModel):
    reason_codes: List[str]
    issues: List[MPSConstraintIssueOut]
    status: MPSFeasibilityStatus
    plan_id: uuid.UUID
    warehouse_id: Optional[uuid.UUID] = None
    demand_run_id: Optional[uuid.UUID] = None
    line_no: Optional[str] = None
    planned_quantity: Optional[Decimal] = None
    required_date: Optional[date] = None
    evaluation_kind: Optional[str] = None
    capacity_mode: Optional[str] = None
    recalculation_state: Optional[Literal["CURRENT", "SUPERSEDED", "NOT_APPLICABLE"]] = None
    superseded_by_run_id: Optional[uuid.UUID] = None
    scenario_id: Optional[uuid.UUID] = None
    scenario_provenance: Optional[str] = None
    capacity_slot_ids: List[uuid.UUID] = Field(default_factory=list)


class MPSLineConstraintDiagnosticOut(BaseModel):
    line_id: uuid.UUID
    run_id: uuid.UUID
    source_version: str
    diagnostics: MPSLineConstraintDetailsOut
    computed_at: Optional[datetime] = None


# ── Campaign ──────────────────────────────────────────────────────────────────

class MPSCampaignOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    campaign_code: str
    campaign_name: str
    mps_id: uuid.UUID
    work_center_id: Optional[uuid.UUID]
    campaign_start: Optional[date]
    campaign_end: Optional[date]
    total_production_hrs: Decimal
    total_changeover_hrs: Decimal
    sequence_order: int
    sku_count: int
    notes: Optional[str]


# ── Capacity Heatmap ──────────────────────────────────────────────────────────

class CapacitySlotOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    work_center_id: uuid.UUID
    slot_date: date
    available_hours: Decimal
    allocated_hours: Decimal
    downtime_hours: Decimal
    overload_hours: Decimal
    utilization_pct: Decimal
    is_overloaded: bool
    work_center_name: Optional[str] = None


class CapacityHeatmapRow(BaseModel):
    work_center_id: uuid.UUID
    work_center_name: str
    slots: List[CapacitySlotOut]
    peak_utilization_pct: float
    overloaded_days: int


class CapacityHeatmap(BaseModel):
    mps_id: uuid.UUID
    rows: List[CapacityHeatmapRow]
    overload_alerts: List[dict]


# ── What-If ───────────────────────────────────────────────────────────────────

class WhatIfChange(BaseModel):
    line_id: uuid.UUID
    change_type: MPSChangeType
    new_value: Any  # e.g. new date string, new qty, new work_center_id


class MPSWhatIfCreate(BaseModel):
    scenario_name: str
    description: Optional[str] = None
    changes: List[WhatIfChange]


class MPSWhatIfOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    scenario_no: str
    scenario_name: str
    mps_id: uuid.UUID
    description: Optional[str]
    changes: Any
    impact_service_level_pct: Optional[Decimal]
    impact_delay_count: Optional[int]
    impact_cost_delta: Optional[Decimal]
    impact_cost_currency: Optional[str]
    impact_summary: Optional[str]
    status: WhatIfStatus
    created_by_id: Optional[uuid.UUID]
    created_at: datetime


# ── AI Recommendations ────────────────────────────────────────────────────────

class MPSAIRecOut(BaseModel):
    model_config = _CFG
    id: uuid.UUID
    mps_id: uuid.UUID
    agent_type: MPSAgentType
    rec_type: MPSRecType
    affected_line_ids: Any
    recommendation: str
    impact_summary: Optional[str]
    confidence_score: Decimal
    status: MPSRecStatus
    reviewed_by_id: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────

class MPSDashboard(BaseModel):
    active_plans: int
    total_lines: int
    overloaded_lines: int
    feasible_lines: int
    pending_ai_recs: int
    pending_approvals: int
    overload_alerts: List[dict]
    recent_plans: List[MPSPlanSummary]


# ── Generate from MRP ─────────────────────────────────────────────────────────

class GenerateFromMRPRequest(BaseModel):
    mrp_run_id: uuid.UUID
    period_type: str = "WEEKLY"  # WEEKLY / MONTHLY / DAILY
    respect_batch_sizes: bool = True
    default_batch_qty: Optional[Decimal] = None
