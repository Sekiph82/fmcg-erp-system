from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, Enum, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class PortalAccountType(str, enum.Enum):
    CUSTOMER      = "CUSTOMER"
    DISTRIBUTOR   = "DISTRIBUTOR"
    KEY_ACCOUNT   = "KEY_ACCOUNT"
    RETAILER      = "RETAILER"
    INSTITUTIONAL = "INSTITUTIONAL"
    MIXED         = "MIXED"


class PortalAccountStatus(str, enum.Enum):
    PENDING   = "PENDING"
    ACTIVE    = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED    = "CLOSED"


class PortalUserRole(str, enum.Enum):
    OWNER     = "OWNER"
    FINANCE   = "FINANCE"
    BUYER     = "BUYER"
    LOGISTICS = "LOGISTICS"
    VIEWER    = "VIEWER"
    CUSTOM    = "CUSTOM"


class PortalActivityType(str, enum.Enum):
    LOGIN             = "LOGIN"
    VIEW_ORDER        = "VIEW_ORDER"
    DOWNLOAD_INVOICE  = "DOWNLOAD_INVOICE"
    SUBMIT_ORDER      = "SUBMIT_ORDER"
    INITIATE_PAYMENT  = "INITIATE_PAYMENT"
    SUBMIT_RETURN     = "SUBMIT_RETURN"
    SUBMIT_CLAIM      = "SUBMIT_CLAIM"
    DOWNLOAD_STATEMENT = "DOWNLOAD_STATEMENT"
    VIEW_SHIPMENT     = "VIEW_SHIPMENT"
    DOWNLOAD_DOCUMENT = "DOWNLOAD_DOCUMENT"
    INVITE_USER       = "INVITE_USER"
    OTHER             = "OTHER"


class PortalClaimType(str, enum.Enum):
    RETURN_REQUEST     = "RETURN_REQUEST"
    SHORTAGE_CLAIM     = "SHORTAGE_CLAIM"
    DAMAGE_CLAIM       = "DAMAGE_CLAIM"
    DELIVERY_DISCREPANCY = "DELIVERY_DISCREPANCY"
    PRICING_DISPUTE    = "PRICING_DISPUTE"
    PRODUCT_COMPLAINT  = "PRODUCT_COMPLAINT"
    INVOICE_DISPUTE    = "INVOICE_DISPUTE"
    OTHER              = "OTHER"


class PortalClaimStatus(str, enum.Enum):
    SUBMITTED   = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED    = "RESOLVED"
    REJECTED    = "REJECTED"
    CLOSED      = "CLOSED"


class PortalOrderMode(str, enum.Enum):
    DIRECT_SUBMIT  = "DIRECT_SUBMIT"
    DRAFT_REQUEST  = "DRAFT_REQUEST"
    REORDER_ONLY   = "REORDER_ONLY"


class PortalAIAgentType(str, enum.Enum):
    SUPPORT_ASSISTANT     = "SUPPORT_ASSISTANT"
    FRICTION_MONITOR      = "FRICTION_MONITOR"
    COMMERCIAL_OPPORTUNITY = "COMMERCIAL_OPPORTUNITY"


class PortalAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


class PortalDraftOrderStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    CONVERTED = "CONVERTED"


# ── Models ────────────────────────────────────────────────────────────────────

class PortalAccount(Base, TimestampMixin):
    __tablename__ = "portal_accounts"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_code           = Column(String(50), unique=True, nullable=False)
    account_type           = Column(Enum(PortalAccountType), nullable=False, default=PortalAccountType.CUSTOMER)
    linked_customer_id     = Column(String(50))
    linked_distributor_id  = Column(String(50))
    portal_status          = Column(Enum(PortalAccountStatus), nullable=False, default=PortalAccountStatus.PENDING)
    default_currency       = Column(String(10), default="KES")
    preferred_language     = Column(String(10), default="en")
    order_mode             = Column(Enum(PortalOrderMode), default=PortalOrderMode.DRAFT_REQUEST)
    primary_contact_name   = Column(String(200))
    primary_contact_email  = Column(String(200))
    primary_contact_phone  = Column(String(50))
    timezone               = Column(String(50), default="Africa/Nairobi")
    can_view_prices        = Column(Boolean, default=True)
    can_view_promotions    = Column(Boolean, default=False)
    can_initiate_payment   = Column(Boolean, default=False)
    notes                  = Column(Text)

    users         = relationship("PortalUser", back_populates="account", cascade="all, delete-orphan")
    claims        = relationship("PortalClaim", back_populates="account", cascade="all, delete-orphan")
    draft_orders  = relationship("PortalDraftOrder", back_populates="account", cascade="all, delete-orphan")


