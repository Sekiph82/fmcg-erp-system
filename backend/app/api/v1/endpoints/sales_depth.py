"""M47.S01.T009 sales depth. Prefix /api/v1/sales-depth (CRM or sales view rights; changes need create/edit rights).

- POST /videos (multipart)            upload/record a video for ONE contact → expiring tracked link (token shown once)
- GET  /videos                        my video messages with view counts (everyone's with crm.view_all)
- POST /videos/{id}/revoke            the creator or crm.edit_all
- POST /meetings/{id}/transcript      text (form field or .txt/.vtt file) or audio through the transcription adapter
- GET  /meetings/{id}/recap           decisions / action items (verbatim quotes)
- POST /meetings/{id}/recap/approve   creates follow-up tasks for the chosen action items (once)
- GET  /meetings/{id}/brief           pre-meeting brief from stored facts
- GET  /deal-model                    active trained deal-win model (version, metrics) or NOT_ENOUGH_DATA
- POST /deal-model/train              crm.edit_all
- GET  /records/{id}/win              rule score beside the trained probability
Public video page: sales_depth_public.py (/api/v1/public/video).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m47_sales_depth import MeetingRecap, SalesVideoMessage
from app.services import pat_service as pats

VIEW = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region", "sales.view")
WRITE = ("crm.create", "crm.edit", "crm.edit_all", "sales.create")
router = APIRouter(dependencies=[Depends(require_any_permission(VIEW))])

TEXT_EXT = {".txt", ".vtt"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4"}
MAX_TEXT = 500_000


def _need(user, codes=WRITE):
    if not (user.is_superuser or has_any_permission(user, codes)):
        raise HTTPException(403, "You may not do this.")


# ── video messages ────────────────────────────────────────────────────────────

@router.post("/videos", status_code=201)
async def create_video(file: UploadFile = File(...), title: str = Form(..., min_length=1, max_length=200),
                       contact_email: EmailStr = Form(...), contact_name: Optional[str] = Form(None, max_length=200),
                       customer_id: Optional[uuid.UUID] = Form(None), crm_record_id: Optional[uuid.UUID] = Form(None),
                       days: int = Form(14, ge=1, le=60), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import video_message_service as vms
    _need(current_user)
    vm, token = await vms.create(db, file, title=title.strip(), contact_email=str(contact_email), contact_name=contact_name,
                                 customer_id=customer_id, crm_record_id=crm_record_id, days=days, user=current_user)
    pats.audit(db, current_user, "VIDEO_MESSAGE_SHARED", "sales_video_message", str(vm.id), {"days": days, "customer": str(customer_id) if customer_id else None})
    await db.commit()
    return {"id": str(vm.id), "url": vms.url(token), "expires_at": vm.expires_at.isoformat()}


@router.get("/videos")
async def list_videos(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import video_message_service as vms
    return await vms.listing(db, current_user, current_user.is_superuser or has_any_permission(current_user, ("crm.view_all",)))


@router.post("/videos/{vid}/revoke")
async def revoke_video(vid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    vm = await db.get(SalesVideoMessage, vid)
    if vm is None:
        raise HTTPException(404, "Video message not found")
    if vm.created_by_id != current_user.id and not (current_user.is_superuser or has_any_permission(current_user, ("crm.edit_all",))):
        raise HTTPException(403, "Only the sender or a CRM manager can withdraw this link.")
    vm.revoked_at = vm.revoked_at or datetime.now(timezone.utc)
    pats.audit(db, current_user, "VIDEO_MESSAGE_REVOKED", "sales_video_message", str(vm.id), {})
    await db.commit()
    return {"revoked": True}


# ── meeting recap and brief ───────────────────────────────────────────────────

async def _meeting(db, meeting_id, user, change=False):
    from app.api.v1.endpoints.meetings import _get, _may_change
    m = await _get(db, meeting_id, user)
    if change and not _may_change(m, user):
        raise HTTPException(403, "Only the host or a CRM manager can change this meeting.")
    return m


def _recap_out(r: Optional[MeetingRecap]) -> dict:
    if r is None:
        return {"status": "NO_TRANSCRIPT"}
    return {"status": "APPROVED" if r.approved_at else "DRAFT", "source": r.source, "engine": r.engine, "recap": r.recap,
            "approved_by": r.approved_by, "task_ids": r.task_ids or [], "transcript_chars": len(r.transcript or ""),
            "participants_consented": bool(((r.recap or {}).get("consent") or {}).get("participants_consented"))}


@router.post("/meetings/{meeting_id}/transcript")
async def add_transcript(meeting_id: uuid.UUID, text: Optional[str] = Form(None, max_length=MAX_TEXT), file: Optional[UploadFile] = File(None),
                         participants_consented: bool = Form(False),
                         db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Recordings go to the transcription engine and transcripts to the AI only when the uploader attests that every
    participant agreed (like call recording_consent). Without it, a text transcript gets the rules-only recap."""
    from app.services import meeting_service as svc
    from app.services import transcription_service as ts
    m = await _meeting(db, meeting_id, current_user, change=True)
    source = "TEXT_UPLOAD"
    if file is not None and file.filename:
        ext = Path(file.filename.lower()).suffix
        raw = await file.read(ts.MAX_AUDIO_BYTES + 1)
        if ext in TEXT_EXT:
            if len(raw) > MAX_TEXT:
                raise HTTPException(413, "Transcript file is too large.")
            text = raw.decode("utf-8", errors="replace")
        elif ext in AUDIO_EXT:
            engine = ts.adapter()
            if engine is None:
                raise HTTPException(409, "No transcription engine is configured (NOT_AVAILABLE). Upload the transcript as text.")
            if not participants_consented:
                raise HTTPException(422, "Confirm that all participants agreed to recording and transcription before uploading audio.")
            if len(raw) > ts.MAX_AUDIO_BYTES:
                raise HTTPException(413, "Recording is too large to transcribe.")
            try:
                result = await ts._http(raw) if engine == "http" else await asyncio.to_thread(ts._local, raw)
            except Exception:
                raise HTTPException(502, "The transcription engine failed; try again or upload text.") from None
            text = "\n".join((f"{s.get('speaker')}: " if s.get("speaker") else "") + str(s.get("text") or "")
                             for s in (result.get("segments") or []))
            source = "TRANSCRIPTION"
        else:
            raise HTTPException(422, "Upload a .txt/.vtt transcript or an audio recording.")
    text = (text or "").strip()
    if len(text) < 20:
        raise HTTPException(422, "The transcript is empty or too short.")
    recap, engine = await svc.build_recap(db, text[:MAX_TEXT], use_ai=participants_consented)
    r = await db.get(MeetingRecap, m.id)
    if r is not None and r.approved_at:
        raise HTTPException(409, "The recap was already approved and its tasks created.")
    if r is None:
        r = MeetingRecap(meeting_id=m.id, transcript="", source=source)
        db.add(r)
    consent = {"participants_consented": participants_consented, "attested_by": current_user.username,
               "attested_at": datetime.now(timezone.utc).isoformat()}
    r.transcript, r.source, r.recap, r.engine, r.updated_at = (text[:MAX_TEXT], source, {**recap, "consent": consent}, engine,
                                                               datetime.now(timezone.utc))
    await db.commit()
    return _recap_out(r)


