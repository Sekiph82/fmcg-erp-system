from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.models.tpm import (
    TPMPeriodType, TPMPlanStatus, TPMPromotionType, TPMObjectiveType,
    TPMPromotionStatus, TPMBudgetType, TPMBaselineMethod,
    TPMClaimantType, TPMClaimType, TPMClaimStatus,
    TPMAIAgentType, TPMAIRecStatus,
)


# ── Plan ──────────────────────────────────────────────────────────────────────

class TPMPlanCreate(BaseModel):
    plan_code: str
    plan_name: str
    fiscal_year: int
    period_type: TPMPeriodType = TPMPeriodType.ANNUAL
    plan_start_date: date
    plan_end_date: date
    total_planned_budget: Decimal = Decimal("0")
    notes: Optional[str] = None


class TPMPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plan_code: str
    plan_name: str
    fiscal_year: int
    period_type: TPMPeriodType
    plan_start_date: date
    plan_end_date: date
    status: TPMPlanStatus
    total_planned_budget: Decimal
    total_approved_budget: Decimal
    total_actual_spend: Decimal
    notes: Optional[str]
    created_at: datetime
    promotion_count: Optional[int] = 0


# ── Promotion ─────────────────────────────────────────────────────────────────

class TPMPromotionCreate(BaseModel):
    promotion_code: str
    promotion_name: str
    tpm_plan_id: Optional[UUID] = None
    linked_scheme_id: Optional[UUID] = None
    promotion_type: TPMPromotionType
    objective_type: TPMObjectiveType
    valid_from: date
    valid_to: date
    brand_id: Optional[str] = None
    category_id: Optional[str] = None
    channel_id: Optional[str] = None
    region_id: Optional[str] = None
    customer_id: Optional[UUID] = None
    distributor_group_id: Optional[str] = None
    notes: Optional[str] = None


class TPMPromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    promotion_code: str
    promotion_name: str
    tpm_plan_id: Optional[UUID]
    linked_scheme_id: Optional[UUID]
    promotion_type: TPMPromotionType
    objective_type: TPMObjectiveType
    status: TPMPromotionStatus
    valid_from: date
    valid_to: date
    brand_id: Optional[str]
    category_id: Optional[str]
    channel_id: Optional[str]
    region_id: Optional[str]
    customer_id: Optional[UUID]
    distributor_group_id: Optional[str]
    notes: Optional[str]
    created_at: datetime
    budget_lines: List[TPMBudgetLineRead] = []
    expected_perf: Optional[TPMExpectedPerfRead] = None
    actual_perf: Optional[TPMActualPerfRead] = None


# ── Budget Line ───────────────────────────────────────────────────────────────

class TPMBudgetLineCreate(BaseModel):
    budget_type: TPMBudgetType
    planned_spend_amount: Decimal = Decimal("0")
    cost_center_id: Optional[UUID] = None
    dimension_value_id: Optional[UUID] = None
    notes: Optional[str] = None


class TPMBudgetLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tpm_promotion_id: UUID
    budget_type: TPMBudgetType
    planned_spend_amount: Decimal
    approved_spend_amount: Decimal
    actual_spend_amount: Decimal
    accrued_spend_amount: Decimal
    settled_spend_amount: Decimal
    remaining_budget_amount: Decimal
    cost_center_id: Optional[UUID]
    notes: Optional[str]


# ── Expected Performance ──────────────────────────────────────────────────────

class TPMExpectedPerfCreate(BaseModel):
    baseline_volume: Decimal = Decimal("0")
    target_volume: Decimal = Decimal("0")
    expected_uplift_qty: Decimal = Decimal("0")
    expected_uplift_pct: Decimal = Decimal("0")
    expected_revenue: Decimal = Decimal("0")
    expected_margin_impact: Decimal = Decimal("0")
    expected_roi_pct: Decimal = Decimal("0")
    baseline_method: TPMBaselineMethod = TPMBaselineMethod.PRIOR_PERIOD
    assumptions: Optional[str] = None
    notes: Optional[str] = None


class TPMExpectedPerfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tpm_promotion_id: UUID
    baseline_volume: Decimal
    target_volume: Decimal
    expected_uplift_qty: Decimal
    expected_uplift_pct: Decimal
    expected_revenue: Decimal
    expected_margin_impact: Decimal
    expected_roi_pct: Decimal
    baseline_method: TPMBaselineMethod
    assumptions: Optional[str]
    notes: Optional[str]


# ── Actual Performance ────────────────────────────────────────────────────────

