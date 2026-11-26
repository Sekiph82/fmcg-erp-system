"""Recurring meetings (M49.S01.T001). Prefix /api/v1/meeting-series.

A series has an RRULE and an IANA time zone; its occurrences are meeting_records rows. Edit and cancel take a scope:
this occurrence / all / this and following. One calendar invitation goes out per change of the series, from the host's
mailbox. Same visibility rules as /meetings: the host and invitees (anyone with crm.view_all / sales.view_all reads,
the host or crm.edit_all changes). Every mutation writes an audit row."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.m49_calendar_mail import MeetingSeries
from app.services import calendar_series_service as svc
from app.services import meeting_service as mtg

router = APIRouter()
BROAD_VIEW, EDIT_ANY = ("crm.view_all", "sales.view_all"), ("crm.edit_all",)
Platform = Literal["jitsi", "google_meet", "zoom", "teams", "in_person", "other"]
Scope = Literal["this", "all", "following"]


class Attendee(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def _one_line(cls, v):
        if v is not None and any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class SeriesIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    platform: Platform = "jitsi"
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    start: datetime = Field(description="wall time of the first occurrence in time_zone, or offset-aware")
    time_zone: str = Field(mtg.DEFAULT_TZ, max_length=64)
    duration_minutes: int = Field(60, ge=5, le=480)
    rrule: str = Field(min_length=5, max_length=500, description="e.g. FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10")
    customer_id: Optional[uuid.UUID] = None
    agenda: Optional[str] = Field(None, max_length=5000)
    attendees: List[Attendee] = Field(default_factory=list, max_length=50)
    send_invites: bool = True

    @field_validator("title")
    @classmethod
    def _title_one_line(cls, v):
        if any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class SeriesPatch(BaseModel):
    scope: Scope
    occurrence_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="local date of the occurrence")
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=r"^https://")
    start: Optional[datetime] = None
    time_zone: Optional[str] = Field(None, max_length=64)
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    rrule: Optional[str] = Field(None, min_length=5, max_length=500)
    agenda: Optional[str] = Field(None, max_length=5000)
    attendees: Optional[List[Attendee]] = Field(None, max_length=50)
    expected_sequence: Optional[int] = None
    send_invites: bool = True

    @field_validator("title")
    @classmethod
    def _title_one_line(cls, v):
        if v is not None and any(ord(c) < 32 for c in v):
            raise ValueError("must be a single line")
        return v


class RsvpIn(BaseModel):
    email: EmailStr
    response: Literal["accepted", "declined", "tentative"]
    occurrence_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


def _iso(v: datetime) -> str:
    return v.replace(tzinfo=timezone.utc).isoformat()


def _may_change(s: MeetingSeries, user) -> bool:
    return bool(getattr(user, "is_superuser", False)) or s.host_id == user.id or has_any_permission(user, EDIT_ANY)


def _may_view(s: MeetingSeries, user) -> bool:
    mail = (getattr(user, "email", "") or "").lower()
    return (_may_change(s, user) or has_any_permission(user, BROAD_VIEW)
            or any(a.get("email") == mail for a in s.attendees or []))


async def _get(db: AsyncSession, sid: uuid.UUID, user, change: bool = False) -> MeetingSeries:
    s = await db.get(MeetingSeries, sid)
    if s is None or not _may_view(s, user):
        raise HTTPException(404, "Series not found")
    if change and not _may_change(s, user):
        raise HTTPException(403, "Only the host can change this series.")
    return s


def _row(s: MeetingSeries) -> dict:
    return {"id": str(s.id), "title": s.title, "platform": s.platform, "meeting_url": s.meeting_url,
            "time_zone": s.time_zone, "start_local": s.start_local.isoformat(), "duration_minutes": s.duration_minutes,
            "rrule": s.rrule, "agenda": s.agenda, "attendees": s.attendees or [], "status": s.status,
            "sequence": s.sequence, "host_id": str(s.host_id) if s.host_id else None,
            "customer_id": str(s.customer_id) if s.customer_id else None}


def _audit(db, user, event: str, s: MeetingSeries, details: dict) -> None:
    db.add(AuditLog(actor_id=user.id, actor_email=user.email, actor_name=getattr(user, "full_name", None), event_type=event,
                    module="meetings", target_type="meeting_series", target_id=str(s.id), target_name=s.title[:200],
                    details=details))


def _bad(e: Exception) -> HTTPException:
    if isinstance(e, svc.SeriesConflict):
        return HTTPException(409, {"detail": "One or more occurrences overlap another meeting of yours.", "conflicts": e.items})
    return HTTPException(422, str(e))


async def _notify(db, user, ids: list, *, removed: Optional[list[str]] = None, cancelled: bool = False,
                  send_invites: bool = True) -> tuple[dict, dict]:
    """One invitation per affected series, then the provider push. Mailbox / provider trouble never undoes the change."""
    from app.models.user import User
    from app.services.email_mailbox_service import MailboxError
    invites, calendar = {}, {}
    host = await db.get(User, user.id)
    for sid in ids:
        s = await db.get(MeetingSeries, sid)
        host = await db.get(User, s.host_id) if s.host_id else host
        if send_invites:
            try:
                invites[str(sid)] = await svc.send_invite(db, s, host, cancelled=cancelled)
                if removed:
                    await svc.send_invite(db, s, host, cancelled=True, recipients=removed)
            except MailboxError as e:
                invites[str(sid)] = f"FAILED: {e}"
        else:
            invites[str(sid)] = "NOT_REQUESTED"
        calendar[str(sid)] = await svc.push_safely(db, s)
    return invites, calendar


@router.post("", status_code=201)
async def create_series(body: SeriesIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.sales import Customer
    if body.customer_id and await db.get(Customer, body.customer_id) is None:
        raise HTTPException(422, "Customer not found")
    try:
        s = await svc.create_series(db, current_user, title=body.title, platform=body.platform, meeting_url=body.meeting_url,
                                    start=body.start, time_zone=body.time_zone, duration_minutes=body.duration_minutes,
                                    rrule=body.rrule, agenda=body.agenda, attendees=[a.model_dump() for a in body.attendees],
                                    customer_id=body.customer_id)
    except (svc.SeriesError, mtg.MeetingError) as e:
        raise _bad(e)
    n = len(await svc._occ_rows(db, s))
    _audit(db, current_user, "MEETING_SERIES_CREATED", s, {"rrule": s.rrule, "time_zone": s.time_zone, "occurrences": n})
    invites, calendar = await _notify(db, current_user, [s.id], send_invites=body.send_invites)
    await db.commit()
    return {"id": str(s.id), "rrule": s.rrule, "occurrences": n, "invites": invites[str(s.id)], "calendar": calendar[str(s.id)]}


@router.get("")
async def list_series(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(MeetingSeries).order_by(MeetingSeries.start_local.desc()).limit(300))).scalars().all()
    return [_row(s) for s in rows if _may_view(s, current_user)][:100]


@router.get("/free-busy")
async def free_busy(start: datetime, end: datetime, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Your busy time between start and end (ERP meetings + your connected calendar's own free/busy)."""
    lo, hi = (x.astimezone(timezone.utc).replace(tzinfo=None) if x.tzinfo else x for x in (start, end))
    if not lo < hi <= lo + timedelta(days=62):
        raise HTTPException(422, "end must be after start, at most 62 days apart")
    return await svc.free_busy(db, current_user.id, lo, hi)


