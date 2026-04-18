from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UtilityTypeBreakdown(BaseModel):
    utility_type: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    cost: Optional[Decimal]


class ProductionUtilitySummary(BaseModel):
    production_order_id: UUID
    order_no: str
    total_utility_cost: Decimal
    by_type: List[UtilityTypeBreakdown]


class PostBillToGLRequest(BaseModel):
    debit_account_id: UUID
    credit_account_id: UUID


class PostBillToGLResult(BaseModel):
    bill_id: UUID
    journal_entry_id: UUID
    entry_no: str
    amount: Decimal


class PostAllocationsResult(BaseModel):
    bill_id: UUID
    entries_created: int
    total_cost_posted: Decimal


class ChemicalSyncRequest(BaseModel):
    warehouse_id: UUID


class ChemicalSyncResult(BaseModel):
    record_id: UUID
    movement_id: UUID
    movement_reference: str
    quantity_issued: Decimal


class MaintenanceActionRequest(BaseModel):
    action_type: str  # PM_WORK_ORDER or BREAKDOWN
    description: str
    scheduled_date: Optional[date] = None
    plan_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None


class MaintenanceActionResult(BaseModel):
    type: str
    alarm_event_id: UUID
    # PM path
    work_order_id: Optional[UUID] = None
    wo_no: Optional[str] = None
    # Breakdown path
    breakdown_id: Optional[UUID] = None
    breakdown_no: Optional[str] = None


class PMPlanSummary(BaseModel):
    id: UUID
    name: str
    next_due_date: Optional[date]
    status: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class BreakdownSummary(BaseModel):
    id: UUID
    breakdown_no: str
    severity: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class MaintenanceStatusResult(BaseModel):
    linked: bool
    utility_asset_id: UUID
    maintenance_asset_id: Optional[UUID] = None
    asset_name: Optional[str] = None
    asset_status: Optional[str] = None
    overdue_pm_count: int = 0
    open_breakdown_count: int = 0
    next_pm_due: Optional[date] = None
    pm_plans: List[PMPlanSummary] = []
    recent_breakdowns: List[BreakdownSummary] = []


class QualityInspectionSummary(BaseModel):
    inspection_id: UUID
    inspection_no: str
    qc_type: str
    status: str
    decision: Optional[str]
    inspection_date: Optional[date]
    lot_number: Optional[str]
    batch_no: Optional[str]
