"""Public customer self-booking with team round-robin (M43.S01.T005).

- Slots: the page's working hours / weekdays in its time zone (DST-safe), at least min_notice ahead and at most
  max_days_ahead; a slot is offered while at least one host is free for [start - buffer_before, end + buffer_after],
  counting ERP meetings and busy time from the host's connected Google / Outlook calendar. Hosts stay anonymous.
- Booking: all page hosts are locked (advisory locks in a fixed order), the slot is re-checked, then the host is
  chosen: round_robin → the free host with the oldest last assignment on this page; first_available → page order.
  Concurrent visitors can never double-book a host. The invite goes from the host's mailbox (existing iCalendar
  REQUEST); a connected calendar also gets the event.
- Visitor: name, e-mail, explicit consent; honeypot and per-IP-hash and per-page rate limits; a one-time manage token
  (stored as SHA-256) for reschedule/cancel. Reminders 24 h before by e-mail.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.models.meetings import Booking, BookingPage, MeetingRecord
from app.services import meeting_service as mtg

log = logging.getLogger(__name__)
UTC = timezone.utc
STEP_MINUTES = 30
PER_IP_LIMIT = (5, timedelta(hours=1))
PER_PAGE_LIMIT = (60, timedelta(hours=1))


class BookingError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hm(v: str) -> time:
    h, m = v.split(":")
    return time(int(h), int(m))


async def _host_free(db: AsyncSession, page: BookingPage, host_id, start: datetime, exclude=None) -> bool:
    lo = start - timedelta(minutes=page.buffer_before)
    minutes = page.buffer_before + page.duration_minutes + page.buffer_after
    return await mtg.overlapping(db, host_id, lo, minutes, exclude=exclude) is None


def _hosts(page: BookingPage) -> list[UUID]:
    return [UUID(str(h)) for h in (page.host_ids or [])]


def _bounds(page: BookingPage) -> tuple[datetime, datetime]:
    now = clock.utcnow().astimezone(UTC).replace(tzinfo=None)
    return now + timedelta(hours=page.min_notice_hours), now + timedelta(days=page.max_days_ahead)


async def slots(db: AsyncSession, page: BookingPage, day: date, visitor_tz: str) -> list[dict]:
    tz = mtg.zone(page.time_zone)
    vtz = mtg.zone(visitor_tz)
    if day.weekday() not in (page.weekdays or []):
        return []
    earliest, latest = _bounds(page)
    start = datetime.combine(day, _hm(page.open_time), tz).astimezone(UTC).replace(tzinfo=None)
    close = datetime.combine(day, _hm(page.close_time), tz).astimezone(UTC).replace(tzinfo=None)
    out, t = [], start
    while t + timedelta(minutes=page.duration_minutes) <= close:
        if earliest <= t <= latest:
            for h in _hosts(page):
                if await _host_free(db, page, h, t):
                    out.append({"start_utc": t.replace(tzinfo=UTC).isoformat(),
                                "start_local": t.replace(tzinfo=UTC).astimezone(vtz).isoformat()})
                    break
        t += timedelta(minutes=STEP_MINUTES)
    return out


async def _check_rate(db: AsyncSession, page: BookingPage, ip_hash: Optional[str]) -> None:
    now = clock.utcnow()
    if ip_hash:
        n = (await db.execute(select(func.count()).select_from(Booking).where(
            Booking.ip_hash == ip_hash, Booking.created_at >= now - PER_IP_LIMIT[1]))).scalar_one()
        if n >= PER_IP_LIMIT[0]:
            raise BookingError("Too many bookings; please try again later.", 429)
    n = (await db.execute(select(func.count()).select_from(Booking).where(
        Booking.page_id == page.id, Booking.created_at >= now - PER_PAGE_LIMIT[1]))).scalar_one()
    if n >= PER_PAGE_LIMIT[0]:
        raise BookingError("This page is busy; please try again later.", 429)


async def _choose_host(db: AsyncSession, page: BookingPage, start: datetime, exclude=None) -> UUID:
    free = [h for h in _hosts(page) if await _host_free(db, page, h, start, exclude)]
    if not free:
        raise BookingError("That time was just taken; please pick another slot.")
    if page.routing != "round_robin" or len(free) == 1:
        return free[0]
    last = dict((await db.execute(select(Booking.host_id, func.max(Booking.created_at)).where(
        Booking.page_id == page.id, Booking.host_id.in_(free)).group_by(Booking.host_id))).all())
    floor = datetime.min.replace(tzinfo=UTC)
    return min(free, key=lambda h: (last.get(h) or floor, _hosts(page).index(h)))


def _validate_start(page: BookingPage, start: datetime) -> None:
    earliest, latest = _bounds(page)
    tz = mtg.zone(page.time_zone)
    local = start.replace(tzinfo=UTC).astimezone(tz)
    on_grid = (local.minute % STEP_MINUTES == 0) and local.second == 0
    in_hours = _hm(page.open_time) <= local.time() and \
        (local + timedelta(minutes=page.duration_minutes)).time() <= _hm(page.close_time) and \
        (local + timedelta(minutes=page.duration_minutes)).date() == local.date()
    if not (earliest <= start <= latest and on_grid and in_hours and local.weekday() in (page.weekdays or [])):
        raise BookingError("That time is not bookable on this page.", 422)


async def book(db: AsyncSession, page: BookingPage, *, start_utc: datetime, name: str, email: str,
               consent: bool, ip_hash: Optional[str]) -> tuple[Booking, str]:
    """Create the meeting for a visitor. Returns (booking, manage token). Caller commits."""
    if page.consent_text and not consent:
        raise BookingError("Please accept the consent statement to book.", 422)
    start = mtg.to_utc(start_utc, None)
    _validate_start(page, start)
    await _check_rate(db, page, ip_hash)
    for h in sorted(_hosts(page), key=str):       # fixed order: no deadlock between two visitors
        await mtg.lock_host(db, h)
    host_id = await _choose_host(db, page, start)
    m = MeetingRecord(title=f"{page.title} — {name}"[:300], platform=page.platform,
                      meeting_url=mtg.jitsi_link() if page.platform == "jitsi" else None, host_id=host_id,
                      scheduled_at=start, duration_minutes=page.duration_minutes, status="SCHEDULED",
                      agenda=f"Booked online by {name} <{email}>.", time_zone=page.time_zone, sequence=0,
                      attendees=[{"name": name, "email": email.lower()}])
    db.add(m)
    await db.flush()
    token = secrets.token_urlsafe(24)
    b = Booking(page_id=page.id, meeting_id=m.id, host_id=host_id, visitor_name=name, visitor_email=email.lower(),
                consent_text=page.consent_text if consent else None, manage_token_hash=digest(token), ip_hash=ip_hash,
                created_at=clock.utcnow())
    db.add(b)
    await db.flush()
    await _after_change(db, m)
    return b, token


async def _after_change(db: AsyncSession, m: MeetingRecord, cancelled: bool = False) -> None:
    from app.models.user import User
    from app.services.calendar_sync_service import push_safely
    from app.services.email_mailbox_service import MailboxError

    await push_safely(db, m)
    host = await db.get(User, m.host_id) if m.host_id else None
    if host is not None:
        try:
            await mtg.send_invite(db, m, host, cancelled, None)
        except MailboxError as e:      # booking stands; host sees the meeting without an e-mailed invite
            log.info("booking invite not sent for meeting %s: %s", m.id, e)


async def by_token(db: AsyncSession, token: str) -> tuple[Booking, MeetingRecord, BookingPage]:
    b = (await db.execute(select(Booking).where(Booking.manage_token_hash == digest(token or "")))).scalar_one_or_none()
    if b is None:
        raise BookingError("Booking not found.", 404)
    m = await db.get(MeetingRecord, b.meeting_id)
    page = await db.get(BookingPage, b.page_id)
    return b, m, page


async def cancel(db: AsyncSession, token: str) -> MeetingRecord:
    b, m, page = await by_token(db, token)
    if m.status != "SCHEDULED":
        return m
    m.status, m.sequence = "CANCELLED", (m.sequence or 0) + 1
    await _after_change(db, m, cancelled=True)
    return m


async def reschedule(db: AsyncSession, token: str, start_utc: datetime) -> MeetingRecord:
    b, m, page = await by_token(db, token)
    if m.status != "SCHEDULED":
        raise BookingError("This booking is no longer active.", 409)
    start = mtg.to_utc(start_utc, None)
    _validate_start(page, start)
    for h in sorted(_hosts(page), key=str):
        await mtg.lock_host(db, h)
    await db.refresh(m)
    if b.host_id and b.host_id in _hosts(page) and await _host_free(db, page, b.host_id, start, exclude=m.id):
        host_id = b.host_id                         # keep the same person when they are free
    else:
        host_id = await _choose_host(db, page, start, exclude=m.id)
    if host_id != m.host_id:                         # old host's invitees get a cancellation for the old event
        m.status = "CANCELLED"
        await _after_change(db, m, cancelled=True)
        m.status, m.host_id, b.host_id = "SCHEDULED", host_id, host_id
    m.scheduled_at, m.sequence = start, (m.sequence or 0) + 1
    await _after_change(db, m)
    return m


async def send_due_reminders(db: AsyncSession) -> int:
    """E-mail visitors 24 h before their booking (once), from the host's connected mailbox."""
    from app.models.email_integration import EmailAccount
    from app.services import email_mailbox_service as mbx

    now = clock.utcnow()
    due = (await db.execute(select(Booking, MeetingRecord).join(MeetingRecord, MeetingRecord.id == Booking.meeting_id)
                            .where(Booking.reminder_sent_at.is_(None), MeetingRecord.status == "SCHEDULED",
                                   MeetingRecord.scheduled_at > now.replace(tzinfo=None),
                                   MeetingRecord.scheduled_at <= (now + timedelta(hours=24)).replace(tzinfo=None))
                            .limit(100))).all()
    sent = 0
    for b, m in due:
        accounts = (await db.execute(select(EmailAccount).where(EmailAccount.created_by_id == m.host_id))).scalars().all()
        acc = next((a for a in accounts if mbx.is_connected(a)), None)
        if acc is None:
            continue
        when = mtg.local(m.scheduled_at, m.time_zone)
        try:
            await mbx.send(db, acc, to=[b.visitor_email], cc=[], subject=f"Reminder: {m.title}",
                           body=f"Hello {b.visitor_name},\n\nThis is a reminder of your meeting on "
                                f"{when:%A %d %B %Y at %H:%M} ({m.time_zone}).\n{m.meeting_url or ''}\n",
                           thread=None, sent_by=None, link={"linked_module": "meeting", "linked_object_id": m.id})
        except mbx.MailboxError:
            continue
        b.reminder_sent_at, sent = now, sent + 1
    return sent


async def run_reminders(interval: float = 600.0) -> None:
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await send_due_reminders(db)
                await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("booking reminder tick failed")
        await asyncio.sleep(interval)
