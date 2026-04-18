"""MPS — Pydantic v2 schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, List
from pydantic import BaseModel, ConfigDict

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
    planned_production_qty: Optional[Decimal] = None
    work_center_id: Optional[uuid.UUID] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    priority_score: Optional[Decimal] = None
    feasibility_status: Optional[MPSFeasibilityStatus] = None
    is_locked: Optional[bool] = None
    remarks: Optional[str] = None


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
