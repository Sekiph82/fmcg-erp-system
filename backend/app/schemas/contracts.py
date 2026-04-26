from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ── Term ──────────────────────────────────────────────────────────────────────

class ContractTermCreate(BaseModel):
    term_type: str
    item_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    value_type: str = "FIXED"
    value: Decimal
    min_threshold: Optional[Decimal] = None
    max_threshold: Optional[Decimal] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    active_flag: bool = True
    notes: Optional[str] = None


class ContractTermOut(ContractTermCreate):
    id: UUID
    contract_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Rebate ────────────────────────────────────────────────────────────────────

class ContractRebateCreate(BaseModel):
    rebate_name: Optional[str] = None
    rebate_type: str = "VOLUME"
    calculation_basis: str = "INVOICE"
    item_id: Optional[UUID] = None
    threshold: Optional[Decimal] = None
    rebate_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    rebate_amount: Optional[Decimal] = None
    settlement_frequency: str = "QUARTERLY"
    active_flag: bool = True
    notes: Optional[str] = None


class ContractRebateOut(ContractRebateCreate):
    id: UUID
    contract_id: UUID
    accrued_amount: Decimal
    settled_amount: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Contract Header ───────────────────────────────────────────────────────────

class ContractCreate(BaseModel):
    contract_code: str
    contract_name: str
    contract_type: str
    party_type: str
    party_id: UUID
    start_date: date
    end_date: Optional[date] = None
    currency: str = "KES"
    payment_terms_id: Optional[UUID] = None
    price_list_id: Optional[UUID] = None
    auto_renew: bool = False
    renewal_notice_days: int = 30
    linked_promo_ids: Optional[List[str]] = None
    linked_tpm_plan_id: Optional[UUID] = None
    notes: Optional[str] = None
    terms: List[ContractTermCreate] = []
    rebates: List[ContractRebateCreate] = []


class ContractUpdate(BaseModel):
    contract_name: Optional[str] = None
    end_date: Optional[date] = None
    currency: Optional[str] = None
    payment_terms_id: Optional[UUID] = None
    price_list_id: Optional[UUID] = None
    auto_renew: Optional[bool] = None
    renewal_notice_days: Optional[int] = None
    linked_promo_ids: Optional[List[str]] = None
    linked_tpm_plan_id: Optional[UUID] = None
    notes: Optional[str] = None
    change_summary: Optional[str] = None  # required to create a new version


class ContractOut(BaseModel):
    id: UUID
    contract_code: str
    contract_name: str
    contract_type: str
    party_type: str
    party_id: UUID
    start_date: date
    end_date: Optional[date]
    status: str
    currency: str
    payment_terms_id: Optional[UUID]
    price_list_id: Optional[UUID]
    auto_renew: bool
    renewal_notice_days: int
    linked_promo_ids: Optional[List[str]]
    linked_tpm_plan_id: Optional[UUID]
    notes: Optional[str]
    created_by: Optional[UUID]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    current_version: int
    created_at: datetime
    updated_at: datetime
    terms: List[ContractTermOut] = []
    rebates: List[ContractRebateOut] = []
    model_config = {"from_attributes": True}


# ── Approval ──────────────────────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    comments: Optional[str] = None


class ApprovalOut(BaseModel):
    id: UUID
    contract_id: UUID
    action: str
    actioned_by: Optional[UUID]
    comments: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Performance ───────────────────────────────────────────────────────────────

class PerformanceCreate(BaseModel):
    period: str
    target_value: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    notes: Optional[str] = None


class PerformanceUpdate(BaseModel):
    actual_value: Optional[Decimal] = None
    notes: Optional[str] = None


class PerformanceOut(BaseModel):
    id: UUID
    contract_id: UUID
    period: str
    target_value: Optional[Decimal]
    actual_value: Optional[Decimal]
    achievement_pct: Optional[Decimal]
    rebate_earned: Optional[Decimal]
    status: str
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Version ───────────────────────────────────────────────────────────────────

class VersionOut(BaseModel):
    id: UUID
    contract_id: UUID
    version_no: int
    change_summary: Optional[str]
    effective_date: Optional[date]
    approved_by: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI ────────────────────────────────────────────────────────────────────────

class CTAIRecOut(BaseModel):
    id: UUID
    agent_type: str
    status: str
    severity: str
    title: str
    body: str
    data: Optional[dict]
    contract_id: Optional[UUID]
    party_id: Optional[UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


class CTAIRecAck(BaseModel):
    status: str


# ── Termination ───────────────────────────────────────────────────────────────

class TerminateRequest(BaseModel):
    reason: str
