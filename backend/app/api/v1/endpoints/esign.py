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
from pydantic import BaseModel, Field
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


def _enrich_request(req: SignatureRequest, viewer_id=None) -> dict:
    # a signature image is returned only to the person it belongs to — never to requesters, viewers or admins
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
                "signature_data": r.signature_data if viewer_id is not None and r.signer_id == viewer_id else None,
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
    return _enrich_request(req, current_user.id)


@router.get("/requests/pending-for-me", response_model=List[SignatureRequestRead],
            dependencies=[Depends(require_permission("esign", "view"))])
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
    return [_enrich_request(r, current_user.id) for r in requests]


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
    return [_enrich_request(r, current_user.id) for r in requests]


@router.get("/requests/{request_id}", response_model=SignatureRequestDetail,
            dependencies=[Depends(require_permission("esign", "view"))])
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
    return _enrich_request(req, current_user.id)


@router.post("/requests/{request_id}/sign", response_model=SignatureRequestRead,
             dependencies=[Depends(require_permission("esign", "sign"))])
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

    from app.models.esign import UserSignatureProfile

    profile = await _active_signature(db, current_user.id)
    if profile is None:
        had_one = (await db.execute(select(UserSignatureProfile.id).where(
            UserSignatureProfile.user_id == current_user.id).limit(1))).first()
        if had_one:  # IT revoked it (e.g. the person left): no signing with a drawn substitute
            raise HTTPException(status_code=403, detail="Your registered signature was revoked; contact IT.")
        if not body.signature_data:
            raise HTTPException(status_code=422, detail="No signature registered for you; ask IT to register it, or draw one.")
        _validated_image(body.signature_data)
    record.status = SignatureRecordStatus.SIGNED
    record.signed_at = datetime.now(timezone.utc)
    # the signer's IT-registered signature is applied automatically; a drawn one is used only when none is on file
    record.signature_data = profile.signature_image if profile else body.signature_data
    record.signed_payload_hash_sha256 = body.signed_payload_hash_sha256
    record.auth_method = (f"registered-signature:{profile.image_sha256[:16]}" if profile
                          else (body.auth_method or "drawn-signature"))
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
    return _enrich_request(req, current_user.id)


@router.post("/requests/{request_id}/decline", response_model=SignatureRequestRead,
             dependencies=[Depends(require_permission("esign", "sign"))])
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
    return _enrich_request(req, current_user.id)



# ── Registered employee signatures (recorded by IT at hiring) ──────────────────

MAX_SIGNATURE_BYTES = 300 * 1024
_SIGNATURE_FORMATS = {"data:image/png;base64,": b"\x89PNG\r\n\x1a\n", "data:image/jpeg;base64,": b"\xff\xd8\xff"}


class SignatureRegistration(BaseModel):
    signature_image: str = Field(min_length=30, max_length=MAX_SIGNATURE_BYTES * 2)


async def _active_signature(db: AsyncSession, user_id):
    from app.models.esign import UserSignatureProfile

    return (await db.execute(select(UserSignatureProfile).where(
        UserSignatureProfile.user_id == user_id, UserSignatureProfile.is_active.is_(True)))).scalar_one_or_none()


def _validated_image(data_url: str) -> str:
    """PNG or JPEG data URL, decodable, real image header, at most 300 KB. Returns its SHA-256."""
    import base64
    import binascii
    import hashlib

    prefix = next((p for p in _SIGNATURE_FORMATS if data_url.startswith(p)), None)
    if prefix is None:
        raise HTTPException(422, "Signature must be a PNG or JPEG image.")
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "Signature image is not valid base64.")
    if len(raw) > MAX_SIGNATURE_BYTES or not raw.startswith(_SIGNATURE_FORMATS[prefix]):
        raise HTTPException(422, "Signature image is too large or not a real PNG/JPEG.")
    return hashlib.sha256(raw).hexdigest()


