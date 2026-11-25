"""Booking pages — staff side (M43.S01.T005). Prefix /api/v1/booking-pages.

Anyone signed in may run a page for themselves; a team (round-robin) page with other hosts needs crm.edit_all.
"""
from __future__ import annotations

import re
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.meetings import Booking, BookingPage
from app.models.user import User
from app.services import meeting_service as mtg

router = APIRouter()
HM = r"^([01]\d|2[0-3]):[0-5]\d$"


class PageIn(BaseModel):
    slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    duration_minutes: int = Field(30, ge=5, le=480)
    buffer_before: int = Field(0, ge=0, le=240)
    buffer_after: int = Field(10, ge=0, le=240)
    min_notice_hours: int = Field(4, ge=0, le=720)
    max_days_ahead: int = Field(30, ge=1, le=365)
    time_zone: str = Field("Africa/Nairobi", max_length=64)
    open_time: str = Field("08:00", pattern=HM)
    close_time: str = Field("17:00", pattern=HM)
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    host_ids: list[uuid.UUID] = Field(default_factory=list)
    routing: Literal["round_robin", "first_available"] = "round_robin"
    platform: Literal["jitsi", "google_meet", "teams", "zoom", "other"] = "jitsi"
    consent_text: Optional[str] = Field(None, max_length=1000)
    is_active: bool = True

    @field_validator("weekdays")
    @classmethod
    def _days(cls, v):
        if not v or any(d not in range(7) for d in v):
            raise ValueError("weekdays must be 0 (Monday) … 6 (Sunday)")
        return sorted(set(v))


def _out(p: BookingPage) -> dict:
    return {"id": str(p.id), "slug": p.slug, "title": p.title, "description": p.description,
            "duration_minutes": p.duration_minutes, "buffer_before": p.buffer_before, "buffer_after": p.buffer_after,
            "min_notice_hours": p.min_notice_hours, "max_days_ahead": p.max_days_ahead, "time_zone": p.time_zone,
            "open_time": p.open_time, "close_time": p.close_time, "weekdays": p.weekdays, "host_ids": p.host_ids,
            "routing": p.routing, "platform": p.platform, "consent_text": p.consent_text, "is_active": p.is_active,
            "public_url": f"{settings.PUBLIC_APP_URL.rstrip('/')}/book/{p.slug}"}


def _may_manage(p: BookingPage, user: User) -> bool:
    return user.is_superuser or has_permission(user, "crm.edit_all") or p.created_by_id == user.id


async def _validate(db: AsyncSession, body: PageIn, user: User) -> list[str]:
    try:
        mtg.zone(body.time_zone)
    except mtg.MeetingError as e:
        raise HTTPException(422, str(e)) from None
    if body.slug == "manage":
        raise HTTPException(422, "That address is reserved.")
    if body.open_time >= body.close_time:
        raise HTTPException(422, "Closing time must be after opening time.")
    hosts = body.host_ids or [user.id]
    if set(hosts) != {user.id} and not (user.is_superuser or has_permission(user, "crm.edit_all")):
        raise HTTPException(403, "Only CRM managers can put other people on a booking page.")
    found = set((await db.execute(select(User.id).where(User.id.in_(hosts), User.is_active.is_(True)))).scalars())
    if found != set(hosts):
        raise HTTPException(422, "Every host must be an active user.")
    return [str(h) for h in dict.fromkeys(hosts)]


@router.get("")
async def list_pages(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(BookingPage).order_by(BookingPage.title))).scalars().all()
    return [_out(p) for p in rows if _may_manage(p, current_user) or str(current_user.id) in (p.host_ids or [])]


@router.post("", status_code=201)
async def create_page(body: PageIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    hosts = await _validate(db, body, current_user)
    if (await db.execute(select(BookingPage.id).where(BookingPage.slug == body.slug))).first():
        raise HTTPException(409, "That address is already taken.")
    p = BookingPage(**body.model_dump(exclude={"host_ids"}), host_ids=hosts, created_by_id=current_user.id)
    db.add(p)
    await db.commit()
    return _out(p)


@router.put("/{page_id}")
async def update_page(page_id: uuid.UUID, body: PageIn, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    p = await db.get(BookingPage, page_id)
    if p is None or not _may_manage(p, current_user):
        raise HTTPException(404, "Booking page not found")
    hosts = await _validate(db, body, current_user)
    if body.slug != p.slug and (await db.execute(select(BookingPage.id).where(BookingPage.slug == body.slug))).first():
        raise HTTPException(409, "That address is already taken.")
    for k, v in body.model_dump(exclude={"host_ids"}).items():
        setattr(p, k, v)
    p.host_ids = hosts
    await db.commit()
    return _out(p)


@router.get("/{page_id}/bookings")
async def page_bookings(page_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    p = await db.get(BookingPage, page_id)
    if p is None or not (_may_manage(p, current_user) or str(current_user.id) in (p.host_ids or [])):
        raise HTTPException(404, "Booking page not found")
    rows = (await db.execute(select(Booking).where(Booking.page_id == p.id).order_by(Booking.created_at.desc())
                             .limit(200))).scalars()
    return [{"id": str(b.id), "meeting_id": str(b.meeting_id), "host_id": str(b.host_id) if b.host_id else None,
             "visitor_name": b.visitor_name, "visitor_email": b.visitor_email, "created_at": b.created_at.isoformat()}
            for b in rows]
