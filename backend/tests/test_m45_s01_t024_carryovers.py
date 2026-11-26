"""M45.S01.T024 M44 carry-overs (robustness part).

Meta paging stops at MAX_PAGES. DB part (M45_DB=1): parallel creates with one idempotency key return one row
(ads drafts and social posts); re-request clears a stale approved_by. The outbox ack is covered in
test_m44_s01_t013_messaging.py (redelivered until acked).
"""
import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import ads_adapters as ads
from tests.provider_sim.ads_app import ads_sim_settings, create_ads_app

BASE = "http://ads.test"
D1 = date(2026, 11, 21)
DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture
def sim(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in ads_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    provider_http.set_test_transport(httpx.ASGITransport(app=create_ads_app()))
    yield
    provider_http.set_test_transport(None)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_meta_paging_stops_at_cap(sim, monkeypatch):
    assert [r.campaign_id for r in await ads.ADAPTERS["meta"].report("1001", D1, D1)] == ["m1", "m2"]
    monkeypatch.setattr(ads, "MAX_PAGES", 1)
    assert [r.campaign_id for r in await ads.ADAPTERS["meta"].report("1001", D1, D1)] == ["m1"]


@DB
@pytest.mark.asyncio
async def test_parallel_same_key_one_row_and_stale_approver(sim):
    from sqlalchemy import func, select
    from app.api.v1.endpoints import ads as ep
    from app.api.v1.endpoints import social as sp
    from app.db.session import AsyncSessionLocal
    from app.models.crm import AdAccount, AdDraft, SocialChannel, SocialPost
    alice = SimpleNamespace(id=None, username="alice", is_superuser=True)
    bob = SimpleNamespace(id=None, username="bob", is_superuser=True)
    async with AsyncSessionLocal() as db:
        a = AdAccount(provider="google", external_id=f"9{uuid.uuid4().int % 10**9}", name="POVU sim", currency="KES")
        ch = SocialChannel(network="facebook", external_id=f"pg-{uuid.uuid4().hex[:8]}", name="POVU page")
        db.add_all([a, ch])
        await db.commit()
        aid, cid = a.id, ch.id

    key = f"k-{uuid.uuid4().hex[:12]}"
    body = ep.DraftIn(account_id=aid, idempotency_key=key, name="POVU WhiteCare", objective="SEARCH", daily_budget=Decimal("20"))

    async def mk_draft():
        async with AsyncSessionLocal() as db:
            return await ep.create_draft(body, db, alice)
    r = await asyncio.gather(*(mk_draft() for _ in range(4)))
    assert len({x["id"] for x in r}) == 1

    pkey = f"p-{uuid.uuid4().hex[:12]}"
    pbody = sp.PostIn(channel_id=cid, idempotency_key=pkey, text="POVU 500 ml back in stock")

    async def mk_post():
        async with AsyncSessionLocal() as db:
            return await sp.create_post(pbody, db, alice)
    r = await asyncio.gather(*(mk_post() for _ in range(4)))
    assert len({x["id"] for x in r}) == 1

    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.count()).select_from(AdDraft).where(AdDraft.idempotency_key == key))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(SocialPost).where(SocialPost.idempotency_key == pkey))).scalar_one() == 1
        did = (await db.execute(select(AdDraft.id).where(AdDraft.idempotency_key == key))).scalar_one()
        await ep.draft_action(did, "request", db, alice)
        await ep.draft_action(did, "reject", db, bob)
        out = await ep.draft_action(did, "request", db, alice)
        assert out["status"] == "PENDING" and out["approved_by"] is None          # stale reviewer cleared


def test_locale_smart_block():
    from app.services import email_design_service as eds
    doc = eds.validate({"blocks": [{"type": "text", "text": "Habari", "audience": {"language": ["sw"]}},
                                    {"type": "text", "text": "Hello", "audience": {"language": ["en"]}},
                                    {"type": "footer", "text": "POVU"}]})[0]
    assert "Habari" in eds.render_text(doc, {"language": "sw"}) and "Hello" not in eds.render_text(doc, {"language": "sw"})
    assert "Habari" not in eds.render_text(doc, {"language": None})          # unknown language → hidden


