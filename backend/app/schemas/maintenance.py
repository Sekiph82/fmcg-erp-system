from __future__ import annotations

from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

from app.models.maintenance import (
    AssetStatus, PMFrequency, PMStatus,
    BreakdownSeverity, BreakdownStatus,
)


# ── Asset ──────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    asset_no: str
    name: str
    description: Optional[str] = None
    asset_type: Optional[str] = None
    line: Optional[str] = None
    serial_no: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    location: Optional[str] = None
    status: AssetStatus = AssetStatus.ACTIVE
    notes: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[str] = None
    line: Optional[str] = None
    serial_no: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    location: Optional[str] = None
    status: Optional[AssetStatus] = None
    notes: Optional[str] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_no: str
    name: str
    description: Optional[str] = None
    asset_type: Optional[str] = None
    line: Optional[str] = None
    serial_no: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    location: Optional[str] = None
    status: AssetStatus
    notes: Optional[str] = None
    created_at: datetime


# ── PM Plan ────────────────────────────────────────────────────────────────────

class PMPlanCreate(BaseModel):
    asset_id: str
    name: str
    description: Optional[str] = None
    frequency: PMFrequency = PMFrequency.MONTHLY
    interval_days: Optional[int] = None
    estimated_duration_minutes: Optional[int] = None
    checklist: Optional[str] = None
    assigned_to: Optional[str] = None
    next_due_date: Optional[date] = None


class PMPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[PMFrequency] = None
    interval_days: Optional[int] = None
    estimated_duration_minutes: Optional[int] = None
    checklist: Optional[str] = None
    assigned_to: Optional[str] = None
    next_due_date: Optional[date] = None
    is_active: Optional[bool] = None


class PMPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    asset_name: Optional[str] = None
    asset_no: Optional[str] = None
    name: str
    description: Optional[str] = None
    frequency: PMFrequency
    interval_days: Optional[int] = None
    estimated_duration_minutes: Optional[int] = None
    is_active: bool
    checklist: Optional[str] = None
    assigned_to: Optional[str] = None
    last_completed_date: Optional[date] = None
    next_due_date: Optional[date] = None
    created_at: datetime


# ── PM Work Order ──────────────────────────────────────────────────────────────

class PMWorkOrderCreate(BaseModel):
    plan_id: str
    scheduled_date: date
    technician: Optional[str] = None


class PMWorkOrderUpdate(BaseModel):
    status: Optional[PMStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    technician: Optional[str] = None
    checklist_notes: Optional[str] = None


class PMWorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    wo_no: str
    plan_id: str
    plan_name: Optional[str] = None
    asset_id: Optional[str] = None
    asset_name: Optional[str] = None
    scheduled_date: date
    status: PMStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    technician: Optional[str] = None
    checklist_notes: Optional[str] = None
    created_at: datetime


# ── Breakdown Record ───────────────────────────────────────────────────────────

class BreakdownCreate(BaseModel):
    asset_id: str
    production_order_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: str
    root_cause: Optional[str] = None
    severity: BreakdownSeverity = BreakdownSeverity.MEDIUM
    corrective_action: Optional[str] = None


class BreakdownUpdate(BaseModel):
    end_time: Optional[datetime] = None
    downtime_minutes: Optional[int] = None
    root_cause: Optional[str] = None
    severity: Optional[BreakdownSeverity] = None
    status: Optional[BreakdownStatus] = None
    corrective_action: Optional[str] = None
    resolved_by_id: Optional[str] = None


class BreakdownRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    breakdown_no: str
    asset_id: str
    asset_name: Optional[str] = None
    asset_no: Optional[str] = None
    production_order_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    downtime_minutes: Optional[int] = None
    reason: str
    root_cause: Optional[str] = None
    severity: BreakdownSeverity
    status: BreakdownStatus
    corrective_action: Optional[str] = None
    created_at: datetime


# ── Spare Part ─────────────────────────────────────────────────────────────────

class SparePartCreate(BaseModel):
    part_no: str
    name: str
    description: Optional[str] = None
    unit: str = "pcs"
    material_id: Optional[str] = None
    current_stock: float = 0
    reorder_level: Optional[float] = None
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    lead_time_days: Optional[int] = None


class SparePartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    current_stock: Optional[float] = None
    reorder_level: Optional[float] = None
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None


class SparePartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_no: str
    name: str
    description: Optional[str] = None
    unit: str
    material_id: Optional[str] = None
    current_stock: float
    reorder_level: Optional[float] = None
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    lead_time_days: Optional[int] = None
    is_active: bool
    created_at: datetime


# ── Spare Part Usage ───────────────────────────────────────────────────────────

class SparePartUsageCreate(BaseModel):
    spare_part_id: str
    asset_id: str
    breakdown_id: Optional[str] = None
    pm_work_order_id: Optional[str] = None
    quantity_used: float
    unit_cost: Optional[float] = None
    notes: Optional[str] = None


class SparePartUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    spare_part_id: str
    spare_part_name: Optional[str] = None
    asset_id: str
    asset_name: Optional[str] = None
    breakdown_id: Optional[str] = None
    pm_work_order_id: Optional[str] = None
    quantity_used: float
    unit_cost: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime


# ── Reports ────────────────────────────────────────────────────────────────────

class MtbfMttrRow(BaseModel):
    asset_id: str
    asset_no: str
    asset_name: str
    line: Optional[str]
    breakdown_count: int
    total_downtime_minutes: int
    avg_downtime_minutes: float      # MTTR
    mtbf_days: Optional[float]       # mean time between failures


class DowntimeByMachineRow(BaseModel):
    asset_id: str
    asset_no: str
    asset_name: str
    line: Optional[str]
    breakdown_count: int
    total_downtime_minutes: int
    open_breakdowns: int


class OverduePMRow(BaseModel):
    plan_id: str
    asset_id: str
    asset_no: str
    asset_name: str
    plan_name: str
    frequency: PMFrequency
    next_due_date: Optional[date]
    days_overdue: int
