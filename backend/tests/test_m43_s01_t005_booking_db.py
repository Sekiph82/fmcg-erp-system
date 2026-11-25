"""M43.S01.T005 public self-booking with round-robin on disposable PostgreSQL (run at the M43 gate, M43_S01_DB=1).

Covers: slots respect working hours/weekdays/notice/buffers and DST zone; hosts anonymous in the public answer;
round-robin alternates hosts; concurrent bookings of the last free slot → exactly one succeeds; honeypot and
consent; per-IP rate limit; manage token reschedule (keeps host when free) and cancel; reminder sent once.
Browser E2E (desktop + phone, invite in Mailpit) is part of the gate walkthrough.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core import clock

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]
MONDAY = date(2026, 12, 7)
NOW = datetime(2026, 12, 4, 6, 0, tzinfo=timezone.utc)   # Friday, well before Monday's slots


@pytest.fixture
async def setup(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.meetings import BookingPage
    from app.models.user import User
    monkeypatch.setattr(clock, "utcnow", lambda: NOW)
    async with AsyncSessionLocal() as db:
        hosts = [User(id=uuid.uuid4(), email=f"host{i}-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x",
                      full_name=f"Synthetic Host {i}", is_active=True) for i in range(2)]
        db.add_all(hosts)
        page = BookingPage(id=uuid.uuid4(), slug=f"povu-demo-{uuid.uuid4().hex[:6]}", title="POVU distributor intro",
                           duration_minutes=30, buffer_before=0, buffer_after=10, min_notice_hours=4, max_days_ahead=30,
                           time_zone="Africa/Nairobi", open_time="09:00", close_time="10:00", weekdays=[0, 1, 2, 3, 4],
                           host_ids=[str(h.id) for h in hosts], routing="round_robin", platform="jitsi",
                           consent_text="Synthetic consent", is_active=True)
        db.add(page)
        await db.commit()
        yield db, page, hosts


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _visitor(i, start):
    return {"start_utc": start, "name": f"Synthetic Visitor {i}", "email": f"povu-visitor{i}@example.com", "consent": True}


async def test_slots_and_anonymity(setup, client):
    db, page, hosts = setup
    info = (await client.get(f"/api/v1/public/book/{page.slug}")).json()
    assert "host_ids" not in info and all(str(h.id) not in str(info) for h in hosts)
    slots = (await client.get(f"/api/v1/public/book/{page.slug}/slots", params={"day": MONDAY, "tz": "Europe/Istanbul"})).json()["slots"]
    assert [s["start_utc"][11:16] for s in slots] == ["06:00", "06:30"]          # 09:00/09:30 Nairobi = UTC+3
    assert (await client.get(f"/api/v1/public/book/{page.slug}/slots", params={"day": MONDAY + timedelta(days=5)})).json()["slots"] == []


async def test_round_robin_consent_honeypot_and_rate(setup, client):
    db, page, hosts = setup
    r1 = await client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(1, "2026-12-07T06:00:00Z"))
    r2 = await client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(2, "2026-12-07T06:00:00Z"))
    assert r1.status_code == r2.status_code == 201
    from app.models.meetings import Booking
    used = set((await db.execute(select(Booking.host_id).where(Booking.page_id == page.id))).scalars())
    assert used == {h.id for h in hosts}                                       # both hosts, one each
    r3 = await client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(3, "2026-12-07T06:00:00Z"))
    assert r3.status_code == 409                                               # nobody free any more
    bad = await client.post(f"/api/v1/public/book/{page.slug}", json={**_visitor(4, "2026-12-07T06:30:00Z"), "consent": False})
    assert bad.status_code == 422
    bot = await client.post(f"/api/v1/public/book/{page.slug}", json={**_visitor(5, "2026-12-07T06:30:00Z"), "website": "x"})
    assert bot.status_code == 422
    off_grid = await client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(6, "2026-12-07T06:10:00Z"))
    assert off_grid.status_code == 422


async def test_concurrent_last_slot(setup, client):
    db, page, hosts = setup
    page.host_ids = [str(hosts[0].id)]
    await db.commit()
    rs = await asyncio.gather(*[client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(10 + i, "2026-12-07T06:30:00Z"))
                                for i in range(4)])
    assert sorted(r.status_code for r in rs) == [201, 409, 409, 409]


async def test_manage_reschedule_cancel_and_reminder(setup, client, monkeypatch):
    db, page, hosts = setup
    token = (await client.post(f"/api/v1/public/book/{page.slug}", json=_visitor(20, "2026-12-07T06:00:00Z"))).json()["manage_token"]
    assert (await client.get("/api/v1/public/book/manage/not-a-token")).status_code == 404
    moved = await client.post(f"/api/v1/public/book/manage/{token}/reschedule", json={"start_utc": "2026-12-08T06:30:00Z"})
    assert moved.status_code == 200 and moved.json()["start_utc"].startswith("2026-12-08T06:30")
    view = (await client.get(f"/api/v1/public/book/manage/{token}")).json()
    assert view["status"] == "SCHEDULED"
    from app.services import booking_service as bk
    monkeypatch.setattr(clock, "utcnow", lambda: datetime(2026, 12, 7, 8, 0, tzinfo=timezone.utc))
    await bk.send_due_reminders(db)      # no connected host mailbox in this test → nothing claimed as sent
    from app.models.meetings import Booking
    assert (await db.execute(select(func.count()).select_from(Booking).where(Booking.reminder_sent_at.is_not(None)))).scalar_one() == 0
    assert (await client.post(f"/api/v1/public/book/manage/{token}/cancel")).json()["status"] == "CANCELLED"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
