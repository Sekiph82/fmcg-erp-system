"""Video Meeting Integration endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.meetings import MeetingRecord

router = APIRouter()

PLATFORM_URLS = {
    "google_meet": "https://meet.google.com/new",
    "zoom": "https://zoom.us/start/videomeeting",
    "teams": "https://teams.microsoft.com/l/meetup-join",
}


def _row(m: MeetingRecord) -> dict:
    return {
        "id": str(m.id),
        "title": m.title,
        "platform": m.platform,
        "meeting_url": m.meeting_url,
        "host_id": str(m.host_id) if m.host_id else None,
        "host_name": m.host.full_name if m.host else None,
        "customer_id": str(m.customer_id) if m.customer_id else None,
        "customer_name": m.customer.name if m.customer else None,
        "scheduled_at": m.scheduled_at.isoformat(),
        "duration_minutes": m.duration_minutes,
        "status": m.status,
        "agenda": m.agenda,
        "notes": m.notes,
        "recording_url": m.recording_url,
        "attendees": m.attendees or [],
        "outcome": m.outcome,
        "follow_up_action": m.follow_up_action,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/", response_model=list)
async def list_meetings(
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    from_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(MeetingRecord).options(
        selectinload(MeetingRecord.host),
        selectinload(MeetingRecord.customer),
    )
    if status:
        q = q.where(MeetingRecord.status == status)
    if customer_id:
        q = q.where(MeetingRecord.customer_id == customer_id)
    if from_date:
        q = q.where(MeetingRecord.scheduled_at >= datetime.fromisoformat(from_date))
    r = await db.execute(q.order_by(MeetingRecord.scheduled_at.desc()).limit(limit))
    return [_row(m) for m in r.scalars()]


@router.post("/", status_code=201)
async def create_meeting(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    platform = body.get("platform", "google_meet")
    meeting_url = body.get("meeting_url") or PLATFORM_URLS.get(platform, "")
    m = MeetingRecord(
        title=body["title"],
        platform=platform,
        meeting_url=meeting_url,
        meeting_id_ext=body.get("meeting_id_ext"),
        host_id=current_user.id,
        customer_id=uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
        crm_record_id=uuid.UUID(body["crm_record_id"]) if body.get("crm_record_id") else None,
        project_id=uuid.UUID(body["project_id"]) if body.get("project_id") else None,
        scheduled_at=datetime.fromisoformat(body["scheduled_at"]),
        duration_minutes=body.get("duration_minutes", 60),
        status="SCHEDULED",
        agenda=body.get("agenda"),
        attendees=body.get("attendees", []),
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return {"id": str(m.id), "meeting_url": m.meeting_url}


@router.patch("/{meeting_id}")
async def update_meeting(
    meeting_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(MeetingRecord).where(MeetingRecord.id == meeting_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Meeting not found")
    for k in ["title", "status", "agenda", "notes", "recording_url",
              "attendees", "outcome", "follow_up_action", "duration_minutes"]:
        if k in body:
            setattr(m, k, body[k])
    if "scheduled_at" in body:
        m.scheduled_at = datetime.fromisoformat(body["scheduled_at"])
    await db.commit()
    return {"id": str(m.id)}


@router.delete("/{meeting_id}")
async def cancel_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(MeetingRecord).where(MeetingRecord.id == meeting_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Meeting not found")
    m.status = "CANCELLED"
    await db.commit()
    return {"ok": True}


@router.get("/stats")
async def meeting_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_r = await db.execute(select(func.count()).select_from(MeetingRecord))
    scheduled_r = await db.execute(
        select(func.count()).select_from(MeetingRecord).where(MeetingRecord.status == "SCHEDULED")
    )
    completed_r = await db.execute(
        select(func.count()).select_from(MeetingRecord).where(MeetingRecord.status == "COMPLETED")
    )
    upcoming_r = await db.execute(
        select(MeetingRecord).options(selectinload(MeetingRecord.customer))
        .where(MeetingRecord.status == "SCHEDULED")
        .order_by(MeetingRecord.scheduled_at).limit(5)
    )
    return {
        "total": total_r.scalar_one(),
        "scheduled": scheduled_r.scalar_one(),
        "completed": completed_r.scalar_one(),
        "upcoming": [_row(m) for m in upcoming_r.scalars()],
    }
