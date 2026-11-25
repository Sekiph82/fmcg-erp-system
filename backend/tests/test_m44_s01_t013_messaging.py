"""M44.S01.T013 messaging channels (unit + DB part with M44_DB=1).

Unit: no page token → reply refused NOT_CONFIGURED; Slack tick without a webhook URL does nothing.
DB: signed Messenger / Instagram webhooks create one conversation (replay and echo dedupe), forged ones are refused,
unregistered pages are ignored; replies go through the simulator Send API inside the 24-hour window and are
refused outside it; Slack notices reach the local stub once and retry after a failure; a custom channel message is
threaded in the inbox, the reply comes back through the outbox once, a wrong token is refused; permissions.
"""
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import messaging_service as ms
from tests.provider_sim.ads_app import create_ads_app, social_sim_settings

BASE = "http://ads.test"
SECRET = "sim-app-secret"


@pytest.mark.asyncio
async def test_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "META_PAGE_ACCESS_TOKEN", "")
    with pytest.raises(ms.MessagingError, match="NOT_CONFIGURED") as e:
        await ms.reply(None, "MESSENGER", "pg:1", "hi", None)
    assert e.value.status == 503
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "")
    assert (await ms.slack_tick(None))["status"] == "NOT_CONFIGURED"


def test_token_and_key_rules():
    t, h = ms.new_token()
    assert t.startswith("pcc_") and h == ms.token_hash(t) and h != ms.token_hash(t + "x")
    assert ms.KEY_RE.match("partner-app") and not ms.KEY_RE.match("Partner App") and not ms.KEY_RE.match("-x")


@pytest.fixture
def sim(monkeypatch):
    app = create_ads_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in social_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "META_APP_SECRET", SECRET)
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", f"{BASE}/slack/hook")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def _sim_calls(provider):
    async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
        return [x for x in (await c.get("/_control/calls")).json() if x["provider"] == provider]


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _admin():
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        u = User(id=uuid.uuid4(), email=f"adm-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}",
                 hashed_password="x", full_name="Admin", is_active=True, is_superuser=True)
        db.add(u)
        await db.commit()
        return SimpleNamespace(id=u.id, username=u.username, is_superuser=True, company_id=None)


def _signed(payload: dict) -> tuple[bytes, dict]:
    raw = json.dumps(payload).encode()
    return raw, {"X-Hub-Signature-256": "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest(),
                 "Content-Type": "application/json"}


