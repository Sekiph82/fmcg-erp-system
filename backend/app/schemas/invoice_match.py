from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Tolerance Rule ────────────────────────────────────────────────────────────

class ToleranceRuleCreate(BaseModel):
    rule_name: str
    supplier_id: Optional[UUID] = None
    item_category: Optional[str] = None
    quantity_tolerance_pct: Decimal = Decimal("1")
    quantity_tolerance_abs: Optional[Decimal] = None
    price_tolerance_pct: Decimal = Decimal("2")
    price_tolerance_abs: Optional[Decimal] = None
    tax_tolerance_pct: Decimal = Decimal("0")
    auto_approve_within_tolerance: bool = True
    block_payment_beyond_tolerance: bool = True
    approval_role_required: Optional[str] = None
    is_active: bool = True
    priority: int = 10
    notes: Optional[str] = None


class ToleranceRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    quantity_tolerance_pct: Optional[Decimal] = None
    price_tolerance_pct: Optional[Decimal] = None
    tax_tolerance_pct: Optional[Decimal] = None
    auto_approve_within_tolerance: Optional[bool] = None
    block_payment_beyond_tolerance: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class ToleranceRuleOut(ToleranceRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


# ── GRN Link ──────────────────────────────────────────────────────────────────

class MatchGRNLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    grn_id: Optional[UUID] = None
    grn_line_id: Optional[UUID] = None
    grn_no: Optional[str] = None
    received_qty: Optional[Decimal] = None
    accepted_qty: Optional[Decimal] = None
    rejected_qty: Optional[Decimal] = None
    received_date: Optional[date] = None


# ── Match Line ────────────────────────────────────────────────────────────────

class MatchLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    invoice_line_id: Optional[UUID] = None
    po_line_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    material_name: Optional[str] = None
    description: Optional[str] = None
    ordered_qty: Optional[Decimal] = None
    ordered_unit_price: Optional[Decimal] = None
    ordered_tax_rate: Optional[Decimal] = None
    total_received_qty: Optional[Decimal] = None
    total_accepted_qty: Optional[Decimal] = None
    prev_invoiced_qty: Decimal
    billable_qty: Optional[Decimal] = None
    invoiced_qty: Optional[Decimal] = None
    invoiced_unit_price: Optional[Decimal] = None
    invoiced_tax_rate: Optional[Decimal] = None
    invoiced_line_total: Optional[Decimal] = None
    qty_variance: Optional[Decimal] = None
    price_variance: Optional[Decimal] = None
    tax_variance: Optional[Decimal] = None
    qty_variance_pct: Optional[Decimal] = None
    price_variance_pct: Optional[Decimal] = None
    match_status: str
    tolerance_rule_id: Optional[UUID] = None
    action_required: bool
    notes: Optional[str] = None
    grn_links: List[MatchGRNLinkOut] = []


# ── Review ────────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    action: str
    reviewer_name: str
    reviewer_role: Optional[str] = None
    justification: Optional[str] = None
    line_ids: Optional[List[str]] = None


class ReviewOut(ReviewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    created_at: datetime


# ── Header ────────────────────────────────────────────────────────────────────

class MatchHeaderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    match_no: str
    invoice_id: UUID
    po_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[date] = None
    currency: str
    invoice_total: Decimal
    overall_status: str
    duplicate_flag: bool
    review_required: bool
    is_payable: bool
    payment_hold_reason: Optional[str] = None
    run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MatchHeaderOut(MatchHeaderSummary):
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    match_lines: List[MatchLineOut] = []
    reviews: List[ReviewOut] = []


# ── Duplicate Log ─────────────────────────────────────────────────────────────

class DuplicateLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_id: UUID
    matched_invoice_id: Optional[UUID] = None
    invoice_no: Optional[str] = None
    matched_invoice_no: Optional[str] = None
    duplicate_risk: str
    match_reasons: Optional[Any] = None
    similarity_score: Optional[Decimal] = None
    is_resolved: bool
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime


# ── AI Rec ────────────────────────────────────────────────────────────────────

class IMAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: Optional[UUID] = None
    agent_type: str
    status: str
    title: str
    explanation: Optional[str] = None
    impact_summary: Optional[str] = None
    suggested_action: Optional[str] = None
    priority: str
    confidence_score: Optional[Decimal] = None
    actioned_at: Optional[datetime] = None
    created_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────

class IMDashboard(BaseModel):
    total_matches: int
    fully_matched: int
    within_tolerance: int
    mismatched: int
    blocked: int
    pending_review: int
    duplicate_suspected: int
    payable_count: int
    on_hold_count: int
    pending_ai_recs: int
    mismatch_by_type: List[dict]
    recent_matches: List[MatchHeaderSummary]


# ── Run Request ───────────────────────────────────────────────────────────────

class RunMatchRequest(BaseModel):
    invoice_id: UUID
    force_rerun: bool = False