@router.get("/my-signature", dependencies=[Depends(require_permission("esign", "view"))])
async def my_signature(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """The caller's own registered signature. Nobody can read another person's signature image."""
    p = await _active_signature(db, current_user.id)
    if p is None:
        return {"has_signature": False}
    return {"has_signature": True, "signature_image": p.signature_image, "image_sha256": p.image_sha256,
            "registered_at": p.registered_at.isoformat()}


@router.get("/signatures", dependencies=[Depends(require_permission("esign", "admin"))])
async def list_registered_signatures(search: Optional[str] = Query(None, max_length=100),
                                     db: AsyncSession = Depends(get_db)):
    """For IT: who has a signature on file (metadata only — never the image)."""
    from app.models.esign import UserSignatureProfile

    q = select(User, UserSignatureProfile).outerjoin(UserSignatureProfile, (UserSignatureProfile.user_id == User.id)
                                                     & UserSignatureProfile.is_active.is_(True)).where(User.is_active.is_(True))
    if search and search.strip():
        like = "%" + search.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        q = q.where((User.full_name.ilike(like, escape="\\")) | (User.username.ilike(like, escape="\\")))
    rows = (await db.execute(q.order_by(User.full_name).limit(500))).all()
    return [{"user_id": str(u.id), "username": u.username, "full_name": u.full_name,
             "has_signature": p is not None, "registered_at": p.registered_at.isoformat() if p else None,
             "image_sha256": p.image_sha256 if p else None} for u, p in rows]


@router.put("/signatures/{user_id}", dependencies=[Depends(require_permission("esign", "admin"))])
async def register_signature(user_id: uuid.UUID, body: SignatureRegistration, http_request: Request,
                             db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """IT records (or replaces) an employee's signature; the previous one is kept as revoked history."""
    from app.crud import audit as audit_crud
    from app.models.esign import UserSignatureProfile

    employee = await db.get(User, user_id)
    if employee is None or not employee.is_active:
        raise HTTPException(404, "Active user not found")
    digest = _validated_image(body.signature_image)
    now = datetime.now(timezone.utc)
    old = await _active_signature(db, user_id)
    if old is not None:
        old.is_active, old.revoked_at, old.revoked_by_id, old.revoke_reason = False, now, current_user.id, "replaced"
        await db.flush()
    from sqlalchemy.exc import IntegrityError

    db.add(UserSignatureProfile(user_id=user_id, signature_image=body.signature_image, image_sha256=digest,
                                is_active=True, registered_by_id=current_user.id, registered_at=now))
    try:
        await db.flush()
    except IntegrityError:  # another IT user registered at the same moment
        await db.rollback()
        raise HTTPException(409, "The signature was changed at the same time; reload and try again.")
    await audit_crud.log_event(db, event_type="ESIGN_SIGNATURE_REGISTERED", actor_id=current_user.id,
                               actor_email=current_user.email, module="esign", target_type="user",
                               target_id=str(user_id), target_name=employee.username,
                               details={"image_sha256": digest, "replaced": old is not None},
                               ip_address=http_request.client.host if http_request.client else None)
    await db.commit()
    return {"user_id": str(user_id), "has_signature": True, "image_sha256": digest, "registered_at": now.isoformat()}


@router.delete("/signatures/{user_id}", dependencies=[Depends(require_permission("esign", "admin"))])
async def revoke_signature(user_id: uuid.UUID, http_request: Request, reason: str = Query("revoked by IT", max_length=300),
                           db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """E.g. when someone leaves: the signature can no longer be applied (history and past signings stay)."""
    from app.crud import audit as audit_crud

    p = await _active_signature(db, user_id)
    if p is None:
        raise HTTPException(404, "No active signature for this user")
    p.is_active, p.revoked_at, p.revoked_by_id, p.revoke_reason = False, datetime.now(timezone.utc), current_user.id, reason
    await audit_crud.log_event(db, event_type="ESIGN_SIGNATURE_REVOKED", actor_id=current_user.id,
                               actor_email=current_user.email, module="esign", target_type="user",
                               target_id=str(user_id), details={"reason": reason, "image_sha256": p.image_sha256},
                               ip_address=http_request.client.host if http_request.client else None)
    await db.commit()
    return {"user_id": str(user_id), "has_signature": False}


# ── M48.S01.T009 provider e-signature: DocuSign eSignature / Adobe Acrobat Sign ────────────────────────────
# Staff routes need esign rights (sales scope is checked on the quotation itself); the public provider callbacks live in
# esign_connect_public.py (prefix /public/esign).

from fastapi import Header  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from pydantic import EmailStr  # noqa: E402

from app.core.access_control import has_any_permission  # noqa: E402
from app.services import esign_provider_service as esp  # noqa: E402



def _esp_fail(e: "esp.ESignError"):
    raise HTTPException(e.status, str(e))


async def _audit(db, user, event: str, target_id: str, details: dict, http_request: Optional[Request] = None):
    from app.crud import audit as audit_crud
    await audit_crud.log_event(db, event_type=event, actor_id=user.id, actor_email=user.email, module="esign",
                               target_type="esign_envelope", target_id=target_id, details=details,
                               ip_address=http_request.client.host if http_request and http_request.client else None)


@router.get("/providers", dependencies=[Depends(require_permission("esign", "view"))])
async def provider_readiness(db: AsyncSession = Depends(get_db)):
    """LOCAL signer-code flow plus each provider: mode (SIMULATED/LIVE), ready, and the precise disabled reasons."""
    return await esp.readiness(db)


class ProviderConfigIn(BaseModel):
    settings: dict = Field(default_factory=dict)
    secrets: dict = Field(default_factory=dict)       # write-only; never returned
    live_enabled: Optional[bool] = None


@router.put("/providers/{provider}", dependencies=[Depends(require_permission("esign", "admin"))])
async def provider_config(provider: str, body: ProviderConfigIn, http_request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    try:
        out = await esp.save_config(db, provider.upper(), body.settings, body.secrets, body.live_enabled, current_user)
    except esp.ESignError as e:
        _esp_fail(e)
    await _audit(db, current_user, "ESIGN_PROVIDER_CONFIG", provider.upper(),
                 {"settings": sorted(body.settings), "secrets_changed": sorted(k for k, v in body.secrets.items() if v),
                  "live_enabled": body.live_enabled}, http_request)
    await db.commit()
    return out


class ProviderSendIn(BaseModel):
    provider: str = Field(pattern="^(DOCUSIGN|ADOBE_SIGN)$")
    source_type: str = Field(pattern="^(QUOTATION|CONTRACT)$")
    source_id: uuid.UUID
    signer_name: str = Field(min_length=2, max_length=120)
    signer_email: EmailStr
    expire_days: int = Field(30, ge=1, le=120)


@router.post("/providers/send", status_code=201, dependencies=[Depends(require_permission("esign", "request"))])
async def provider_send(body: ProviderSendIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
                        idempotency_key: Optional[str] = Header(None, max_length=80, pattern=r"^[A-Za-z0-9_.:-]{8,80}$")):
    """Send the immutable approved snapshot (quotation SENT with approvals complete, or contract APPROVED/ACTIVE)."""
    try:
        env = await esp.send(db, provider=body.provider, source_type=body.source_type, source_id=body.source_id,
                             signer_name=body.signer_name.strip(), signer_email=str(body.signer_email),
                             expire_days=body.expire_days, idempotency_key=idempotency_key, user=current_user)
    except esp.ESignError as e:
        _esp_fail(e)
    return esp.envelope_out(env)


@router.get("/providers/envelopes", dependencies=[Depends(require_permission("esign", "view"))])
async def provider_envelopes(source_type: Optional[str] = Query(None, pattern="^(QUOTATION|CONTRACT)$"),
                             source_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """Only envelopes whose quotation / contract the caller may see (e-signature admins: all)."""
    from app.models.m48_esign import ESignEnvelope
    q = select(ESignEnvelope).order_by(ESignEnvelope.created_at.desc(), ESignEnvelope.id)
    if source_type:
        q = q.where(ESignEnvelope.source_type == source_type)
    if source_id:
        q = q.where(ESignEnvelope.source_id == source_id)
    out, offset = [], 0
    while len(out) < 200:              # page until 200 visible ones: scope is filtered after the query (review N1)
        page = list((await db.execute(q.offset(offset).limit(200))).scalars())
        if not page:
            break
        out += await esp.visible_envelopes(db, current_user, page)
        offset += len(page)
    return [esp.envelope_out(e) for e in out[:200]]


async def _envelope(db, env_id, user):
    """The envelope, or 404 when it does not exist or its source record is outside the caller's scope."""
    from app.models.m48_esign import ESignEnvelope
    env = await db.get(ESignEnvelope, env_id)
    try:
        await esp.ensure_envelope_visible(db, user, env)
    except esp.ESignError as e:
        _esp_fail(e)
    return env


@router.get("/providers/envelopes/{env_id}", dependencies=[Depends(require_permission("esign", "view"))])
async def provider_envelope(env_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return esp.envelope_out(await _envelope(db, env_id, current_user))


@router.post("/providers/envelopes/{env_id}/reconcile",
             dependencies=[Depends(require_permission("esign", "request"))])
async def provider_reconcile(env_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Read the status back from the provider (and resolve an unknown create by our reference)."""
    await _envelope(db, env_id, current_user)
    try:
        env = await esp.reconcile(db, env_id, "user", current_user)
    except esp.ESignError as e:
        _esp_fail(e)
    await db.commit()
    return esp.envelope_out(env)


class ProviderCancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=200)


@router.post("/providers/envelopes/{env_id}/cancel", dependencies=[Depends(require_permission("esign", "cancel"))])
async def provider_cancel(env_id: uuid.UUID, body: ProviderCancelIn, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    env = await _envelope(db, env_id, current_user)
    if not (current_user.is_superuser or has_any_permission(current_user, ("esign.admin",)) or env.created_by_id == current_user.id):
        raise HTTPException(403, "Only the requester or an e-signature admin can cancel this request.")
    try:
        env = await esp.cancel(db, env_id, body.reason, current_user)
    except esp.ESignError as e:
        _esp_fail(e)
    await db.commit()
    return esp.envelope_out(env)


@router.get("/providers/envelopes/{env_id}/files/{kind}", dependencies=[Depends(require_permission("esign", "view"))])
async def provider_file(env_id: uuid.UUID, kind: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """snapshot (what was sent), signed (combined signed document), evidence (certificate / audit trail).
    The stored SHA-256 is checked before the file is served."""
    import hashlib
    env = await _envelope(db, env_id, current_user)
    blob, digest = {"snapshot": (env.snapshot_pdf, env.snapshot_sha256), "signed": (env.signed_pdf, env.signed_sha256),
                    "evidence": (env.evidence_pdf, env.evidence_sha256)}.get(kind, (None, None))
    if blob is None:
        raise HTTPException(404, "No such file for this request")
    if hashlib.sha256(blob).hexdigest() != digest:
        raise HTTPException(500, "Stored file does not match its recorded SHA-256; not served.")
    await _audit(db, current_user, "ESIGN_PROVIDER_FILE_DOWNLOADED", str(env.id), {"kind": kind, "sha256": digest})
    await db.commit()
    cert = "provider-certified" if env.provider_certified else ("simulated" if env.mode == "SIMULATED" else "not-certified")
    name = env.source_ref.replace(" ", "_")
    return Response(blob, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={name}-{kind}.pdf",
        "X-Content-SHA256": digest, "X-Evidence-Status": cert, "Cache-Control": "private, no-store"})
