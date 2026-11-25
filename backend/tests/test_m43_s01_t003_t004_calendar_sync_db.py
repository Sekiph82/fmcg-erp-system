"""M43.S01.T003/T004 two-way Google / Outlook calendar sync against the local simulator (disposable PostgreSQL).

Prepared 2026-11-25; run at the M43 gate (M43_S01_DB=1). Covers: push create/update/cancel with Meet/Teams link,
no duplicate on repeated push (Graph transactionId), external busy events block booking (no private titles kept),
free events do not, DST-zone meeting stored in UTC, provider-side move applied, provider-side cancellation,
simultaneous edit → ERP wins + conflict recorded, sync-token expiry (Google 410 / Graph syncStateNotFound) rebuilds
busy blocks without duplicates, disconnect stops pushes.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import func, select

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import create_app, sim_settings

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]
SIM = "http://127.0.0.1:8765"


@pytest.fixture
def sim(monkeypatch):
    app = create_app()
    for k, v in sim_settings(SIM).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture
async def db_user():
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        u = User(id=uuid.uuid4(), email=f"host-{uuid.uuid4().hex[:8]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x",
                 full_name="Synthetic Host", is_active=True)
        db.add(u)
        await db.commit()
        yield db, u


async def _ctl(body):
    async with provider_http.provider_client() as c:
        await c.post(f"{SIM}/_control", json=body)


async def _connect(db, user, provider):
    from app.services import oauth_service as oauth
    url = await oauth.start(db, user.id, provider, "calendar")
    parts = urlsplit(url)
    form = {k: v[0] for k, v in parse_qs(parts.query).items()}
    async with provider_http.provider_client() as c:
        r = await c.post(f"{parts.scheme}://{parts.netloc}{parts.path}", data={**form, "decision": "allow"})
    back = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
    conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    await db.commit()
    return conn


def _meeting(user, start, platform="jitsi", tz="Europe/London"):
    from app.models.meetings import MeetingRecord
    return MeetingRecord(id=uuid.uuid4(), title="Synthetic distributor review", platform=platform, host_id=user.id,
                         scheduled_at=start, duration_minutes=60, status="SCHEDULED", time_zone=tz, sequence=0,
                         attendees=[])


@pytest.mark.parametrize("provider,platform,link_prefix", [("google", "google_meet", "https://meet.google.com/"),
                                                             ("microsoft", "teams", "https://teams.microsoft.com/")])
async def test_push_lifecycle_and_conference_link(sim, db_user, provider, platform, link_prefix):
    from app.services import calendar_sync_service as cal
    db, user = db_user
    conn = await _connect(db, user, provider)
    m = _meeting(user, datetime(2026, 3, 29, 9, 0), platform)       # Europe/London DST change day, stored UTC
    db.add(m); await db.flush()
    assert await cal.push_safely(db, m) == "SYNCED"
    assert m.meeting_url and m.meeting_url.startswith(link_prefix)
    assert await cal.push_safely(db, m) == "SYNCED"                 # unchanged sequence → no second event
    st = sim.state.sim
    assert len([e for e in st["cal"][provider].values() if not e.get("cancelled")]) == 1
    m.scheduled_at, m.sequence = m.scheduled_at + timedelta(hours=2), 1
    await cal.push_safely(db, m)
    m.status, m.sequence = "CANCELLED", 2
    await cal.push_safely(db, m)
    assert all(e.get("cancelled") for e in st["cal"][provider].values())
    await db.commit()


@pytest.mark.parametrize("provider", ["google", "microsoft"])
async def test_busy_blocks_prevent_double_booking(sim, db_user, provider):
    from app.services import calendar_sync_service as cal
    from app.services import meeting_service as mtg
    db, user = db_user
    conn = await _connect(db, user, provider)
    await _ctl({"calendar": [
        {"provider": provider, "id": "private-1", "start": "2026-12-01T09:00:00+03:00", "end": "2026-12-01T10:00:00+03:00"},
        {"provider": provider, "id": "free-1", "start": "2026-12-01T11:00:00+03:00", "end": "2026-12-01T12:00:00+03:00", "free": True}]})
    await cal.sync_connection(db, conn); await db.commit()
    hit = await mtg.overlapping(db, user.id, datetime(2026, 12, 1, 6, 30), 60)     # 09:30 Nairobi
    assert hit is not None and hit.title == "Busy in your calendar"
    assert await mtg.overlapping(db, user.id, datetime(2026, 12, 1, 8, 0), 60) is None   # free event ignored
    await _ctl({"cal_token_gone": True})
    await cal.sync_connection(db, conn); await db.commit()
    from app.models.meetings import CalendarBusyBlock
    n = (await db.execute(select(func.count()).select_from(CalendarBusyBlock)
                          .where(CalendarBusyBlock.connection_id == conn.id))).scalar_one()
    assert n == 1


async def test_provider_move_cancel_and_conflict(sim, db_user):
    from app.models.meetings import CalendarEventLink
    from app.services import calendar_sync_service as cal
    db, user = db_user
    conn = await _connect(db, user, "google")
    a, b = _meeting(user, datetime(2026, 12, 2, 7, 0)), _meeting(user, datetime(2026, 12, 3, 7, 0))
    db.add_all([a, b]); await db.flush()
    await cal.push_safely(db, a); await cal.push_safely(db, b); await db.commit()
    la = (await db.execute(select(CalendarEventLink).where(CalendarEventLink.meeting_id == a.id))).scalar_one()
    lb = (await db.execute(select(CalendarEventLink).where(CalendarEventLink.meeting_id == b.id))).scalar_one()
    await cal.sync_connection(db, conn); await db.commit()
    await _ctl({"calendar": [
        {"provider": "google", "id": la.external_event_id, "start": "2026-12-02T08:00:00+00:00", "end": "2026-12-02T09:00:00+00:00"},
        {"provider": "google", "id": lb.external_event_id, "cancelled": True}]})
    await cal.sync_connection(db, conn); await db.commit()
    await db.refresh(a); await db.refresh(b)
    assert a.scheduled_at == datetime(2026, 12, 2, 8, 0) and b.status == "CANCELLED"
    # simultaneous edit: ERP changes, then the calendar moves the same event → ERP kept, conflict recorded
    a.title, a.sequence = "Changed in ERP", a.sequence + 1
    await db.commit()
    await _ctl({"calendar": [{"provider": "google", "id": la.external_event_id,
                              "start": "2026-12-02T12:00:00+00:00", "end": "2026-12-02T13:00:00+00:00"}]})
    await cal.pull(db, conn); await db.commit()
    await db.refresh(a); await db.refresh(la)
    assert a.scheduled_at == datetime(2026, 12, 2, 8, 0) and la.conflict


async def test_disconnected_calendar_is_not_used(sim, db_user):
    from app.services import calendar_sync_service as cal
    from app.services import oauth_service as oauth
    db, user = db_user
    conn = await _connect(db, user, "microsoft")
    await oauth.disconnect(db, conn, user.id); await db.commit()
    m = _meeting(user, datetime(2026, 12, 5, 7, 0))
    db.add(m); await db.flush()
    assert await cal.push_safely(db, m) == "NO_CALENDAR"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
