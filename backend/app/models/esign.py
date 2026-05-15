"""Electronic Signatures — self-hosted signing workflow."""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class SignatureRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class SignatureRecordStatus(str, enum.Enum):
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"


class SignatureRequest(Base, TimestampMixin):
    __tablename__ = "signature_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_no = Column(String(50), unique=True, nullable=False, index=True)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_type = Column(String(100), nullable=False)
    document_ref = Column(String(255), nullable=False)

    requester_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    status = Column(
        SAEnum(SignatureRequestStatus),
        nullable=False,
        default=SignatureRequestStatus.PENDING,
        index=True,
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)

    required_count = Column(Integer, nullable=False, default=0)
    signed_count = Column(Integer, nullable=False, default=0)
    declined_count = Column(Integer, nullable=False, default=0)

    # ERP scope and related-record hints for permission checks and dashboards.
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    department_id = Column(String(100), nullable=True)
    factory_id = Column(String(100), nullable=True)
    module_key = Column(String(100), nullable=True, index=True)
    related_entity_type = Column(String(100), nullable=True)
    related_entity_id = Column(String(100), nullable=True)

    # Evidence and lifecycle hardening fields.
    document_hash_sha256 = Column(String(64), nullable=True)
    payload_hash_sha256 = Column(String(64), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_summary = Column(JSON, nullable=True)
    audit_request_id = Column(String(100), nullable=True)

    requester = relationship("User", foreign_keys=[requester_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    signature_records = relationship(
        "SignatureRecord", back_populates="request", cascade="all, delete-orphan"
    )
    document = relationship("Document", foreign_keys=[document_id])


class SignatureRecord(Base, TimestampMixin):
    __tablename__ = "signature_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("signature_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = Column(
        SAEnum(SignatureRecordStatus),
        nullable=False,
        default=SignatureRecordStatus.PENDING,
    )
    signed_at = Column(DateTime(timezone=True), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    signature_data = Column(Text, nullable=True)
    signed_payload_hash_sha256 = Column(String(64), nullable=True)
    decline_reason = Column(Text, nullable=True)
    evidence_hash_sha256 = Column(String(64), nullable=True)
    auth_method = Column(String(50), nullable=True)
    signed_document_version = Column(Integer, nullable=True)
    signed_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    request = relationship("SignatureRequest", back_populates="signature_records")
    signer = relationship("User", foreign_keys=[signer_id])
    signed_document = relationship("Document", foreign_keys=[signed_document_id])
