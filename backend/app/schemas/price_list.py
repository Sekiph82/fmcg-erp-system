from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel

from app.models.price_list import (
    PLType, PLStatus, PLDiscountType, PLApprovalAction,
    PLDiscountScope, PLChangeType, PLAIAgentType, PLAIRecStatus,
)


# ── Header ─────────────────────────────────────────────────────────────────────

class PLHeaderCreate(BaseModel):
    price_list_code: str
    price_list_name: str
    currency: str = "KES"
    pl_type: PLType = PLType.STANDARD
    country: Optional[str] = None
    region: Optional[str] = None
    channel: Optional[str] = None
    customer_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    valid_from: date
    valid_to: Optional[date] = None
    priority_rank: int = 50
    default_flag: bool = False
    minimum_margin_pct: Optional[Decimal] = None
    max_manual_discount: Optional[Decimal] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


class PLHeaderUpdate(BaseModel):
    price_list_name: Optional[str] = None
    currency: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    priority_rank: Optional[int] = None
    default_flag: Optional[bool] = None
    minimum_margin_pct: Optional[Decimal] = None
    max_manual_discount: Optional[Decimal] = None
    notes: Optional[str] = None


class PLHeaderOut(BaseModel):
    id: UUID
    price_list_code: str
    price_list_name: str
    currency: str
    pl_type: PLType
    country: Optional[str]
    region: Optional[str]
    channel: Optional[str]
    customer_id: Optional[UUID]
    distributor_id: Optional[UUID]
    valid_from: date
    valid_to: Optional[date]
    status: PLStatus
    priority_rank: int
    default_flag: bool
    minimum_margin_pct: Optional[Decimal]
    max_manual_discount: Optional[Decimal]
    created_by: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Line ───────────────────────────────────────────────────────────────────────

class PLLineCreate(BaseModel):
    product_id: UUID
    brand: Optional[str] = None
    category: Optional[str] = None
    uom: str = "KG"
    base_price: Decimal
    minimum_price: Optional[Decimal] = None
    recommended_price: Optional[Decimal] = None
    currency: str = "KES"
    tax_included_flag: bool = False
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


class PLLineUpdate(BaseModel):
    base_price: Optional[Decimal] = None
    minimum_price: Optional[Decimal] = None
    recommended_price: Optional[Decimal] = None
    uom: Optional[str] = None
    active_flag: Optional[bool] = None
    notes: Optional[str] = None


class PLLineOut(BaseModel):
    id: UUID
    header_id: UUID
    product_id: UUID
    brand: Optional[str]
    category: Optional[str]
    uom: str
    base_price: Decimal
    minimum_price: Optional[Decimal]
    recommended_price: Optional[Decimal]
    currency: str
    tax_included_flag: bool
    valid_from: Optional[date]
    valid_to: Optional[date]
    active_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Tier ───────────────────────────────────────────────────────────────────────

class PLTierCreate(BaseModel):
    min_qty: Decimal
    max_qty: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    discount_pct: Optional[Decimal] = None
    fixed_discount_amount: Optional[Decimal] = None
    effective_margin_pct: Optional[Decimal] = None


class PLTierOut(BaseModel):
    id: UUID
    line_id: UUID
    min_qty: Decimal
    max_qty: Optional[Decimal]
    unit_price: Optional[Decimal]
    discount_pct: Optional[Decimal]
    fixed_discount_amount: Optional[Decimal]
    effective_margin_pct: Optional[Decimal]
    active_flag: bool

    model_config = {"from_attributes": True}


# ── Assignment ─────────────────────────────────────────────────────────────────

class PLAssignmentCreate(BaseModel):
    customer_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    segment: Optional[str] = None
    valid_from: date
    valid_to: Optional[date] = None
    priority_rank: int = 50
    notes: Optional[str] = None


