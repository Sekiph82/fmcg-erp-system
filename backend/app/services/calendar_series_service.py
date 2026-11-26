"""M49.S01.T001 recurring Google / Outlook meetings.

Official contracts used (checked against the public documentation, see CAPABILITY_MATRIX.md):
- Google Calendar API v3 (https://developers.google.com/calendar/api/v3/reference): events.insert/patch with
  ``recurrence: ["RRULE:..."]`` plus start/end ``timeZone``; events.instances (``originalStartTime``) to find one
  occurrence; PATCH / DELETE of an instance id writes an exception / a cancelled occurrence; freeBusy.query
  (POST /freeBusy); ``UNTIL`` must be UTC when the event has a time.
- Microsoft Graph v1.0 (https://learn.microsoft.com/graph/api/resources/patternedrecurrence): event ``recurrence``
  {pattern{type, interval, daysOfWeek, dayOfMonth, index, month, firstDayOfWeek}, range{type, startDate, endDate,
  numberOfOccurrences, recurrenceTimeZone}}; GET /me/events/{id}/instances (``originalStart``); PATCH / DELETE of an
  instance; POST /me/calendar/getSchedule for free/busy. IANA zone names in dateTimeTimeZone: UNVERIFIED for every
  tenant (Graph documents Windows names; the ERP sends IANA names).
- RFC 5545 / RFC 5546 for the e-mailed invitation: one master VEVENT (RRULE, EXDATE) plus RECURRENCE-ID overrides, one
  UID per series, SEQUENCE up on each change.

Model: a series stores the rule and the wall-clock start in its IANA zone, so every occurrence keeps its local time
across DST changes (a wall time inside a spring-forward gap runs after the gap, as RFC 5545 says). Occurrences are
ordinary meeting_records rows (so the existing double-booking, busy-time and reminder logic applies unchanged), tied
to the series by meeting_series_occurrences. They are materialised for MAX_HORIZON_DAYS ahead (a rule with no end is
not expanded further than that; the next edit or ``extend`` run adds the following months).

Edit scopes (Google "this event / this and following / all events"): ``this`` writes an exception for one date,
``all`` rewrites every future non-exception occurrence, ``following`` splits the series (old rule ends the day before,
a new series carries the change) so there is still one UID per series and no duplicate invitation.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from dateutil.rrule import rrulestr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import settings
from app.models.m49_calendar_mail import MeetingSeries, MeetingSeriesCalendarLink, MeetingSeriesOccurrence
from app.models.meetings import MeetingRecord
from app.services import meeting_service as mtg

UTC = timezone.utc
MAX_HORIZON_DAYS = 366
MAX_OCCURRENCES = 400
_DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_GRAPH_DAY = dict(zip(_DAYS, ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")))
_BYDAY = re.compile(r"^(-1|\+?[1-4])?(MO|TU|WE|TH|FR|SA|SU)$")
_UNTIL = re.compile(r"^\d{8}(T\d{6})?$")
_ALLOWED = {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYMONTH", "COUNT", "UNTIL", "WKST"}
RESPONSES = ("accepted", "declined", "tentative")


class SeriesError(ValueError):
    pass


class SeriesConflict(SeriesError):
    def __init__(self, items: list[dict]):
        super().__init__("One or more occurrences overlap another meeting of the host.")
        self.items = items


# ── rule ──────────────────────────────────────────────────────────────────────

def _parse(rule: str) -> dict:
    s = (rule or "").strip()
    s = s[6:] if s.upper().startswith("RRULE:") else s
    out: dict = {}
    for part in filter(None, s.split(";")):
        k, _, v = part.partition("=")
        k = k.strip().upper()
        if k not in _ALLOWED or not v or k in out:
            raise SeriesError(f"Unsupported or repeated recurrence part: {k or part}")
        out[k] = v.strip().upper()
    return out


def _int(d: dict, key: str, lo: int, hi: int, default: Optional[int] = None) -> Optional[int]:
    if key not in d:
        return default
    try:
        n = int(d[key])
    except ValueError:
        raise SeriesError(f"{key} must be a number") from None
    if not lo <= n <= hi:
        raise SeriesError(f"{key} must be between {lo} and {hi}")
    return n


def normalize_rrule(rule: str, start_local: datetime) -> str:
    """Validate the supported subset (the part both Google and Graph can express) and make it explicit: a weekly
    rule lists its weekdays, a monthly one its day, a yearly one its month, so the provider never guesses."""
    d = _parse(rule)
    freq = d.get("FREQ")
    if freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        raise SeriesError("FREQ must be DAILY, WEEKLY, MONTHLY or YEARLY")
    out: dict = {"FREQ": freq}
    interval = _int(d, "INTERVAL", 1, 99, 1)
    if interval != 1:
        out["INTERVAL"] = str(interval)
    days = [t for t in d.get("BYDAY", "").split(",") if t]
    for t in days:
        if not _BYDAY.match(t):
            raise SeriesError(f"Bad BYDAY value: {t}")
    if freq == "DAILY" and (days or "BYMONTHDAY" in d or "BYMONTH" in d):
        raise SeriesError("A daily rule takes no BYDAY / BYMONTHDAY / BYMONTH")
    if freq == "WEEKLY":
        if "BYMONTHDAY" in d or "BYMONTH" in d or any(t[0] in "+-123456789" for t in days):
            raise SeriesError("A weekly rule takes plain weekdays only")
        days = days or [_DAYS[start_local.weekday()]]
        out["BYDAY"] = ",".join(sorted(set(days), key=_DAYS.index))
    if freq == "MONTHLY":
        if "BYMONTH" in d:
            raise SeriesError("A monthly rule takes no BYMONTH")
        if days:
            if len(days) != 1 or not _BYDAY.match(days[0]).group(1) or "BYMONTHDAY" in d:
                raise SeriesError("Monthly by weekday needs one value like 2TU or -1FR and no BYMONTHDAY")
            out["BYDAY"] = days[0]
        else:
            out["BYMONTHDAY"] = str(_int(d, "BYMONTHDAY", 1, 31, start_local.day))
    if freq == "YEARLY":
        if days:
            raise SeriesError("A yearly rule takes no BYDAY")
        out["BYMONTH"] = str(_int(d, "BYMONTH", 1, 12, start_local.month))
        out["BYMONTHDAY"] = str(_int(d, "BYMONTHDAY", 1, 31, start_local.day))
    if "COUNT" in d and "UNTIL" in d:
        raise SeriesError("Use COUNT or UNTIL, not both")
    if "COUNT" in d:
        out["COUNT"] = str(_int(d, "COUNT", 1, MAX_OCCURRENCES))
    if "UNTIL" in d:
        u = d["UNTIL"]
        if not _UNTIL.match(u):
            raise SeriesError("UNTIL must be a local date (YYYYMMDD) or YYYYMMDDTHHMMSS")
        u = u if "T" in u else u + "T235959"
        if datetime.strptime(u, "%Y%m%dT%H%M%S") < start_local:
            raise SeriesError("UNTIL is before the first occurrence")
        out["UNTIL"] = u
    return ";".join(f"{k}={out[k]}" for k in ("FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYMONTH", "COUNT", "UNTIL") if k in out)


def _utc(local_naive: datetime, tz_name: str) -> datetime:
    """Wall time -> naive UTC; a time inside a clock-change gap runs after the gap, an ambiguous one takes the first."""
    return local_naive.replace(tzinfo=mtg.zone(tz_name)).astimezone(UTC).replace(tzinfo=None)


def slots(rule: str, start_local: datetime, tz_name: str, horizon_utc: datetime) -> list[datetime]:
    """Wall-clock occurrence starts (naive local) up to the horizon."""
    out: list[datetime] = []
    for dt in rrulestr(rule, dtstart=start_local):
        if len(out) >= MAX_OCCURRENCES or _utc(dt, tz_name) > horizon_utc:
            break
        out.append(dt)
    return out


def _horizon(series: MeetingSeries) -> datetime:
    now = clock.utcnow().replace(tzinfo=None)
    return max(now, _utc(series.start_local, series.time_zone)) + timedelta(days=MAX_HORIZON_DAYS)


def provider_rrule(series: MeetingSeries) -> str:
    """Rule text for Google / iCalendar: UNTIL as UTC (required when the event has a time)."""
    d = _parse(series.rrule)
    if "UNTIL" in d:
        u = _utc(datetime.strptime(d["UNTIL"], "%Y%m%dT%H%M%S"), series.time_zone)
        d["UNTIL"] = u.strftime("%Y%m%dT%H%M%SZ")
    return ";".join(f"{k}={v}" for k, v in d.items())


def graph_recurrence(series: MeetingSeries) -> dict:
    d = _parse(series.rrule)
    start = series.start_local.date()
    pattern: dict = {"interval": int(d.get("INTERVAL", "1"))}
    f = d["FREQ"]
    if f == "DAILY":
        pattern["type"] = "daily"
    elif f == "WEEKLY":
        pattern.update(type="weekly", daysOfWeek=[_GRAPH_DAY[x] for x in d["BYDAY"].split(",")], firstDayOfWeek="monday")
    elif f == "MONTHLY" and "BYDAY" in d:
        m = _BYDAY.match(d["BYDAY"])
        n = int(m.group(1))
        pattern.update(type="relativeMonthly", daysOfWeek=[_GRAPH_DAY[m.group(2)]], firstDayOfWeek="monday",
                       index={1: "first", 2: "second", 3: "third", 4: "fourth", -1: "last"}.get(n, "last"))
    elif f == "MONTHLY":
        pattern.update(type="absoluteMonthly", dayOfMonth=int(d["BYMONTHDAY"]))
    else:
        pattern.update(type="absoluteYearly", month=int(d["BYMONTH"]), dayOfMonth=int(d["BYMONTHDAY"]))
    rng: dict = {"startDate": start.isoformat(), "recurrenceTimeZone": series.time_zone}
    if "COUNT" in d:
        rng.update(type="numbered", numberOfOccurrences=int(d["COUNT"]))
    elif "UNTIL" in d:
        rng.update(type="endDate", endDate=datetime.strptime(d["UNTIL"], "%Y%m%dT%H%M%S").date().isoformat())
    else:
        rng["type"] = "noEnd"
    return {"pattern": pattern, "range": rng}


# ── create / materialise ──────────────────────────────────────────────────────

def _wall(series: MeetingSeries, d: str) -> datetime:
    return datetime.combine(date.fromisoformat(d), series.start_local.time())


def _attendee_list(items: Optional[list], old: Optional[list] = None) -> list[dict]:
    prev = {(a.get("email") or "").lower(): a.get("response") for a in old or []}
    out = []
    for a in items or []:
        email = str(a["email"]).lower()
        row = {"email": email, **({"name": a["name"]} if a.get("name") else {})}
        if prev.get(email):
            row["response"] = prev[email]
        out.append(row)
    return out


async def _occ_rows(db: AsyncSession, series: MeetingSeries) -> list[tuple[MeetingSeriesOccurrence, MeetingRecord]]:
    rows = (await db.execute(select(MeetingSeriesOccurrence, MeetingRecord).join(
        MeetingRecord, MeetingRecord.id == MeetingSeriesOccurrence.meeting_id).where(
        MeetingSeriesOccurrence.series_id == series.id).order_by(MeetingSeriesOccurrence.occ_date))).all()
    return [(o, m) for o, m in rows]


def _conflict_item(other: MeetingRecord, wanted: datetime) -> dict:
    return {"wanted_start": wanted.replace(tzinfo=UTC).isoformat(), "conflicts_with": other.title,
            "at": other.scheduled_at.replace(tzinfo=UTC).isoformat()}


async def sync_occurrences(db: AsyncSession, series: MeetingSeries) -> dict:
    """Make the occurrence rows match the rule: add missing dates, move future non-exception ones, drop future ones
    the rule no longer produces. Exceptions are never touched. Refuses the whole change on a double booking."""
    now = clock.utcnow().replace(tzinfo=None)
    await mtg.lock_host(db, series.host_id)
    want = {dt.date().isoformat(): _utc(dt, series.time_zone)
            for dt in slots(series.rrule, series.start_local, series.time_zone, _horizon(series))}
    have = {o.occ_date: (o, m) for o, m in await _occ_rows(db, series)}
    conflicts: list[dict] = []
    for d, start in want.items():
        o_m = have.get(d)
        if o_m is None or (not o_m[0].is_exception and o_m[1].status == "SCHEDULED" and o_m[1].scheduled_at >= now
                           and (o_m[1].scheduled_at, o_m[1].duration_minutes) != (start, series.duration_minutes)):
            if o_m is None and start < now:
                continue                                   # never create history
            other = await mtg.overlapping(db, series.host_id, start, series.duration_minutes,
                                          exclude=o_m[1].id if o_m else None)
            if other is not None:
                conflicts.append(_conflict_item(other, start))
    if conflicts:
        raise SeriesConflict(conflicts[:5])
    created = updated = removed = 0
    for d, start in want.items():
        o_m = have.get(d)
        if o_m is None:
            if start < now:
                continue
            m = MeetingRecord(title=series.title, platform=series.platform, meeting_url=series.meeting_url,
                              host_id=series.host_id, customer_id=series.customer_id, scheduled_at=start,
                              duration_minutes=series.duration_minutes, status="SCHEDULED", agenda=series.agenda,
                              attendees=_attendee_list(series.attendees), time_zone=series.time_zone, sequence=0)
            db.add(m)
            await db.flush()
            db.add(MeetingSeriesOccurrence(series_id=series.id, meeting_id=m.id, occ_date=d))
            created += 1
        else:
            o, m = o_m
            if o.is_exception or m.status != "SCHEDULED" or m.scheduled_at < now:
                continue
            new = dict(title=series.title, platform=series.platform, meeting_url=series.meeting_url, agenda=series.agenda,
                       scheduled_at=start, duration_minutes=series.duration_minutes, time_zone=series.time_zone,
                       attendees=_attendee_list(series.attendees, m.attendees))
            if any(getattr(m, k) != v for k, v in new.items()):
                for k, v in new.items():
                    setattr(m, k, v)
                m.sequence = (m.sequence or 0) + 1
                updated += 1
    for d, (o, m) in have.items():
        if d not in want and not o.is_exception and m.status == "SCHEDULED" and m.scheduled_at >= now:
            await db.delete(m)                              # cascades the occurrence row
            removed += 1
    await db.flush()
    return {"created": created, "updated": updated, "removed": removed}


async def create_series(db: AsyncSession, host: Any, *, title: str, platform: str, meeting_url: Optional[str],
                        start: datetime, time_zone: str, duration_minutes: int, rrule: str,
                        agenda: Optional[str], attendees: list[dict], customer_id: Optional[UUID]) -> MeetingSeries:
    tz = mtg.zone(time_zone).key
    if start.tzinfo is not None:
        start = start.astimezone(mtg.zone(tz)).replace(tzinfo=None)
    try:
        mtg.to_utc(start, tz)                               # first occurrence must exist on the wall clock
        rule = normalize_rrule(rrule, start)
    except mtg.MeetingError as e:
        raise SeriesError(str(e)) from None
    url = meeting_url or (mtg.jitsi_link() if platform == "jitsi" else None)
    series = MeetingSeries(host_id=host.id, customer_id=customer_id, title=title, platform=platform, meeting_url=url,
                           time_zone=tz, start_local=start, duration_minutes=duration_minutes, rrule=rule,
                           agenda=agenda, attendees=_attendee_list(attendees), status="ACTIVE", sequence=0)
    db.add(series)
    await db.flush()
    await sync_occurrences(db, series)
    return series


# ── edit / cancel ─────────────────────────────────────────────────────────────

async def _occurrence(db: AsyncSession, series: MeetingSeries, occ_date: Optional[str]):
    if not occ_date:
        raise SeriesError("occurrence_date is required for this scope")
    for o, m in await _occ_rows(db, series):
        if o.occ_date == occ_date:
            return o, m
    raise SeriesError(f"No occurrence on {occ_date}")


def _truncate(series: MeetingSeries, occ_date: str, before_count: int) -> None:
    d = _parse(series.rrule)
    if "COUNT" in d:
        d["COUNT"] = str(before_count)
    else:
        d.pop("COUNT", None)
        d["UNTIL"] = (date.fromisoformat(occ_date) - timedelta(days=1)).strftime("%Y%m%d") + "T235959"
    series.rrule = ";".join(f"{k}={v}" for k, v in d.items())


def _before_count(series: MeetingSeries, occ_date: str) -> int:
    n = 0
    for dt in rrulestr(series.rrule, dtstart=series.start_local):
        if dt.date().isoformat() >= occ_date or n > MAX_OCCURRENCES:
            break
        n += 1
    return n


def _apply_fields(series: MeetingSeries, ch: dict) -> None:
    for k in ("title", "meeting_url", "agenda", "duration_minutes"):
        if ch.get(k) is not None:
            setattr(series, k, ch[k])
    if ch.get("attendees") is not None:
        series.attendees = _attendee_list(ch["attendees"], series.attendees)
    if ch.get("start") is not None:
        s = ch["start"]
        s = s.astimezone(mtg.zone(series.time_zone)).replace(tzinfo=None) if s.tzinfo else s
        series.start_local = datetime.combine(series.start_local.date(), s.time())
    if ch.get("rrule") is not None:
        series.rrule = normalize_rrule(ch["rrule"], series.start_local)


async def edit(db: AsyncSession, series: MeetingSeries, scope: str, occ_date: Optional[str], ch: dict) -> dict:
    """Apply a change with Google-style scope. Returns {"series": [affected series ids], "removed": [emails]}."""
    if series.status != "ACTIVE":
        raise SeriesError("The series is cancelled.")
    old_emails = {a["email"] for a in series.attendees or []}
    if scope == "this":
        if ch.get("rrule") is not None or ch.get("time_zone"):
            raise SeriesError("The rule and time zone change the whole series, not one occurrence.")
        o, m = await _occurrence(db, series, occ_date)
        if m.status != "SCHEDULED":
            raise SeriesError("That occurrence is cancelled.")
        await mtg.lock_host(db, series.host_id)
        start, minutes = m.scheduled_at, ch.get("duration_minutes") or m.duration_minutes
        if ch.get("start") is not None:
            try:
                start = mtg.to_utc(ch["start"], series.time_zone)
            except mtg.MeetingError as e:
                raise SeriesError(str(e)) from None
        if (start, minutes) != (m.scheduled_at, m.duration_minutes):
            other = await mtg.overlapping(db, series.host_id, start, minutes, exclude=m.id)
            if other is not None:
                raise SeriesConflict([_conflict_item(other, start)])
        for k in ("title", "meeting_url", "agenda"):
            if ch.get(k) is not None:
                setattr(m, k, ch[k])
        if ch.get("attendees") is not None:
            m.attendees = _attendee_list(ch["attendees"], m.attendees)
        m.scheduled_at, m.duration_minutes = start, minutes
        m.sequence = (m.sequence or 0) + 1
        o.is_exception = True
        series.sequence += 1
        await db.flush()
        return {"series": [series.id], "removed": []}
    if ch.get("time_zone"):
        series.time_zone = mtg.zone(ch["time_zone"]).key
    target = series
    if scope == "following":
        o, _ = await _occurrence(db, series, occ_date)
        if occ_date > series.start_local.date().isoformat():
            before = _before_count(series, occ_date)
            target = MeetingSeries(host_id=series.host_id, customer_id=series.customer_id, title=series.title,
                                   platform=series.platform, meeting_url=series.meeting_url, time_zone=series.time_zone,
                                   start_local=datetime.combine(date.fromisoformat(occ_date), series.start_local.time()),
                                   duration_minutes=series.duration_minutes, rrule=series.rrule, agenda=series.agenda,
                                   attendees=list(series.attendees or []), status="ACTIVE", sequence=0)
            if "COUNT" in _parse(series.rrule):
                target.rrule = series.rrule.replace(f"COUNT={_parse(series.rrule)['COUNT']}",
                                                    f"COUNT={int(_parse(series.rrule)['COUNT']) - before}")
            db.add(target)
            await db.flush()
            _truncate(series, occ_date, before)
            series.sequence += 1
            for oo, _m in await _occ_rows(db, series):
                if oo.occ_date >= occ_date:
                    oo.series_id = target.id
            await db.flush()
    _apply_fields(target, ch)
    if target is series:
        series.sequence += 1
    await sync_occurrences(db, target)
    if target is not series:
        await sync_occurrences(db, series)
    removed = sorted(old_emails - {a["email"] for a in target.attendees or []})
    return {"series": [series.id] + ([target.id] if target is not series else []), "removed": removed}


async def cancel(db: AsyncSession, series: MeetingSeries, scope: str, occ_date: Optional[str]) -> dict:
    if series.status != "ACTIVE":
        return {"series": [], "already": True}
    now = clock.utcnow().replace(tzinfo=None)
    if scope == "this":
        o, m = await _occurrence(db, series, occ_date)
        if m.status == "CANCELLED":
            return {"series": [], "already": True}
        m.status, m.sequence, o.is_exception = "CANCELLED", (m.sequence or 0) + 1, True
        series.sequence += 1
    elif scope == "following" and occ_date and occ_date > series.start_local.date().isoformat():
        await _occurrence(db, series, occ_date)
        _truncate(series, occ_date, _before_count(series, occ_date))
        series.sequence += 1
        for o, m in await _occ_rows(db, series):
            if o.occ_date >= occ_date:
                if m.status == "SCHEDULED":
                    m.status, m.sequence = "CANCELLED", (m.sequence or 0) + 1
                await db.delete(o)                         # detached: kept as a cancelled meeting, outside the series
    else:                                                  # all (or following from the first date)
        series.status, series.sequence = "CANCELLED", series.sequence + 1
        for o, m in await _occ_rows(db, series):
            if m.status == "SCHEDULED" and m.scheduled_at >= now:
                m.status, m.sequence = "CANCELLED", (m.sequence or 0) + 1
    await db.flush()
    return {"series": [series.id], "already": False}


# ── RSVP ──────────────────────────────────────────────────────────────────────

async def rsvp(db: AsyncSession, series: MeetingSeries, email: str, response: str, occ_date: Optional[str]) -> int:
    """Record an invitee's answer for one occurrence or all future ones. Returns the number of meetings updated."""
    email = email.strip().lower()
    if response not in RESPONSES:
        raise SeriesError("response must be accepted, declined or tentative")
    if email not in {a["email"] for a in series.attendees or []}:
        raise SeriesError(f"{email} is not an invitee of this series")
    now = clock.utcnow().replace(tzinfo=None)
    n = 0
    for o, m in await _occ_rows(db, series):
        if occ_date and o.occ_date != occ_date or (not occ_date and (m.scheduled_at < now or m.status != "SCHEDULED")):
            continue
        m.attendees = [({**a, "response": response} if a.get("email") == email else a) for a in m.attendees or []]
        n += 1
    if not occ_date:
        series.attendees = [({**a, "response": response} if a["email"] == email else a) for a in series.attendees]
    if occ_date and n == 0:
        raise SeriesError(f"No occurrence on {occ_date}")
    await db.flush()
    return n