class PortalUser(Base, TimestampMixin):
    __tablename__ = "portal_users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=False)
    full_name        = Column(String(200), nullable=False)
    email            = Column(String(200), nullable=False, unique=True)
    phone            = Column(String(50))
    login_identifier = Column(String(200), unique=True)
    password_hash    = Column(String(255))
    role_type        = Column(Enum(PortalUserRole), nullable=False, default=PortalUserRole.VIEWER)
    is_active        = Column(Boolean, default=True)
    invited_by       = Column(String(200))
    last_login_at    = Column(DateTime)
    invitation_token = Column(String(255))
    token_expires_at = Column(DateTime)
    notes            = Column(Text)

    account       = relationship("PortalAccount", back_populates="users")
    activity_logs = relationship("PortalActivityLog", back_populates="user", cascade="all, delete-orphan")


class PortalActivityLog(Base, TimestampMixin):
    __tablename__ = "portal_activity_logs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_user_id    = Column(UUID(as_uuid=True), ForeignKey("portal_users.id"), nullable=False)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=True)
    activity_type     = Column(Enum(PortalActivityType), nullable=False)
    reference_type    = Column(String(50))
    reference_id      = Column(String(50))
    activity_datetime = Column(DateTime, nullable=False)
    ip_or_session_ref = Column(String(200))
    notes             = Column(Text)

    user = relationship("PortalUser", back_populates="activity_logs")


class PortalClaim(Base, TimestampMixin):
    __tablename__ = "portal_claims"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_no          = Column(String(50), unique=True, nullable=False)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=False)
    submitted_by      = Column(String(50))
    claim_type        = Column(Enum(PortalClaimType), nullable=False)
    linked_order_id   = Column(String(50))
    linked_invoice_id = Column(String(50))
    linked_shipment_id = Column(String(50))
    linked_lot_id     = Column(String(50))
    quantity_involved = Column(Numeric(18, 3))
    reason            = Column(Text, nullable=False)
    description       = Column(Text)
    status            = Column(Enum(PortalClaimStatus), nullable=False, default=PortalClaimStatus.SUBMITTED)
    resolution_notes  = Column(Text)
    resolved_by       = Column(String(50))
    resolved_date     = Column(Date)
    notes             = Column(Text)

    account = relationship("PortalAccount", back_populates="claims")


class PortalDraftOrder(Base, TimestampMixin):
    __tablename__ = "portal_draft_orders"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_no          = Column(String(50), unique=True, nullable=False)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=False)
    submitted_by      = Column(String(50))
    source_order_id   = Column(String(50))
    requested_delivery_date = Column(Date)
    delivery_address  = Column(Text)
    order_comments    = Column(Text)
    status            = Column(Enum(PortalDraftOrderStatus), nullable=False, default=PortalDraftOrderStatus.DRAFT)
    total_amount      = Column(Numeric(18, 2), default=0)
    currency          = Column(String(10), default="KES")
    converted_order_id = Column(String(50))
    review_notes      = Column(Text)
    reviewed_by       = Column(String(50))
    notes             = Column(Text)

    account = relationship("PortalAccount", back_populates="draft_orders")
    lines   = relationship("PortalDraftOrderLine", back_populates="draft_order", cascade="all, delete-orphan")


class PortalDraftOrderLine(Base, TimestampMixin):
    __tablename__ = "portal_draft_order_lines"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_order_id  = Column(UUID(as_uuid=True), ForeignKey("portal_draft_orders.id"), nullable=False)
    product_id      = Column(String(50))
    product_name    = Column(String(200))
    product_sku     = Column(String(100))
    quantity        = Column(Numeric(18, 3), nullable=False)
    unit            = Column(String(20), default="PCS")
    unit_price      = Column(Numeric(14, 4), default=0)
    line_total      = Column(Numeric(18, 2), default=0)
    notes           = Column(Text)

    draft_order = relationship("PortalDraftOrder", back_populates="lines")


class PortalAIRecommendation(Base, TimestampMixin):
    __tablename__ = "portal_ai_recommendations"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type        = Column(Enum(PortalAIAgentType), nullable=False)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=True)
    title             = Column(String(300), nullable=False)
    body              = Column(Text, nullable=False)
    priority          = Column(String(20))
    action_label      = Column(String(100))
    status            = Column(Enum(PortalAIRecStatus), default=PortalAIRecStatus.PENDING)
    acknowledged_by   = Column(String(50))
    notes             = Column(Text)


class PortalSellThroughUpload(Base, TimestampMixin):
    """Distributor portal self-service sell-through submission."""
    __tablename__ = "portal_sell_through_uploads"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start     = Column(Date, nullable=False)
    period_end       = Column(Date, nullable=False)
    total_units_sold = Column(Integer, nullable=False, default=0)
    total_value      = Column(Numeric(18, 2), nullable=True)
    notes            = Column(Text, nullable=True)
    upload_reference = Column(String(100), nullable=True)
    review_status    = Column(String(30), default="PENDING", nullable=False)
    reviewed_by      = Column(String(200), nullable=True)
    reviewed_at      = Column(DateTime, nullable=True)

    account = relationship("PortalAccount", foreign_keys=[portal_account_id])
