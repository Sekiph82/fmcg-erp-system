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

class SPAccountStatus(str, enum.Enum):
    PENDING   = "PENDING"
    ACTIVE    = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED    = "CLOSED"


class SPUserRole(str, enum.Enum):
    OWNER     = "OWNER"
    SALES     = "SALES"
    LOGISTICS = "LOGISTICS"
    FINANCE   = "FINANCE"
    QUALITY   = "QUALITY"
    VIEWER    = "VIEWER"
    CUSTOM    = "CUSTOM"


class SPActivityType(str, enum.Enum):
    LOGIN              = "LOGIN"
    VIEW_PO            = "VIEW_PO"
    ACKNOWLEDGE_PO     = "ACKNOWLEDGE_PO"
    PROPOSE_ETA        = "PROPOSE_ETA"
    UPLOAD_INVOICE     = "UPLOAD_INVOICE"
    UPLOAD_DOC         = "UPLOAD_DOC"
    VIEW_PAYMENT       = "VIEW_PAYMENT"
    UPDATE_PROFILE     = "UPDATE_PROFILE"
    INVITE_USER        = "INVITE_USER"
    DEACTIVATE_USER    = "DEACTIVATE_USER"
    OTHER              = "OTHER"


class SPPOResponseStatus(str, enum.Enum):
    PENDING_RESPONSE      = "PENDING_RESPONSE"
    ACCEPTED              = "ACCEPTED"
    ACCEPTED_REVISED_ETA  = "ACCEPTED_REVISED_ETA"
    PARTIALLY_ACCEPTED    = "PARTIALLY_ACCEPTED"
    REJECTED              = "REJECTED"
    UNDER_REVIEW          = "UNDER_REVIEW"


class SPETAStatus(str, enum.Enum):
    ORIGINAL   = "ORIGINAL"
    REVISED    = "REVISED"
    APPROVED   = "APPROVED"
    REJECTED   = "REJECTED"


class SPDocUploadType(str, enum.Enum):
    INVOICE               = "INVOICE"
    DELIVERY_NOTE         = "DELIVERY_NOTE"
    PACKING_LIST          = "PACKING_LIST"
    BILL_OF_LADING        = "BILL_OF_LADING"
    COA                   = "COA"
    MSDS                  = "MSDS"
    SPECIFICATION         = "SPECIFICATION"
    COMPLIANCE_CERT       = "COMPLIANCE_CERT"
    FOOD_SAFETY_CERT      = "FOOD_SAFETY_CERT"
    HALAL_CERT            = "HALAL_CERT"
    TEST_RESULT           = "TEST_RESULT"
    TAX_DOC               = "TAX_DOC"
    OTHER                 = "OTHER"


class SPDocReviewStatus(str, enum.Enum):
    PENDING    = "PENDING"
    ACCEPTED   = "ACCEPTED"
    REJECTED   = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class SPPaymentVisibility(str, enum.Enum):
    SUBMITTED          = "SUBMITTED"
    UNDER_REVIEW       = "UNDER_REVIEW"
    MATCHED            = "MATCHED"
    BLOCKED            = "BLOCKED"
    APPROVED_PAYMENT   = "APPROVED_PAYMENT"
    PAID               = "PAID"
    PARTIALLY_PAID     = "PARTIALLY_PAID"
    DISPUTED           = "DISPUTED"


class SPAIAgentType(str, enum.Enum):
    COLLABORATION_MONITOR = "COLLABORATION_MONITOR"
    FRICTION_ASSISTANT    = "FRICTION_ASSISTANT"
    RISK_SIGNAL           = "RISK_SIGNAL"


class SPAIRecStatus(str, enum.Enum):
    PENDING       = "PENDING"
    ACKNOWLEDGED  = "ACKNOWLEDGED"
    ACTIONED      = "ACTIONED"
    DISMISSED     = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class SPAccount(Base, TimestampMixin):
    __tablename__ = "sp_accounts"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id           = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, unique=True)
    portal_status         = Column(Enum(SPAccountStatus), nullable=False, default=SPAccountStatus.PENDING)
    default_currency      = Column(String(10), nullable=False, default="KES")
    preferred_language    = Column(String(20), nullable=False, default="en")
    allowed_modules_mask  = Column(JSON, nullable=True)
    primary_contact_name  = Column(String(200), nullable=True)
    primary_contact_email = Column(String(200), nullable=True)
    primary_contact_phone = Column(String(50), nullable=True)
    timezone              = Column(String(60), nullable=False, default="Africa/Nairobi")
    can_view_prices       = Column(Boolean, nullable=False, default=True)
    can_view_payment      = Column(Boolean, nullable=False, default=False)
    notes                 = Column(Text, nullable=True)

    users          = relationship("SPUser", back_populates="account", cascade="all, delete-orphan")
    activity_logs  = relationship("SPActivityLog", back_populates="account", cascade="all, delete-orphan")
    documents      = relationship("SPDocument", back_populates="account", cascade="all, delete-orphan")
    po_responses   = relationship("SPPOResponse", back_populates="account", cascade="all, delete-orphan")
    eta_logs       = relationship("SPETALog", back_populates="account", cascade="all, delete-orphan")


