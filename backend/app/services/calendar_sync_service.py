"""Two-way Google Calendar / Microsoft Outlook calendar sync (M43.S01.T003 / T004).

Push (ERP → provider): every SCHEDULED/CANCELLED meeting of a host whose calendar is connected is written to the
host's primary calendar (create, update when meeting.sequence moved, delete on cancel). The event carries no
attendees, so the provider never e-mails them: invitations stay the ERP's iCalendar REQUEST/CANCEL from the host's
mailbox (one UID, one source of invites). Google Meet links are created through conferenceData.createRequest;
Teams links through isOnlineMeeting where the Microsoft account supports it (otherwise the pasted link stays).

Pull (provider → ERP), incremental:
- Google: events.list(singleEvents=true) on the primary calendar within a window, then nextSyncToken; 410 Gone →
  full resync of the window.
- Graph: /me/calendarView/delta (instances, recurrence expanded) with Prefer outlook.timezone="UTC"; 410 /
  syncStateNotFound → reset.
Events we pushed (matched by external id) apply back: provider cancellation → meeting CANCELLED; provider time
change → moved when the ERP has not changed the meeting since our last push and the new time does not double-book
the host; otherwise the ERP version wins and the conflict is recorded on the link for the host to see.
All other events become busy blocks (start/end only — titles, attendees and bodies of private events are never
stored) that the booking checks (overlapping / free_slots / public booking) treat as busy. Free/transparent events
are not busy; all-day events block the day in the meeting's time zone.

Tasks (M47.S01.T009): open CRM tasks (PLANNED crm_activities with a due time) assigned to a user with a connected
calendar are pushed as 30-minute free (transparent / showAs=free) events — created, updated when subject or due time
change, deleted when the task is completed, cancelled, reassigned or deleted. Without a calendar link: NOT_CONFIGURED.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.meetings import CalendarBusyBlock, CalendarEventLink, MeetingRecord
from app.models.oauth_connection import OAuthConnection
from app.services import oauth_service as oauth

log = logging.getLogger(__name__)
UTC = timezone.utc
WINDOW_PAST, WINDOW_FUTURE = timedelta(days=30), timedelta(days=180)
PAGE_LIMIT = 25


class CalendarApiError(Exception):
    pass


async def _call(db, conn, method, url, **kw) -> httpx.Response:
    for attempt in (1, 2):
        token = await oauth.access_token(db, conn)
        headers = {"Authorization": f"Bearer {token}", **kw.get("headers", {})}
        try:
            async with provider_client() as c:
                resp = await c.request(method, url, **{**kw, "headers": headers})
        except EgressBlocked as e:
            raise CalendarApiError(str(e)) from None
        except httpx.HTTPError:
            raise oauth.OAuthTemporaryError("The calendar provider could not be reached.") from None
        if resp.status_code == 401 and attempt == 1:
            conn.expires_at = clock.utcnow()
            continue
        if resp.status_code == 401:
            conn.status, conn.last_error = "ERROR", "The provider rejected the token; reconnect."
            raise oauth.OAuthReauthRequired()
        if resp.status_code == 429 or resp.status_code >= 500 or (
                resp.status_code == 403 and "rateLimitExceeded" in resp.text):
            ra = resp.headers.get("Retry-After")
            raise oauth.OAuthTemporaryError(f"Calendar provider busy ({resp.status_code}).",
                                            int(ra) if ra and ra.isdigit() else None)
        return resp
    raise AssertionError("unreachable")


def _naive_utc(v: datetime) -> datetime:
    return (v if v.tzinfo else v.replace(tzinfo=UTC)).astimezone(UTC).replace(tzinfo=None)


def _parse_google_time(t: dict, tz_name: str) -> datetime:
    if "dateTime" in t:
        return _naive_utc(datetime.fromisoformat(t["dateTime"].replace("Z", "+00:00")))
    return _naive_utc(datetime.combine(date.fromisoformat(t["date"]), time(0), ZoneInfo(t.get("timeZone") or tz_name)))


def _parse_graph_time(t: dict) -> datetime:
    # Prefer: outlook.timezone="UTC" → "2026-11-26T09:00:00.0000000" in UTC (7 fractional digits)
    raw = t["dateTime"].split(".")[0]
    return datetime.fromisoformat(raw)


# ── push ──────────────────────────────────────────────────────────────────────

def _google_body(m: MeetingRecord, want_meet: bool) -> dict:
    tz = m.time_zone or "Africa/Nairobi"
    start = m.scheduled_at.replace(tzinfo=UTC).astimezone(ZoneInfo(tz))
    end = start + timedelta(minutes=m.duration_minutes)
    body = {"summary": m.title, "description": (m.agenda or "")[:4000],
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": end.isoformat(), "timeZone": tz},
            "location": m.meeting_url or "",
            "extendedProperties": {"private": {"povuMeetingId": str(m.id)}}}
    if want_meet:
        body["conferenceData"] = {"createRequest": {"requestId": f"povu-{m.id}",
                                                    "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    return body


def _graph_body(m: MeetingRecord, want_teams: bool) -> dict:
    start = m.scheduled_at
    end = start + timedelta(minutes=m.duration_minutes)
    body = {"subject": m.title, "body": {"contentType": "text", "content": (m.agenda or "")[:4000]},
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "location": {"displayName": m.meeting_url or ""},
            "transactionId": f"povu-{m.id}"}          # Graph dedupes repeated creates with the same transactionId
    if want_teams:
        body.update(isOnlineMeeting=True, onlineMeetingProvider="teamsForBusiness")
    return body


def _cal_base(conn) -> str:
    if conn.provider == "google":
        return settings.GOOGLE_CALENDAR_API_URL.rstrip("/") + "/calendars/primary/events"
    return settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + "/me/events"


async def push_meeting(db: AsyncSession, m: MeetingRecord, conn: OAuthConnection) -> None:
    link = (await db.execute(select(CalendarEventLink).where(
        CalendarEventLink.meeting_id == m.id, CalendarEventLink.connection_id == conn.id))).scalar_one_or_none()
    if link is None:
        if m.status != "SCHEDULED":
            return                                      # never pushed, nothing to cancel
        link = CalendarEventLink(meeting_id=m.id, connection_id=conn.id)
        db.add(link)
        await db.flush()
    if link.pushed_sequence == (m.sequence or 0) and link.external_event_id:
        return
    base = _cal_base(conn)
    google = conn.provider == "google"
    if m.status != "SCHEDULED":
        if link.external_event_id:
            r = await _call(db, conn, "DELETE", f"{base}/{link.external_event_id}",
                            params={"sendUpdates": "none"} if google else None)
            if r.status_code not in (200, 204, 404, 410):
                raise CalendarApiError(f"Calendar delete failed ({r.status_code}).")
        link.pushed_sequence, link.updated_at = m.sequence or 0, clock.utcnow()
        return
    want_conf = (m.platform == "google_meet" and google and not m.meeting_url) or \
                (m.platform == "teams" and not google and not m.meeting_url)
    body = _google_body(m, want_conf) if google else _graph_body(m, want_conf)
    params = {"sendUpdates": "none", "conferenceDataVersion": 1} if google else None
    if link.external_event_id:
        r = await _call(db, conn, "PATCH", f"{base}/{link.external_event_id}", json=body, params=params)
        if r.status_code in (404, 410):            # deleted at the provider: create again
            link.external_event_id = None
    if not link.external_event_id:
        r = await _call(db, conn, "POST", base, json=body, params=params)
    if r.status_code not in (200, 201):
        raise CalendarApiError(f"Calendar write failed ({r.status_code}).")
    ev = r.json()
    link.external_event_id, link.etag = ev.get("id"), ev.get("etag") or ev.get("@odata.etag")
    join = ev.get("hangoutLink") if google else (ev.get("onlineMeeting") or {}).get("joinUrl")
    if join and not m.meeting_url:
        m.meeting_url = join[:500]
    link.pushed_sequence, link.updated_at, link.conflict = m.sequence or 0, clock.utcnow(), None


async def _host_calendar(db: AsyncSession, host_id) -> Optional[OAuthConnection]:
    return (await db.execute(select(OAuthConnection).where(
        OAuthConnection.user_id == host_id, OAuthConnection.purpose == "calendar",
        OAuthConnection.status == "CONNECTED").order_by(OAuthConnection.created_at).limit(1))).scalar_one_or_none()


async def push_safely(db: AsyncSession, m: MeetingRecord) -> str:
    """Called after a booking change; never blocks the booking. Failures are retried by the background loop."""
    if not m.host_id:
        return "NO_CALENDAR"
    conn = await _host_calendar(db, m.host_id)
    if conn is None:
        return "NO_CALENDAR"
    try:
        async with db.begin_nested():
            await push_meeting(db, m, conn)
        return "SYNCED"
    except (oauth.OAuthError, CalendarApiError) as e:
        conn.last_error = str(e)[:500]
        return f"PENDING: {e}"


# ── pull ──────────────────────────────────────────────────────────────────────

async def _google_pull(db, conn) -> tuple[list[dict], dict]:
    cursor = dict(conn.sync_cursor or {})
    base = _cal_base(conn)
    now = clock.utcnow()
    params = {"singleEvents": "true", "maxResults": 250, "showDeleted": "true"}
    if cursor.get("sync_token"):
        params["syncToken"] = cursor["sync_token"]
    else:
        params.update(timeMin=(now - WINDOW_PAST).isoformat(), timeMax=(now + WINDOW_FUTURE).isoformat())
    items, full = [], not cursor.get("sync_token")
    for _ in range(PAGE_LIMIT):
        r = await _call(db, conn, "GET", base, params=params)
        if r.status_code == 410:                    # sync token invalid → full resync of the window
            return await _google_pull_full(db, conn)
        if r.status_code != 200:
            raise CalendarApiError(f"Calendar list failed ({r.status_code}).")
        body = r.json()
        items += body.get("items", [])
        if body.get("nextPageToken"):
            params["pageToken"] = body["nextPageToken"]
            continue
        return [_norm_google(e, conn) for e in items], {"sync_token": body.get("nextSyncToken"), "full": full}
    return [_norm_google(e, conn) for e in items], dict(conn.sync_cursor or {})


async def _google_pull_full(db, conn):
    conn.sync_cursor = {}
    events, cursor = await _google_pull(db, conn)
    cursor["full"] = True
    return events, cursor


def _norm_google(e: dict, conn) -> dict:
    cancelled = e.get("status") == "cancelled"
    out = {"id": e["id"], "cancelled": cancelled,
           "busy": not cancelled and e.get("transparency") != "transparent",
           "erp_id": ((e.get("extendedProperties") or {}).get("private") or {}).get("povuMeetingId")}
    if not cancelled and "start" in e:
        out["start"], out["end"] = _parse_google_time(e["start"], "Africa/Nairobi"), _parse_google_time(e["end"], "Africa/Nairobi")
    return out


async def _graph_pull(db, conn) -> tuple[list[dict], dict]:
    cursor = dict(conn.sync_cursor or {})
    now = clock.utcnow()
    start_url = (settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + "/me/calendarView/delta"
                 f"?startDateTime={(now - WINDOW_PAST):%Y-%m-%dT%H:%M:%SZ}"
                 f"&endDateTime={(now + WINDOW_FUTURE):%Y-%m-%dT%H:%M:%SZ}")
    url, full = cursor.get("delta_link") or start_url, not cursor.get("delta_link")
    items = []
    headers = {"Prefer": 'outlook.timezone="UTC", odata.maxpagesize=100'}
    for _ in range(PAGE_LIMIT):
        r = await _call(db, conn, "GET", url, headers=headers)
        if r.status_code == 410 or (r.status_code == 400 and "syncStateNotFound" in r.text):
            url, items, full = start_url, [], True
            continue
        if r.status_code != 200:
            raise CalendarApiError(f"Calendar delta failed ({r.status_code}).")
        body = r.json()
        items += body.get("value", [])
        if body.get("@odata.deltaLink"):
            return [_norm_graph(e) for e in items], {"delta_link": body["@odata.deltaLink"], "full": full}
        url = body.get("@odata.nextLink")
        if not url:
            break
    return [_norm_graph(e) for e in items], dict(conn.sync_cursor or {})


def _norm_graph(e: dict) -> dict:
    removed = "@removed" in e or e.get("isCancelled")
    out = {"id": e["id"], "cancelled": bool(removed), "busy": not removed and e.get("showAs") not in ("free", "unknown"),
           "erp_id": None, "tx": e.get("transactionId")}
    if not removed and "start" in e:
        out["start"], out["end"] = _parse_graph_time(e["start"]), _parse_graph_time(e["end"])
    return out


async def pull(db: AsyncSession, conn: OAuthConnection) -> dict:
    from app.services import meeting_service as mtg

    events, cursor = await (_google_pull if conn.provider == "google" else _graph_pull)(db, conn)
    links = {l.external_event_id: l for l in (await db.execute(select(CalendarEventLink).where(
        CalendarEventLink.connection_id == conn.id))).scalars()}
    from app.models.m47_sales_depth import CRMTaskCalendarLink
    task_events = set((await db.execute(select(CRMTaskCalendarLink.external_event_id).where(
        CRMTaskCalendarLink.connection_id == conn.id))).scalars())
    if cursor.get("full"):                         # full window: rebuild busy blocks from scratch
        await db.execute(delete(CalendarBusyBlock).where(CalendarBusyBlock.connection_id == conn.id))
    moved = cancelled = busy = conflicts = 0
    for e in events:
        if e["id"] in task_events:
            continue                               # our own task reminders are never busy time
        link = links.get(e["id"])
        if link is None and e.get("tx", "") and str(e.get("tx")).startswith("povu-"):
            continue                               # our own create echoed back before the link id was stored
        if link is not None:
            m = await db.get(MeetingRecord, link.meeting_id)
            if m is None or m.status != "SCHEDULED":
                continue
            erp_changed = (m.sequence or 0) != (link.pushed_sequence or 0)
            if e["cancelled"]:
                if erp_changed:
                    link.conflict, conflicts = "Deleted in the calendar but changed in the ERP; kept.", conflicts + 1
                    continue
                m.status, m.sequence = "CANCELLED", (m.sequence or 0) + 1
                link.pushed_sequence, cancelled = m.sequence, cancelled + 1
                continue
            new_minutes = int((e["end"] - e["start"]).total_seconds() // 60)
            if (e["start"], new_minutes) == (m.scheduled_at, m.duration_minutes):
                continue
            if erp_changed:
                link.conflict, conflicts = "Moved in the calendar and changed in the ERP; ERP version kept.", conflicts + 1
                continue
            await mtg.lock_host(db, m.host_id)
            other = await mtg.overlapping(db, m.host_id, e["start"], new_minutes, exclude=m.id, ignore_calendar=True)
            if other is not None:
                link.conflict, conflicts = "Moved in the calendar onto another meeting; not applied.", conflicts + 1
                continue
            m.scheduled_at, m.duration_minutes = e["start"], max(5, new_minutes)
            m.sequence = (m.sequence or 0) + 1
            link.pushed_sequence, link.conflict, moved = m.sequence, None, moved + 1
            continue
        await db.execute(delete(CalendarBusyBlock).where(CalendarBusyBlock.connection_id == conn.id,
                                                         CalendarBusyBlock.external_event_id == e["id"]))
        if not e["cancelled"] and e["busy"] and e.get("start"):
            db.add(CalendarBusyBlock(connection_id=conn.id, external_event_id=e["id"][:1024],
                                     starts_at=e["start"], ends_at=e["end"]))
            busy += 1
    cursor.pop("full", None)
    conn.sync_cursor, conn.last_sync_at, conn.last_error = cursor, clock.utcnow(), None
    await db.flush()
    return {"busy": busy, "moved": moved, "cancelled": cancelled, "conflicts": conflicts}


async def sync_connection(db: AsyncSession, conn: OAuthConnection) -> dict:
    """Push pending meeting changes, then pull provider changes. Caller commits."""
    pending = (await db.execute(select(MeetingRecord).where(
        MeetingRecord.host_id == conn.user_id, MeetingRecord.scheduled_at >= clock.utcnow().replace(tzinfo=None) - WINDOW_PAST,
        MeetingRecord.status.in_(("SCHEDULED", "CANCELLED"))))).scalars().all()
    pushed = 0
    for m in pending:
        async with db.begin_nested():
            await push_meeting(db, m, conn)
            pushed += 1
    tasks = await sync_tasks(db, conn)
    result = await pull(db, conn)
    return {"pushed": pushed, "tasks": tasks, **result}


# ── CRM tasks (M47.S01.T009) ──────────────────────────────────────────────────

TASK_MINUTES = 30


def _task_hash(act) -> str:
    return hashlib.sha256(f"{act.subject}|{act.due_datetime.isoformat()}".encode()).hexdigest()


def _task_body(act, google: bool) -> dict:
    start = act.due_datetime.replace(tzinfo=None)              # crm_activities times are naive UTC
    end = start + timedelta(minutes=TASK_MINUTES)
    text = f"CRM task. Open: {settings.PUBLIC_APP_URL.rstrip('/')}/dashboard/crm/records/{act.crm_record_id}"
    if google:
        return {"summary": f"Task: {act.subject}"[:300], "description": text, "transparency": "transparent",
                "start": {"dateTime": start.replace(tzinfo=UTC).isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.replace(tzinfo=UTC).isoformat(), "timeZone": "UTC"},
                "extendedProperties": {"private": {"povuTaskId": str(act.id)}}}
    return {"subject": f"Task: {act.subject}"[:255], "body": {"contentType": "text", "content": text}, "showAs": "free",
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"}, "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "transactionId": f"povu-task-{act.id}"}


async def push_task(db: AsyncSession, conn: OAuthConnection, activity_id, act=None) -> str:
    """act = the open task when it should be on this calendar; None = remove its event (done, deleted, reassigned)."""
    from app.models.m47_sales_depth import CRMTaskCalendarLink
    link = (await db.execute(select(CRMTaskCalendarLink).where(
        CRMTaskCalendarLink.activity_id == activity_id, CRMTaskCalendarLink.connection_id == conn.id))).scalar_one_or_none()
    base, google = _cal_base(conn), conn.provider == "google"
    if act is None:
        if link is None:
            return "SKIPPED"
        if link.external_event_id:
            r = await _call(db, conn, "DELETE", f"{base}/{link.external_event_id}",
                            params={"sendUpdates": "none"} if google else None)
            if r.status_code not in (200, 204, 404, 410):
                raise CalendarApiError(f"Calendar delete failed ({r.status_code}).")
        await db.delete(link)
        return "DELETED"
    h = _task_hash(act)
    if link is not None and link.pushed_hash == h and link.external_event_id:
        return "UNCHANGED"
    if link is None:
        link = CRMTaskCalendarLink(activity_id=act.id, connection_id=conn.id)
        db.add(link)
        await db.flush()
    body, params = _task_body(act, google), ({"sendUpdates": "none"} if google else None)
    r = None
    if link.external_event_id:
        r = await _call(db, conn, "PATCH", f"{base}/{link.external_event_id}", json=body, params=params)
        if r.status_code in (404, 410):
            link.external_event_id = None
    if not link.external_event_id:
        r = await _call(db, conn, "POST", base, json=body, params=params)
    if r.status_code not in (200, 201):
        raise CalendarApiError(f"Calendar write failed ({r.status_code}).")
    link.external_event_id, link.pushed_hash, link.updated_at = r.json().get("id"), h, clock.utcnow()
    return "SYNCED"


async def sync_tasks(db: AsyncSession, conn: OAuthConnection) -> dict:
    """Push the user's open tasks with due times; remove events of tasks that are no longer open for them."""
    from app.models.crm import CRMActivity, CRMActivityResult
    from app.models.m47_sales_depth import CRMTaskCalendarLink
    from app.models.user import User
    user = await db.get(User, conn.user_id)
    if user is None:
        return {}
    acts = (await db.execute(select(CRMActivity).where(
        CRMActivity.assigned_to.in_((str(user.id), user.username)), CRMActivity.result_status == CRMActivityResult.PLANNED,
        CRMActivity.due_datetime.is_not(None), CRMActivity.due_datetime >= clock.utcnow().replace(tzinfo=None) - WINDOW_PAST)
        .limit(500))).scalars().all()
    open_ids = {a.id for a in acts}
    stale = [i for i in (await db.execute(select(CRMTaskCalendarLink.activity_id).where(
        CRMTaskCalendarLink.connection_id == conn.id))).scalars() if i not in open_ids]
    out: dict = {}
    for act_id, act in [(a.id, a) for a in acts] + [(i, None) for i in stale]:
        async with db.begin_nested():
            res = await push_task(db, conn, act_id, act)
        out[res] = out.get(res, 0) + 1
    return out


