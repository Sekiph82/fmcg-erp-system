from __future__ import annotations

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.maintenance import (
    AssetStatus, PMFrequency, PMStatus,
    BreakdownSeverity, BreakdownStatus,
    MaintenancePredictionRisk, MaintenancePredictionStatus,
)


class DowntimeReasonCodeRead(BaseModel):
    code: str
    label: str
    parent_code: Optional[str] = None
    is_selectable: bool
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


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
    work_center_id: Optional[str] = None
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
    work_center_id: Optional[str] = None
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
    work_center_id: Optional[str] = None
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


class PMPlanSparePartRequirementInput(BaseModel):
    spare_part_id: UUID
    quantity_required: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=4)


class PMPlanSparePartRequirementsUpdate(BaseModel):
    items: List[PMPlanSparePartRequirementInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_parts(self):
        part_ids = [item.spare_part_id for item in self.items]
        if len(part_ids) != len(set(part_ids)):
            raise ValueError("Each spare part may appear only once")
        return self


class PMPlanSparePartRequirementRead(BaseModel):
    spare_part_id: str
    part_no: str
    name: str
    unit: str
    is_active: bool
    quantity_required: float
    current_stock: float
    reserved_quantity: float
    available_quantity: float
    is_available: bool


class PMPlanSparePartRequirementsReport(BaseModel):
    plan_id: str
    requirements: List[PMPlanSparePartRequirementRead] = Field(default_factory=list)
    data_notes: List[str] = Field(default_factory=list)


# ── PM Work Order ──────────────────────────────────────────────────────────────

class PMWorkOrderCreate(BaseModel):
    plan_id: str
    scheduled_date: date
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    technician: Optional[str] = None

    @model_validator(mode="after")
    def validate_window(self):
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("window_start and window_end must be provided together")
        if self.window_start is not None:
            if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
                raise ValueError("PM window timestamps must include a timezone")
            if self.window_end <= self.window_start:
                raise ValueError("window_end must be after window_start")
        return self


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
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    work_center_id: Optional[str] = None
    status: PMStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    technician: Optional[str] = None
    checklist_notes: Optional[str] = None
    created_at: datetime


class PMWindowScheduleConflict(BaseModel):
    schedule_id: str
    production_order_id: str
    work_center_id: str
    start_time: datetime
    end_time: datetime
    status: str


class PMWindowScheduleImpact(BaseModel):
    pm_work_order_id: str
    pm_work_order_no: str
    pm_status: PMStatus
    asset_id: str
    asset_no: str
    asset_name: str
    work_center_id: Optional[str] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    conflicts: List[PMWindowScheduleConflict] = Field(default_factory=list)
    unavailable_reason: Optional[str] = None


class PMWindowScheduleImpactReport(BaseModel):
    date_from: date
    date_to: date
    windows: List[PMWindowScheduleImpact] = Field(default_factory=list)
    data_notes: List[str] = Field(default_factory=list)


class MaintenanceScheduleOverlap(BaseModel):
    schedule_id: str
    production_order_id: str
    start_time: datetime
    end_time: datetime
    overlap_minutes: int


class MaintenanceDowntimeCapacityImpact(BaseModel):
    source_type: str
    source_id: str
    source_number: str
    status: str
    asset_id: str
    asset_no: str
    asset_name: str
    work_center_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    observed_through: Optional[datetime] = None
    ongoing: bool = False
    schedule_minutes_at_risk: float = 0
    affected_production_order_ids: List[str] = Field(default_factory=list)
    overlaps: List[MaintenanceScheduleOverlap] = Field(default_factory=list)
    unavailable_reason: Optional[str] = None


class MaintenanceDowntimeCapacityReport(BaseModel):
    date_from: date
    date_to: date
    as_of: datetime
    impacts: List[MaintenanceDowntimeCapacityImpact] = Field(default_factory=list)
    total_schedule_minutes_at_risk: float = 0
    data_notes: List[str] = Field(default_factory=list)


class BreakdownPriorityAssessment(BaseModel):
    breakdown_id: str
    priority: Optional[str] = None
    severity: str
    escalate_after_minutes: Optional[int] = None
    age_minutes: Optional[float] = None
    minutes_until_escalation: Optional[float] = None
    state: str
    recommended_action: str
    policy_version: str


class BreakdownPriorityEscalationReport(BaseModel):
    as_of: datetime
    policy_version: str
    assessments: List[BreakdownPriorityAssessment] = Field(default_factory=list)
    data_notes: List[str] = Field(default_factory=list)


# ── Breakdown Record ───────────────────────────────────────────────────────────

class BreakdownCreate(BaseModel):
    asset_id: str
    production_order_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: str
    reason_code: Optional[str] = None
    root_cause: Optional[str] = None
    severity: BreakdownSeverity = BreakdownSeverity.MEDIUM
    corrective_action: Optional[str] = None


class BreakdownUpdate(BaseModel):
    end_time: Optional[datetime] = None
    downtime_minutes: Optional[int] = None
    root_cause: Optional[str] = None
    reason_code: Optional[str] = None
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
    reason_code: Optional[str] = None
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
    current_stock: float = Field(default=0, ge=0, allow_inf_nan=False)
    reorder_level: Optional[float] = None
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    lead_time_days: Optional[int] = None


class SparePartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    current_stock: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
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
    quantity_used: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=4)
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


# Predictive Maintenance

class MaintenancePredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    asset_name: Optional[str] = None
    machine_id: str
    machine_name: Optional[str] = None
    predicted_failure_date: date
    confidence: float
    risk_level: MaintenancePredictionRisk
    failure_mode: str
    recommended_action: str
    evidence_summary: Optional[str] = None
    source_metrics: Optional[dict] = None
    status: MaintenancePredictionStatus
    generated_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    work_order_id: Optional[str] = None
    work_order_created_by_id: Optional[str] = None
    work_order_created_at: Optional[datetime] = None
    created_at: datetime


class MaintenancePredictionReview(BaseModel):
    status: MaintenancePredictionStatus = MaintenancePredictionStatus.REVIEWED
    # Kept optional for older clients; the API records the authenticated user instead.
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


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
