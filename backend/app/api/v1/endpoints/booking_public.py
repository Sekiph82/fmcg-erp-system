"""Public booking pages (no login, M43.S01.T005). Prefix /api/v1/public/book; allow-listed in PUBLIC_ROUTES.

Hosts stay anonymous (no names, e-mails or calendar details). The manage token is the visitor's credential for
reschedule/cancel; unknown and inactive pages answer 404 alike.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.meetings import BookingPage
from app.services import booking_service as bk
from app.services import meeting_service as mtg
from app.services.crm_lead_capture_service import ip_hash

router = APIRouter()


class BookIn(BaseModel):
    start_utc: datetime
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    consent: bool = False
    website: Optional[str] = Field(None, max_length=200)   # honeypot: real visitors never fill it


class MoveIn(BaseModel):
    start_utc: datetime


async def _page(db: AsyncSession, slug: str) -> BookingPage:
    p = (await db.execute(select(BookingPage).where(BookingPage.slug == slug[:80]))).scalar_one_or_none()
    if p is None or not p.is_active or not p.host_ids:
        raise HTTPException(404, "Booking page not found")
    return p


def _fail(e: bk.BookingError) -> HTTPException:
    return HTTPException(e.status_code, str(e))


@router.get("/manage/{token}")
async def manage_view(token: str, db: AsyncSession = Depends(get_db)):
    try:
        b, m, page = await bk.by_token(db, token)
    except bk.BookingError as e:
        raise _fail(e) from None
    return {"page_slug": page.slug, "title": page.title, "status": m.status, "time_zone": m.time_zone,
            "start_utc": m.scheduled_at.isoformat() + "Z", "duration_minutes": m.duration_minutes,
            "meeting_url": m.meeting_url if m.status == "SCHEDULED" else None, "visitor_name": b.visitor_name}


@router.post("/manage/{token}/cancel")
async def manage_cancel(token: str, db: AsyncSession = Depends(get_db)):
    try:
        m = await bk.cancel(db, token)
    except bk.BookingError as e:
        raise _fail(e) from None
    await db.commit()
    return {"status": m.status}


@router.post("/manage/{token}/reschedule")
async def manage_reschedule(token: str, body: MoveIn, db: AsyncSession = Depends(get_db)):
    try:
        m = await bk.reschedule(db, token, body.start_utc)
    except bk.BookingError as e:
        raise _fail(e) from None
    except mtg.MeetingError as e:
        raise HTTPException(422, str(e)) from None
    await db.commit()
    return {"status": m.status, "start_utc": m.scheduled_at.isoformat() + "Z"}


@router.get("/{slug}")
async def page_info(slug: str, db: AsyncSession = Depends(get_db)):
    p = await _page(db, slug)
    return {"slug": p.slug, "title": p.title, "description": p.description, "duration_minutes": p.duration_minutes,
            "time_zone": p.time_zone, "weekdays": p.weekdays, "max_days_ahead": p.max_days_ahead,
            "consent_text": p.consent_text, "platform": p.platform}


@router.get("/{slug}/slots")
async def page_slots(slug: str, day: date, tz: str = Query("Africa/Nairobi", max_length=64),
                     db: AsyncSession = Depends(get_db)):
    p = await _page(db, slug)
    try:
        return {"day": day.isoformat(), "time_zone": tz, "slots": await bk.slots(db, p, day, tz)}
    except mtg.MeetingError as e:
        raise HTTPException(422, str(e)) from None


@router.post("/{slug}", status_code=201)
async def page_book(slug: str, body: BookIn, request: Request, db: AsyncSession = Depends(get_db)):
    p = await _page(db, slug)
    if body.website:                                   # bot: same answer shape, nothing booked
        raise HTTPException(422, "That time is not bookable on this page.")
    try:
        b, token = await bk.book(db, p, start_utc=body.start_utc, name=body.name.strip(), email=str(body.email),
                                 consent=body.consent, ip_hash=ip_hash(request.client.host if request.client else None))
    except bk.BookingError as e:
        await db.rollback()
        raise _fail(e) from None
    except mtg.MeetingError as e:
        await db.rollback()
        raise HTTPException(422, str(e)) from None
    await db.commit()
    return {"status": "booked", "manage_token": token, "invitation": getattr(b, "invite_status", "NO_MAILBOX")}
