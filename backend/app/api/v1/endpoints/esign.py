"""
Electronic Signatures
─────────────────────
Prefix: /api/v1/esign

Routes:
  POST /requests                      – create signature request
  GET  /requests                      – list all requests (requester view)
  GET  /requests/pending-for-me       – my pending signing tasks
  GET  /dashboard                     – stats
  GET  /requests/{id}                 – request detail (includes signature_data)
  POST /requests/{id}/sign            – current user signs
  POST /requests/{id}/decline         – current user declines
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.models.esign import (
    SignatureRequest, SignatureRecord,
    SignatureRequestStatus, SignatureRecordStatus,
)
from app.models.user import User
from app.schemas.esign import (
    SignatureRequestCreate, SignatureRequestRead, SignatureRequestDetail,
    SignatureRecordRead, SignatureRecordDetail,
    SignAction, DeclineAction, ESignDashboard,
)
from app.services.esignature_service import ensure_signature_action_allowed

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _request_no(seq: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"ESIGN-{today}-{str(seq + 1).zfill(4)}"


def _enrich_request(req: SignatureRequest) -> dict:
    data = {
        "id": req.id,
        "request_no": req.request_no,
        "document_id": req.document_id,
        "document_type": req.document_type,
        "document_ref": req.document_ref,
        "requester_id": req.requester_id,
        "requester_name": req.requester.full_name if req.requester else None,
        "subject": req.subject,
        "message": req.message,
        "status": req.status,
        "expires_at": req.expires_at,
        "required_count": req.required_count,
        "signed_count": req.signed_count,
        "declined_count": req.declined_count,
        "company_id": req.company_id,
        "branch_id": req.branch_id,
        "department_id": req.department_id,
        "factory_id": req.factory_id,
        "module_key": req.module_key,
        "related_entity_type": req.related_entity_type,
        "related_entity_id": req.related_entity_id,
        "document_hash_sha256": req.document_hash_sha256,
        "payload_hash_sha256": req.payload_hash_sha256,
        "completed_at": req.completed_at,
        "expired_at": req.expired_at,
        "cancelled_at": req.cancelled_at,
        "cancelled_by_id": req.cancelled_by_id,
        "evidence_summary": req.evidence_summary,
        "audit_request_id": req.audit_request_id,
        "created_at": req.created_at,
        "signature_records": [
            {
                "id": r.id,
                "request_id": r.request_id,
                "signer_id": r.signer_id,
                "signer_name": r.signer.full_name if r.signer else None,
                "signer_email": r.signer.email if r.signer else None,
                "status": r.status,
                "signed_at": r.signed_at,
                "declined_at": r.declined_at,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "signature_data": r.signature_data,
                "signed_payload_hash_sha256": r.signed_payload_hash_sha256,
                "decline_reason": r.decline_reason,
                "evidence_hash_sha256": r.evidence_hash_sha256,
                "auth_method": r.auth_method,
                "signed_document_version": r.signed_document_version,
                "signed_document_id": r.signed_document_id,
            }
            for r in req.signature_records
        ],
    }
    return data


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/requests", response_model=SignatureRequestRead,
             dependencies=[Depends(require_permission("esign", "request"))])
async def create_request(
    body: SignatureRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.signer_ids:
        raise HTTPException(status_code=400, detail="At least one signer required")

    count_res = await db.execute(select(func.count()).select_from(SignatureRequest))
    seq = count_res.scalar() or 0

    req = SignatureRequest(
        request_no=_request_no(seq),
        document_id=body.document_id,
        document_type=body.document_type,
        document_ref=body.document_ref,
        requester_id=current_user.id,
        subject=body.subject,
        message=body.message,
        expires_at=body.expires_at,
        required_count=len(body.signer_ids),
        company_id=body.company_id,
        branch_id=body.branch_id,
        department_id=body.department_id,
        factory_id=body.factory_id,
        module_key=body.module_key,
        related_entity_type=body.related_entity_type,
        related_entity_id=body.related_entity_id,
        document_hash_sha256=body.document_hash_sha256,
        payload_hash_sha256=body.payload_hash_sha256,
    )
    db.add(req)
    await db.flush()

    for signer_id in body.signer_ids:
        rec = SignatureRecord(
            request_id=req.id,
            signer_id=signer_id,
            status=SignatureRecordStatus.PENDING,
        )
        db.add(rec)

    await db.commit()
    await db.refresh(req)

    result = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == req.id)
    )
    req = result.scalar_one()
    return _enrich_request(req)


@router.get("/requests/pending-for-me", response_model=List[SignatureRequestRead])
async def pending_for_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SignatureRequest)
        .join(SignatureRecord, SignatureRecord.request_id == SignatureRequest.id)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(
            SignatureRecord.signer_id == current_user.id,
            SignatureRecord.status == SignatureRecordStatus.PENDING,
            SignatureRequest.status == SignatureRequestStatus.PENDING,
        )
        .order_by(SignatureRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return [_enrich_request(r) for r in requests]


@router.get("/dashboard", response_model=ESignDashboard,
            dependencies=[Depends(require_permission("esign", "view"))])
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count()).select_from(SignatureRequest))).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(SignatureRequest)
        .where(SignatureRequest.status == SignatureRequestStatus.PENDING)
    )).scalar() or 0
    signed = (await db.execute(
        select(func.count()).select_from(SignatureRequest)
        .where(SignatureRequest.status == SignatureRequestStatus.SIGNED)
    )).scalar() or 0
    declined = (await db.execute(
        select(func.count()).select_from(SignatureRequest)
        .where(SignatureRequest.status == SignatureRequestStatus.DECLINED)
    )).scalar() or 0
    expired = (await db.execute(
        select(func.count()).select_from(SignatureRequest)
        .where(SignatureRequest.status == SignatureRequestStatus.EXPIRED)
    )).scalar() or 0
    my_pending = (await db.execute(
        select(func.count()).select_from(SignatureRecord)
        .where(
            SignatureRecord.signer_id == current_user.id,
            SignatureRecord.status == SignatureRecordStatus.PENDING,
        )
    )).scalar() or 0

    return ESignDashboard(
        total_requests=total,
        pending=pending,
        signed=signed,
        declined=declined,
        expired=expired,
        my_pending_signatures=my_pending,
    )


@router.get("/requests", response_model=List[SignatureRequestRead],
            dependencies=[Depends(require_permission("esign", "view"))])
async def list_requests(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .order_by(SignatureRequest.created_at.desc())
    )
    if status:
        try:
            q = q.where(SignatureRequest.status == SignatureRequestStatus(status.upper()))
        except ValueError:
            pass
    result = await db.execute(q)
    requests = result.scalars().all()
    return [_enrich_request(r) for r in requests]


@router.get("/requests/{request_id}", response_model=SignatureRequestDetail)
async def get_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Signature request not found")
    ensure_signature_action_allowed(current_user, req, "view")
    return _enrich_request(req)


@router.post("/requests/{request_id}/sign", response_model=SignatureRequestRead)
async def sign_request(
    request_id: uuid.UUID,
    body: SignAction,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Signature request not found")
    ensure_signature_action_allowed(current_user, req, "sign")

    record = next(
        (r for r in req.signature_records if r.signer_id == current_user.id),
        None,
    )
    if not record:
        raise HTTPException(status_code=403, detail="You are not a signer for this request")
    if record.status != SignatureRecordStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"You have already {record.status.value.lower()} this request")

    record.status = SignatureRecordStatus.SIGNED
    record.signed_at = datetime.now(timezone.utc)
    record.signature_data = body.signature_data
    record.signed_payload_hash_sha256 = body.signed_payload_hash_sha256
    record.auth_method = body.auth_method
    record.ip_address = http_request.client.host if http_request.client else None
    record.user_agent = http_request.headers.get("user-agent", "")[:500]

    req.signed_count += 1
    if req.signed_count >= req.required_count:
        req.status = SignatureRequestStatus.SIGNED
        req.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(req)

    result2 = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == req.id)
    )
    req = result2.scalar_one()
    return _enrich_request(req)


@router.post("/requests/{request_id}/decline", response_model=SignatureRequestRead)
async def decline_request(
    request_id: uuid.UUID,
    body: DeclineAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Signature request not found")
    ensure_signature_action_allowed(current_user, req, "decline")

    record = next(
        (r for r in req.signature_records if r.signer_id == current_user.id),
        None,
    )
    if not record:
        raise HTTPException(status_code=403, detail="You are not a signer for this request")
    if record.status != SignatureRecordStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"You have already {record.status.value.lower()} this request")

    record.status = SignatureRecordStatus.DECLINED
    record.declined_at = datetime.now(timezone.utc)
    record.decline_reason = body.reason

    req.declined_count += 1
    req.status = SignatureRequestStatus.DECLINED
    req.completed_at = datetime.now(timezone.utc)

    await db.commit()

    result2 = await db.execute(
        select(SignatureRequest)
        .options(
            selectinload(SignatureRequest.requester),
            selectinload(SignatureRequest.signature_records).selectinload(SignatureRecord.signer),
        )
        .where(SignatureRequest.id == req.id)
    )
    req = result2.scalar_one()
    return _enrich_request(req)
