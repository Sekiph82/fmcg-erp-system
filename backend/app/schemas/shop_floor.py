from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Session ────────────────────────────────────────────────────────────────────

class SFSessionCreate(BaseModel):
    operator_name: str
    work_center_id: Optional[UUID] = None
    line_id: Optional[str] = None
    shift_id: Optional[UUID] = None
    machine_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    notes: Optional[str] = None


class SFSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_code: str
    operator_id: Optional[UUID]
    operator_name: str
    team_id: Optional[UUID]
    machine_id: Optional[UUID]
    line_id: Optional[str]
    work_center_id: Optional[UUID]
    shift_id: Optional[UUID]
    login_time: datetime
    logout_time: Optional[datetime]
    current_work_order_id: Optional[UUID]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# ── Activity Log ───────────────────────────────────────────────────────────────

class WOActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    production_order_id: Optional[UUID]
    session_id: Optional[UUID]
    operator_name: Optional[str]
    line_id: Optional[str]
    event_type: str
    timestamp_start: datetime
    timestamp_end: Optional[datetime]
    duration_minutes: Optional[Decimal]
    qty_good: Optional[Decimal]
    qty_scrap: Optional[Decimal]
    qty_rework: Optional[Decimal]
    reason_code: Optional[str]
    remarks: Optional[str]
    extra_data: Optional[dict]
    created_at: datetime


# ── Downtime ───────────────────────────────────────────────────────────────────

class SFDowntimeCreate(BaseModel):
    work_order_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    machine_id: Optional[UUID] = None
    machine_name: Optional[str] = None
    line_id: Optional[str] = None
    operator_name: Optional[str] = None
    downtime_category: str
    root_reason: Optional[str] = None
    impact_level: str = "MEDIUM"
    comments: Optional[str] = None


class SFDowntimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: Optional[UUID]
    production_order_id: Optional[UUID]
    machine_id: Optional[UUID]
    machine_name: Optional[str]
    line_id: Optional[str]
    operator_name: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[Decimal]
    is_closed: bool
    downtime_category: str
    root_reason: Optional[str]
    impact_level: str
    comments: Optional[str]
    created_at: datetime


# ── Shift Handover ─────────────────────────────────────────────────────────────

class ShiftHandoverCreate(BaseModel):
    line_id: Optional[str] = None
    work_center_id: Optional[UUID] = None
    shift_from_id: Optional[UUID] = None
    shift_to_id: Optional[UUID] = None
    shift_from_name: Optional[str] = None
    shift_to_name: Optional[str] = None
    outgoing_supervisor: Optional[str] = None
    incoming_supervisor: Optional[str] = None
    outgoing_operators: Optional[List[str]] = None
    incoming_operators: Optional[List[str]] = None
    open_work_orders: Optional[List[dict]] = None
    qty_completed: Optional[Decimal] = None
    qty_remaining: Optional[Decimal] = None
    issues_open: Optional[List[str]] = None
    qc_pending_items: Optional[List[str]] = None
    material_shortages: Optional[List[str]] = None
    notes: Optional[str] = None


class ShiftHandoverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_id: Optional[str]
    work_center_id: Optional[UUID]
    shift_from_name: Optional[str]
    shift_to_name: Optional[str]
    outgoing_supervisor: Optional[str]
    incoming_supervisor: Optional[str]
    outgoing_operators: Optional[list]
    incoming_operators: Optional[list]
    open_work_orders: Optional[list]
    qty_completed: Optional[Decimal]
    qty_remaining: Optional[Decimal]
    issues_open: Optional[list]
    qc_pending_items: Optional[list]
    material_shortages: Optional[list]
    notes: Optional[str]
    handover_time: datetime
    is_approved: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime


# ── Supervisor Override ────────────────────────────────────────────────────────

class SupervisorOverrideCreate(BaseModel):
    work_order_id: Optional[UUID] = None
    production_order_id: Optional[UUID] = None
    supervisor_name: str
    override_type: str
    reason: Optional[str] = None
    target_operator_name: Optional[str] = None
    notes: Optional[str] = None


class SupervisorOverrideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: Optional[UUID]
    production_order_id: Optional[UUID]
    supervisor_name: str
    override_type: str
    reason: Optional[str]
    target_operator_name: Optional[str]
    approved_at: datetime
    notes: Optional[str]
    created_at: datetime


# ── Action Requests ────────────────────────────────────────────────────────────

class StartWORequest(BaseModel):
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None
    line_id: Optional[str] = None
    machine_id: Optional[UUID] = None


class PauseWORequest(BaseModel):
    session_id: Optional[UUID] = None
    reason_code: Optional[str] = None
    remarks: Optional[str] = None
    operator_name: Optional[str] = None


class ResumeWORequest(BaseModel):
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None


class QtyUpdateRequest(BaseModel):
    qty_good: Decimal
    qty_scrap: Decimal = Decimal("0")
    qty_rework: Decimal = Decimal("0")
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None
    remarks: Optional[str] = None


class ScrapRequest(BaseModel):
    qty_scrap: Decimal
    reason_code: Optional[str] = None
    remarks: Optional[str] = None
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None


class FinishWORequest(BaseModel):
    qty_good: Decimal
    qty_scrap: Decimal = Decimal("0")
    qty_rework: Decimal = Decimal("0")
    run_time_actual: Optional[Decimal] = None
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None
    remarks: Optional[str] = None


class HelpRequest(BaseModel):
    remarks: str
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None


class QCTriggerRequest(BaseModel):
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None
    remarks: Optional[str] = None


class NoteRequest(BaseModel):
    remarks: str
    session_id: Optional[UUID] = None
    operator_name: Optional[str] = None


class StopDowntimeRequest(BaseModel):
    comments: Optional[str] = None


# ── Live Queue & Status ────────────────────────────────────────────────────────

class LiveWOItem(BaseModel):
    id: str
    work_order_id: str
    production_order_id: Optional[str]
    order_no: Optional[str]
    step_sequence: int
    step_name: str
    work_center_id: Optional[str]
    line_id: Optional[str]
    planned_qty: float
    completed_qty: float
    scrap_qty: float
    status: str               # from ExecWorkOrder
    live_status: str          # derived shop floor status
    started_at: Optional[str]
    planned_start: Optional[str]
    planned_end: Optional[str]
    product_name: Optional[str]
    batch_no: Optional[str]
    qc_required_flag: bool
    has_active_downtime: bool
    last_event: Optional[str]
    last_event_time: Optional[str]
    operator_name: Optional[str]


class LiveStatusResponse(BaseModel):
    total_work_orders: int
    running: int
    paused: int
    waiting: int
    qc_hold: int
    active_sessions: int
    active_downtime: int
    alerts: List[dict]
    by_line: Dict[str, Any]
    timestamp: str


# ── AI ─────────────────────────────────────────────────────────────────────────

class SFAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: Optional[UUID]
    production_order_id: Optional[UUID]
    agent_type: str
    status: str
    title: str
    explanation: Optional[str]
    impact_summary: Optional[str]
    confidence_score: Optional[Decimal]
    actioned_at: Optional[datetime]
    created_at: datetime


# ── Dashboard ──────────────────────────────────────────────────────────────────

class SFDashboard(BaseModel):
    active_sessions: int
    running_work_orders: int
    paused_work_orders: int
    qc_hold_count: int
    active_downtime_count: int
    help_requests_open: int
    total_scrap_today: float
    total_good_qty_today: float
    pending_ai_recs: int
    recent_handovers: List[ShiftHandoverOut]
    active_downtimes: List[SFDowntimeOut]
    supervisor_overrides_today: int