_PARTSTAT = {"ACCEPTED": "accepted", "DECLINED": "declined", "TENTATIVE": "tentative"}


def parse_reply(ics: str) -> Optional[dict]:
    """Minimal RFC 5546 METHOD:REPLY reader -> {series_id, occ_date|None, email, response}."""
    text = re.sub(r"\r?\n[ \t]", "", ics)
    if not re.search(r"^METHOD:REPLY", text, re.M | re.I):
        return None
    uid = re.search(r"^UID:([0-9a-f-]{36})@povu-erp-series", text, re.M | re.I)
    att = re.search(r"^ATTENDEE([^:\n]*):mailto:(\S+)", text, re.M | re.I)
    ps = re.search(r"PARTSTAT=([A-Z-]+)", att.group(1), re.I) if att else None
    if not (uid and att and ps and ps.group(1).upper() in _PARTSTAT):
        return None
    rid = re.search(r"^RECURRENCE-ID[^:\n]*:(\d{4})(\d{2})(\d{2})", text, re.M | re.I)
    return {"series_id": uid.group(1), "email": att.group(2).strip().lower(), "response": _PARTSTAT[ps.group(1).upper()],
            "occ_date": f"{rid.group(1)}-{rid.group(2)}-{rid.group(3)}" if rid else None}