class TPMActualPerfCreate(BaseModel):
    actual_volume: Decimal = Decimal("0")
    actual_uplift_qty: Decimal = Decimal("0")
    actual_revenue: Decimal = Decimal("0")
    actual_margin_impact: Decimal = Decimal("0")
    actual_spend: Decimal = Decimal("0")
    post_event_notes: Optional[str] = None


class TPMActualPerfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tpm_promotion_id: UUID
    actual_volume: Decimal
    actual_uplift_qty: Decimal
    actual_uplift_pct: Decimal
    actual_revenue: Decimal
    actual_margin_impact: Decimal
    actual_spend: Decimal
    actual_roi_pct: Decimal
    post_event_notes: Optional[str]


# ── Claim ─────────────────────────────────────────────────────────────────────

class TPMClaimLineCreate(BaseModel):
    source_order_id: Optional[UUID] = None
    source_scheme_id: Optional[UUID] = None
    item_id: Optional[UUID] = None
    quantity_basis: Optional[Decimal] = None
    rate_basis: Optional[Decimal] = None
    claimed_amount: Decimal = Decimal("0")
    supporting_doc_ref: Optional[str] = None
    notes: Optional[str] = None


class TPMClaimLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tpm_claim_id: UUID
    source_order_id: Optional[UUID]
    source_scheme_id: Optional[UUID]
    item_id: Optional[UUID]
    quantity_basis: Optional[Decimal]
    rate_basis: Optional[Decimal]
    claimed_amount: Decimal
    approved_amount: Decimal
    supporting_doc_ref: Optional[str]
    notes: Optional[str]


class TPMClaimCreate(BaseModel):
    tpm_promotion_id: UUID
    claimant_type: TPMClaimantType
    claimant_id: Optional[UUID] = None
    claim_date: date
    claim_type: TPMClaimType
    claimed_amount: Decimal
    reference_document_no: Optional[str] = None
    notes: Optional[str] = None
    claim_lines: List[TPMClaimLineCreate] = []


class TPMClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    claim_no: str
    tpm_promotion_id: UUID
    claimant_type: TPMClaimantType
    claimant_id: Optional[UUID]
    claim_date: date
    claim_type: TPMClaimType
    claimed_amount: Decimal
    approved_amount: Decimal
    rejected_amount: Decimal
    settled_amount: Decimal
    status: TPMClaimStatus
    reference_document_no: Optional[str]
    reviewer_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime
    claim_lines: List[TPMClaimLineRead] = []


class TPMClaimReviewRequest(BaseModel):
    approved: bool
    approved_amount: Optional[Decimal] = None
    reviewer_notes: Optional[str] = None


class TPMClaimSettleRequest(BaseModel):
    settle_amount: Decimal
    reference_document_no: Optional[str] = None


# ── AI ────────────────────────────────────────────────────────────────────────

class TPMAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_type: TPMAIAgentType
    tpm_promotion_id: Optional[UUID]
    tpm_claim_id: Optional[UUID]
    title: str
    detail: Optional[str]
    severity: Optional[str]
    status: TPMAIRecStatus
    actioned_notes: Optional[str]
    created_at: datetime


class TPMAIRecAckRequest(BaseModel):
    status: TPMAIRecStatus
    actioned_notes: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TPMDashboard(BaseModel):
    active_plans: int
    active_promotions: int
    total_planned_budget: Decimal
    total_actual_spend: Decimal
    open_claims: int
    open_claims_amount: Decimal
    pending_approvals: int
    promotions_by_status: dict
    top_promotions: list


# ── Reports ───────────────────────────────────────────────────────────────────

class BudgetVsActualRow(BaseModel):
    promotion_id: str
    promotion_code: str
    promotion_name: str
    promotion_type: str
    planned: Decimal
    approved: Decimal
    actual: Decimal
    accrued: Decimal
    variance: Decimal
    utilization_pct: Decimal


class ROIRow(BaseModel):
    promotion_id: str
    promotion_code: str
    promotion_name: str
    objective_type: str
    expected_roi_pct: Decimal
    actual_roi_pct: Decimal
    expected_uplift_pct: Decimal
    actual_uplift_pct: Decimal
    actual_spend: Decimal
    roi_vs_plan: Decimal


class ClaimAgingRow(BaseModel):
    claim_id: str
    claim_no: str
    promotion_name: str
    claimant_type: str
    claim_type: str
    claimed_amount: Decimal
    approved_amount: Decimal
    settled_amount: Decimal
    status: str
    claim_date: date
    age_days: int


# Fix forward refs
TPMPromotionRead.model_rebuild()
