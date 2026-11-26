"""Transcription jobs, review and withdrawal (M49.S01.T005). Mounted by voip.py under /calls/transcripts. No public routes.

Access: the call's agent (or the meeting host) and CRM managers. A transcript is a machine draft until approved; only
approved text reaches coaching. Every mutation writes an audit log; edits are kept in an edit trail.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.m49_voice import TranscriptJob
from app.models.voip import CallLog
from app.services import transcription_pipeline_service as tp

router = APIRouter()
EDIT_ALL = ("crm.edit_all", "sales.edit_all")


def _manager(u) -> bool:
    return bool(getattr(u, "is_superuser", False)) or has_any_permission(u, EDIT_ALL)


def _audit(db: AsyncSession, user, event: str, job: TranscriptJob) -> None:
    db.add(AuditLog(actor_id=user.id, event_type=f"TRANSCRIPT_{event}", module="voip", target_type="transcript_job",
                    target_id=str(job.id), target_name=f"{job.source_type}:{job.language_requested}:{job.engine}"))


def _out(j: TranscriptJob, segments: bool = True) -> dict:
    d = {"id": str(j.id), "source_type": j.source_type, "source_id": str(j.source_id), "engine": j.engine, "model": j.model,
         "language_requested": j.language_requested, "language_detected": j.language_detected, "diarize": j.diarize,
         "status": j.status, "review_status": j.review_status, "error_code": j.error_code, "error": j.error,
         "attempts": j.attempts, "quality": j.quality, "warnings": j.warnings, "redacted_segments": j.redacted_segments,
         "expires_at": j.expires_at.isoformat() if j.expires_at else None,
         "created_at": j.created_at.isoformat() if j.created_at else None}
    if segments:
        d["segments"] = j.segments or []
    return d


async def _source_ok(db: AsyncSession, source_type: str, source_id: uuid.UUID, user) -> None:
    if source_type == "call":
        c = await db.get(CallLog, source_id)
        ok = c is not None and (_manager(user) or c.agent_id == user.id)
    else:
        from app.models.meetings import MeetingRecord
        m = await db.get(MeetingRecord, source_id)
        ok = m is not None and (_manager(user) or m.host_id == user.id)
    if not ok:
        raise HTTPException(404, "Source not found")


async def _job(db: AsyncSession, job_id: uuid.UUID, user, lock: bool = False) -> TranscriptJob:
    j = await db.get(TranscriptJob, job_id, with_for_update=lock)
    if j is None:
        raise HTTPException(404, "Transcript not found")
    await _source_ok(db, j.source_type, j.source_id, user)
    return j


def _tx(e: tp.TxError):
    return HTTPException(e.status_code, str(e))


@router.get("/engines")
async def engines(current_user=Depends(get_current_user)):
    return {"engines": tp.engines(), "default": tp.default_engine(), "languages": list(tp.LANGS) + ["auto"]}


class StartIn(BaseModel):
    source_type: Literal["call", "meeting"]
    source_id: uuid.UUID
    language: Literal["auto", "en", "sw", "tr"] = "auto"
    diarize: bool = False
    engine: Optional[Literal["openai", "local", "http"]] = None
    participants_consented: bool = False        # meetings: attestation that everyone agreed to recording and transcription


@router.post("", status_code=201)
async def start(body: StartIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _source_ok(db, body.source_type, body.source_id, current_user)
    engine = body.engine or tp.default_engine()
    if engine is None:
        raise HTTPException(409, "No transcription engine is available (NOT_AVAILABLE). " + tp.LOCAL_NOTE
                            + " Or configure the OpenAI adapter (TRANSCRIPTION_OPENAI_API_KEY). You can still type the transcript manually.")
    if tp._state(engine) != "AVAILABLE":
        info = next(e for e in tp.engines() if e["key"] == engine)
        raise HTTPException(409, f"Engine {engine} is {info['state']}: {info['note'] or ''}".strip())
    if body.source_type == "meeting" and not body.participants_consented:
        raise HTTPException(422, "Confirm that all participants agreed to recording and transcription.")
    open_job = (await db.execute(select(TranscriptJob).where(TranscriptJob.source_type == body.source_type,
                TranscriptJob.source_id == body.source_id, TranscriptJob.status.in_(("PENDING", "DONE"))))).scalars().first()
    if open_job is not None:
        raise HTTPException(409, "This source already has a transcript; withdraw it first.")
    job = TranscriptJob(source_type=body.source_type, source_id=body.source_id, engine=engine, language_requested=body.language,
                        diarize=body.diarize, status="PENDING", review_status="UNREVIEWED",
                        participants_consented=body.participants_consented, created_by_id=current_user.id, attempts=0)
    db.add(job)
    await db.flush()
    _audit(db, current_user, "START", job)
    await db.commit()
    await tp.process(db, job)
    await db.commit()
    await db.refresh(job)
    return _out(job)


@router.get("")
async def list_jobs(source_type: Optional[Literal["call", "meeting"]] = None, source_id: Optional[uuid.UUID] = None,
                    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = select(TranscriptJob).order_by(TranscriptJob.created_at.desc()).limit(100)
    if source_type:
        q = q.where(TranscriptJob.source_type == source_type)
    if source_id:
        q = q.where(TranscriptJob.source_id == source_id)
    if not _manager(current_user):
        q = q.where(TranscriptJob.created_by_id == current_user.id)
    return [_out(j, segments=False) for j in (await db.execute(q)).scalars()]


@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return _out(await _job(db, job_id, current_user))


class SegmentPatch(BaseModel):
    text: Optional[str] = Field(None, max_length=4000)
    speaker: Optional[str] = Field(None, max_length=20)


@router.patch("/{job_id}/segments/{index}")
async def edit_segment(job_id: uuid.UUID, index: int, body: SegmentPatch, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    j = await _job(db, job_id, current_user, lock=True)
    if j.status != "DONE":
        raise HTTPException(409, f"A {j.status} transcript cannot be edited.")
    if body.text is None and body.speaker is None:
        raise HTTPException(422, "Nothing to change.")
    try:
        seg = await tp.edit_segment(db, j, index, body.text, body.speaker, current_user.id)
    except tp.TxError as e:
        raise _tx(e) from None
    _audit(db, current_user, "EDIT", j)
    await db.commit()
    return seg


@router.post("/{job_id}/approve")
async def approve(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    j = await _job(db, job_id, current_user, lock=True)
    if j.status != "DONE" or not j.segments:
        raise HTTPException(409, "Only a finished, non-empty transcript can be approved.")
    j.review_status, j.reviewed_by_id, j.reviewed_at = "REVIEWED", current_user.id, datetime.now(timezone.utc)
    note = await tp.feed(db, j)
    _audit(db, current_user, "APPROVE", j)
    await db.commit()
    return {**_out(j), "note": note}


@router.post("/{job_id}/withdraw")
async def withdraw(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    j = await _job(db, job_id, current_user, lock=True)
    if j.status == "WITHDRAWN":
        return _out(j)
    try:
        await tp.withdraw(db, j)
    except tp.TxError as e:
        raise _tx(e) from None
    _audit(db, current_user, "WITHDRAW", j)
    await db.commit()
    return _out(j)


@router.post("/{job_id}/retry")
async def retry(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    j = await _job(db, job_id, current_user, lock=True)
    if j.status != "FAILED":
        raise HTTPException(409, "Only a failed transcript can be retried.")
    if tp._state(j.engine) != "AVAILABLE" and tp.default_engine() is None:
        raise HTTPException(409, "No transcription engine is available (NOT_AVAILABLE).")
    if tp._state(j.engine) != "AVAILABLE":
        j.engine = tp.default_engine()
    j.status, j.error, j.error_code = "PENDING", None, None
    await tp.process(db, j)
    _audit(db, current_user, "RETRY", j)
    await db.commit()
    return _out(j)


class ManualIn(BaseModel):
    text: str = Field(min_length=3, max_length=200000)


@router.put("/{job_id}/manual")
async def manual(job_id: uuid.UUID, body: ManualIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Fallback when the engine failed or none exists: a person supplies the text (redacted like any transcript)."""
    j = await _job(db, job_id, current_user, lock=True)
    if j.status not in ("FAILED", "NOT_AVAILABLE"):
        raise HTTPException(409, "Manual text is only for a failed transcript.")
    tp.manual(j, body.text)
    _audit(db, current_user, "MANUAL", j)
    await db.commit()
    return _out(j)