async def apply_reply(db: AsyncSession, ics: str, from_email: str) -> bool:
    """Inbound iCalendar REPLY mail -> RSVP. The ATTENDEE must be the person who sent the mail."""
    r = parse_reply(ics)
    if r is None or r["email"] != (from_email or "").lower():
        return False
    series = await db.get(MeetingSeries, UUID(r["series_id"]))
    if series is None:
        return False
    try:
        await rsvp(db, series, r["email"], r["response"], r["occ_date"])
    except SeriesError:
        return False
    return True


# ── invitations (one per change) ──────────────────────────────────────────────

def _tzdt(prop: str, naive: datetime, tz: str) -> str:
    return f"{prop};TZID={tz}:{naive:%Y%m%dT%H%M%S}"


def series_events(series: MeetingSeries, occs: list, organizer: Optional[str], cancelled: bool = False) -> list[list[str]]:
    tz, uid = series.time_zone, f"{series.id}@povu-erp-series"
    stamp = f"DTSTAMP:{mtg._ics_dt(datetime.now(UTC))}"
    dur = timedelta(minutes=series.duration_minutes)
    head = ["BEGIN:VEVENT", f"UID:{uid}", f"SEQUENCE:{series.sequence}", stamp,
            _tzdt("DTSTART", series.start_local, tz), _tzdt("DTEND", series.start_local + dur, tz),
            f"RRULE:{provider_rrule(series)}", f"SUMMARY:{mtg._esc(series.title)}",
            f"STATUS:{'CANCELLED' if cancelled or series.status == 'CANCELLED' else 'CONFIRMED'}"]
    for o, m in occs:
        if o.is_exception and m.status == "CANCELLED":
            head.append(_tzdt("EXDATE", _wall(series, o.occ_date), tz))
    desc = "\n\n".join(x for x in (series.agenda, f"Join: {series.meeting_url}" if series.meeting_url else None) if x)
    if desc:
        head.append(f"DESCRIPTION:{mtg._esc(desc)}")
    if series.meeting_url:
        head += [f"URL:{mtg._esc(series.meeting_url)}", f"LOCATION:{mtg._esc(series.meeting_url)}"]
    people = []
    if organizer:
        people.append(f"ORGANIZER:mailto:{organizer}")
    for a in series.attendees or []:
        name = "".join(c for c in str(a.get("name") or "") if c != '"' and ord(c) >= 32)
        cn = ';CN="' + name + '"' if name else ""
        people.append(f"ATTENDEE{cn};RSVP=TRUE:mailto:{a['email']}")
    events = [head + people + ["END:VEVENT"]]
    for o, m in occs:
        if o.is_exception and m.status == "SCHEDULED":
            s = mtg.local(m.scheduled_at, tz).replace(tzinfo=None)
            events.append(["BEGIN:VEVENT", f"UID:{uid}", _tzdt("RECURRENCE-ID", _wall(series, o.occ_date), tz),
                           f"SEQUENCE:{series.sequence}", stamp, _tzdt("DTSTART", s, tz),
                           _tzdt("DTEND", s + timedelta(minutes=m.duration_minutes), tz),
                           f"SUMMARY:{mtg._esc(m.title)}", "STATUS:CONFIRMED", *people, "END:VEVENT"])
    return events


