"""Promotional Schemes Auto-Apply schemas."""
from __future__ import annotations
from typing import Optional, List
from datetime import date
from decimal import Decimal
import uuid
from pydantic import BaseModel, ConfigDict

from app.models.promotions import (
    SchemeStatus, SchemeType, TriggerBasis, RewardType,
    PromoApplicationType, PromoImpactType, OverrideStatus,
    PromoAIAgentType, PromoAIRecStatus,
)


# ── Eligibility Scope ──────────────────────────────────────────────────────────

class PromoEligibilityCreate(BaseModel):
    applies_to_customer_id: Optional[uuid.UUID] = None
    applies_to_customer_group: Optional[str] = None
    applies_to_distributor_group: Optional[str] = None
    applies_to_region: Optional[str] = None
    applies_to_channel: Optional[str] = None
    applies_to_sales_team: Optional[str] = None
    applies_to_price_list_id: Optional[uuid.UUID] = None
    applies_to_item_id: Optional[uuid.UUID] = None
    applies_to_item_category: Optional[str] = None
    applies_to_brand: Optional[str] = None
    min_order_qty: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    active: bool = True
    notes: Optional[str] = None


class PromoEligibilityRead(PromoEligibilityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scheme_id: uuid.UUID


# ── Tier Line ──────────────────────────────────────────────────────────────────

class PromoTierLineCreate(BaseModel):
    min_qty: Optional[Decimal] = None
    max_qty: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    reward_percent: Optional[Decimal] = None
    reward_amount: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    sort_order: int = 1


class PromoTierLineRead(PromoTierLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rule_line_id: uuid.UUID


# ── Rule Line ──────────────────────────────────────────────────────────────────

class PromoRuleLineCreate(BaseModel):
    trigger_basis: TriggerBasis = TriggerBasis.SKU
    trigger_item_id: Optional[uuid.UUID] = None
    trigger_category: Optional[str] = None
    trigger_brand: Optional[str] = None
    min_trigger_qty: Decimal = Decimal(0)
    min_trigger_value: Decimal = Decimal(0)
    max_trigger_qty: Optional[Decimal] = None
    reward_type: RewardType
    reward_item_id: Optional[uuid.UUID] = None
    reward_qty: Optional[Decimal] = None
    reward_percent: Optional[Decimal] = None
    reward_amount: Optional[Decimal] = None
    reward_special_unit_price: Optional[Decimal] = None
    max_reward_qty: Optional[Decimal] = None
    repeatable: bool = False
    sort_order: int = 1
    notes: Optional[str] = None
    tiers: List[PromoTierLineCreate] = []


class PromoRuleLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scheme_id: uuid.UUID
    trigger_basis: TriggerBasis
    trigger_item_id: Optional[uuid.UUID] = None
    trigger_item_name: Optional[str] = None
    trigger_category: Optional[str] = None
    trigger_brand: Optional[str] = None
    min_trigger_qty: Decimal
    min_trigger_value: Decimal
    max_trigger_qty: Optional[Decimal] = None
    reward_type: RewardType
    reward_item_id: Optional[uuid.UUID] = None
    reward_item_name: Optional[str] = None
    reward_qty: Optional[Decimal] = None
    reward_percent: Optional[Decimal] = None
    reward_amount: Optional[Decimal] = None
    reward_special_unit_price: Optional[Decimal] = None
    max_reward_qty: Optional[Decimal] = None
    repeatable: bool
    sort_order: int
    notes: Optional[str] = None


# ── Scheme Header ──────────────────────────────────────────────────────────────

class PromoSchemeCreate(BaseModel):
    scheme_code: str
    scheme_name: str
    scheme_type: SchemeType
    valid_from: date
    valid_to: date
    priority_rank: int = 10
    stackable: bool = False
    exclusive: bool = False
    requires_approval_override: bool = False
    cost_center_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    eligibility_scopes: List[PromoEligibilityCreate] = []
    rule_lines: List[PromoRuleLineCreate] = []


class PromoSchemeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scheme_code: str
    scheme_name: str
    scheme_type: SchemeType
    status: SchemeStatus
    valid_from: date
    valid_to: date
    priority_rank: int
    stackable: bool
    exclusive: bool
    requires_approval_override: bool
    notes: Optional[str] = None
    eligibility_scopes: List[PromoEligibilityRead] = []
    rule_lines: List[PromoRuleLineRead] = []
    usage_count: int = 0
    total_cost: Decimal = Decimal(0)


class PromoSchemeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scheme_code: str
    scheme_name: str
    scheme_type: SchemeType
    status: SchemeStatus
    valid_from: date
    valid_to: date
    priority_rank: int
    stackable: bool
    exclusive: bool


# ── Evaluation ─────────────────────────────────────────────────────────────────

class EvaluateOrderRequest(BaseModel):
    sales_order_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    price_list_id: Optional[uuid.UUID] = None
    order_lines: List[OrderLineInput]


class OrderLineInput(BaseModel):
    line_id: Optional[str] = None
    item_id: uuid.UUID
    item_category: Optional[str] = None
    item_brand: Optional[str] = None
    qty: Decimal
    unit_price: Decimal
    line_total: Decimal


class PromoLineImpactResult(BaseModel):
    impact_type: PromoImpactType
    sales_order_line_id: Optional[str] = None
    reward_item_id: Optional[uuid.UUID] = None
    reward_item_name: Optional[str] = None
    reward_qty: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_pct: Optional[Decimal] = None
    notes: Optional[str] = None


class PromoApplicationResult(BaseModel):
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_name: str
    application_type: PromoApplicationType
    calculated_benefit: Decimal
    promo_cost_estimate: Decimal
    stack_sequence: int
    line_impacts: List[PromoLineImpactResult]
    next_threshold_hint: Optional[str] = None


class EvaluateOrderResult(BaseModel):
    sales_order_id: uuid.UUID
    applied_promos: List[PromoApplicationResult]
    skipped_promos: List[dict]
    total_discount: Decimal
    total_free_goods_value: Decimal
    total_promo_cost: Decimal


# ── Sales Order Promo Read ────────────────────────────────────────────────────

class SalesOrderPromoLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sales_order_line_id: Optional[uuid.UUID] = None
    impact_type: PromoImpactType
    impacted_qty: Optional[Decimal] = None
    impacted_amount: Optional[Decimal] = None
    reward_item_id: Optional[uuid.UUID] = None
    reward_qty: Optional[Decimal] = None
    reward_item_name: Optional[str] = None
    notes: Optional[str] = None


class SalesOrderPromoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sales_order_id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: Optional[str] = None
    scheme_code: Optional[str] = None
    application_type: PromoApplicationType
    calculated_benefit_amount: Decimal
    promo_cost_estimate: Decimal
    stack_sequence: int
    line_impacts: List[SalesOrderPromoLineRead] = []


# ── Override Request ───────────────────────────────────────────────────────────

class OverrideRequestCreate(BaseModel):
    sales_order_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None
    requested_discount_pct: Optional[Decimal] = None
    requested_free_qty: Optional[Decimal] = None
    reason: str


class OverrideRequestRead(OverrideRequestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: OverrideStatus
    requested_by_id: Optional[uuid.UUID] = None
    approved_by_id: Optional[uuid.UUID] = None
    approver_notes: Optional[str] = None


class ApproveOverrideRequest(BaseModel):
    approved: bool
    approver_notes: Optional[str] = None


# ── Usage Report ──────────────────────────────────────────────────────────────

class PromoUsageRow(BaseModel):
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_name: str
    scheme_type: SchemeType
    order_count: int
    total_discount: Decimal
    total_free_value: Decimal
    total_cost: Decimal


# ── AI Recommendations ─────────────────────────────────────────────────────────

class PromoAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_type: PromoAIAgentType
    title: str
    detail: Optional[str] = None
    severity: str
    status: PromoAIRecStatus
    scheme_id: Optional[uuid.UUID] = None


class AckPromoAIRec(BaseModel):
    status: PromoAIRecStatus


# ── Dashboard ──────────────────────────────────────────────────────────────────

class PromoDashboard(BaseModel):
    active_schemes: int
    expiring_soon: int
    total_applications_month: int
    total_discount_month: Decimal
    total_free_value_month: Decimal
    pending_override_requests: int
    pending_ai_recs: int


# Forward reference resolution
EvaluateOrderRequest.model_rebuild()
