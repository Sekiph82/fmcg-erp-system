"""Pydantic schemas for Electronic Signatures."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

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
    created_at: datetime
    signature_records: List[SignatureRecordRead] = []

    class Config:
        from_attributes = True


class SignatureRequestDetail(SignatureRequestRead):
    signature_records: List[SignatureRecordDetail] = []


class SignAction(BaseModel):
    signature_data: str


class DeclineAction(BaseModel):
    reason: Optional[str] = None


class ESignDashboard(BaseModel):
    total_requests: int
    pending: int
    signed: int
    declined: int
    expired: int
    my_pending_signatures: int
