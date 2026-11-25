"""M36.S01.T005 meeting scheduling.

- Times: the API takes a local wall time plus an IANA time zone (or an offset-aware time) and stores UTC.
  A wall time that does not exist (spring-forward gap) is refused; an ambiguous one (fall-back) takes
  the first occurrence. Africa/Nairobi has no DST, but staff and customers abroad do.
- Double booking: a host cannot have two scheduled meetings that overlap (checked under a per-host
  advisory lock, so two simultaneous requests cannot both pass).
- Links: "jitsi" generates a working meeting link (no account needed); Google Meet / Teams / Zoom links
  are pasted by the host (creating them needs the provider's OAuth app: live gate [!]).
- Invites: an iCalendar (RFC 5545) REQUEST/CANCEL with a SEQUENCE that rises on every change, e-mailed
  from the host's connected mailbox, so Google/Outlook calendars update or cancel the same event.
- Calendar feed: a personal, revocable .ics subscription URL (Google/Outlook "add calendar from URL")
  showing the user's meetings; rotating or revoking the token cuts old links off at once.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable, Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import cast, func, literal, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meetings import MeetingCalendarFeed, MeetingRecord

UTC = timezone.utc
DEFAULT_TZ = "Africa/Nairobi"
LINKED_PLATFORMS = ("google_meet", "zoom", "teams", "other")


class MeetingError(ValueError):
    pass


# ── time zones ────────────────────────────────────────────────────────────────

def zone(name: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TZ)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise MeetingError(f"Unknown time zone: {name}") from e


def to_utc(value: datetime, tz_name: Optional[str]) -> datetime:
    """Aware -> UTC. Naive -> wall time in tz_name; a non-existent wall time is refused. Returns naive UTC."""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    tz = zone(tz_name)
    local = value.replace(tzinfo=tz, fold=0)
    back = local.astimezone(UTC).astimezone(tz)
    if back.replace(tzinfo=None) != value:
        raise MeetingError(f"{value:%Y-%m-%d %H:%M} does not exist in {tz.key} (clock change)")
    return local.astimezone(UTC).replace(tzinfo=None)


def local(value_utc: datetime, tz_name: Optional[str]) -> datetime:
    return value_utc.replace(tzinfo=UTC).astimezone(zone(tz_name))


# ── double booking ────────────────────────────────────────────────────────────

def _end(m_start, minutes):
    return m_start + func.make_interval(0, 0, 0, 0, 0, minutes)


async def lock_host(db: AsyncSession, host_id: UUID) -> None:
    key = int(hashlib.sha256(f"meeting-host:{host_id}".encode()).hexdigest()[:15], 16)
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})


def _busy_blocks(host_id: UUID, lo: datetime, hi: datetime):
    """M43.S01.T003/T004: busy time imported from the host's connected Google / Outlook calendar."""
    from app.models.meetings import CalendarBusyBlock
    from app.models.oauth_connection import OAuthConnection
    return select(CalendarBusyBlock).join(OAuthConnection, OAuthConnection.id == CalendarBusyBlock.connection_id).where(
        OAuthConnection.user_id == host_id, OAuthConnection.status == "CONNECTED",
        CalendarBusyBlock.starts_at < hi, CalendarBusyBlock.ends_at > lo)


