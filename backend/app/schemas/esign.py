"""Pydantic schemas for Electronic Signatures."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel

from app.models.esign import SignatureRequestStatus, SignatureRecordStatus


class SignatureRecordRead(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    signer_id: Optional[uuid.UUID] = None
    signer_name: Optional[str] = None
    signer_email: Optional[str] = None
    status: SignatureRecordStatus
    signed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    signed_payload_hash_sha256: Optional[str] = None
    decline_reason: Optional[str] = None
    evidence_hash_sha256: Optional[str] = None
    auth_method: Optional[str] = None
    signed_document_version: Optional[int] = None
    signed_document_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class SignatureRecordDetail(SignatureRecordRead):
    signature_data: Optional[str] = None


class SignatureRequestCreate(BaseModel):
    document_type: str
    document_ref: str
    subject: str
    message: Optional[str] = None
    signer_ids: List[uuid.UUID]
    expires_at: Optional[datetime] = None
    document_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    module_key: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    document_hash_sha256: Optional[str] = None
    payload_hash_sha256: Optional[str] = None


class SignatureRequestRead(BaseModel):
    id: uuid.UUID
    request_no: str
    document_id: Optional[uuid.UUID] = None
    document_type: str
    document_ref: str
    requester_id: Optional[uuid.UUID] = None
    requester_name: Optional[str] = None
    subject: str
    message: Optional[str] = None
    status: SignatureRequestStatus
    expires_at: Optional[datetime] = None
    required_count: int
    signed_count: int
    declined_count: int
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    factory_id: Optional[str] = None
    module_key: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    document_hash_sha256: Optional[str] = None
    payload_hash_sha256: Optional[str] = None
    completed_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[uuid.UUID] = None
    evidence_summary: Optional[Any] = None
    audit_request_id: Optional[str] = None
    created_at: datetime
    signature_records: List[SignatureRecordRead] = []

    class Config:
        from_attributes = True


class SignatureRequestDetail(SignatureRequestRead):
    signature_records: List[SignatureRecordDetail] = []


class SignAction(BaseModel):
    signature_data: str
    signed_payload_hash_sha256: Optional[str] = None
    auth_method: Optional[str] = None


class DeclineAction(BaseModel):
    reason: Optional[str] = None


class ESignDashboard(BaseModel):
    total_requests: int
    pending: int
    signed: int
    declined: int
    expired: int
    my_pending_signatures: int
