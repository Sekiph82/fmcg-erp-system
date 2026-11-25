"""M44.S01.T009 first-party web analytics (unit; DB part needs M44_DB=1). Runs at the M44 gate.

Unit: query strings and fragments never stored, referrer reduced to host, raw visitor id never stored (keyed hash).
DB: no consent → nothing stored; bot UA dropped; same event id twice counts once; identity only with marketing
consent; funnel counts ordered steps; journey shows first touch; forget and retention purge delete events.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services import web_analytics_service as wa


def test_privacy_helpers():
    assert wa.clean_path("/products?email=a@b.c#x") == "/products"
    assert wa.referrer_host("https://www.google.com/search?q=secret") == "www.google.com"
    assert wa.referrer_host(None) is None
    vid = "a" * 32
    assert vid not in wa.hashed("v", vid) and len(wa.hashed("v", vid)) == 64
    assert wa.BOT_RE.search("Mozilla/5.0 (compatible; Googlebot/2.1)") and not wa.BOT_RE.search("Mozilla/5.0 (Windows NT 10.0) Chrome/120")


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _ev(kind="PAGE", path="/", name=None, eid=None, **utm):
    return {"event_id": eid or uuid.uuid4().hex, "kind": kind, "path": path, "name": name, **utm}


@DB
@pytest.mark.asyncio
async def test_collect_consent_bots_dedupe_identity_funnel_forget():
    from sqlalchemy import select, update
    from app.db.session import AsyncSessionLocal
    from app.models.crm import WebEvent
    v, s = uuid.uuid4().hex, uuid.uuid4().hex
    email = f"visitor-{v[:6]}@povu-demo.test"
    async with AsyncSessionLocal() as db:
        assert (await wa.collect(db, v, s, [_ev()]))["stored"] == 0                      # no consent yet
        await wa.record_consent(db, v, analytics=True, marketing=False)
        await db.flush()
        assert (await wa.collect(db, v, s, [_ev()], "Googlebot/2.1"))["stored"] == 0      # bot
        same = _ev(eid="dup-" + v[:20])
        r = await wa.collect(db, v, s, [_ev("PAGE", "/?utm=x", utm_source="newsletter", utm_campaign="povu-launch"),
                                        same, same, _ev("PAGE", "/products"), _ev("FORM", "/contact", "contact")])
        assert r["stored"] == 4
        assert not await wa.identify(db, v, email)                                         # no marketing consent
        await wa.record_consent(db, v, analytics=True, marketing=True)
        await db.flush()
        assert await wa.identify(db, v, email)
        steps = await wa.funnel(db, ["/", "/products", "FORM:contact"], 1)
        assert [x["visitors"] for x in steps][-1] >= 1
        j = await wa.journey(db, email)
        assert j["linked"] and j["first_touch"]["source"] == "newsletter"
        # withdrawing marketing consent unlinks the e-mail (review fix); consenting again and identifying relinks it
        await wa.record_consent(db, v, analytics=True, marketing=False)
        await db.flush()
        assert not (await wa.journey(db, email))["linked"]
        await wa.record_consent(db, v, analytics=True, marketing=True)
        await db.flush()
        assert await wa.identify(db, v, email)
        stored = (await db.execute(select(WebEvent.path).where(WebEvent.visitor_hash == wa.hashed("v", v)))).scalars().all()
        assert all("?" not in p for p in stored)
        # retention: age one event past the window
        await db.execute(update(WebEvent).where(WebEvent.visitor_hash == wa.hashed("v", v), WebEvent.path == "/products")
                         .values(occurred_at=datetime.now(timezone.utc) - timedelta(days=4000)))
        assert await wa.purge_expired(db) >= 1
        assert await wa.forget(db, v) == 3
        assert not (await wa.journey(db, email))["linked"]
        await db.rollback()