def test_asset_signature_and_usability():
    from types import SimpleNamespace as NS
    from app.api.v1.endpoints import marketing_assets as ma
    from app.models.documents import DocumentCategory, DocumentStatus
    did = uuid.uuid4()
    assert ma.sign(did) == ma.sign(did) and ma.sign(did) != ma.sign(uuid.uuid4())
    ok = NS(category=DocumentCategory.MARKETING_CREATIVE, status=DocumentStatus.APPROVED, is_latest=True,
            file_scan_status="CLEAN", mime_type="image/png", storage_key="a" * 32, storage_provider="local")
    assert ma._usable(ok)
    for change in ({"status": DocumentStatus.ARCHIVED}, {"is_latest": False}, {"file_scan_status": "NOT_SCANNED"},
                   {"mime_type": "application/pdf"}, {"category": DocumentCategory.INVOICE}):
        assert not ma._usable(NS(**{**ok.__dict__, **change}))


@DB
@pytest.mark.asyncio
async def test_portal_chat_identity_and_deal_journey():
    from datetime import datetime, timedelta, timezone
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMContactAssociation, CRMRecord, WebEvent, WebIdentity
    from app.models.portal import PortalAccount, PortalAccountStatus, PortalUser
    from app.services import crm_chat_service as chat
    from app.services import web_analytics_service as wa
    async with AsyncSessionLocal() as db:
        acc = PortalAccount(account_code=f"PA-{uuid.uuid4().hex[:6]}", portal_status=PortalAccountStatus.ACTIVE)
        db.add(acc)
        await db.flush()
        pu = PortalUser(portal_account_id=acc.id, full_name="Amina Synthetic", email=f"amina-{uuid.uuid4().hex[:4]}@povu-demo.test")
        db.add(pu)
        await db.flush()
        sess, _ = await chat.start(db, ip="127.0.0.9", name="typed name", email="typed@example.com", consent=False,
                                   page_url=None, honeypot=None, portal_user=pu)
        assert (sess.portal_account_id, sess.visitor_name, sess.visitor_email) == (acc.id, "Amina Synthetic", pu.email)
        assert sess.consent_given is False                       # identity is not marketing consent
        anon, _ = await chat.start(db, ip="127.0.0.10", name="Visitor", email=None, consent=False, page_url=None, honeypot=None)
        assert anon.portal_account_id is None
        # deal journey: merged, time-ordered events of the deal's contacts
        rec = CRMRecord(company_name="POVU Synthetic Outlet")
        db.add(rec)
        await db.flush()
        e1, e2 = f"d1-{uuid.uuid4().hex[:4]}@povu-demo.test", f"d2-{uuid.uuid4().hex[:4]}@povu-demo.test"
        now = datetime.now(timezone.utc)
        for i, e in enumerate((e1, e2)):
            c = CRMContact(full_name=f"Deal contact {i}", email=e)
            db.add(c)
            await db.flush()
            db.add(CRMContactAssociation(contact_id=c.id, object_type="crm_record", object_id=rec.id, label="primary", created_at=now))
            vh = f"vh-{uuid.uuid4().hex}"[:64]
            db.add(WebIdentity(visitor_hash=vh, email=e, linked_at=now))
            db.add(WebEvent(visitor_hash=vh, session_id="s", event_id=uuid.uuid4().hex, kind="PAGE", path=f"/p{i}",
                            occurred_at=now - timedelta(minutes=10 - i)))
        await db.flush()
        j = await wa.deal_journey(db, rec.id)
        assert j["contacts"] >= 2 and j["linked"] >= 2
        mine = [ev for ev in j["events"] if ev["email"] in (e1, e2)]
        assert [ev["path"] for ev in mine] == ["/p0", "/p1"]
        await db.rollback()