@router.get("/meetings/{meeting_id}/recap")
async def get_recap(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    m = await _meeting(db, meeting_id, current_user)
    return _recap_out(await db.get(MeetingRecap, m.id))


class ApproveIn(BaseModel):
    action_items: list[int] = Field(default_factory=list, max_length=30)    # indexes into recap.action_items


@router.post("/meetings/{meeting_id}/recap/approve")
async def approve_recap(meeting_id: uuid.UUID, body: ApproveIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.crm import CRMActivity, CRMActivityResult, CRMActivityType
    m = await _meeting(db, meeting_id, current_user, change=True)
    r = await db.get(MeetingRecap, m.id, with_for_update=True)
    if r is None:
        raise HTTPException(404, "Attach a transcript first.")
    if r.approved_at:
        raise HTTPException(409, "The recap was already approved.")
    items = (r.recap or {}).get("action_items") or []
    picked = sorted({i for i in body.action_items if 0 <= i < len(items)})
    if picked and not m.crm_record_id:
        raise HTTPException(409, "Link the meeting to a CRM record before creating follow-up tasks.")
    ids = []
    for i in picked:
        it = items[i]
        a = CRMActivity(crm_record_id=m.crm_record_id, activity_type=CRMActivityType.TASK, subject=it["quote"][:300],
                        description=f"Follow-up from meeting '{m.title}'", result_status=CRMActivityResult.PLANNED,
                        due_datetime=datetime.utcnow() + timedelta(days=it.get("due_in_days") if it.get("due_in_days") is not None else 3),
                        assigned_to=str(m.host_id or current_user.id), created_by=current_user.username)
        db.add(a)
        await db.flush()
        ids.append(str(a.id))
    r.approved_at, r.approved_by, r.task_ids = datetime.now(timezone.utc), current_user.username, ids
    pats.audit(db, current_user, "MEETING_RECAP_APPROVED", "meeting", str(m.id), {"tasks": len(ids)})
    await db.commit()
    return _recap_out(r)


@router.get("/meetings/{meeting_id}/brief")
async def meeting_brief(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import meeting_service as svc
    m = await _meeting(db, meeting_id, current_user)
    return await svc.brief(db, m, current_user)


# ── trained deal-win model ────────────────────────────────────────────────────

@router.get("/deal-model")
async def deal_model(db: AsyncSession = Depends(get_db)):
    from app.services import crm_deal_score_service as ds
    m = await ds.active_win_model(db)
    if m is None:
        return {"status": "NOT_ENOUGH_DATA", "min_per_class": ds.MIN_PER_CLASS}
    return {"status": "TRAINED", "version": m.params.get("version"), "features": m.params.get("features"),
            "trained_at": m.trained_at.isoformat() if m.trained_at else None, "trained_by": m.trained_by, "metrics": m.metrics}


@router.post("/deal-model/train")
async def train_deal_model(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import crm_deal_score_service as ds
    _need(current_user, ("crm.edit_all",))
    out = await ds.train_win_model(db, current_user.username)
    if out.get("trained"):
        pats.audit(db, current_user, "DEAL_WIN_MODEL_TRAINED", "ci_model", out["model_id"], {"version": out["version"]})
    await db.commit()
    return out


@router.get("/records/{record_id}/win")
async def deal_win(record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    from app.services import crm_deal_score_service as ds
    rec = await _scoped_record(db, record_id, current_user, "view")
    s = await ds.score(db, rec)
    return {"record_id": str(rec.id), "rule_score": s["score"], "rule_method": s["method"], "trained": s["trained"]}
