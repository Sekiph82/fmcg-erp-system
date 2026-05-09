"""Regulatory Certificate Tracking — KEBS, HALAL, ISO, FSSC, etc."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, Date, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CertAuthority(str, PyEnum):
    KEBS = "KEBS"               # Kenya Bureau of Standards
    KEPHIS = "KEPHIS"           # Kenya Plant Health Inspectorate
    PPB = "PPB"                 # Pharmacy and Poisons Board
    NEMA = "NEMA"               # National Environment Management Authority
    FSCC = "FSCC"               # Food Safety System Certification
    HALAL = "HALAL"             # Halal certification
    KOSHER = "KOSHER"           # Kosher certification
    ISO_9001 = "ISO_9001"
    ISO_22000 = "ISO_22000"     # Food safety management
    FSSC_22000 = "FSSC_22000"
    BRC = "BRC"                 # British Retail Consortium
    NAFDAC = "NAFDAC"           # Nigeria (export)
    WHO_GMP = "WHO_GMP"
    ORGANIC = "ORGANIC"
    FAIR_TRADE = "FAIR_TRADE"
    OTHER = "OTHER"


class CertEntityType(str, PyEnum):
    PRODUCT = "PRODUCT"
    PLANT = "PLANT"
    SUPPLIER = "SUPPLIER"
    COMPANY = "COMPANY"


class CertStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    PENDING_RENEWAL = "PENDING_RENEWAL"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    PENDING_INITIAL = "PENDING_INITIAL"


class RegulatoryCertificate(Base):
    __tablename__ = "regulatory_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cert_ref = Column(String(50), unique=True, nullable=False, index=True)
    certificate_number = Column(String(200), nullable=True, index=True)
    authority = Column(Enum(CertAuthority), nullable=False, default=CertAuthority.KEBS)
    entity_type = Column(Enum(CertEntityType), nullable=False, default=CertEntityType.PRODUCT)
    entity_id = Column(String(100), nullable=True, index=True)    # UUID string of product/plant/supplier
    entity_name = Column(String(300), nullable=False)
    country = Column(String(100), default="Kenya", nullable=False)
    issuing_body = Column(String(300), nullable=True)
    scope = Column(Text, nullable=True)                           # what exactly is certified
    issued_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)
    status = Column(Enum(CertStatus), nullable=False, default=CertStatus.ACTIVE, index=True)
    document_id = Column(String(100), nullable=True)              # soft link to documents table
    document_url = Column(Text, nullable=True)
    renewal_notes = Column(Text, nullable=True)
    alert_sent_30d = Column(Boolean, default=False, nullable=False)
    alert_sent_60d = Column(Boolean, default=False, nullable=False)
    alert_sent_90d = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit_entries = relationship("CertAuditEntry", back_populates="certificate", cascade="all, delete-orphan")


class CertAuditEntry(Base):
    __tablename__ = "cert_audit_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cert_id = Column(UUID(as_uuid=True), ForeignKey("regulatory_certificates.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False)    # ISSUED | RENEWED | SUSPENDED | REVOKED | UPDATED | EXPIRY_ALERT
    performed_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    certificate = relationship("RegulatoryCertificate", back_populates="audit_entries")
