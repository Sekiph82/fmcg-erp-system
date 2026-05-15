from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
import uuid

from pydantic import BaseModel

from app.models.documents import DocumentCategory, DocumentStatus


# ── Base ──────────────────────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    title: str
    category: DocumentCategory
    description: Optional[str] = None
    document_no: Optional[str] = None
    lineage_id: Optional[uuid.UUID] = None
    document_type: Optional[str] = None
    version: int = 1
    revision_note: Optional[str] = None
    status: DocumentStatus = DocumentStatus.DRAFT
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    owner_user_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    product_category_id: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    confidentiality_level: str = "INTERNAL"
    retention_until: Optional[date] = None
    legal_hold: bool = False
    review_due_date: Optional[date] = None
    next_review_owner_id: Optional[uuid.UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    storage_provider: Optional[str] = None
    storage_key: Optional[str] = None
    file_checksum_sha256: Optional[str] = None
    file_scan_status: str = "NOT_SCANNED"
    file_scan_result: Optional[str] = None
    file_locked: bool = False


# ── Create / Update ───────────────────────────────────────────────────────────

class DocumentCreate(DocumentBase):
    # Optionally supersede an existing document (creates new version)
    previous_version_id: Optional[uuid.UUID] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[DocumentCategory] = None
    description: Optional[str] = None
    document_no: Optional[str] = None
    document_type: Optional[str] = None
    revision_note: Optional[str] = None
    status: Optional[DocumentStatus] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    owner_user_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    product_category_id: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    confidentiality_level: Optional[str] = None
    retention_until: Optional[date] = None
    legal_hold: Optional[bool] = None
    review_due_date: Optional[date] = None
    next_review_owner_id: Optional[uuid.UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    storage_provider: Optional[str] = None
    storage_key: Optional[str] = None
    file_checksum_sha256: Optional[str] = None
    file_scan_status: Optional[str] = None
    file_scan_result: Optional[str] = None
    file_locked: Optional[bool] = None


class DocumentApprove(BaseModel):
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None


# ── Read ──────────────────────────────────────────────────────────────────────

class DocumentOwnerShort(BaseModel):
    id: uuid.UUID
    full_name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentRead(DocumentBase):
    id: uuid.UUID
    version: int
    is_latest: bool
    previous_version_id: Optional[uuid.UUID]
    approved_by_id: Optional[uuid.UUID]
    created_by_id: Optional[uuid.UUID] = None
    updated_by_id: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    obsolete_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[uuid.UUID] = None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class DocumentShort(BaseModel):
    id: uuid.UUID
    title: str
    category: DocumentCategory
    document_no: Optional[str] = None
    version: int
    status: DocumentStatus
    is_latest: bool
    expiry_date: Optional[date] = None
    review_due_date: Optional[date] = None
    confidentiality_level: Optional[str] = None
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    file_name: Optional[str]
    created_at: Any

    model_config = {"from_attributes": True}


class DocumentVersionHistory(BaseModel):
    id: uuid.UUID
    version: int
    status: DocumentStatus
    is_latest: bool
    revision_note: Optional[str]
    created_at: Any

    model_config = {"from_attributes": True}