async def send_invite(db: AsyncSession, series: MeetingSeries, host: Any, *, cancelled: bool = False,
                      recipients: Optional[list[str]] = None) -> str:
    """One calendar invitation (or cancellation) per change of the series, from the host's mailbox. Returns SENT,
    ALREADY_SENT, NO_ATTENDEES or NO_MAILBOX."""
    from app.models.email_integration import EmailAccount
    from app.services import email_mailbox_service as mbx

    to = recipients if recipients is not None else [a["email"] for a in series.attendees or []]
    if not to:
        return "NO_ATTENDEES"
    if recipients is None and not cancelled and series.invited_sequence is not None \
            and series.invited_sequence >= series.sequence:
        return "ALREADY_SENT"
    accounts = (await db.execute(select(EmailAccount).where(EmailAccount.created_by_id == host.id,
                                                           EmailAccount.is_active.is_(True)))).scalars().all()
    acc = next((a for a in accounts if mbx.is_connected(a)), None)
    if acc is None:
        return "NO_MAILBOX"
    method = "CANCEL" if cancelled else "REQUEST"
    ics = mtg.calendar(series_events(series, await _occ_rows(db, series), acc.email_address, cancelled), method=method)
    when = mtg.local(series.start_local.replace(tzinfo=mtg.zone(series.time_zone)).astimezone(UTC).replace(tzinfo=None),
                     series.time_zone)
    verb = "Cancelled" if cancelled else ("Updated" if series.sequence > 0 else "Invitation")
    body = (f"{series.title} (recurring)\nFirst: {when:%A %d %B %Y, %H:%M} ({series.time_zone}), {series.duration_minutes} min\n"
            f"Repeats: {series.rrule}\n" + (f"Join: {series.meeting_url}\n" if series.meeting_url and not cancelled else ""))
    await mbx.send(db, acc, to=to, cc=[], subject=f"{verb}: {series.title}", body=body, thread=None, sent_by=host,
                   link={"linked_module": "customer" if series.customer_id else None,
                         "linked_object_id": series.customer_id, "linked_object_ref": None}, calendar=(method, ics))
    if recipients is None:
        series.invited_sequence = series.sequence
    return "SENT"


