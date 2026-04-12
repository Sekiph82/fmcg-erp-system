from __future__ import annotations

from datetime import date
from typing import Any, List, Optional
import uuid

from pydantic import BaseModel

from app.models.documents import DocumentCategory, DocumentStatus


# ── Base ──────────────────────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    title: str
    category: DocumentCategory
    description: Optional[str] = None
    version: int = 1
    revision_note: Optional[str] = None
    status: DocumentStatus = DocumentStatus.DRAFT
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    owner_user_id: Optional[uuid.UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


# ── Create / Update ───────────────────────────────────────────────────────────

class DocumentCreate(DocumentBase):
    # Optionally supersede an existing document (creates new version)
    previous_version_id: Optional[uuid.UUID] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[DocumentCategory] = None
    description: Optional[str] = None
    revision_note: Optional[str] = None
    status: Optional[DocumentStatus] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    owner_user_id: Optional[uuid.UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


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
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class DocumentShort(BaseModel):
    id: uuid.UUID
    title: str
    category: DocumentCategory
    version: int
    status: DocumentStatus
    is_latest: bool
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
