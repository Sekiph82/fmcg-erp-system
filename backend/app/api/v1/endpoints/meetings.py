"""Meetings (M36.S01.T005): scheduling with time zones, double-booking protection, working meeting links,
e-mailed calendar invites/cancellations and a personal calendar feed.

Visibility: your own meetings (host or invited by e-mail); everyone's with crm.view_all / sales.view_all.
Changes: the host, or crm.edit_all. Times go in as wall time + IANA zone and are stored in UTC."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.access_control import has_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.meetings import MeetingRecord
from app.services import meeting_service as svc

router = APIRouter()

BROAD_VIEW = ("crm.view_all", "sales.view_all")
EDIT_ANY = ("crm.edit_all",)
Platform = Literal["jitsi", "google_meet", "zoom", "teams", "in_person", "other"]


class Attendee(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    email: EmailStr
    attended: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _one_line(cls, v):
        if v is not None and any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class MeetingIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    platform: Platform = "jitsi"
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    start: datetime = Field(description="wall time in time_zone, or an offset-aware time")
    time_zone: str = Field(svc.DEFAULT_TZ, max_length=64)
    duration_minutes: int = Field(60, ge=5, le=480)
    customer_id: Optional[uuid.UUID] = None
    crm_record_id: Optional[uuid.UUID] = None
    agenda: Optional[str] = Field(None, max_length=5000)
    attendees: List[Attendee] = Field(default_factory=list, max_length=50)
    send_invites: bool = True

    @field_validator("title")
    @classmethod
    def _title_one_line(cls, v):
        if any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class MeetingPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    start: Optional[datetime] = None
    time_zone: Optional[str] = Field(None, max_length=64)
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    status: Optional[Literal["SCHEDULED", "COMPLETED", "NO_SHOW"]] = None  # cancel with DELETE
    agenda: Optional[str] = Field(None, max_length=5000)
    notes: Optional[str] = Field(None, max_length=20000)
    recording_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    attendees: Optional[List[Attendee]] = Field(None, max_length=50)
    outcome: Optional[str] = Field(None, max_length=100)
    follow_up_action: Optional[str] = Field(None, max_length=5000)
    expected_sequence: Optional[int] = Field(None, description="409 if the meeting changed since you loaded it")
    send_invites: bool = True

    @field_validator("title")
    @classmethod
    def _title_one_line(cls, v):
        if v is not None and any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


def _iso(v: datetime) -> str:
    return v.replace(tzinfo=timezone.utc).isoformat()


def _row(m: MeetingRecord, user=None) -> dict:
    tz = m.time_zone or svc.DEFAULT_TZ
    return {
        "id": str(m.id), "title": m.title, "platform": m.platform, "meeting_url": m.meeting_url,
        "host_id": str(m.host_id) if m.host_id else None, "host_name": m.host.full_name if m.host else None,
        "customer_id": str(m.customer_id) if m.customer_id else None,
        "customer_name": m.customer.name if m.customer else None,
        "crm_record_id": str(m.crm_record_id) if m.crm_record_id else None,
        "scheduled_at": _iso(m.scheduled_at), "ends_at": _iso(m.scheduled_at + timedelta(minutes=m.duration_minutes)),
        "local_start": svc.local(m.scheduled_at, tz).isoformat(), "time_zone": tz,
        "duration_minutes": m.duration_minutes, "status": m.status, "sequence": m.sequence or 0,
        "agenda": m.agenda, "notes": m.notes, "recording_url": m.recording_url, "attendees": m.attendees or [],
        "outcome": m.outcome, "follow_up_action": m.follow_up_action,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "can_change": bool(user is not None and _may_change(m, user)),
    }


def _visible(user):
    if getattr(user, "is_superuser", False) or has_any_permission(user, BROAD_VIEW + EDIT_ANY):
        return None
    return or_(MeetingRecord.host_id == user.id, svc.attendee_clause(getattr(user, "email", "") or ""))


def _may_change(m: MeetingRecord, user) -> bool:
    return bool(getattr(user, "is_superuser", False)) or m.host_id == user.id or has_any_permission(user, EDIT_ANY)


async def _get(db: AsyncSession, meeting_id: uuid.UUID, user) -> MeetingRecord:
    q = select(MeetingRecord).options(selectinload(MeetingRecord.host), selectinload(MeetingRecord.customer)) \
        .where(MeetingRecord.id == meeting_id)
    clause = _visible(user)
    if clause is not None:
        q = q.where(clause)
    m = (await db.execute(q)).scalar_one_or_none()
    if m is None:
        raise HTTPException(404, "Meeting not found")
    return m


def _utc(start: datetime, tz: str) -> datetime:
    try:
        return svc.to_utc(start, tz)
    except svc.MeetingError as e:
        raise HTTPException(422, str(e))


def _conflict(other: MeetingRecord) -> HTTPException:
    return HTTPException(409, {"detail": "You already have a meeting at that time.",
                               "conflict": {"id": str(other.id), "title": other.title,
                                            "scheduled_at": _iso(other.scheduled_at),
                                            "duration_minutes": other.duration_minutes}})


def _attendees(items) -> list[dict]:
    """Stored lower-cased so invitee matching is exact and case-insensitive."""
    return [{**a.model_dump(exclude_none=True), "email": str(a.email).lower()} for a in items or []]


async def _invite(db, m, cancelled=False, recipients=None) -> str:
    """Always from the host's mailbox: the calendar ORGANIZER must not change between updates."""
    from app.models.user import User
    from app.services.email_mailbox_service import MailboxError
    host = await db.get(User, m.host_id) if m.host_id else None  # never touch the lazy relationship in async
    if host is None:
        return "NO_MAILBOX"
    try:
        return await svc.send_invite(db, m, host, cancelled, recipients)
    except MailboxError as e:  # the meeting is saved; tell the host the invite did not go out
        return f"FAILED: {e}"