class SPUser(Base, TimestampMixin):
    __tablename__ = "sp_users"
    __table_args__ = (UniqueConstraint("email", name="uq_sp_user_email"),)

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id         = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=False)
    full_name          = Column(String(200), nullable=False)
    email              = Column(String(200), nullable=False)
    phone              = Column(String(50), nullable=True)
    login_identifier   = Column(String(200), nullable=True)
    password_hash      = Column(String(200), nullable=True)
    role_type          = Column(Enum(SPUserRole), nullable=False, default=SPUserRole.VIEWER)
    is_active          = Column(Boolean, nullable=False, default=True)
    last_login_at      = Column(DateTime(timezone=True), nullable=True)
    invited_by         = Column(String(200), nullable=True)
    notes              = Column(Text, nullable=True)

    account            = relationship("SPAccount", back_populates="users")
    activity_logs      = relationship("SPActivityLog", back_populates="user")


class SPPermissionProfile(Base, TimestampMixin):
    __tablename__ = "sp_permission_profiles"
    __table_args__ = (UniqueConstraint("role_type", name="uq_sp_perm_role"),)

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_type                 = Column(Enum(SPUserRole), nullable=False)
    can_view_po               = Column(Boolean, nullable=False, default=True)
    can_acknowledge_po        = Column(Boolean, nullable=False, default=False)
    can_propose_delivery      = Column(Boolean, nullable=False, default=False)
    can_upload_invoice        = Column(Boolean, nullable=False, default=False)
    can_upload_delivery_docs  = Column(Boolean, nullable=False, default=False)
    can_upload_quality_docs   = Column(Boolean, nullable=False, default=False)
    can_view_payment_status   = Column(Boolean, nullable=False, default=False)
    can_manage_users          = Column(Boolean, nullable=False, default=False)
    can_update_profile        = Column(Boolean, nullable=False, default=False)
    notes                     = Column(Text, nullable=True)


class SPActivityLog(Base):
    __tablename__ = "sp_activity_logs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id       = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=False)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("sp_users.id"), nullable=True)
    activity_type    = Column(Enum(SPActivityType), nullable=False)
    reference_type   = Column(String(80), nullable=True)
    reference_id     = Column(String(80), nullable=True)
    activity_datetime= Column(DateTime(timezone=True), nullable=False)
    ip_or_session    = Column(String(120), nullable=True)
    notes            = Column(Text, nullable=True)

    account          = relationship("SPAccount", back_populates="activity_logs")
    user             = relationship("SPUser", back_populates="activity_logs")


class SPDocument(Base, TimestampMixin):
    __tablename__ = "sp_documents"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id          = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=False)
    supplier_id         = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    upload_type         = Column(Enum(SPDocUploadType), nullable=False)
    linked_po_id        = Column(UUID(as_uuid=True), nullable=True)
    linked_grn_id       = Column(UUID(as_uuid=True), nullable=True)
    linked_invoice_id   = Column(UUID(as_uuid=True), nullable=True)
    file_name           = Column(String(300), nullable=False)
    file_path           = Column(Text, nullable=False)
    file_size_kb        = Column(Integer, nullable=True)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("sp_users.id"), nullable=True)
    uploaded_at         = Column(DateTime(timezone=True), nullable=False)
    review_status       = Column(Enum(SPDocReviewStatus), nullable=False, default=SPDocReviewStatus.PENDING)
    reviewed_by         = Column(String(200), nullable=True)
    reviewed_at         = Column(DateTime(timezone=True), nullable=True)
    expiry_date         = Column(Date, nullable=True)
    notes               = Column(Text, nullable=True)

    account             = relationship("SPAccount", back_populates="documents")


class SPPOResponse(Base, TimestampMixin):
    __tablename__ = "sp_po_responses"
    __table_args__ = (UniqueConstraint("account_id", "po_id", name="uq_sp_po_response"),)

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id        = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=False)
    po_id             = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False)
    responded_by_user = Column(UUID(as_uuid=True), ForeignKey("sp_users.id"), nullable=True)
    response_status   = Column(Enum(SPPOResponseStatus), nullable=False, default=SPPOResponseStatus.PENDING_RESPONSE)
    accepted_qty_json = Column(JSON, nullable=True)
    supplier_comment  = Column(Text, nullable=True)
    rejection_reason  = Column(Text, nullable=True)
    proposed_eta      = Column(Date, nullable=True)
    responded_at      = Column(DateTime(timezone=True), nullable=True)

    account           = relationship("SPAccount", back_populates="po_responses")


class SPETALog(Base, TimestampMixin):
    __tablename__ = "sp_eta_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=False)
    po_id           = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False)
    proposed_by     = Column(UUID(as_uuid=True), ForeignKey("sp_users.id"), nullable=True)
    original_date   = Column(Date, nullable=True)
    proposed_date   = Column(Date, nullable=False)
    eta_status      = Column(Enum(SPETAStatus), nullable=False, default=SPETAStatus.REVISED)
    revision_no     = Column(Integer, nullable=False, default=1)
    supplier_reason = Column(Text, nullable=True)
    buyer_notes     = Column(Text, nullable=True)
    reviewed_by     = Column(String(200), nullable=True)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)

    account         = relationship("SPAccount", back_populates="eta_logs")


class SPAIRecommendation(Base, TimestampMixin):
    __tablename__ = "sp_ai_recommendations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("sp_accounts.id"), nullable=True)
    agent_type      = Column(Enum(SPAIAgentType), nullable=False)
    status          = Column(Enum(SPAIRecStatus), nullable=False, default=SPAIRecStatus.PENDING)
    title           = Column(String(300), nullable=False)
    body            = Column(Text, nullable=False)
    severity        = Column(String(20), nullable=False, default="INFO")
    reference_type  = Column(String(80), nullable=True)
    reference_id    = Column(String(80), nullable=True)
    actioned_by     = Column(String(200), nullable=True)
    actioned_at     = Column(DateTime(timezone=True), nullable=True)
