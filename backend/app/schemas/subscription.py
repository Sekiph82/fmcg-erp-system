from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Line ──────────────────────────────────────────────────────────────────────

class SubscriptionLineCreate(BaseModel):
    item_id: UUID
    item_variant_id: Optional[UUID] = None
    uom: str
    quantity: Decimal = Field(gt=0)
    min_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    allow_quantity_change: bool = False
    price_source: str = "CURRENT_PRICE_LIST"
    fixed_price: Optional[Decimal] = None
    active_flag: bool = True
    sort_order: int = 0
    notes: Optional[str] = None


class SubscriptionLineOut(SubscriptionLineCreate):
    id: UUID
    template_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Template ──────────────────────────────────────────────────────────────────

class SubscriptionTemplateCreate(BaseModel):
    template_code: str
    template_name: str
    customer_id: UUID
    distributor_id: Optional[UUID] = None
    price_list_id: Optional[UUID] = None
    contract_id: Optional[UUID] = None
    currency: str = "KES"

    recurrence_type: str
    recurrence_interval: Optional[int] = None
    recurrence_day_of_month: Optional[int] = None
    recurrence_weekday: Optional[int] = None
    recurrence_week_ordinal: Optional[int] = None

    start_date: date
    end_date: Optional[date] = None
    next_generation_date: Optional[date] = None

    generation_mode: str = "DRAFT_ONLY"
    delivery_address_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    payment_terms_id: Optional[UUID] = None

    allow_promotion_eval: bool = True
    price_change_threshold_pct: Optional[Decimal] = None
    notes: Optional[str] = None

    lines: List[SubscriptionLineCreate] = []


class SubscriptionTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    price_list_id: Optional[UUID] = None
    currency: Optional[str] = None
    recurrence_type: Optional[str] = None
    recurrence_interval: Optional[int] = None
    recurrence_day_of_month: Optional[int] = None
    recurrence_weekday: Optional[int] = None
    recurrence_week_ordinal: Optional[int] = None
    end_date: Optional[date] = None
    next_generation_date: Optional[date] = None
    generation_mode: Optional[str] = None
    delivery_address_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    payment_terms_id: Optional[UUID] = None
    allow_promotion_eval: Optional[bool] = None
    price_change_threshold_pct: Optional[Decimal] = None
    notes: Optional[str] = None


class SubscriptionTemplateOut(BaseModel):
    id: UUID
    template_code: str
    template_name: str
    customer_id: UUID
    distributor_id: Optional[UUID]
    price_list_id: Optional[UUID]
    contract_id: Optional[UUID]
    currency: str
    recurrence_type: str
    recurrence_interval: Optional[int]
    recurrence_day_of_month: Optional[int]
    recurrence_weekday: Optional[int]
    recurrence_week_ordinal: Optional[int]
    start_date: date
    end_date: Optional[date]
    next_generation_date: Optional[date]
    last_generation_date: Optional[date]
    status: str
    generation_mode: str
    delivery_address_id: Optional[UUID]
    route_id: Optional[UUID]
    payment_terms_id: Optional[UUID]
    allow_promotion_eval: bool
    price_change_threshold_pct: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    lines: List[SubscriptionLineOut] = []

    model_config = {"from_attributes": True}


# ── Generation Log ─────────────────────────────────────────────────────────────

class GenerationLogOut(BaseModel):
    id: UUID
    template_id: UUID
    generated_so_id: Optional[UUID]
    scheduled_date: date
    actual_generation_date: Optional[datetime]
    generation_status: str
    failure_reason: Optional[str]
    validation_warnings: Optional[list]
    generated_by_system: bool
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pause / Skip ──────────────────────────────────────────────────────────────

class PauseSkipCreate(BaseModel):
    action_type: str   # PAUSE / SKIP_ONE_CYCLE / RESUME / CANCEL
    effective_from: date
    effective_to: Optional[date] = None
    reason: Optional[str] = None
    portal_request: bool = False
    notes: Optional[str] = None


class PauseSkipOut(PauseSkipCreate):
    id: UUID
    template_id: UUID
    requested_by: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Recommendation ─────────────────────────────────────────────────────────

class SubAIRecOut(BaseModel):
    id: UUID
    agent_type: str
    status: str
    severity: str
    title: str
    body: str
    data: Optional[dict]
    template_id: Optional[UUID]
    customer_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubAIRecAck(BaseModel):
    status: str  # ACKNOWLEDGED / ACTIONED / DISMISSED


# ── Demand summary ────────────────────────────────────────────────────────────

class UpcomingDemandLine(BaseModel):
    template_id: UUID
    template_code: str
    customer_id: UUID
    item_id: UUID
    uom: str
    quantity: Decimal
    scheduled_date: date


class GenerateNowRequest(BaseModel):
    force: bool = False  # skip validation warnings
    notes: Optional[str] = None