async def _refuse_series_occurrence(db: AsyncSession, meeting_id: uuid.UUID) -> None:
    """M49.S01.T001: an occurrence of a recurring series is changed through /meeting-series (one invitation per
    series change, one provider event), not as a stand-alone meeting."""
    from app.models.m49_calendar_mail import MeetingSeriesOccurrence
    hit = (await db.execute(select(MeetingSeriesOccurrence.series_id).where(
        MeetingSeriesOccurrence.meeting_id == meeting_id))).scalar_one_or_none()
    if hit is not None:
        raise HTTPException(409, {"detail": "This meeting is part of a recurring series; change or cancel it with "
                                            "the series (this occurrence, this and following, or all).",
                                  "series_id": str(hit)})


@router.get("/", response_model=list)
async def list_meetings(
    status: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(MeetingRecord).options(selectinload(MeetingRecord.host), selectinload(MeetingRecord.customer))
    clause = _visible(current_user)
    if clause is not None:
        q = q.where(clause)
    if status:
        q = q.where(MeetingRecord.status == status)
    if customer_id:
        q = q.where(MeetingRecord.customer_id == customer_id)
    if from_date:
        q = q.where(MeetingRecord.scheduled_at >= datetime.combine(from_date, datetime.min.time()))
    r = await db.execute(q.order_by(MeetingRecord.scheduled_at.desc()).limit(limit))
    return [_row(m, current_user) for m in r.scalars()]


@router.post("/", status_code=201)
async def create_meeting(body: MeetingIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Book a meeting. 409 if it overlaps another scheduled meeting of yours. platform=jitsi creates a
    working link; with a connected Google / Outlook calendar a Meet / Teams link is created there (M43.S01.T003/T004),
    otherwise Google Meet / Teams / Zoom links are pasted."""
    from app.models.sales import Customer

    start = _utc(body.start, body.time_zone)
    if body.customer_id and await db.get(Customer, body.customer_id) is None:
        raise HTTPException(422, "Customer not found")
    await svc.lock_host(db, current_user.id)
    other = await svc.overlapping(db, current_user.id, start, body.duration_minutes)
    if other is not None:
        raise _conflict(other)
    url = body.meeting_url or (svc.jitsi_link() if body.platform == "jitsi" else None)
    m = MeetingRecord(title=body.title, platform=body.platform, meeting_url=url, host_id=current_user.id,
                      customer_id=body.customer_id, crm_record_id=body.crm_record_id, scheduled_at=start,
                      duration_minutes=body.duration_minutes, status="SCHEDULED", agenda=body.agenda,
                      attendees=_attendees(body.attendees),
                      time_zone=svc.zone(body.time_zone).key, sequence=0)
    db.add(m)
    await db.flush()
    from app.services.calendar_sync_service import push_safely
    calendar = await push_safely(db, m)          # may fill a Google Meet / Teams link before the invite goes out
    invites = await _invite(db, m) if body.send_invites else "NOT_REQUESTED"
    await db.commit()
    return {"id": str(m.id), "meeting_url": m.meeting_url, "scheduled_at": _iso(m.scheduled_at), "invites": invites,
            "calendar": calendar}


# fixed paths before /{meeting_id}
@router.post("/calendar-feed")
async def rotate_calendar_feed(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Your private calendar subscription link (Google Calendar / Outlook: add calendar from URL).
    Calling it again replaces the link; the old one stops working."""
    token = await svc.rotate_feed(db, current_user.id)
    await db.commit()
    return {"url": f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/calendar/{token}.ics"}


@router.get("/calendar-conflicts")
async def calendar_conflicts(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """M43.S01.T003/T004: two-way sync conflicts on your meetings (calendar edit not applied); newest first."""
    from app.models.meetings import CalendarEventLink
    rows = (await db.execute(select(CalendarEventLink, MeetingRecord).join(
        MeetingRecord, MeetingRecord.id == CalendarEventLink.meeting_id).where(
        MeetingRecord.host_id == current_user.id, CalendarEventLink.conflict.is_not(None))
        .order_by(CalendarEventLink.updated_at.desc()).limit(50))).all()
    return [{"meeting_id": str(m.id), "title": m.title, "scheduled_at": _iso(m.scheduled_at), "conflict": l.conflict}
            for l, m in rows]


@router.delete("/calendar-feed", status_code=204)
async def revoke_calendar_feed(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await svc.revoke_feed(db, current_user.id)
    await db.commit()


@router.patch("/{meeting_id}")
async def update_meeting(meeting_id: uuid.UUID, body: MeetingPatch, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    m = await _get(db, meeting_id, current_user)
    if not _may_change(m, current_user):
        raise HTTPException(403, "Only the host can change this meeting.")
    if m.status == "CANCELLED":
        raise HTTPException(409, "The meeting is cancelled.")
    if body.model_fields_set & {"title", "meeting_url", "start", "time_zone", "duration_minutes", "agenda", "attendees"}             or body.status == "SCHEDULED":
        await _refuse_series_occurrence(db, m.id)
    await svc.lock_host(db, m.host_id)
    await db.refresh(m)
    if body.expected_sequence is not None and body.expected_sequence != (m.sequence or 0):
        raise HTTPException(409, "The meeting was changed by someone else; reload it.")
    data = body.model_dump(exclude_unset=True, exclude={"expected_sequence", "send_invites", "start", "time_zone"})
    for key in ("title", "status", "duration_minutes", "attendees"):
        if key in data and data[key] is None:
            raise HTTPException(422, f"{key} cannot be empty")
    tz = body.time_zone or m.time_zone or svc.DEFAULT_TZ
    start = _utc(body.start, tz) if body.start is not None else m.scheduled_at
    minutes = body.duration_minutes or m.duration_minutes
    timing = start != m.scheduled_at or minutes != m.duration_minutes
    new_status = data.get("status", m.status)
    if new_status == "SCHEDULED" and (timing or m.status != "SCHEDULED"):  # moved, or re-opened
        other = await svc.overlapping(db, m.host_id, start, minutes, exclude=m.id)
        if other is not None:
            raise _conflict(other)
    removed: list[str] = []
    if "attendees" in data:
        data["attendees"] = _attendees(body.attendees)
        keep = {a["email"] for a in data["attendees"]}
        removed = [a["email"] for a in (m.attendees or []) if a.get("email") and a["email"].lower() not in keep]
    invite_fields = {"title", "meeting_url", "agenda", "attendees"}
    changed = timing or any(k in data and data[k] != getattr(m, k) for k in invite_fields)
    for k, v in data.items():
        setattr(m, k, v)
    m.scheduled_at, m.duration_minutes = start, minutes
    if body.time_zone:
        m.time_zone = svc.zone(body.time_zone).key
    from app.services.calendar_sync_service import push_safely
    invites, calendar = "NOT_REQUESTED", "UNCHANGED"
    if changed:
        m.sequence = (m.sequence or 0) + 1
        if body.send_invites and m.status == "SCHEDULED":
            invites = await _invite(db, m)
            if removed:  # people taken off the meeting get a cancellation for the same event
                await _invite(db, m, cancelled=True, recipients=removed)
        calendar = await push_safely(db, m)
    await db.commit()
    return {"id": str(m.id), "sequence": m.sequence, "invites": invites, "calendar": calendar}


@router.delete("/{meeting_id}")
async def cancel_meeting(meeting_id: uuid.UUID, send_invites: bool = True, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    """Cancel (kept as history). Invitees get a calendar cancellation for the same event."""
    m = await _get(db, meeting_id, current_user)
    if not _may_change(m, current_user):
        raise HTTPException(403, "Only the host can cancel this meeting.")
    if m.status == "CANCELLED":
        return {"ok": True, "invites": "ALREADY_CANCELLED"}
    await _refuse_series_occurrence(db, m.id)
    m.status, m.sequence = "CANCELLED", (m.sequence or 0) + 1
    invites = await _invite(db, m, cancelled=True) if send_invites else "NOT_REQUESTED"
    from app.services.calendar_sync_service import push_safely
    calendar = await push_safely(db, m)
    await db.commit()
    return {"ok": True, "invites": invites, "calendar": calendar}


@router.get("/availability")
async def availability(day: date, tz: str = Query(svc.DEFAULT_TZ, max_length=64),
                       duration_minutes: int = Query(60, ge=5, le=480),
                       db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Your free start times on `day`, 08:00–17:00 in `tz` (DST-safe)."""
    try:
        return {"day": day.isoformat(), "time_zone": tz,
                "slots": await svc.free_slots(db, current_user.id, day, tz, duration_minutes)}
    except svc.MeetingError as e:
        raise HTTPException(422, str(e))


@router.get("/stats")
async def meeting_stats(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    clause = _visible(current_user)

    def scoped(q):
        return q if clause is None else q.where(clause)

    count = lambda *w: scoped(select(func.count()).select_from(MeetingRecord).where(*w))  # noqa: E731
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    upcoming = await db.execute(scoped(select(MeetingRecord).options(selectinload(MeetingRecord.host),
                                                                     selectinload(MeetingRecord.customer)))
                                .where(MeetingRecord.status == "SCHEDULED", MeetingRecord.scheduled_at >= now)
                                .order_by(MeetingRecord.scheduled_at).limit(5))
    return {
        "total": (await db.execute(count())).scalar_one(),
        "scheduled": (await db.execute(count(MeetingRecord.status == "SCHEDULED"))).scalar_one(),
        "completed": (await db.execute(count(MeetingRecord.status == "COMPLETED"))).scalar_one(),
        "upcoming": [_row(m, current_user) for m in upcoming.scalars()],
    }