class PLAssignmentOut(BaseModel):
    id: UUID
    header_id: UUID
    customer_id: Optional[UUID]
    distributor_id: Optional[UUID]
    channel: Optional[str]
    region: Optional[str]
    country: Optional[str]
    segment: Optional[str]
    valid_from: date
    valid_to: Optional[date]
    priority_rank: int
    active_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Discount Rule ──────────────────────────────────────────────────────────────

class PLDiscountRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    scope: PLDiscountScope = PLDiscountScope.LINE
    discount_type: PLDiscountType
    discount_value: Decimal
    max_discount_pct: Optional[Decimal] = None
    requires_approval: bool = False
    min_margin_pct: Optional[Decimal] = None
    applies_to_pl_type: Optional[str] = None
    applies_to_channel: Optional[str] = None
    applies_to_customer_id: Optional[UUID] = None
    reason_required: bool = False
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


class PLDiscountRuleOut(BaseModel):
    id: UUID
    rule_code: str
    rule_name: str
    scope: PLDiscountScope
    discount_type: PLDiscountType
    discount_value: Decimal
    max_discount_pct: Optional[Decimal]
    requires_approval: bool
    min_margin_pct: Optional[Decimal]
    applies_to_pl_type: Optional[str]
    applies_to_channel: Optional[str]
    reason_required: bool
    valid_from: Optional[date]
    valid_to: Optional[date]
    active_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Approval ───────────────────────────────────────────────────────────────────

class PLApprovalSubmit(BaseModel):
    submitted_by: str
    notes: Optional[str] = None


class PLApprovalReview(BaseModel):
    action: PLApprovalAction
    reviewed_by: str
    notes: Optional[str] = None


class PLApprovalOut(BaseModel):
    id: UUID
    header_id: UUID
    action: PLApprovalAction
    submitted_by: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Price Resolution ───────────────────────────────────────────────────────────

class PriceResolveRequest(BaseModel):
    product_id: UUID
    quantity: Decimal
    uom: str = "KG"
    customer_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    as_of_date: Optional[date] = None


class PriceResolveResult(BaseModel):
    product_id: str
    quantity: Decimal
    uom: str
    unit_price: Decimal
    currency: str
    source_price_list: Optional[str]
    source_pl_id: Optional[str]
    source_pl_type: Optional[str]
    tier_applied: bool
    discount_applied: Optional[Decimal]
    effective_price: Decimal
    minimum_price: Optional[Decimal]
    margin_warning: bool
    margin_pct: Optional[Decimal]
    resolution_path: List[str]


# ── Margin Check ───────────────────────────────────────────────────────────────

class MarginCheckRequest(BaseModel):
    product_id: UUID
    proposed_price: Decimal
    quantity: Decimal
    currency: str = "KES"


class MarginCheckResult(BaseModel):
    product_id: str
    proposed_price: Decimal
    cost_price: Optional[Decimal]
    margin_pct: Optional[Decimal]
    margin_status: str
    blocked: bool
    requires_approval: bool
    message: str


# ── Bulk Import ────────────────────────────────────────────────────────────────

class PLBulkImportRow(BaseModel):
    product_code: str
    uom: str
    base_price: Decimal
    currency: str = "KES"
    minimum_price: Optional[Decimal] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


class PLBulkImportRequest(BaseModel):
    header_id: UUID
    rows: List[PLBulkImportRow]
    imported_by: str


class PLBulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[str]


# ── Change History ─────────────────────────────────────────────────────────────

class PLChangeHistoryOut(BaseModel):
    id: UUID
    header_id: UUID
    line_id: Optional[UUID]
    change_type: PLChangeType
    changed_by: str
    changed_at: datetime
    old_value_json: Optional[Dict[str, Any]]
    new_value_json: Optional[Dict[str, Any]]
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── AI ─────────────────────────────────────────────────────────────────────────

class PLAIRecAck(BaseModel):
    status: PLAIRecStatus
    actioned_by: str


class PLAIRecOut(BaseModel):
    id: UUID
    header_id: Optional[UUID]
    line_id: Optional[UUID]
    agent_type: PLAIAgentType
    status: PLAIRecStatus
    title: str
    body: str
    severity: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}