def _dm(obj, acct, psid, mid, text, ts=None, echo=False):
    who = {"sender": {"id": acct}, "recipient": {"id": psid}} if echo else {"sender": {"id": psid}, "recipient": {"id": acct}}
    return {"object": obj, "entry": [{"id": acct, "time": 1, "messaging": [{
        **who, "timestamp": ts or int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": {"mid": mid, "text": text, **({"is_echo": True} if echo else {})}}]}]}


@DB
@pytest.mark.asyncio
async def test_meta_dms_into_inbox_and_reply(sim):
    from fastapi import HTTPException
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from app.api.v1.endpoints import crm_channels as ep
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.crm import CRMChannelMessage, CRMConversation, SocialChannel
    from app.services import crm_inbox_service as inbox

    tag = uuid.uuid4().hex[:8]
    page, ig, psid = f"pg{tag}", f"ig{tag}", f"u{tag}"
    admin = await _admin()
    async with AsyncSessionLocal() as db:
        db.add_all([SocialChannel(network="facebook", external_id=page, name="POVU Page"),
                    SocialChannel(network="instagram", external_id=ig, name="POVU IG")])
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        raw, h = _signed(_dm("page", page, psid, f"m1{tag}", "Is POVU mango available in 1L?"))
        assert (await c.post("/api/v1/public/social/meta", content=raw, headers=h)).json()["messages"] == 1
        assert (await c.post("/api/v1/public/social/meta", content=raw, headers=h)).json()["messages"] == 0   # replay
        assert (await c.post("/api/v1/public/social/meta", content=raw,
                             headers={**h, "X-Hub-Signature-256": "sha256=" + "0" * 64})).status_code == 403
        raw, h = _signed(_dm("instagram", ig, psid, f"m2{tag}", "Hello from Instagram"))
        assert (await c.post("/api/v1/public/social/meta", content=raw, headers=h)).json()["messages"] == 1
        raw, h = _signed(_dm("page", f"unknown{tag}", psid, f"m3{tag}", "x"))
        assert (await c.post("/api/v1/public/social/meta", content=raw, headers=h)).json()["messages"] == 0
    async with AsyncSessionLocal() as db:
        await inbox.sync(db)
        await db.commit()
        conv = (await db.execute(select(CRMConversation).where(CRMConversation.channel == "MESSENGER",
                                                               CRMConversation.source_ref == f"{page}:{psid}"))).scalar_one()
        assert conv.sla_due_at is not None
        assert (await db.execute(select(CRMConversation).where(CRMConversation.channel == "INSTAGRAM",
                                                               CRMConversation.source_ref == f"{ig}:{psid}"))).scalar_one()
        out = await ep.reply(str(conv.id), ep.ReplyIn(text="Yes, POVU 1L is in stock"), db, admin)
        assert out["status"] == "SENT"
        call = (await _sim_calls("messenger"))[-1]
        assert call["node"] == page and call["json"]["recipient"]["id"] == psid
        mid = (await db.execute(select(CRMChannelMessage.external_id).where(CRMChannelMessage.id == uuid.UUID(out["id"])))).scalar_one()
    # Meta echoes our own send: deduped by message id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        raw, h = _signed(_dm("page", page, psid, mid, "Yes, POVU 1L is in stock", echo=True))
        assert (await c.post("/api/v1/public/social/meta", content=raw, headers=h)).json()["messages"] == 0
    async with AsyncSessionLocal() as db:
        t = await ep.get_thread(str(conv.id), db, admin)
        assert [m["direction"] for m in t["messages"]] == ["IN", "OUT"]
        # outside the 24-hour window: refused
        old = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp() * 1000)
        await ms.ingest_meta(db, _dm("page", page, f"old{tag}", f"m4{tag}", "old", ts=old))
        await inbox.sync(db)
        await db.commit()
        oc = (await db.execute(select(CRMConversation).where(CRMConversation.source_ref == f"{page}:old{tag}"))).scalar_one()
        with pytest.raises(HTTPException) as e:
            await ep.reply(str(oc.id), ep.ReplyIn(text="late"), db, admin)
        assert e.value.status_code == 409
        # a user without CRM rights does not see the conversation
        nobody = SimpleNamespace(id=uuid.uuid4(), username="n", is_superuser=False, company_id=None, roles=[])
        with pytest.raises(HTTPException) as e:
            await ep.get_thread(str(conv.id), db, nobody)
        assert e.value.status_code == 404


@DB
@pytest.mark.asyncio
async def test_custom_channel_and_slack(sim):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from app.api.v1.endpoints import crm_channels as ep
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.crm import CRMConversation, SlackDelivery
    from app.models.helpdesk import HelpdeskTicket
    from app.services import crm_inbox_service as inbox

    tag = uuid.uuid4().hex[:8]
    admin = await _admin()
    async with AsyncSessionLocal() as db:
        ch = await ep.create_custom(ep.CustomIn(key=f"partner-{tag}", name="POVU partner app"), db, admin)
    key, token = ch["key"], ch["token"]
    msg = {"thread_id": "t1", "message_id": "1", "sender": "Duka Moja", "text": "Need 20 crates of POVU juice"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        url = f"/api/v1/public/channels/{key}"
        assert (await c.post(f"{url}/messages", json=msg, headers={"Authorization": "Bearer wrong"})).status_code == 401
        auth = {"Authorization": f"Bearer {token}"}
        assert (await c.post(f"{url}/messages", json=msg, headers=auth)).json() == {"stored": True, "duplicate": False}
        assert (await c.post(f"{url}/messages", json=msg, headers=auth)).json()["duplicate"]
        async with AsyncSessionLocal() as db:
            await inbox.sync(db)
            await db.commit()
            conv = (await db.execute(select(CRMConversation).where(CRMConversation.channel == "CUSTOM",
                                                                   CRMConversation.source_ref == f"{key}:t1"))).scalar_one()
            assert conv.subject == "Channel: Duka Moja"
            assert (await ep.reply(str(conv.id), ep.ReplyIn(text="Confirmed, delivery Friday"), db, admin))["status"] == "QUEUED"
        items = (await c.get(f"{url}/outbox", headers=auth)).json()["items"]
        assert [(i["thread_id"], i["text"]) for i in items] == [("t1", "Confirmed, delivery Friday")]
        assert (await c.get(f"{url}/outbox", headers=auth)).json()["items"] == []        # handed over once
        async with AsyncSessionLocal() as db:
            rot = await ep.custom_action(ch["id"], "rotate", db, admin)
        assert (await c.get(f"{url}/outbox", headers=auth)).status_code == 401           # old token stops
        assert (await c.get(f"{url}/outbox", headers={"Authorization": f"Bearer {rot['token']}"})).status_code == 200

    # Slack: a new ticket is announced once; a failed post is retried
    async with AsyncSessionLocal() as db:
        t = HelpdeskTicket(ticket_no=f"TK-{tag}", subject="POVU bottle leaking (customer phone inside)")
        db.add(t)
        await db.commit()
        async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
            await c.post("/_control", json={"faults": {"slack": ["down"]}})
        await ms.slack_tick(db)
        d = (await db.execute(select(SlackDelivery).where(SlackDelivery.kind == "TICKET", SlackDelivery.ref == str(t.id)))).scalar_one()
        assert d.status == "FAILED" and d.attempts == 1
        await ms.slack_tick(db)
        await db.refresh(d)
        assert d.status == "SENT"
        texts = [x["json"]["text"] for x in await _sim_calls("slack")]
        assert sum(f"TK-{tag}" in x for x in texts) == 1 and not any("phone inside" in x for x in texts)
        await ms.slack_tick(db)
        assert sum(f"TK-{tag}" in x["json"]["text"] for x in await _sim_calls("slack")) == 1
