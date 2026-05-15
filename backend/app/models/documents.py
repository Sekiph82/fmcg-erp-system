"""Document Management – generic document store linkable to any ERP entity."""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, Date, DateTime,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enumerations ──────────────────────────────────────────────────────────────

class DocumentCategory(str, enum.Enum):
    SOP = "SOP"
    WORK_INSTRUCTION = "WORK_INSTRUCTION"
    QC_DOCUMENT = "QC_DOCUMENT"
    CUSTOMS_DOCUMENT = "CUSTOMS_DOCUMENT"
    INVOICE = "INVOICE"
    SHIPMENT_DOCUMENT = "SHIPMENT_DOCUMENT"
    PAYMENT_PROOF = "PAYMENT_PROOF"
    RECONCILIATION = "RECONCILIATION"
    MAINTENANCE_MANUAL = "MAINTENANCE_MANUAL"
    HR_DOCUMENT = "HR_DOCUMENT"
    # ── Marketing categories ──────────────────────────────────────────────────
    CAMPAIGN_DOCUMENT = "CAMPAIGN_DOCUMENT"          # briefs, plans, decks
    INFLUENCER_CONTRACT = "INFLUENCER_CONTRACT"      # influencer agreements
    SURVEY_DOCUMENT = "SURVEY_DOCUMENT"              # survey forms and results
    BRAND_SPEND_INVOICE = "BRAND_SPEND_INVOICE"      # agency/media invoices
    TRADE_SPEND_APPROVAL = "TRADE_SPEND_APPROVAL"    # retailer/distributor support approvals
    MARKETING_CREATIVE = "MARKETING_CREATIVE"        # artwork, copy, video links
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"
    ARCHIVED = "ARCHIVED"


# ── Document Record ───────────────────────────────────────────────────────────

class Document(Base, TimestampMixin):
    """
    Central document record. Linked to any ERP entity via (related_entity_type,
    related_entity_id) – a soft polymorphic FK pattern that avoids hard FK
    constraints across modules.

    Storage is abstracted: file_url holds whatever the upload layer provides
    (S3 key, local path, external URL). No upload engine is embedded here.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    category = Column(SAEnum(DocumentCategory), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Versioning
    document_no = Column(String(80), nullable=True, index=True)
    lineage_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    document_type = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    revision_note = Column(Text, nullable=True)          # what changed in this version
    previous_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_latest = Column(Boolean, default=True, nullable=False)

    # Lifecycle
    status = Column(SAEnum(DocumentStatus), nullable=False, default=DocumentStatus.DRAFT)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Ownership / accountability
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    obsolete_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # ERP scope hints for permission + scope access checks
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    department_id = Column(String(100), nullable=True, index=True)
    factory_id = Column(String(100), nullable=True, index=True)
    product_category_id = Column(String(100), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    confidentiality_level = Column(String(30), nullable=False, default="INTERNAL")
    retention_until = Column(Date, nullable=True)
    legal_hold = Column(Boolean, default=False, nullable=False)
    review_due_date = Column(Date, nullable=True, index=True)
    next_review_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Soft polymorphic entity link
    # e.g. related_entity_type="mpesa_transaction", related_entity_id="<uuid>"
    #      related_entity_type="purchase_order",    related_entity_id="<uuid>"
    related_entity_type = Column(String(100), nullable=True, index=True)
    related_entity_id = Column(String(36), nullable=True, index=True)  # stored as string UUID

    # Storage abstraction – fill with S3 key, GCS URI, local path, or signed URL
    file_url = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    storage_provider = Column(String(30), nullable=True)
    storage_key = Column(Text, nullable=True)
    file_checksum_sha256 = Column(String(64), nullable=True, index=True)
    file_scan_status = Column(String(30), nullable=False, default="NOT_SCANNED")
    file_scan_result = Column(Text, nullable=True)
    file_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    next_review_owner = relationship("User", foreign_keys=[next_review_owner_id])
    locked_by = relationship("User", foreign_keys=[locked_by_id])
    previous_version = relationship("Document", remote_side="Document.id", foreign_keys=[previous_version_id])
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")


class DocumentTag(Base, TimestampMixin):
    """Freeform tags attached to a document for search and filtering."""
    __tablename__ = "document_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    created_by = Column(String(200), nullable=True)

    document = relationship("Document", back_populates="tags")
