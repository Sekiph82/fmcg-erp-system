"""Fixed Asset Accounting + Depreciation schemas."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator

from app.models.fixed_assets import (
    DepreciationMethod, DepreciationFrequency, DepreciationStartRule,
    FAAssetStatus, ScheduleStatus, AssetEventType, DisposalMethod,
    FAIAgentType, FAIRecStatus,
)


# ── Asset Category ─────────────────────────────────────────────────────────────

class FAAssetCategoryCreate(BaseModel):
    category_code: str
    category_name: str
    default_depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    default_useful_life_months: Optional[int] = None
    default_salvage_value_pct: Optional[Decimal] = Decimal("0")
    capitalization_threshold: Optional[Decimal] = None
    depreciation_start_rule: DepreciationStartRule = DepreciationStartRule.FIRST_OF_NEXT_MONTH
    asset_account: Optional[str] = None
    accum_depreciation_account: Optional[str] = None
    depreciation_expense_account: Optional[str] = None
    disposal_gain_account: Optional[str] = None
    disposal_loss_account: Optional[str] = None
    impairment_account: Optional[str] = None
    revaluation_reserve_account: Optional[str] = None
    maintenance_integration: bool = False
    is_active: bool = True
    notes: Optional[str] = None


class FAAssetCategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    default_depreciation_method: Optional[DepreciationMethod] = None
    default_useful_life_months: Optional[int] = None
    default_salvage_value_pct: Optional[Decimal] = None
    capitalization_threshold: Optional[Decimal] = None
    depreciation_start_rule: Optional[DepreciationStartRule] = None
    asset_account: Optional[str] = None
    accum_depreciation_account: Optional[str] = None
    depreciation_expense_account: Optional[str] = None
    disposal_gain_account: Optional[str] = None
    disposal_loss_account: Optional[str] = None
    impairment_account: Optional[str] = None
    revaluation_reserve_account: Optional[str] = None
    maintenance_integration: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class FAAssetCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category_code: str
    category_name: str
    default_depreciation_method: DepreciationMethod
    default_useful_life_months: Optional[int]
    default_salvage_value_pct: Optional[Decimal]
    capitalization_threshold: Optional[Decimal]
    depreciation_start_rule: DepreciationStartRule
    asset_account: Optional[str]
    accum_depreciation_account: Optional[str]
    depreciation_expense_account: Optional[str]
    disposal_gain_account: Optional[str]
    disposal_loss_account: Optional[str]
    impairment_account: Optional[str]
    revaluation_reserve_account: Optional[str]
    maintenance_integration: bool
    is_active: bool
    notes: Optional[str]
    created_at: datetime


# ── Fixed Asset ────────────────────────────────────────────────────────────────

class FAFixedAssetCreate(BaseModel):
    asset_code: str
    asset_name: str
    asset_category_id: UUID
    asset_type: Optional[str] = None
    serial_no: Optional[str] = None
    asset_tag_no: Optional[str] = None
    physical_asset_id: Optional[UUID] = None
    procurement_reference_type: Optional[str] = None
    procurement_reference_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    acquisition_date: Optional[date] = None
    in_service_date: Optional[date] = None
    capitalization_date: Optional[date] = None
    original_cost: Decimal
    currency: str = "KES"
    exchange_rate: Decimal = Decimal("1")
    local_currency_cost: Decimal
    salvage_value: Decimal = Decimal("0")
    useful_life_months: Optional[int] = None
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    depreciation_frequency: DepreciationFrequency = DepreciationFrequency.MONTHLY
    declining_balance_rate: Optional[Decimal] = None
    total_production_units: Optional[Decimal] = None
    location: Optional[str] = None
    warehouse_id: Optional[UUID] = None
    plant: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    custodian_employee_id: Optional[UUID] = None
    condition_status: Optional[str] = None
    is_legacy_import: bool = False
    legacy_accumulated_depreciation: Optional[Decimal] = None
    notes: Optional[str] = None


class FAFixedAssetUpdate(BaseModel):
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    serial_no: Optional[str] = None
    asset_tag_no: Optional[str] = None
    physical_asset_id: Optional[UUID] = None
    in_service_date: Optional[date] = None
    salvage_value: Optional[Decimal] = None
    useful_life_months: Optional[int] = None
    depreciation_method: Optional[DepreciationMethod] = None
    declining_balance_rate: Optional[Decimal] = None
    total_production_units: Optional[Decimal] = None
    location: Optional[str] = None
    warehouse_id: Optional[UUID] = None
    plant: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    custodian_employee_id: Optional[UUID] = None
    condition_status: Optional[str] = None
    notes: Optional[str] = None


class FAFixedAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_code: str
    asset_name: str
    asset_category_id: UUID
    category_name: Optional[str] = None
    asset_type: Optional[str]
    serial_no: Optional[str]
    asset_tag_no: Optional[str]
    physical_asset_id: Optional[UUID]
    supplier_id: Optional[UUID]
    acquisition_date: Optional[date]
    in_service_date: Optional[date]
    capitalization_date: Optional[date]
    depreciation_start_date: Optional[date]
    depreciation_end_date: Optional[date]
    original_cost: Decimal
    currency: str
    exchange_rate: Decimal
    local_currency_cost: Decimal
    salvage_value: Decimal
    depreciable_base: Decimal
    useful_life_months: Optional[int]
    depreciation_method: DepreciationMethod
    depreciation_frequency: DepreciationFrequency
    declining_balance_rate: Optional[Decimal]
    total_production_units: Optional[Decimal]
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    last_depreciation_date: Optional[date]
    status: FAAssetStatus
    location: Optional[str]
    plant: Optional[str]
    department: Optional[str]
    cost_center: Optional[str]
    condition_status: Optional[str]
    is_legacy_import: bool
    notes: Optional[str]
    created_at: datetime


# ── Capitalize ─────────────────────────────────────────────────────────────────

class FACapitalizeRequest(BaseModel):
    capitalization_date: date
    in_service_date: Optional[date] = None
    depreciation_start_date: Optional[date] = None
    notes: Optional[str] = None


# ── Transfer ───────────────────────────────────────────────────────────────────

class FATransferRequest(BaseModel):
    effective_date: date
    new_location: Optional[str] = None
    new_plant: Optional[str] = None
    new_department: Optional[str] = None
    new_cost_center: Optional[str] = None
    new_custodian_employee_id: Optional[UUID] = None
    reason: Optional[str] = None


# ── Revaluation ────────────────────────────────────────────────────────────────

class FARevaluationRequest(BaseModel):
    revaluation_date: date
    new_carrying_value: Decimal
    reason: str
    treatment: str = "RESERVE"  # RESERVE or PNL


# ── Impairment ─────────────────────────────────────────────────────────────────

class FAImpairmentRequest(BaseModel):
    impairment_date: date
    impairment_amount: Decimal
    reason: str
    notes: Optional[str] = None


# ── Disposal ───────────────────────────────────────────────────────────────────

class FADisposalRequest(BaseModel):
    disposal_date: date
    disposal_method: DisposalMethod
    sale_proceeds: Decimal = Decimal("0")
    buyer_name: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class FADisposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    disposal_method: DisposalMethod
    disposal_date: date
    sale_proceeds: Optional[Decimal]
    nbv_at_disposal: Decimal
    cost_at_disposal: Decimal
    accum_depr_at_disposal: Decimal
    gain_loss: Decimal
    reason: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Depreciation Schedule ──────────────────────────────────────────────────────

class FADepreciationScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    period_start: date
    period_end: date
    scheduled_amount: Decimal
    posted_amount: Optional[Decimal]
    posting_date: Optional[date]
    schedule_status: ScheduleStatus
    opening_nbv: Decimal
    closing_nbv: Decimal
    actual_production_units: Optional[Decimal]
    notes: Optional[str]


# ── Depreciation Posting Run ───────────────────────────────────────────────────

class FADepreciationGenerateRequest(BaseModel):
    asset_ids: Optional[List[UUID]] = None  # None = all active assets
    through_date: date


class FADepreciationPostRequest(BaseModel):
    period_start: date
    period_end: date
    asset_ids: Optional[List[UUID]] = None
    dry_run: bool = False


class FADepreciationPostResult(BaseModel):
    total_assets: int
    total_posted: int
    total_amount: Decimal
    failed: List[str] = []
    dry_run: bool


# ── Asset Event ────────────────────────────────────────────────────────────────

class FAAssetEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    event_type: AssetEventType
    event_date: date
    reference_type: Optional[str]
    amount: Optional[Decimal]
    nbv_before: Optional[Decimal]
    nbv_after: Optional[Decimal]
    reason: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Component ──────────────────────────────────────────────────────────────────

class FAComponentCreate(BaseModel):
    component_name: str
    component_cost: Decimal
    salvage_value: Decimal = Decimal("0")
    useful_life_months: Optional[int] = None
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    in_service_date: Optional[date] = None
    notes: Optional[str] = None


class FAComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parent_asset_id: UUID
    component_name: str
    component_cost: Decimal
    salvage_value: Decimal
    useful_life_months: Optional[int]
    depreciation_method: DepreciationMethod
    in_service_date: Optional[date]
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    is_active: bool
    notes: Optional[str]


# ── Legacy Import ──────────────────────────────────────────────────────────────

class FALegacyImportRow(BaseModel):
    asset_code: str
    asset_name: str
    asset_category_id: UUID
    original_cost: Decimal
    accumulated_depreciation_to_date: Decimal
    in_service_date: date
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    useful_life_months: Optional[int] = None
    salvage_value: Decimal = Decimal("0")
    cost_center: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class FALegacyImportRequest(BaseModel):
    rows: List[FALegacyImportRow]
    as_of_date: date


class FALegacyImportResult(BaseModel):
    total: int
    succeeded: int
    failed: List[str]


# ── NBV Report ─────────────────────────────────────────────────────────────────

class FANBVReportRow(BaseModel):
    asset_id: str
    asset_code: str
    asset_name: str
    category: str
    cost_center: Optional[str]
    original_cost: Decimal
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    status: str
    as_of_date: date


# ── AI Recommendation ──────────────────────────────────────────────────────────

class FAAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: Optional[UUID]
    agent_type: FAIAgentType
    status: FAIRecStatus
    title: str
    detail: str
    severity: Optional[str]
    action_taken: Optional[str]
    created_at: datetime


class FAAIRecAck(BaseModel):
    status: FAIRecStatus
    action_taken: Optional[str] = None