# ── free / busy ───────────────────────────────────────────────────────────────

async def free_busy(db: AsyncSession, host_id: UUID, lo: datetime, hi: datetime) -> dict:
    """Busy intervals (naive UTC) of the host: scheduled ERP meetings plus the connected calendar's own busy time
    (provider freeBusy / getSchedule queried now; imported busy blocks when the provider is unreachable)."""
    from app.services import calendar_sync_service as cal
    from app.services import oauth_service as oauth

    erp = (await db.execute(select(MeetingRecord).where(
        MeetingRecord.host_id == host_id, MeetingRecord.status == "SCHEDULED",
        MeetingRecord.scheduled_at < hi, MeetingRecord.scheduled_at >= lo - timedelta(hours=8)))).scalars().all()
    busy = [{"start": m.scheduled_at, "end": m.scheduled_at + timedelta(minutes=m.duration_minutes), "source": "erp"}
            for m in erp if m.scheduled_at + timedelta(minutes=m.duration_minutes) > lo]
    provider, note = [], None
    conn = await cal._host_calendar(db, host_id)
    if conn is not None:
        try:
            if conn.provider == "google":
                r = await cal._call(db, conn, "POST", settings.GOOGLE_CALENDAR_API_URL.rstrip("/") + "/freeBusy",
                                    json={"timeMin": lo.replace(tzinfo=UTC).isoformat(), "timeMax": hi.replace(tzinfo=UTC).isoformat(),
                                          "items": [{"id": "primary"}]})
                if r.status_code != 200:
                    raise cal.CalendarApiError(f"freeBusy failed ({r.status_code}).")
                for b in (r.json().get("calendars", {}).get("primary", {}) or {}).get("busy", []):
                    provider.append((cal._naive_utc(datetime.fromisoformat(b["start"].replace("Z", "+00:00"))),
                                     cal._naive_utc(datetime.fromisoformat(b["end"].replace("Z", "+00:00")))))
            else:
                r = await cal._call(db, conn, "POST", settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + "/me/calendar/getSchedule",
                                    json={"schedules": [conn.account_email], "availabilityViewInterval": 30,
                                          "startTime": {"dateTime": lo.isoformat(), "timeZone": "UTC"},
                                          "endTime": {"dateTime": hi.isoformat(), "timeZone": "UTC"}})
                if r.status_code != 200:
                    raise cal.CalendarApiError(f"getSchedule failed ({r.status_code}).")
                for v in r.json().get("value", []):
                    for it in v.get("scheduleItems", []):
                        if it.get("status") in ("busy", "oof", "tentative"):
                            provider.append((cal._parse_graph_time(it["start"]), cal._parse_graph_time(it["end"])))
        except (oauth.OAuthError, cal.CalendarApiError) as e:
            note = f"The calendar provider could not be asked: {e}"
            from app.services.meeting_service import _busy_blocks
            provider = [(b.starts_at, b.ends_at) for b in (await db.execute(_busy_blocks(host_id, lo, hi))).scalars()]
    busy += [{"start": s, "end": e, "source": conn.provider} for s, e in provider]
    busy.sort(key=lambda b: b["start"])
    merged: list[list] = []
    for b in busy:
        if merged and b["start"] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b["end"])
        else:
            merged.append([b["start"], b["end"]])
    iso = lambda v: v.replace(tzinfo=UTC).isoformat()  # noqa: E731
    return {"busy": [{"start": iso(s), "end": iso(e)} for s, e in merged],
            "sources": [{"start": iso(b["start"]), "end": iso(b["end"]), "source": b["source"]} for b in busy],
            "provider": conn.provider if conn else None, "note": note}


