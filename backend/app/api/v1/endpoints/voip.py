"""VoIP / Call Center endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.voip import CallLog, CallScript

router = APIRouter()


def _call_row(c: CallLog) -> dict:
    return {
        "id": str(c.id),
        "call_ref": c.call_ref,
        "direction": c.direction,
        "phone_number": c.phone_number,
        "customer_id": str(c.customer_id) if c.customer_id else None,
        "customer_name": c.customer.name if c.customer else None,
        "agent_id": str(c.agent_id) if c.agent_id else None,
        "agent_name": c.agent.full_name if c.agent else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "duration_seconds": c.duration_seconds,
        "outcome": c.outcome,
        "notes": c.notes,
        "recording_url": c.recording_url,
        "follow_up_required": c.follow_up_required,
        "follow_up_date": c.follow_up_date.isoformat() if c.follow_up_date else None,
        "tags": c.tags,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ── Call Logs ─────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=list)
async def list_calls(
    customer_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CallLog).options(
        selectinload(CallLog.customer),
        selectinload(CallLog.agent),
    )
    if customer_id:
        q = q.where(CallLog.customer_id == customer_id)
    if agent_id:
        q = q.where(CallLog.agent_id == agent_id)
    if direction:
        q = q.where(CallLog.direction == direction)
    if outcome:
        q = q.where(CallLog.outcome == outcome)
    r = await db.execute(q.order_by(CallLog.created_at.desc()).limit(limit))
    return [_call_row(c) for c in r.scalars()]


@router.post("/logs", status_code=201)
async def create_call_log(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    call = CallLog(
        call_ref=body.get("call_ref") or f"CALL-{uuid.uuid4().hex[:8].upper()}",
        direction=body.get("direction", "OUTBOUND"),
        phone_number=body["phone_number"],
        customer_id=uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
        crm_record_id=uuid.UUID(body["crm_record_id"]) if body.get("crm_record_id") else None,
        agent_id=current_user.id,
        started_at=datetime.fromisoformat(body["started_at"]) if body.get("started_at") else datetime.utcnow(),
        ended_at=datetime.fromisoformat(body["ended_at"]) if body.get("ended_at") else None,
        duration_seconds=body.get("duration_seconds"),
        outcome=body.get("outcome", "ANSWERED"),
        notes=body.get("notes"),
        recording_url=body.get("recording_url"),
        call_script_id=uuid.UUID(body["call_script_id"]) if body.get("call_script_id") else None,
        follow_up_required=body.get("follow_up_required", False),
        follow_up_date=datetime.fromisoformat(body["follow_up_date"]) if body.get("follow_up_date") else None,
        tags=body.get("tags"),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return {"id": str(call.id), "call_ref": call.call_ref}


@router.patch("/logs/{call_id}")
async def update_call_log(
    call_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(CallLog).where(CallLog.id == call_id))
    call = r.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call log not found")
    for k in ["outcome", "notes", "duration_seconds", "recording_url",
              "follow_up_required", "follow_up_date", "tags"]:
        if k in body:
            setattr(call, k, body[k])
    if "ended_at" in body and body["ended_at"]:
        call.ended_at = datetime.fromisoformat(body["ended_at"])
        if call.started_at:
            delta = call.ended_at - call.started_at
            call.duration_seconds = int(delta.total_seconds())
    await db.commit()
    return {"id": str(call.id)}


# ── Call Scripts ──────────────────────────────────────────────────────────────

@router.get("/scripts", response_model=list)
async def list_scripts(
    purpose: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CallScript).where(CallScript.is_active == True)
    if purpose:
        q = q.where(CallScript.purpose == purpose)
    r = await db.execute(q.order_by(CallScript.title))
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "purpose": s.purpose,
            "script_text": s.script_text,
            "talking_points": s.talking_points,
            "objection_handlers": s.objection_handlers,
        }
        for s in r.scalars()
    ]


@router.post("/scripts", status_code=201)
async def create_script(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    script = CallScript(
        title=body["title"],
        purpose=body.get("purpose", "sales"),
        script_text=body["script_text"],
        talking_points=body.get("talking_points"),
        objection_handlers=body.get("objection_handlers"),
        created_by_id=current_user.id,
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return {"id": str(script.id), "title": script.title}


# ── Dashboard / Stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def call_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    total_r = await db.execute(select(func.count()).select_from(CallLog))
    answered_r = await db.execute(
        select(func.count()).select_from(CallLog).where(CallLog.outcome == "ANSWERED")
    )
    followup_r = await db.execute(
        select(func.count()).select_from(CallLog).where(CallLog.follow_up_required == True)
    )
    avg_dur_r = await db.execute(
        select(func.avg(CallLog.duration_seconds)).where(CallLog.duration_seconds.isnot(None))
    )
    by_outcome_r = await db.execute(
        select(CallLog.outcome, func.count().label("cnt")).group_by(CallLog.outcome)
    )
    by_outcome = {str(row.outcome): row.cnt for row in by_outcome_r.all()}
    total = total_r.scalar_one()
    answered = answered_r.scalar_one()
    return {
        "total_calls": total,
        "answered_calls": answered,
        "answer_rate": round(answered / total * 100, 1) if total else 0,
        "follow_ups_pending": followup_r.scalar_one(),
        "avg_duration_seconds": round(avg_dur_r.scalar_one() or 0),
        "by_outcome": by_outcome,
    }
