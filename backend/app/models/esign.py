"""Electronic Signatures — self-hosted signing workflow."""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum,
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

    requester = relationship("User", foreign_keys=[requester_id])
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

    request = relationship("SignatureRequest", back_populates="signature_records")
    signer = relationship("User", foreign_keys=[signer_id])