# ── provider push (series master + exceptions) ────────────────────────────────

def _google_series_body(series: MeetingSeries) -> dict:
    tz, start = series.time_zone, series.start_local
    return {"summary": series.title, "description": (series.agenda or "")[:4000], "location": series.meeting_url or "",
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": (start + timedelta(minutes=series.duration_minutes)).isoformat(), "timeZone": tz},
            "recurrence": [f"RRULE:{provider_rrule(series)}"],
            "extendedProperties": {"private": {"povuSeriesId": str(series.id)}}}


def _graph_series_body(series: MeetingSeries) -> dict:
    tz, start = series.time_zone, series.start_local
    return {"subject": series.title, "body": {"contentType": "text", "content": (series.agenda or "")[:4000]},
            "location": {"displayName": series.meeting_url or ""},
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": (start + timedelta(minutes=series.duration_minutes)).isoformat(), "timeZone": tz},
            "recurrence": graph_recurrence(series), "transactionId": f"povu-series-{series.id}"}


async def _instance_id(db, conn, base: str, ext_id: str, series: MeetingSeries, occ_date: str) -> Optional[str]:
    """The provider's id for one occurrence, found through its instances list (Google events.instances / Graph)."""
    from app.services import calendar_sync_service as cal
    orig = _utc(_wall(series, occ_date), series.time_zone)
    lo, hi = orig - timedelta(days=2), orig + timedelta(days=2)
    google = conn.provider == "google"
    params = ({"timeMin": lo.replace(tzinfo=UTC).isoformat(), "timeMax": hi.replace(tzinfo=UTC).isoformat(), "showDeleted": "false"}
              if google else {"startDateTime": lo.isoformat() + "Z", "endDateTime": hi.isoformat() + "Z"})
    r = await cal._call(db, conn, "GET", f"{base}/{ext_id}/instances", params=params,
                        headers={} if google else {"Prefer": 'outlook.timezone="UTC"'})
    if r.status_code != 200:
        raise cal.CalendarApiError(f"Calendar instances failed ({r.status_code}).")
    for it in r.json().get("items" if google else "value", []):
        o = it.get("originalStartTime") if google else {"dateTime": it.get("originalStart")}
        if not o or not o.get("dateTime"):
            continue
        raw = o["dateTime"]
        got = cal._naive_utc(datetime.fromisoformat(raw.replace("Z", "+00:00"))) if google or raw.endswith("Z") or "+" in raw[10:] \
            else datetime.fromisoformat(raw.split(".")[0])
        if got == orig:
            return it["id"]
    return None