async def push_tasks_safely(db: AsyncSession, user_id) -> dict:
    conn = await _host_calendar(db, user_id)
    if conn is None:
        return {"status": "NOT_CONFIGURED", "detail": "Connect your Google or Outlook calendar first."}
    try:
        return {"status": "SYNCED", **await sync_tasks(db, conn)}
    except (oauth.OAuthError, CalendarApiError) as e:
        conn.last_error = str(e)[:500]
        return {"status": "PENDING", "detail": str(e)[:300]}


async def run_calendar_sync(interval: float = 300.0) -> None:
    """Lifespan task: every 5 minutes, two-way sync for each connected calendar."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                conns = (await db.execute(select(OAuthConnection).where(
                    OAuthConnection.purpose == "calendar", OAuthConnection.status == "CONNECTED"))).scalars().all()
                for conn in conns:
                    try:
                        await sync_connection(db, conn)
                        await db.commit()
                    except Exception as e:
                        await db.rollback()
                        log.warning("calendar sync failed for connection %s", conn.id, exc_info=True)
                        try:
                            fresh = await db.get(OAuthConnection, conn.id)
                            fresh.last_error = (str(e) if isinstance(e, (oauth.OAuthError, CalendarApiError))
                                                else "Calendar sync failed.")[:500]
                            await db.commit()
                        except Exception:
                            await db.rollback()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("calendar sync tick failed")
        await asyncio.sleep(interval)