async def overlapping(db: AsyncSession, host_id: UUID, start: datetime, minutes: int,
                      exclude: Optional[UUID] = None, ignore_calendar: bool = False) -> Optional[MeetingRecord]:
    end = start + timedelta(minutes=minutes)
    q = select(MeetingRecord).where(
        MeetingRecord.host_id == host_id, MeetingRecord.status == "SCHEDULED",
        MeetingRecord.scheduled_at < end, _end(MeetingRecord.scheduled_at, MeetingRecord.duration_minutes) > start)
    if exclude:
        q = q.where(MeetingRecord.id != exclude)
    hit = (await db.execute(q.limit(1))).scalar_one_or_none()
    if hit is not None or ignore_calendar:
        return hit
    block = (await db.execute(_busy_blocks(host_id, start, end).limit(1))).scalar_one_or_none()
    if block is None:
        return None
    # transient (never added to the session): busy time in the host's own calendar, without its private title
    return MeetingRecord(id=block.id, title="Busy in your calendar", scheduled_at=block.starts_at,
                         duration_minutes=int((block.ends_at - block.starts_at).total_seconds() // 60))


async def free_slots(db: AsyncSession, host_id: UUID, day: date, tz_name: str, minutes: int,
                     open_at: time = time(8), close_at: time = time(17), step: int = 30) -> list[dict]:
    """Free start times on `day` (local working hours) for a meeting of `minutes`, DST-safe."""
    tz = zone(tz_name)
    start = datetime.combine(day, open_at, tz)
    close = datetime.combine(day, close_at, tz)
    lo, hi = start.astimezone(UTC).replace(tzinfo=None), close.astimezone(UTC).replace(tzinfo=None)
    busy = (await db.execute(select(MeetingRecord.scheduled_at, MeetingRecord.duration_minutes).where(
        MeetingRecord.host_id == host_id, MeetingRecord.status == "SCHEDULED",
        MeetingRecord.scheduled_at < hi, _end(MeetingRecord.scheduled_at, MeetingRecord.duration_minutes) > lo))).all()
    busy += [(b.starts_at, int((b.ends_at - b.starts_at).total_seconds() // 60))
             for b in (await db.execute(_busy_blocks(host_id, lo, hi))).scalars()]
    out, t = [], lo
    while t + timedelta(minutes=minutes) <= hi:
        t_end = t + timedelta(minutes=minutes)
        if not any(b < t_end and b + timedelta(minutes=d) > t for b, d in busy):
            out.append({"start_utc": t.replace(tzinfo=UTC).isoformat(), "start_local": local(t, tz.key).isoformat()})
        t += timedelta(minutes=step)
    return out


# ── links and invites ─────────────────────────────────────────────────────────

def jitsi_link() -> str:
    return f"https://meet.jit.si/POVU-{secrets.token_urlsafe(12).replace('_', '').replace('-', '')}"


def _esc(v: Any) -> str:
    return str(v or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, b = [], line.encode()
    while len(b) > 73:
        cut = 73
        while cut and (b[cut] & 0xC0) == 0x80:  # never split a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode())
        b = b[cut:]
    out.append(b.decode())
    return "\r\n ".join(out)


def _ics_dt(v: datetime) -> str:
    return v.strftime("%Y%m%dT%H%M%SZ")


def vevent(m: MeetingRecord, organizer: Optional[str], cancelled: bool = False) -> list[str]:
    end = m.scheduled_at + timedelta(minutes=m.duration_minutes)
    lines = [
        "BEGIN:VEVENT", f"UID:{m.id}@povu-erp", f"SEQUENCE:{m.sequence or 0}",
        f"DTSTAMP:{_ics_dt(datetime.now(UTC))}", f"DTSTART:{_ics_dt(m.scheduled_at)}", f"DTEND:{_ics_dt(end)}",
        f"SUMMARY:{_esc(m.title)}", f"STATUS:{'CANCELLED' if cancelled or m.status == 'CANCELLED' else 'CONFIRMED'}",
    ]
    desc = "\n\n".join(x for x in (m.agenda, f"Join: {m.meeting_url}" if m.meeting_url else None) if x)
    if desc:
        lines.append(f"DESCRIPTION:{_esc(desc)}")
    if m.meeting_url:
        lines += [f"URL:{_esc(m.meeting_url)}", f"LOCATION:{_esc(m.meeting_url)}"]
    if organizer:
        lines.append(f"ORGANIZER:mailto:{organizer}")
    for a in m.attendees or []:
        if a.get("email"):
            # CN is a parameter value: quote it and drop quotes/control chars (no parameter or property injection)
            name = "".join(c for c in str(a.get("name") or "") if c != '"' and ord(c) >= 32)
            cn = f';CN="{name}"' if name else ""
            lines.append(f"ATTENDEE{cn};RSVP=TRUE:mailto:{a['email']}")
    lines.append("END:VEVENT")
    return lines


def calendar(events: Iterable[list[str]], method: Optional[str] = None, name: Optional[str] = None) -> str:
    head = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//POVU ERP//Meetings//EN", "CALSCALE:GREGORIAN"]
    if method:
        head.append(f"METHOD:{method}")
    if name:
        head.append(f"X-WR-CALNAME:{_esc(name)}")
    body = [line for ev in events for line in ev]
    return "\r\n".join(_fold(x) for x in head + body + ["END:VCALENDAR"]) + "\r\n"


def attendee_clause(email: str):
    """Exact, case-insensitive match of one invitee e-mail (attendees are stored lower-cased);
    a JSONB containment test, so LIKE wildcards in an address match nothing extra."""
    probe = json.dumps([{"email": (email or "").strip().lower()}])
    return cast(MeetingRecord.attendees, JSONB).op("@>")(cast(literal(probe), JSONB))


async def send_invite(db: AsyncSession, m: MeetingRecord, host: Any, cancelled: bool = False,
                      recipients: Optional[list[str]] = None) -> str:
    """E-mail the iCalendar invite/cancellation from the host's connected mailbox (the ORGANIZER must stay
    the same, so it is always the host's, whoever made the change). `recipients` limits who gets it (e.g. a
    CANCEL for people removed from the meeting). Returns SENT, NO_ATTENDEES or NO_MAILBOX."""
    from app.models.email_integration import EmailAccount
    from app.services import email_mailbox_service as mbx

    to = recipients if recipients is not None else [a["email"] for a in (m.attendees or []) if a.get("email")]
    if not to:
        return "NO_ATTENDEES"
    accounts = (await db.execute(select(EmailAccount).where(EmailAccount.created_by_id == host.id,
                                                           EmailAccount.is_active.is_(True)))).scalars().all()
    acc = next((a for a in accounts if mbx.is_connected(a)), None)
    if acc is None:
        return "NO_MAILBOX"
    method = "CANCEL" if cancelled else "REQUEST"
    ics = calendar([vevent(m, acc.email_address, cancelled)], method=method)
    when = local(m.scheduled_at, m.time_zone)
    verb = "Cancelled" if cancelled else ("Updated" if (m.sequence or 0) > 0 else "Invitation")
    body = (f"{m.title}\n{when:%A %d %B %Y, %H:%M} ({when.tzinfo.key}), {m.duration_minutes} min\n"
            + (f"Join: {m.meeting_url}\n" if m.meeting_url and not cancelled else "")
            + (f"\n{m.agenda}\n" if m.agenda and not cancelled else ""))
    await mbx.send(db, acc, to=to, cc=[], subject=f"{verb}: {m.title}", body=body, thread=None, sent_by=host,
                   link={"linked_module": "customer" if m.customer_id else None, "linked_object_id": m.customer_id,
                         "linked_object_ref": None},
                   calendar=(method, ics))
    return "SENT"


# ── personal calendar feed ────────────────────────────────────────────────────

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def rotate_feed(db: AsyncSession, user_id: UUID) -> str:
    """New subscription token for the user (any older link stops working). Returns the token once."""
    token = secrets.token_urlsafe(32)
    row = await db.get(MeetingCalendarFeed, user_id)
    if row is None:
        db.add(MeetingCalendarFeed(user_id=user_id, token_hash=_digest(token)))
    else:
        row.token_hash, row.created_at = _digest(token), datetime.now(UTC)
    await db.flush()
    return token


async def revoke_feed(db: AsyncSession, user_id: UUID) -> None:
    row = await db.get(MeetingCalendarFeed, user_id)
    if row is not None:
        await db.delete(row)
        await db.flush()


async def feed_ics(db: AsyncSession, token: str) -> Optional[str]:
    from app.models.user import User

    row = (await db.execute(select(MeetingCalendarFeed).where(MeetingCalendarFeed.token_hash == _digest(token)))).scalar_one_or_none()
    if row is None:
        return None
    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)
    mine = or_(MeetingRecord.host_id == user.id, attendee_clause(user.email))
    meetings = (await db.execute(select(MeetingRecord).where(mine, MeetingRecord.scheduled_at >= since)
                                 .order_by(MeetingRecord.scheduled_at.desc()).limit(500))).scalars().all()  # newest kept
    return calendar([vevent(m, None) for m in meetings], name="POVU ERP meetings")
