"""M43.S01.T006 e-mail engagement tracking (run at the M43 gate; DB part needs M43_S01_DB=1).

Unit: signed tokens (tamper → None), HTML render keeps unsubscribe untracked, domain allow-list, machine UA.
DB: tracking only when enabled + opted in + not opted out; INVOICE never tracked; click redirects only to the
stored link (index outside → 404, no open redirect); duplicates within 60 s from the same client ignored; proxy and
too-fast events flagged machine and excluded; opt-out stops recording but still redirects; analytics per sender.
Mail delivery is checked in Mailpit during the gate walkthrough (multipart text+html only for tracked mail).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.services import crm_engagement_service as eng


def _msg(**kw):
    from app.models.crm import CRMOutboundMessage
    base = dict(id=uuid.uuid4(), dedupe_key=f"t:{uuid.uuid4()}", purpose="CAMPAIGN", to_email="buyer@povu-demo.test",
                subject="POVU synthetic offer", body_text="See https://povu-demo.test/offer?a=1&b=2 now",
                status="SENT", attempts=1, next_attempt_at=datetime.now(timezone.utc), created_by="rep1",
                created_at=datetime.now(timezone.utc), sent_at=datetime.now(timezone.utc) - timedelta(hours=1),
                track_engagement=True)
    base.update(kw)
    return CRMOutboundMessage(**base)


def test_token_roundtrip_and_tamper():
    mid = uuid.uuid4()
    t = eng.token(mid, 3)
    assert eng.parse_token(t) == (mid, 3)
    assert eng.parse_token(t[:-2] + "xx") is None
    assert eng.parse_token(eng.token(mid, 3).replace("-3.", "-4.")) is None


def test_render_html_links_and_unsubscribe(monkeypatch):
    monkeypatch.setattr(settings, "CRM_TRACKING_LINK_DOMAINS", "")
    m = _msg()
    html, links = eng.render_html(m, m.body_text + "\n--\nTo stop: https://erp.test/unsubscribe?t=abc")
    assert links == ["https://povu-demo.test/offer?a=1&b=2"]
    assert "/public/t/c/" in html and "/public/t/o/" in html and "https://erp.test/unsubscribe?t=abc" in html
    monkeypatch.setattr(settings, "CRM_TRACKING_LINK_DOMAINS", "example.test")
    _, links = eng.render_html(m, m.body_text)
    assert links == []                                    # outside the allow-list → plain, untracked link


def test_machine_detection():
    m = _msg()
    now = datetime.now(timezone.utc)
    assert eng.is_machine(m, "Mozilla/5.0 (via ggpht.com GoogleImageProxy)", now)
    assert eng.is_machine(_msg(sent_at=now - timedelta(seconds=3)), "Mozilla/5.0", now)
    assert not eng.is_machine(m, "Mozilla/5.0 (Windows NT 10.0)", now)


DB = pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture
async def db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


@DB
@pytest.mark.asyncio
async def test_record_redirect_dedupe_optout_and_analytics(db, monkeypatch):
    monkeypatch.setattr(settings, "CRM_EMAIL_TRACKING_ENABLED", True)
    m = _msg(created_by=f"rep-{uuid.uuid4().hex[:6]}")
    m.tracked_links = ["https://povu-demo.test/offer?a=1&b=2"]
    db.add(m)
    await db.commit()
    assert await eng.may_track(db, m)
    assert not await eng.may_track(db, _msg(purpose="INVOICE"))
    assert await eng.record(db, eng.token(m.id, 1), "CLICK", "Mozilla/5.0", "ip1") == m.tracked_links[0]
    assert await eng.record(db, eng.token(m.id, 2), "CLICK", "Mozilla/5.0", "ip1") is None     # no such link
    await eng.record(db, eng.token(m.id, 0), "OPEN", "Mozilla/5.0", "ip1")
    await eng.record(db, eng.token(m.id, 0), "OPEN", "Mozilla/5.0", "ip1")                    # duplicate
    await eng.record(db, eng.token(m.id, 0), "OPEN", "GoogleImageProxy", "ip2")               # machine
    await db.commit()
    out = await eng.analytics(db, since=datetime.now(timezone.utc) - timedelta(days=1), created_by=m.created_by)
    row = next(x for x in out["messages"] if x["id"] == str(m.id))
    assert (row["human_opens"], row["machine_opens"], row["clicks"]) == (1, 1, 1)
    assert out["senders"][0]["open_rate"] == 1.0
    await eng.opt_out(db, m.to_email)
    await db.commit()
    assert not await eng.may_track(db, m)
    assert await eng.record(db, eng.token(m.id, 1), "CLICK", "Mozilla/5.0", "ip3") == m.tracked_links[0]
    await db.commit()
    out = await eng.analytics(db, since=datetime.now(timezone.utc) - timedelta(days=1), created_by=m.created_by)
    assert next(x for x in out["messages"] if x["id"] == str(m.id))["clicks"] == 1           # not recorded


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
