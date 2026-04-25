"""Accounting Dimensions / Cost Centers schemas."""
from __future__ import annotations
from typing import Optional, List
from datetime import date
from decimal import Decimal
import uuid
from pydantic import BaseModel, ConfigDict

from app.models.dimensions import (
    DimensionScope, CostCenterType, DimSourceType,
    AllocationBasis, AllocationFrequency, AllocationRunStatus,
    ValidationSeverity, DimAIAgentType, DimAIRecStatus,
)


# ── Dim Type ───────────────────────────────────────────────────────────────────

class DimTypeCreate(BaseModel):
    type_code: str
    type_name: str
    dimension_scope: DimensionScope = DimensionScope.BOTH
    hierarchy_enabled: bool = True
    is_mandatory: bool = False
    active: bool = True
    notes: Optional[str] = None


class DimTypeRead(DimTypeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    value_count: int = 0


# ── Dim Value ──────────────────────────────────────────────────────────────────

class DimValueCreate(BaseModel):
    dim_type_id: uuid.UUID
    dim_code: str
    dim_name: str
    parent_id: Optional[uuid.UUID] = None
    level_no: int = 1
    responsible_user_id: Optional[uuid.UUID] = None
    active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class DimValueRead(DimValueCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dim_type_name: Optional[str] = None
    parent_name: Optional[str] = None
    children_count: int = 0


# ── Cost Center ────────────────────────────────────────────────────────────────

class CostCenterCreate(BaseModel):
    cost_center_code: str
    cost_center_name: str
    parent_id: Optional[uuid.UUID] = None
    cost_center_type: CostCenterType = CostCenterType.ADMIN
    plant_id: Optional[uuid.UUID] = None
    manager_employee_id: Optional[uuid.UUID] = None
    department: Optional[str] = None
    active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class CostCenterRead(CostCenterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    parent_name: Optional[str] = None
    children_count: int = 0


# ── Transaction Dimension ──────────────────────────────────────────────────────

class TransactionDimensionCreate(BaseModel):
    transaction_type: str
    transaction_id: str
    line_id: Optional[str] = None
    dim_type_id: uuid.UUID
    dim_value_id: uuid.UUID
    source_type: DimSourceType = DimSourceType.MANUAL
    locked: bool = False
    notes: Optional[str] = None


class TransactionDimensionRead(TransactionDimensionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dim_type_code: Optional[str] = None
    dim_type_name: Optional[str] = None
    dim_value_code: Optional[str] = None
    dim_value_name: Optional[str] = None


# ── Derive Request / Response ──────────────────────────────────────────────────

class DeriveRequest(BaseModel):
    transaction_type: str
    transaction_id: str
    source_field: Optional[str] = None
    source_field_value: Optional[str] = None


class DeriveResult(BaseModel):
    dim_type_id: uuid.UUID
    dim_type_name: str
    dim_value_id: uuid.UUID
    dim_value_name: str
    source_type: DimSourceType


# ── Validation ─────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    transaction_type: str
    transaction_id: str
    dim_tags: List[TransactionDimensionCreate]


class ValidationIssue(BaseModel):
    dim_type_code: str
    dim_type_name: str
    severity: ValidationSeverity
    message: str


class ValidateResult(BaseModel):
    valid: bool
    issues: List[ValidationIssue]


# ── Validation Rule ────────────────────────────────────────────────────────────

class DimValidationRuleCreate(BaseModel):
    rule_name: str
    transaction_type: Optional[str] = None
    gl_account_pattern: Optional[str] = None
    module: Optional[str] = None
    dim_type_id: uuid.UUID
    severity: ValidationSeverity = ValidationSeverity.WARN
    active: bool = True
    effective_date: Optional[date] = None
    notes: Optional[str] = None


class DimValidationRuleRead(DimValidationRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dim_type_name: Optional[str] = None


# ── Allocation Rule ────────────────────────────────────────────────────────────

class AllocationRuleLineCreate(BaseModel):
    target_dim_value_id: uuid.UUID
    fixed_pct: Optional[Decimal] = None
    weight_value: Optional[Decimal] = None
    active: bool = True
    notes: Optional[str] = None


class AllocationRuleLineRead(AllocationRuleLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    target_dim_value_name: Optional[str] = None


class AllocationRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    source_dim_type_id: uuid.UUID
    source_dim_value_id: uuid.UUID
    target_dim_type_id: uuid.UUID
    allocation_basis: AllocationBasis = AllocationBasis.FIXED_PCT
    frequency: AllocationFrequency = AllocationFrequency.MONTHLY
    gl_account_cost_pool: Optional[str] = None
    gl_account_allocation_dr: Optional[str] = None
    gl_account_allocation_cr: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None
    lines: List[AllocationRuleLineCreate] = []


class AllocationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rule_code: str
    rule_name: str
    source_dim_type_id: uuid.UUID
    source_dim_value_id: uuid.UUID
    target_dim_type_id: uuid.UUID
    allocation_basis: AllocationBasis
    frequency: AllocationFrequency
    gl_account_cost_pool: Optional[str] = None
    gl_account_allocation_dr: Optional[str] = None
    gl_account_allocation_cr: Optional[str] = None
    active: bool
    notes: Optional[str] = None
    source_dim_value_name: Optional[str] = None
    target_dim_type_name: Optional[str] = None
    lines: List[AllocationRuleLineRead] = []


# ── Allocation Run ─────────────────────────────────────────────────────────────

class AllocationRunRequest(BaseModel):
    rule_id: uuid.UUID
    period_start: date
    period_end: date
    dry_run: bool = True
    source_pool_amount: Decimal
    run_notes: Optional[str] = None


class AllocationRunLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    target_dim_value_id: uuid.UUID
    target_dim_value_name: Optional[str] = None
    pct_applied: Optional[Decimal] = None
    allocated_amount: Optional[Decimal] = None
    journal_entry_id: Optional[str] = None


class AllocationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: Optional[str] = None
    period_start: date
    period_end: date
    dry_run: bool
    status: AllocationRunStatus
    source_pool_amount: Decimal
    total_allocated: Decimal
    run_notes: Optional[str] = None
    lines: List[AllocationRunLineRead] = []


# ── Default Rule ───────────────────────────────────────────────────────────────

class DimDefaultRuleCreate(BaseModel):
    rule_name: str
    transaction_type: str
    source_field: Optional[str] = None
    source_field_value: Optional[str] = None
    dim_type_id: uuid.UUID
    dim_value_id: uuid.UUID
    priority: int = 10
    active: bool = True


class DimDefaultRuleRead(DimDefaultRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dim_type_name: Optional[str] = None
    dim_value_name: Optional[str] = None


# ── Reclassification ───────────────────────────────────────────────────────────

class ReclassifyRequest(BaseModel):
    transaction_type: str
    transaction_id: str
    dim_type_id: uuid.UUID
    new_dim_value_id: uuid.UUID
    reason: str
    journal_entry_ref: Optional[str] = None


class ReclassifyRead(ReclassifyRequest):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    old_dim_value_id: Optional[uuid.UUID] = None
    old_dim_value_name: Optional[str] = None
    new_dim_value_name: Optional[str] = None
    dim_type_name: Optional[str] = None


# ── Reporting ──────────────────────────────────────────────────────────────────

class DimExpenseRow(BaseModel):
    dim_value_id: str
    dim_value_name: str
    dim_type_name: str
    total_amount: Decimal
    transaction_count: int


class DimTaggingCompletenessRow(BaseModel):
    transaction_type: str
    total_transactions: int
    tagged_count: int
    untagged_count: int
    completeness_pct: float


class DimDashboardSummary(BaseModel):
    total_dim_types: int
    total_dim_values: int
    total_cost_centers: int
    active_allocation_rules: int
    untagged_transactions_today: int
    pending_ai_recs: int


# ── AI Recommendations ─────────────────────────────────────────────────────────

class DimAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_type: DimAIAgentType
    title: str
    detail: Optional[str] = None
    severity: str
    status: DimAIRecStatus


class AckDimAIRec(BaseModel):
    status: DimAIRecStatus