async def push_series(db: AsyncSession, series: MeetingSeries, conn) -> str:
    from app.services import calendar_sync_service as cal

    link = (await db.execute(select(MeetingSeriesCalendarLink).where(
        MeetingSeriesCalendarLink.series_id == series.id, MeetingSeriesCalendarLink.connection_id == conn.id))).scalar_one_or_none()
    if link is None:
        if series.status != "ACTIVE":
            return "SKIPPED"
        link = MeetingSeriesCalendarLink(series_id=series.id, connection_id=conn.id)
        db.add(link)
        await db.flush()
    base, google = cal._cal_base(conn), conn.provider == "google"
    if link.pushed_sequence != series.sequence or not link.external_event_id:
        if series.status != "ACTIVE":
            if link.external_event_id:
                r = await cal._call(db, conn, "DELETE", f"{base}/{link.external_event_id}",
                                    params={"sendUpdates": "none"} if google else None)
                if r.status_code not in (200, 204, 404, 410):
                    raise cal.CalendarApiError(f"Calendar delete failed ({r.status_code}).")
            link.pushed_sequence = series.sequence
            return "CANCELLED"
        body = _google_series_body(series) if google else _graph_series_body(series)
        params = {"sendUpdates": "none"} if google else None
        r = None
        if link.external_event_id:
            r = await cal._call(db, conn, "PATCH", f"{base}/{link.external_event_id}", json=body, params=params)
            if r.status_code in (404, 410):
                link.external_event_id = None
        if not link.external_event_id:
            r = await cal._call(db, conn, "POST", base, json=body, params=params)
        if r.status_code not in (200, 201):
            raise cal.CalendarApiError(f"Calendar write failed ({r.status_code}).")
        link.external_event_id = r.json().get("id")
        link.pushed_sequence, link.updated_at = series.sequence, clock.utcnow()
    if series.status == "ACTIVE":
        for o, m in await _occ_rows(db, series):
            if not o.is_exception or o.exc_pushed_sequence == (m.sequence or 0):
                continue
            iid = await _instance_id(db, conn, base, link.external_event_id, series, o.occ_date)
            if iid is None:
                o.exc_pushed_sequence = m.sequence or 0     # provider no longer has that date
                continue
            if m.status == "CANCELLED":
                r = await cal._call(db, conn, "DELETE", f"{base}/{iid}", params={"sendUpdates": "none"} if google else None)
                if r.status_code not in (200, 204, 404, 410):
                    raise cal.CalendarApiError(f"Calendar instance delete failed ({r.status_code}).")
            else:
                end = m.scheduled_at + timedelta(minutes=m.duration_minutes)
                tz = series.time_zone
                s_l, e_l = mtg.local(m.scheduled_at, tz).replace(tzinfo=None), mtg.local(end, tz).replace(tzinfo=None)
                body = ({"summary": m.title, "start": {"dateTime": s_l.isoformat(), "timeZone": tz},
                         "end": {"dateTime": e_l.isoformat(), "timeZone": tz}} if google else
                        {"subject": m.title, "start": {"dateTime": s_l.isoformat(), "timeZone": tz},
                         "end": {"dateTime": e_l.isoformat(), "timeZone": tz}})
                r = await cal._call(db, conn, "PATCH", f"{base}/{iid}", json=body,
                                    params={"sendUpdates": "none"} if google else None)
                if r.status_code != 200:
                    raise cal.CalendarApiError(f"Calendar instance write failed ({r.status_code}).")
            o.exc_pushed_sequence = m.sequence or 0
    return "SYNCED"


