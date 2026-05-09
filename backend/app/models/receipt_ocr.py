"""AI-Powered Receipt OCR models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class OCRStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    LINKED = "LINKED"


class ReceiptOCRRecord(Base):
    """AI-extracted receipt data from uploaded image."""
    __tablename__ = "receipt_ocr_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by = Column(String(200), nullable=True)
    user_id = Column(String(100), nullable=True, index=True)

    # Input
    image_url = Column(Text, nullable=False)
    file_name = Column(String(300), nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Extracted fields
    extracted_date = Column(String(20), nullable=True)       # ISO date string
    extracted_vendor = Column(String(300), nullable=True)
    extracted_amount = Column(Numeric(14, 2), nullable=True)
    extracted_currency = Column(String(10), nullable=True)
    extracted_category = Column(String(100), nullable=True)
    extracted_tax_amount = Column(Numeric(12, 2), nullable=True)
    raw_extracted_text = Column(Text, nullable=True)

    # Quality
    confidence_score = Column(Integer, nullable=True)        # 0-100
    processing_notes = Column(Text, nullable=True)
    status = Column(Enum(OCRStatus), nullable=False, default=OCRStatus.PENDING)

    # Duplicate detection
    duplicate_hash = Column(String(64), nullable=True, index=True)  # sha256(vendor+amount+date)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_id = Column(UUID(as_uuid=True), ForeignKey("receipt_ocr_records.id", ondelete="SET NULL"), nullable=True)

    # Linkage
    linked_expense_claim_id = Column(String(100), nullable=True, index=True)  # soft FK to expense_claims
    linked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
