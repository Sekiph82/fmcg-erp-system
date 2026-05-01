from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.cycle_count import (
    ABCClass, AdjustmentStatus, PlanStatus, PlanType, TaskStatus,
)


# ── Plan ─────────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    plan_code: str
    name: str
    warehouse_id: UUID
    plan_type: PlanType
    frequency_days: Optional[int] = None
    abc_classes: Optional[str] = "ABC"
    variance_tolerance_pct: Decimal = Decimal("2.0")
    auto_approve_within_tolerance: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[PlanStatus] = None
    frequency_days: Optional[int] = None
    abc_classes: Optional[str] = None
    variance_tolerance_pct: Optional[Decimal] = None
    auto_approve_within_tolerance: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class PlanOut(BaseModel):
    id: UUID
    plan_code: str
    name: str
    warehouse_id: UUID
    plan_type: PlanType
    status: PlanStatus
    frequency_days: Optional[int] = None
    abc_classes: Optional[str] = None
    variance_tolerance_pct: Decimal
    auto_approve_within_tolerance: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Task ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    plan_id: UUID
    warehouse_id: UUID
    location_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    abc_class: Optional[ABCClass] = None
    scheduled_date: date
    assigned_to_id: Optional[UUID] = None
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    assigned_to_id: Optional[UUID] = None
    status: Optional[TaskStatus] = None
    scheduled_date: Optional[date] = None
    notes: Optional[str] = None


class TaskOut(BaseModel):
    id: UUID
    task_no: str
    plan_id: UUID
    warehouse_id: UUID
    location_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    abc_class: Optional[ABCClass] = None
    scheduled_date: date
    assigned_to_id: Optional[UUID] = None
    status: TaskStatus
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Count Entry ───────────────────────────────────────────────────────────────

class CountEntryCreate(BaseModel):
    task_id: UUID
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    counted_qty: Decimal
    unit: str = "KG"
    unit_cost: Optional[Decimal] = None
    root_cause: Optional[str] = None


class CountEntryOut(BaseModel):
    id: UUID
    task_id: UUID
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    system_qty: Decimal
    counted_qty: Decimal
    variance_qty: Decimal
    variance_pct: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    variance_value: Optional[Decimal] = None
    unit: str
    within_tolerance: bool
    root_cause: Optional[str] = None
    counted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Adjustment ────────────────────────────────────────────────────────────────

class AdjustmentApprove(BaseModel):
    entry_ids: List[UUID]
    notes: Optional[str] = None


class AdjustmentReject(BaseModel):
    entry_ids: List[UUID]
    rejection_reason: str


class AdjustmentOut(BaseModel):
    id: UUID
    entry_id: UUID
    status: AdjustmentStatus
    adjustment_qty: Decimal
    adjustment_value: Optional[Decimal] = None
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    posted_flag: bool
    stock_movement_ref: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── ABC Classification ────────────────────────────────────────────────────────

class ABCClassificationOut(BaseModel):
    id: UUID
    warehouse_id: UUID
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    abc_class: ABCClass
    stock_value: Optional[Decimal] = None
    annual_movements: Optional[int] = None
    classification_date: date
    count_frequency_days: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class CycleCountDashboard(BaseModel):
    total_plans: int
    active_plans: int
    tasks_today: int
    tasks_overdue: int
    tasks_pending: int
    tasks_completed_today: int
    accuracy_pct_7d: float
    open_variances: int
    pending_adjustments: int
    recent_variances: List[Dict[str, Any]]
