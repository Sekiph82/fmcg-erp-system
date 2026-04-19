"""Pydantic schemas for Advanced Production Planning Suite."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.planning import (
    ScenarioStatus, ScenarioMode, OpQueueStatus,
    BottleneckSeverity, PlanningAgentType, PlanningRecStatus,
    SimulationStatus,
)


# ── PlanningScenario ───────────────────────────────────────────────────────────

class ScenarioCreate(BaseModel):
    scenario_name: str
    description: Optional[str] = None
    mode: ScenarioMode = ScenarioMode.FINITE
    horizon_start: Optional[date] = None
    horizon_end: Optional[date] = None
    mps_plan_id: Optional[UUID] = None

class ScenarioUpdate(BaseModel):
    scenario_name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[ScenarioMode] = None
    horizon_start: Optional[date] = None
    horizon_end: Optional[date] = None

class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    scenario_no: str
    scenario_name: str
    description: Optional[str]
    status: ScenarioStatus
    mode: ScenarioMode
    horizon_start: Optional[date]
    horizon_end: Optional[date]
    mps_plan_id: Optional[UUID]
    total_ops: int
    scheduled_ops: int
    blocked_ops: int
    avg_utilization_pct: Optional[Decimal]
    total_changeover_hrs: Optional[Decimal]
    bottleneck_count: int
    calculated_at: Optional[datetime]
    created_at: datetime

class ScenarioSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    scenario_no: str
    scenario_name: str
    status: ScenarioStatus
    mode: ScenarioMode
    horizon_start: Optional[date]
    horizon_end: Optional[date]
    total_ops: int
    scheduled_ops: int
    bottleneck_count: int
    calculated_at: Optional[datetime]


# ── ResourceCalendar ───────────────────────────────────────────────────────────

class CalendarCreate(BaseModel):
    work_center_id: UUID
    calendar_date: date
    available_hours: Decimal = Decimal("8.0")
    shift_1_start: Optional[str] = None
    shift_1_end: Optional[str] = None
    shift_2_start: Optional[str] = None
    shift_2_end: Optional[str] = None
    shift_3_start: Optional[str] = None
    shift_3_end: Optional[str] = None
    is_holiday: bool = False
    is_maintenance: bool = False
    notes: Optional[str] = None

class CalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    work_center_id: UUID
    calendar_date: date
    available_hours: Decimal
    shift_1_start: Optional[str]
    shift_1_end: Optional[str]
    shift_2_start: Optional[str]
    shift_2_end: Optional[str]
    shift_3_start: Optional[str]
    shift_3_end: Optional[str]
    is_holiday: bool
    is_maintenance: bool
    notes: Optional[str]


# ── OperationQueue ─────────────────────────────────────────────────────────────

class OpQueueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    op_no: str
    scenario_id: UUID
    mps_line_id: Optional[UUID]
    production_order_id: Optional[UUID]
    work_order_id: Optional[UUID]
    routing_step_id: Optional[UUID]
    work_center_id: Optional[UUID]
    product_id: Optional[UUID]
    product_name: Optional[str]
    product_code: Optional[str]
    work_center_name: Optional[str]
    step_name: Optional[str]
    planned_qty: Decimal
    rate_per_hour: Optional[Decimal]
    setup_minutes: int
    run_minutes: int
    cleanup_minutes: int
    changeover_minutes: int
    total_minutes: int
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    priority: int
    status: OpQueueStatus
    is_critical_path: bool
    predecessor_ids: Optional[List[str]]
    block_reason: Optional[str]


# ── CapacityLoadSnapshot ───────────────────────────────────────────────────────

class LoadSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    scenario_id: UUID
    work_center_id: UUID
    work_center_name: Optional[str]
    slot_date: date
    slot_hour: Optional[int]
    available_hours: Decimal
    allocated_hours: Decimal
    changeover_hours: Decimal
    utilization_pct: Decimal
    is_overloaded: bool
    overload_hours: Decimal

class CapacityBoardRow(BaseModel):
    work_center_id: str
    work_center_name: str
    peak_utilization_pct: float
    overloaded_days: int
    total_overload_hrs: float
    slots: List[LoadSnapshotOut]

class CapacityBoard(BaseModel):
    rows: List[CapacityBoardRow]
    overload_alerts: List[dict]
    total_ops: int
    avg_utilization_pct: float


# ── ChangeoverMatrix ───────────────────────────────────────────────────────────

class ChangeoverCreate(BaseModel):
    work_center_id: UUID
    from_family: str
    to_family: str
    changeover_minutes: int
    notes: Optional[str] = None

class ChangeoverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    work_center_id: UUID
    from_family: str
    to_family: str
    changeover_minutes: int
    notes: Optional[str]
    is_active: bool


# ── PlanningBottleneck ─────────────────────────────────────────────────────────

class BottleneckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    scenario_id: UUID
    work_center_id: Optional[UUID]
    work_center_name: Optional[str]
    severity: BottleneckSeverity
    peak_utilization_pct: Decimal
    overloaded_days: int
    total_overload_hrs: Decimal
    blocked_op_count: int
    recommendation: Optional[str]
    detected_at: Optional[datetime]
    is_resolved: bool


# ── PlanningAIRec ──────────────────────────────────────────────────────────────

class AIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    scenario_id: UUID
    agent_type: PlanningAgentType
    status: PlanningRecStatus
    title: str
    explanation: Optional[str]
    impact_summary: Optional[str]
    confidence_score: Optional[Decimal]
    affected_op_ids: Optional[List[str]]
    payload: Optional[Any]
    actioned_at: Optional[datetime]

class AIRecAction(BaseModel):
    status: PlanningRecStatus
    actioned_by_id: UUID


# ── PlanningSimulation ─────────────────────────────────────────────────────────

class SimulationCreate(BaseModel):
    sim_name: str
    description: Optional[str] = None
    changes: List[dict]   # [{op_id, field, new_value}]

class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sim_no: str
    sim_name: str
    description: Optional[str]
    scenario_id: UUID
    status: SimulationStatus
    changes: Optional[List[dict]]
    ops_rescheduled: Optional[int]
    ops_delayed: Optional[int]
    utilization_delta: Optional[Decimal]
    changeover_delta_hrs: Optional[Decimal]
    throughput_delta_pct: Optional[Decimal]
    impact_summary: Optional[str]
    computed_at: Optional[datetime]
    published_at: Optional[datetime]


# ── Dashboard ──────────────────────────────────────────────────────────────────

class PlanningDashboard(BaseModel):
    active_scenarios: int
    total_ops_today: int
    scheduled_pct: float
    avg_utilization_pct: float
    critical_bottlenecks: int
    pending_ai_recs: int
    scenarios: List[ScenarioSummary]
    top_bottlenecks: List[BottleneckOut]
    recent_ai_recs: List[AIRecOut]
