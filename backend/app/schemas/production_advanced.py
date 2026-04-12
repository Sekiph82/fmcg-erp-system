"""
Pydantic schemas for the Advanced Production Module.
Closely mirrors the user-provided CSV column structures.
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Work Center ────────────────────────────────────────────────────────────────

class WorkCenterCreate(BaseModel):
    work_center_id: str = Field(..., max_length=50)
    name:           str = Field(..., max_length=255)
    type:           str = Field("MACHINE")
    capacity:       Optional[Decimal] = None
    capacity_uom:   Optional[str]     = None
    location:       Optional[str]     = None
    department:     Optional[str]     = None
    setup_time_min: Optional[int]     = None
    ideal_cycle_time_sec: Optional[Decimal] = None
    status:         str = Field("active")
    notes:          Optional[str]     = None

class WorkCenterUpdate(BaseModel):
    name:           Optional[str]     = None
    type:           Optional[str]     = None
    capacity:       Optional[Decimal] = None
    capacity_uom:   Optional[str]     = None
    location:       Optional[str]     = None
    department:     Optional[str]     = None
    setup_time_min: Optional[int]     = None
    ideal_cycle_time_sec: Optional[Decimal] = None
    status:         Optional[str]     = None
    notes:          Optional[str]     = None

class WorkCenterRead(BaseModel):
    id:             UUID
    work_center_id: str
    name:           str
    type:           str
    capacity:       Optional[Decimal]
    capacity_uom:   Optional[str]
    location:       Optional[str]
    department:     Optional[str]
    setup_time_min: Optional[int]
    status:         str
    notes:          Optional[str]
    created_at:     datetime

    model_config = {"from_attributes": True}


# ── Routing ────────────────────────────────────────────────────────────────────

class RoutingStepCreate(BaseModel):
    step_number:           int
    operation:             str = Field(..., max_length=255)
    work_center_id:        UUID
    standard_time_minutes: int   = Field(0)
    setup_time_minutes:    Optional[int] = None
    is_parallel:           bool  = False
    notes:                 Optional[str] = None

class RoutingCreate(BaseModel):
    routing_id: str = Field(..., max_length=50)
    product_id: UUID
    version:    int  = 1
    name:       Optional[str] = None
    is_active:  bool = True
    notes:      Optional[str] = None

class RoutingUpdate(BaseModel):
    name:      Optional[str]  = None
    is_active: Optional[bool] = None
    notes:     Optional[str]  = None

class RoutingStepRead(BaseModel):
    id:                    UUID
    routing_id:            UUID
    step_number:           int
    operation:             str
    work_center_id:        UUID
    work_center_name:      Optional[str] = None
    standard_time_minutes: int
    setup_time_minutes:    Optional[int]
    is_parallel:           bool

    model_config = {"from_attributes": True}

class RoutingRead(BaseModel):
    id:         UUID
    routing_id: str
    product_id: UUID
    product_name: Optional[str] = None
    product_sku:  Optional[str] = None
    version:    int
    name:       Optional[str]
    is_active:  bool
    steps:      List[RoutingStepRead] = []

    model_config = {"from_attributes": True}


# ── Work Orders ────────────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    work_order_id:       str  = Field(..., max_length=50)
    production_order_id: UUID
    work_center_id:      UUID
    operation:           str  = Field(..., max_length=255)
    operator:            Optional[str] = None
    routing_step_id:     Optional[UUID] = None
    status:              str  = "planned"
    planned_quantity:    Optional[Decimal] = None
    start_time:          Optional[datetime] = None
    end_time:            Optional[datetime] = None
    planned_start:       Optional[datetime] = None
    planned_end:         Optional[datetime] = None
    notes:               Optional[str] = None

class WorkOrderUpdate(BaseModel):
    status:           Optional[str]      = None
    operator:         Optional[str]      = None
    actual_quantity:  Optional[Decimal]  = None
    start_time:       Optional[datetime] = None
    end_time:         Optional[datetime] = None
    notes:            Optional[str]      = None

class WorkOrderRead(BaseModel):
    id:                  UUID
    work_order_id:       str
    production_order_id: UUID
    order_no:            Optional[str]  = None
    work_center_id:      UUID
    work_center_name:    Optional[str] = None
    operation:           str
    operator:            Optional[str]
    status:              str
    planned_quantity:    Optional[Decimal]
    actual_quantity:     Optional[Decimal]
    start_time:          Optional[datetime]
    end_time:            Optional[datetime]
    planned_start:       Optional[datetime]
    planned_end:         Optional[datetime]
    created_at:          datetime

    model_config = {"from_attributes": True}


# ── Shifts ─────────────────────────────────────────────────────────────────────

class ShiftCreate(BaseModel):
    shift_code:     str = Field(..., max_length=50)
    name:           str = Field(..., max_length=255)
    start_time_str: str = Field(..., description="HH:MM format")
    end_time_str:   str = Field(..., description="HH:MM format")
    duration_hours: Decimal
    is_active:      bool = True
    notes:          Optional[str] = None

class ShiftUpdate(BaseModel):
    name:           Optional[str]  = None
    start_time_str: Optional[str]  = None
    end_time_str:   Optional[str]  = None
    duration_hours: Optional[Decimal] = None
    is_active:      Optional[bool] = None

class ShiftRead(BaseModel):
    id:             UUID
    shift_code:     str
    name:           str
    start_time_str: str
    end_time_str:   str
    duration_hours: Decimal
    is_active:      bool

    model_config = {"from_attributes": True}


# ── Production Schedule ────────────────────────────────────────────────────────

class ProductionScheduleCreate(BaseModel):
    schedule_id:         str = Field(..., max_length=50)
    production_order_id: UUID
    work_center_id:      UUID
    shift_id:            Optional[UUID]   = None
    shift_name:          Optional[str]    = None
    start_time:          datetime
    end_time:            datetime
    status:              str = "planned"
    priority:            str = "medium"
    notes:               Optional[str]    = None

class ProductionScheduleUpdate(BaseModel):
    status:     Optional[str]      = None
    priority:   Optional[str]      = None
    start_time: Optional[datetime] = None
    end_time:   Optional[datetime] = None
    notes:      Optional[str]      = None

class ProductionScheduleRead(BaseModel):
    id:                  UUID
    schedule_id:         str
    production_order_id: UUID
    order_no:            Optional[str] = None
    work_center_id:      UUID
    work_center_name:    Optional[str] = None
    shift_id:            Optional[UUID]
    shift_name:          Optional[str]
    start_time:          datetime
    end_time:            datetime
    status:              str
    priority:            str
    conflict_flag:       bool

    model_config = {"from_attributes": True}


# ── Time Tracking ──────────────────────────────────────────────────────────────

class TimeTrackingCreate(BaseModel):
    log_id:               str  = Field(..., max_length=50)
    work_order_id:        UUID
    actual_start:         datetime
    actual_end:           Optional[datetime] = None
    duration_planned_min: Optional[int]      = None
    downtime_minutes:     Optional[int]      = 0
    category:             str = "productive"
    reason:               Optional[str]      = None
    notes:                Optional[str]      = None

class TimeTrackingUpdate(BaseModel):
    actual_end:       Optional[datetime] = None
    downtime_minutes: Optional[int]      = None
    category:         Optional[str]      = None
    reason:           Optional[str]      = None

class TimeTrackingRead(BaseModel):
    id:                   UUID
    log_id:               str
    work_order_id:        UUID
    work_order_code:      Optional[str] = None
    actual_start:         datetime
    actual_end:           Optional[datetime]
    duration_actual_min:  Optional[int]
    duration_planned_min: Optional[int]
    downtime_minutes:     Optional[int]
    category:             str
    reason:               Optional[str]
    efficiency_pct:       Optional[Decimal]

    model_config = {"from_attributes": True}


# ── Downtime Events ────────────────────────────────────────────────────────────

class DowntimeEventCreate(BaseModel):
    downtime_id:    str  = Field(..., max_length=50)
    work_center_id: UUID
    machine_id:     Optional[str]      = None
    work_order_id:  Optional[UUID]     = None
    start_time:     datetime
    end_time:       Optional[datetime] = None
    reason:         str
    category:       str = "unplanned"
    reported_by:    Optional[str]      = None
    impact_units:   Optional[int]      = None
    notes:          Optional[str]      = None

class DowntimeEventUpdate(BaseModel):
    end_time:     Optional[datetime] = None
    reason:       Optional[str]      = None
    category:     Optional[str]      = None
    impact_units: Optional[int]      = None
    notes:        Optional[str]      = None

class DowntimeEventRead(BaseModel):
    id:              UUID
    downtime_id:     str
    work_center_id:  UUID
    work_center_name: Optional[str] = None
    machine_id:      Optional[str]
    work_order_id:   Optional[UUID]
    start_time:      datetime
    end_time:        Optional[datetime]
    duration_min:    Optional[int]
    reason:          str
    category:        str
    reported_by:     Optional[str]

    model_config = {"from_attributes": True}


# ── QC Inspections ─────────────────────────────────────────────────────────────

class AdvQCResultCreate(BaseModel):
    test_type:     str
    actual_value:  Optional[Decimal] = None
    min_value:     Optional[Decimal] = None
    max_value:     Optional[Decimal] = None
    unit:          Optional[str]     = None
    result:        str = "pass"
    notes:         Optional[str]     = None

class AdvQCInspectionCreate(BaseModel):
    qc_id:               str  = Field(..., max_length=50)
    production_order_id: UUID
    work_order_id:       Optional[UUID]     = None
    inspection_type:     str  = "inline"
    status:              str  = "pending"
    checked_by:          Optional[str]      = None
    inspected_at:        Optional[datetime] = None
    batch_ref:           Optional[str]      = None
    notes:               Optional[str]      = None
    results:             List[AdvQCResultCreate] = []

class AdvQCInspectionUpdate(BaseModel):
    status:      Optional[str]      = None
    checked_by:  Optional[str]      = None
    inspected_at: Optional[datetime] = None
    notes:        Optional[str]     = None

class AdvQCResultRead(BaseModel):
    id:            UUID
    inspection_id: UUID
    test_type:     str
    actual_value:  Optional[Decimal]
    min_value:     Optional[Decimal]
    max_value:     Optional[Decimal]
    unit:          Optional[str]
    result:        str

    model_config = {"from_attributes": True}

class AdvQCInspectionRead(BaseModel):
    id:                  UUID
    qc_id:               str
    production_order_id: UUID
    order_no:            Optional[str] = None
    work_order_id:       Optional[UUID]
    inspection_type:     str
    status:              str
    checked_by:          Optional[str]
    inspected_at:        Optional[datetime]
    batch_ref:           Optional[str]
    results:             List[AdvQCResultRead] = []

    model_config = {"from_attributes": True}


# ── Waste & Yield ──────────────────────────────────────────────────────────────

class WasteRecordCreate(BaseModel):
    waste_id:            str  = Field(..., max_length=50)
    production_order_id: UUID
    work_order_id:       Optional[UUID]    = None
    material_id:         Optional[UUID]    = None
    material_code:       Optional[str]     = None
    waste_type:          str  = "MATERIAL"
    waste_category:      str  = "normal"
    expected_qty:        Decimal
    actual_qty:          Decimal
    loss_qty:            Optional[Decimal] = None   # auto = expected - actual
    uom:                 str  = "KG"
    reason:              Optional[str]     = None
    notes:               Optional[str]     = None

    @model_validator(mode="after")
    def compute_loss(self) -> "WasteRecordCreate":
        if self.loss_qty is None:
            self.loss_qty = self.expected_qty - self.actual_qty
        return self

class WasteRecordUpdate(BaseModel):
    actual_qty:     Optional[Decimal] = None
    loss_qty:       Optional[Decimal] = None
    waste_category: Optional[str]     = None
    reason:         Optional[str]     = None

class WasteRecordRead(BaseModel):
    id:                  UUID
    waste_id:            str
    production_order_id: UUID
    order_no:            Optional[str]  = None
    material_code:       Optional[str]
    waste_type:          str
    waste_category:      str
    expected_qty:        Decimal
    actual_qty:          Decimal
    loss_qty:            Decimal
    loss_pct:            Optional[Decimal]
    uom:                 Optional[str]
    reason:              Optional[str]
    is_anomaly:          bool

    model_config = {"from_attributes": True}


# ── Batch / Lot Tracking ───────────────────────────────────────────────────────

class BatchLotCreate(BaseModel):
    batch_id:            str  = Field(..., max_length=100)
    production_order_id: UUID
    product_id:          UUID
    product_sku:         Optional[str]  = None
    quantity:            Decimal
    uom:                 str  = "KG"
    manufacture_date:    Optional[date] = None
    expiry_date:         Optional[date] = None
    status:              str  = "quarantine"
    traceability_code:   Optional[str]  = None
    warehouse_id:        Optional[UUID] = None
    notes:               Optional[str]  = None

class BatchLotUpdate(BaseModel):
    status:             Optional[str]  = None
    released_by:        Optional[str]  = None
    quarantine_reason:  Optional[str]  = None
    warehouse_id:       Optional[UUID] = None
    notes:              Optional[str]  = None

class BatchLotRead(BaseModel):
    id:                  UUID
    batch_id:            str
    production_order_id: UUID
    order_no:            Optional[str]  = None
    product_id:          UUID
    product_name:        Optional[str]  = None
    product_sku:         Optional[str]
    quantity:            Decimal
    uom:                 str
    manufacture_date:    Optional[date]
    expiry_date:         Optional[date]
    status:              str
    traceability_code:   Optional[str]
    warehouse_id:        Optional[UUID]

    model_config = {"from_attributes": True}


# ── Labor Tracking ─────────────────────────────────────────────────────────────

class LaborLogCreate(BaseModel):
    labor_id:       str  = Field(..., max_length=50)
    work_order_id:  UUID
    employee_id:    Optional[UUID]     = None
    employee_code:  Optional[str]      = None
    operator_name:  Optional[str]      = None
    start_time:     Optional[datetime] = None
    end_time:       Optional[datetime] = None
    hours_worked:   Optional[Decimal]  = None
    role:           Optional[str]      = None
    activity_type:  str  = "production"
    pieces_produced: Optional[int]     = None
    notes:          Optional[str]      = None

class LaborLogUpdate(BaseModel):
    end_time:       Optional[datetime] = None
    hours_worked:   Optional[Decimal]  = None
    pieces_produced: Optional[int]     = None
    notes:          Optional[str]      = None

class LaborLogRead(BaseModel):
    id:             UUID
    labor_id:       str
    work_order_id:  UUID
    work_order_code: Optional[str] = None
    employee_id:    Optional[UUID]
    employee_code:  Optional[str]
    operator_name:  Optional[str]
    hours_worked:   Optional[Decimal]
    role:           Optional[str]
    activity_type:  str
    pieces_produced: Optional[int]
    created_at:     datetime

    model_config = {"from_attributes": True}


# ── OEE Records ────────────────────────────────────────────────────────────────

class OEERecordCreate(BaseModel):
    oee_id:                     str  = Field(..., max_length=50)
    work_center_id:             UUID
    machine_id:                 Optional[str]  = None
    shift_id:                   Optional[UUID] = None
    record_date:                date
    planned_production_time_min: int
    actual_production_time_min:  Optional[int]     = None
    downtime_min:               Optional[int]      = 0
    ideal_cycle_time_sec:       Optional[Decimal]  = None
    total_units_produced:       Optional[int]      = 0
    good_units_produced:        Optional[int]      = 0
    # Accept pre-computed KPIs from CSV
    availability:               Optional[Decimal]  = None
    performance:                Optional[Decimal]  = None
    quality:                    Optional[Decimal]  = None
    oee_score:                  Optional[Decimal]  = None
    notes:                      Optional[str]      = None

class OEERecordUpdate(BaseModel):
    actual_production_time_min: Optional[int]     = None
    downtime_min:               Optional[int]      = None
    total_units_produced:       Optional[int]      = None
    good_units_produced:        Optional[int]      = None
    notes:                      Optional[str]      = None

class OEERecordRead(BaseModel):
    id:                         UUID
    oee_id:                     str
    work_center_id:             UUID
    work_center_name:           Optional[str] = None
    machine_id:                 Optional[str]
    shift_id:                   Optional[UUID]
    shift_name:                 Optional[str] = None
    record_date:                date
    planned_production_time_min: int
    actual_production_time_min:  Optional[int]
    downtime_min:               Optional[int]
    total_units_produced:       Optional[int]
    good_units_produced:        Optional[int]
    availability:               Optional[Decimal]
    performance:                Optional[Decimal]
    quality:                    Optional[Decimal]
    oee_score:                  Optional[Decimal]
    is_low_oee:                 bool
    is_high_downtime:           bool

    model_config = {"from_attributes": True}


# ── KPI / Analytics Schemas ────────────────────────────────────────────────────

class OEESummary(BaseModel):
    work_center_id:   UUID
    work_center_name: Optional[str]
    period_from:      date
    period_to:        date
    avg_availability: Optional[Decimal]
    avg_performance:  Optional[Decimal]
    avg_quality:      Optional[Decimal]
    avg_oee:          Optional[Decimal]
    total_downtime_min: int
    records_count:    int

class WasteSummary(BaseModel):
    production_order_id: UUID
    order_no:            Optional[str]
    total_expected:      Decimal
    total_actual:        Decimal
    total_loss:          Decimal
    avg_loss_pct:        Optional[Decimal]
    anomaly_count:       int

class ScheduleConflict(BaseModel):
    work_center_id:   UUID
    work_center_name: Optional[str]
    conflicting_schedules: List[str]
    overlap_minutes:  int