async def push_safely(db: AsyncSession, series: MeetingSeries) -> str:
    from app.services import calendar_sync_service as cal
    from app.services import oauth_service as oauth

    conn = await cal._host_calendar(db, series.host_id) if series.host_id else None
    if conn is None:
        return "NO_CALENDAR"
    try:
        async with db.begin_nested():
            return await push_series(db, series, conn)
    except (oauth.OAuthError, cal.CalendarApiError) as e:
        conn.last_error = str(e)[:500]
        return f"PENDING: {e}"


async def sync_series(db: AsyncSession, conn) -> int:
    """Called by the calendar sync loop: write every series of this host whose provider copy is behind."""
    rows = (await db.execute(select(MeetingSeries).where(MeetingSeries.host_id == conn.user_id))).scalars().all()
    n = 0
    for s in rows:
        async with db.begin_nested():
            if await push_series(db, s, conn) in ("SYNCED", "CANCELLED"):
                n += 1
    return n


# ── provider -> ERP (instance moved / cancelled in the calendar) ──────────────

async def apply_provider_instance(db: AsyncSession, series_id: UUID, e: dict) -> Optional[str]:
    """One occurrence changed in the host's own calendar. Cancelled there -> cancelled here; moved there -> moved here
    unless it would double-book. Returns 'cancelled', 'moved', 'conflict' or None."""
    series = await db.get(MeetingSeries, series_id)
    orig = e.get("orig_start")
    if series is None or series.status != "ACTIVE" or orig is None:
        return None
    occ_date = mtg.local(orig, series.time_zone).date().isoformat()
    found = next(((o, m) for o, m in await _occ_rows(db, series) if o.occ_date == occ_date), None)
    if found is None:
        return None
    o, m = found
    if m.status != "SCHEDULED":
        return None
    changed = False
    if e["cancelled"]:
        m.status, changed, result = "CANCELLED", True, "cancelled"
    else:
        minutes = int((e["end"] - e["start"]).total_seconds() // 60)
        if (e["start"], minutes) == (m.scheduled_at, m.duration_minutes):
            return None
        await mtg.lock_host(db, series.host_id)
        if await mtg.overlapping(db, series.host_id, e["start"], minutes, exclude=m.id, ignore_calendar=True) is not None:
            return "conflict"
        m.scheduled_at, m.duration_minutes, changed, result = e["start"], max(5, minutes), True, "moved"
    if changed:
        m.sequence = (m.sequence or 0) + 1
        o.is_exception, o.exc_pushed_sequence = True, m.sequence
        series.sequence += 1
        await db.flush()
    return result
