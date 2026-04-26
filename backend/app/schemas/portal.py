from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, EmailStr
import uuid

from app.models.portal import (
    PortalAccountType, PortalAccountStatus, PortalUserRole,
    PortalActivityType, PortalClaimType, PortalClaimStatus,
    PortalOrderMode, PortalDraftOrderStatus,
    PortalAIAgentType, PortalAIRecStatus,
)


# ── Portal Account ─────────────────────────────────────────────────────────────

class PortalAccountCreate(BaseModel):
    account_type: PortalAccountType = PortalAccountType.CUSTOMER
    linked_customer_id: Optional[str] = None
    linked_distributor_id: Optional[str] = None
    default_currency: str = "KES"
    preferred_language: str = "en"
    order_mode: PortalOrderMode = PortalOrderMode.DRAFT_REQUEST
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    timezone: str = "Africa/Nairobi"
    can_view_prices: bool = True
    can_view_promotions: bool = False
    can_initiate_payment: bool = False
    notes: Optional[str] = None


class PortalAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_code: str
    account_type: PortalAccountType
    linked_customer_id: Optional[str] = None
    linked_distributor_id: Optional[str] = None
    portal_status: PortalAccountStatus
    default_currency: str
    preferred_language: str
    order_mode: PortalOrderMode
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    timezone: str
    can_view_prices: bool
    can_view_promotions: bool
    can_initiate_payment: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class PortalAccountUpdate(BaseModel):
    portal_status: Optional[PortalAccountStatus] = None
    order_mode: Optional[PortalOrderMode] = None
    can_view_prices: Optional[bool] = None
    can_view_promotions: Optional[bool] = None
    can_initiate_payment: Optional[bool] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    notes: Optional[str] = None


# ── Portal User ────────────────────────────────────────────────────────────────

class PortalUserInvite(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    role_type: PortalUserRole = PortalUserRole.VIEWER
    invited_by: Optional[str] = None


class PortalUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    portal_account_id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    role_type: PortalUserRole
    is_active: bool
    last_login_at: Optional[datetime] = None
    invited_by: Optional[str] = None
    created_at: Optional[datetime] = None


class PortalLoginRequest(BaseModel):
    email: str
    password: str


class PortalLoginResponse(BaseModel):
    token: str
    portal_user_id: str
    portal_account_id: str
    full_name: str
    role_type: str
    account_type: str
    account_code: str


class PortalPasswordResetRequest(BaseModel):
    email: str


class PortalPasswordSetRequest(BaseModel):
    token: str
    new_password: str


# ── Activity Log ──────────────────────────────────────────────────────────────

class PortalActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    portal_user_id: uuid.UUID
    activity_type: PortalActivityType
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    activity_datetime: datetime
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Claims ─────────────────────────────────────────────────────────────────────

class PortalClaimCreate(BaseModel):
    claim_type: PortalClaimType
    linked_order_id: Optional[str] = None
    linked_invoice_id: Optional[str] = None
    linked_shipment_id: Optional[str] = None
    linked_lot_id: Optional[str] = None
    quantity_involved: Optional[Decimal] = None
    reason: str
    description: Optional[str] = None
    notes: Optional[str] = None


class PortalClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    claim_no: str
    portal_account_id: uuid.UUID
    submitted_by: Optional[str] = None
    claim_type: PortalClaimType
    linked_order_id: Optional[str] = None
    linked_invoice_id: Optional[str] = None
    linked_shipment_id: Optional[str] = None
    quantity_involved: Optional[Decimal] = None
    reason: str
    description: Optional[str] = None
    status: PortalClaimStatus
    resolution_notes: Optional[str] = None
    resolved_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class PortalClaimReview(BaseModel):
    status: PortalClaimStatus
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None


# ── Draft Order ───────────────────────────────────────────────────────────────

class PortalDraftOrderLineCreate(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: Decimal
    unit: str = "PCS"
    unit_price: Optional[Decimal] = Decimal("0")
    notes: Optional[str] = None


class PortalDraftOrderCreate(BaseModel):
    source_order_id: Optional[str] = None
    requested_delivery_date: Optional[date] = None
    delivery_address: Optional[str] = None
    order_comments: Optional[str] = None
    currency: str = "KES"
    lines: List[PortalDraftOrderLineCreate] = []


class PortalDraftOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: Decimal
    unit: str
    unit_price: Optional[Decimal] = None
    line_total: Optional[Decimal] = None


class PortalDraftOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    draft_no: str
    portal_account_id: uuid.UUID
    submitted_by: Optional[str] = None
    source_order_id: Optional[str] = None
    requested_delivery_date: Optional[date] = None
    delivery_address: Optional[str] = None
    order_comments: Optional[str] = None
    status: PortalDraftOrderStatus
    total_amount: Optional[Decimal] = None
    currency: str
    converted_order_id: Optional[str] = None
    review_notes: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    lines: List[PortalDraftOrderLineRead] = []


class PortalDraftOrderReview(BaseModel):
    status: PortalDraftOrderStatus
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    converted_order_id: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class PortalAccountDashboard(BaseModel):
    account_code: str
    account_type: str
    outstanding_balance: float
    overdue_balance: float
    current_due: float
    aging_0_30: float
    aging_31_60: float
    aging_61_90: float
    aging_90_plus: float
    open_orders: int
    recent_orders: List[dict]
    recent_invoices: List[dict]
    recent_payments: List[dict]
    open_claims: int
    credit_limit: Optional[float] = None


# ── AI ────────────────────────────────────────────────────────────────────────

class PortalAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_type: PortalAIAgentType
    portal_account_id: Optional[uuid.UUID] = None
    title: str
    body: str
    priority: Optional[str] = None
    action_label: Optional[str] = None
    status: PortalAIRecStatus
    acknowledged_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class PortalAIRecAck(BaseModel):
    status: PortalAIRecStatus
    acknowledged_by: Optional[str] = None
    notes: Optional[str] = None
