from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ── Rule ──────────────────────────────────────────────────────────────────────

class RuleLineCreate(BaseModel):
    condition_type: str
    min_threshold: Optional[Decimal] = None
    max_threshold: Optional[Decimal] = None
    commission_type: str = "PERCENTAGE"
    commission_value: Decimal = Field(ge=0)
    target_flag: bool = False
    sort_order: int = 0
    notes: Optional[str] = None


class RuleLineOut(RuleLineCreate):
    id: UUID
    rule_id: UUID
    model_config = {"from_attributes": True}


class CommissionRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    applies_to: str
    applicable_scope: str = "GLOBAL"
    scope_ref_id: Optional[UUID] = None
    priority: int = 10
    start_date: date
    end_date: Optional[date] = None
    contract_id: Optional[UUID] = None
    notes: Optional[str] = None
    lines: List[RuleLineCreate] = []


class CommissionRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    priority: Optional[int] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CommissionRuleOut(BaseModel):
    id: UUID
    rule_code: str
    rule_name: str
    applies_to: str
    applicable_scope: str
    scope_ref_id: Optional[UUID]
    priority: int
    start_date: date
    end_date: Optional[date]
    status: str
    contract_id: Optional[UUID]
    notes: Optional[str]
    created_at: datetime
    lines: List[RuleLineOut] = []
    model_config = {"from_attributes": True}


# ── Target ────────────────────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    entity_id: UUID
    applies_to: str
    period: str
    target_value: Decimal = Field(gt=0)
    notes: Optional[str] = None


class TargetOut(TargetCreate):
    id: UUID
    actual_value: Decimal
    achievement_pct: Optional[Decimal]
    bonus_earned: Optional[Decimal]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Transaction ───────────────────────────────────────────────────────────────

class CommissionCalcRequest(BaseModel):
    sales_order_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    distributor_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    base_amount: Decimal = Field(gt=0)
    calculation_date: date
    period: Optional[str] = None
    is_reversal: bool = False
    notes: Optional[str] = None


class CommissionTxnOut(BaseModel):
    id: UUID
    rule_id: Optional[UUID]
    sales_order_id: Optional[UUID]
    invoice_id: Optional[UUID]
    sales_rep_id: Optional[UUID]
    distributor_id: Optional[UUID]
    customer_id: Optional[UUID]
    base_amount: Decimal
    commission_pct: Optional[Decimal]
    commission_amount: Decimal
    calculation_date: date
    period: str
    status: str
    is_reversal: bool
    calc_detail: Optional[dict]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    comments: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str


# ── Adjustment ────────────────────────────────────────────────────────────────

class AdjustmentCreate(BaseModel):
    adjustment_amount: Decimal
    reason: str
    notes: Optional[str] = None


class AdjustmentOut(AdjustmentCreate):
    id: UUID
    txn_id: UUID
    approved_by: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Payout ────────────────────────────────────────────────────────────────────

class PayoutCreate(BaseModel):
    entity_id: UUID
    applies_to: str
    period: str
    notes: Optional[str] = None


class PayoutOut(BaseModel):
    id: UUID
    entity_id: UUID
    applies_to: str
    period: str
    total_commission: Decimal
    adjustments_total: Decimal
    net_commission: Decimal
    paid_amount: Decimal
    payment_date: Optional[date]
    status: str
    txn_ids: Optional[list]
    approved_by: Optional[UUID]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI ────────────────────────────────────────────────────────────────────────

class CMAIRecOut(BaseModel):
    id: UUID
    agent_type: str
    status: str
    severity: str
    title: str
    body: str
    data: Optional[dict]
    entity_id: Optional[UUID]
    rule_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


class CMAIRecAck(BaseModel):
    status: str
