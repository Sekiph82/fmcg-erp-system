from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

from app.models.supplier_portal import (
    SPAccountStatus, SPUserRole, SPActivityType,
    SPPOResponseStatus, SPETAStatus, SPDocUploadType, SPDocReviewStatus,
    SPPaymentVisibility, SPAIAgentType, SPAIRecStatus,
)


# ── Account ────────────────────────────────────────────────────────────────────

class SPAccountCreate(BaseModel):
    supplier_id: UUID
    default_currency: str = "KES"
    preferred_language: str = "en"
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    timezone: str = "Africa/Nairobi"
    can_view_prices: bool = True
    can_view_payment: bool = False
    notes: Optional[str] = None


class SPAccountUpdate(BaseModel):
    portal_status: Optional[SPAccountStatus] = None
    default_currency: Optional[str] = None
    preferred_language: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    timezone: Optional[str] = None
    can_view_prices: Optional[bool] = None
    can_view_payment: Optional[bool] = None
    notes: Optional[str] = None


class SPAccountOut(BaseModel):
    id: UUID
    supplier_id: UUID
    portal_status: SPAccountStatus
    default_currency: str
    preferred_language: str
    primary_contact_name: Optional[str]
    primary_contact_email: Optional[str]
    primary_contact_phone: Optional[str]
    timezone: str
    can_view_prices: bool
    can_view_payment: bool
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── User ───────────────────────────────────────────────────────────────────────

class SPUserInvite(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    role_type: SPUserRole = SPUserRole.VIEWER
    notes: Optional[str] = None


class SPUserOut(BaseModel):
    id: UUID
    account_id: UUID
    full_name: str
    email: str
    phone: Optional[str]
    role_type: SPUserRole
    is_active: bool
    last_login_at: Optional[datetime]
    invited_by: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Permission Profile ─────────────────────────────────────────────────────────

class SPPermissionProfileOut(BaseModel):
    id: UUID
    role_type: SPUserRole
    can_view_po: bool
    can_acknowledge_po: bool
    can_propose_delivery: bool
    can_upload_invoice: bool
    can_upload_delivery_docs: bool
    can_upload_quality_docs: bool
    can_view_payment_status: bool
    can_manage_users: bool
    can_update_profile: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Activity Log ───────────────────────────────────────────────────────────────

class SPActivityLogOut(BaseModel):
    id: UUID
    account_id: UUID
    user_id: Optional[UUID]
    activity_type: SPActivityType
    reference_type: Optional[str]
    reference_id: Optional[str]
    activity_datetime: datetime
    ip_or_session: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Document Upload ────────────────────────────────────────────────────────────

class SPDocumentCreate(BaseModel):
    upload_type: SPDocUploadType
    linked_po_id: Optional[UUID] = None
    linked_grn_id: Optional[UUID] = None
    linked_invoice_id: Optional[UUID] = None
    file_name: str
    file_path: str
    file_size_kb: Optional[int] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class SPDocumentReview(BaseModel):
    review_status: SPDocReviewStatus
    reviewed_by: str
    notes: Optional[str] = None


class SPDocumentOut(BaseModel):
    id: UUID
    account_id: UUID
    supplier_id: UUID
    upload_type: SPDocUploadType
    linked_po_id: Optional[UUID]
    linked_grn_id: Optional[UUID]
    linked_invoice_id: Optional[UUID]
    file_name: str
    file_path: str
    file_size_kb: Optional[int]
    uploaded_at: datetime
    review_status: SPDocReviewStatus
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    expiry_date: Optional[date]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── PO Response ────────────────────────────────────────────────────────────────

class SPPOAcknowledge(BaseModel):
    response_status: SPPOResponseStatus
    supplier_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    proposed_eta: Optional[date] = None
    accepted_qty_json: Optional[Dict[str, Any]] = None


class SPPOResponseOut(BaseModel):
    id: UUID
    account_id: UUID
    po_id: UUID
    response_status: SPPOResponseStatus
    accepted_qty_json: Optional[Dict[str, Any]]
    supplier_comment: Optional[str]
    rejection_reason: Optional[str]
    proposed_eta: Optional[date]
    responded_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── ETA Log ────────────────────────────────────────────────────────────────────

class SPETAPropose(BaseModel):
    po_id: UUID
    proposed_date: date
    supplier_reason: Optional[str] = None
    original_date: Optional[date] = None


class SPETAReview(BaseModel):
    eta_status: SPETAStatus
    buyer_notes: Optional[str] = None
    reviewed_by: str


class SPETALogOut(BaseModel):
    id: UUID
    account_id: UUID
    po_id: UUID
    proposed_date: date
    original_date: Optional[date]
    eta_status: SPETAStatus
    revision_no: int
    supplier_reason: Optional[str]
    buyer_notes: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Auth ───────────────────────────────────────────────────────────────────────

class SPLoginRequest(BaseModel):
    email: str
    password: str


class SPLoginResponse(BaseModel):
    token: str
    user_id: str
    account_id: str
    full_name: str
    role_type: SPUserRole


class SPPasswordReset(BaseModel):
    email: str
    new_password: str


# ── AI Recommendation ──────────────────────────────────────────────────────────

class SPAIRecAck(BaseModel):
    status: SPAIRecStatus
    actioned_by: str


class SPAIRecommendationOut(BaseModel):
    id: UUID
    account_id: Optional[UUID]
    agent_type: SPAIAgentType
    status: SPAIRecStatus
    title: str
    body: str
    severity: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Dashboard ──────────────────────────────────────────────────────────────────

class SPDashboard(BaseModel):
    account_id: str
    supplier_name: str
    open_pos: int
    pending_acknowledgment: int
    uploaded_invoices_30d: int
    uploaded_docs_30d: int
    expiring_certs: int
    recent_activity: List[SPActivityLogOut]
    ai_alerts: List[SPAIRecommendationOut]