@router.get("/{series_id}")
async def get_series(series_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    s = await _get(db, series_id, current_user)
    occs = await svc._occ_rows(db, s)
    return {**_row(s), "can_change": _may_change(s, current_user),
            "occurrences": [{"date": o.occ_date, "meeting_id": str(m.id), "status": m.status, "is_exception": o.is_exception,
                             "start": _iso(m.scheduled_at), "local_start": mtg.local(m.scheduled_at, s.time_zone).isoformat(),
                             "duration_minutes": m.duration_minutes, "title": m.title,
                             "attendees": m.attendees or []} for o, m in occs]}


@router.patch("/{series_id}")
async def edit_series(series_id: uuid.UUID, body: SeriesPatch, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    s = await _get(db, series_id, current_user, change=True)
    await mtg.lock_host(db, s.host_id)
    await db.refresh(s)
    if body.expected_sequence is not None and body.expected_sequence != s.sequence:
        raise HTTPException(409, "The series was changed by someone else; reload it.")
    ch = body.model_dump(exclude={"scope", "occurrence_date", "expected_sequence", "send_invites"}, exclude_unset=True)
    if "attendees" in ch and ch["attendees"] is None or any(ch.get(k, 1) is None for k in ("title", "duration_minutes")):
        raise HTTPException(422, "title, duration and attendees cannot be empty")
    if ch.get("attendees") is not None:
        ch["attendees"] = [{"name": a.get("name"), "email": str(a["email"])} for a in ch["attendees"]]
    try:
        res = await svc.edit(db, s, body.scope, body.occurrence_date, ch)
    except (svc.SeriesError, mtg.MeetingError) as e:
        raise _bad(e)
    _audit(db, current_user, "MEETING_SERIES_UPDATED", s, {"scope": body.scope, "occurrence_date": body.occurrence_date,
                                                           "fields": sorted(ch), "series": [str(x) for x in res["series"]]})
    invites, calendar = await _notify(db, current_user, res["series"], removed=res["removed"], send_invites=body.send_invites)
    await db.commit()
    return {"id": str(s.id), "series": [str(x) for x in res["series"]], "sequence": s.sequence, "invites": invites,
            "calendar": calendar}


@router.delete("/{series_id}")
async def cancel_series(series_id: uuid.UUID, scope: Scope = "all", occurrence_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                        send_invites: bool = True, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    s = await _get(db, series_id, current_user, change=True)
    await mtg.lock_host(db, s.host_id)
    await db.refresh(s)
    try:
        res = await svc.cancel(db, s, scope, occurrence_date)
    except (svc.SeriesError, mtg.MeetingError) as e:
        raise _bad(e)
    if res.get("already"):
        return {"ok": True, "invites": "ALREADY_CANCELLED"}
    whole = s.status == "CANCELLED"
    _audit(db, current_user, "MEETING_SERIES_CANCELLED", s, {"scope": scope, "occurrence_date": occurrence_date, "whole": whole})
    invites, calendar = await _notify(db, current_user, res["series"], cancelled=whole, send_invites=send_invites)
    await db.commit()
    return {"ok": True, "invites": invites, "calendar": calendar}


@router.post("/{series_id}/rsvp")
async def rsvp(series_id: uuid.UUID, body: RsvpIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Record an invitee's answer (from a phone call, or entered by the host). Replies that arrive as e-mail
    (iCalendar REPLY) are recorded automatically by the mailbox import."""
    s = await _get(db, series_id, current_user, change=True)
    try:
        n = await svc.rsvp(db, s, str(body.email), body.response, body.occurrence_date)
    except svc.SeriesError as e:
        raise _bad(e)
    _audit(db, current_user, "MEETING_SERIES_RSVP", s, {"email": str(body.email).lower(), "response": body.response,
                                                         "occurrence_date": body.occurrence_date})
    await db.commit()
    return {"updated": n}
