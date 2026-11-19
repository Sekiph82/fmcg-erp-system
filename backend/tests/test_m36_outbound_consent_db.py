"""M36 consent register + outbox on disposable PostgreSQL with a real local SMTP server (Mailpit):
dedupe, consent requirements, suppression at queue and send time, one-click unsubscribe, no fake SENT."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMOutboundMessage
from app.services import crm_outbound_service as outbound

TASK_DB_ENV = "M36_OUTBOUND_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_OUTBOUND_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_outbound_[a-f0-9]{24}")
SMTP = os.environ.get("SMTP_TEST_SERVER", "")        # e.g. 127.0.0.1:51025 (local Mailpit)
MAILPIT_API = os.environ.get("MAILPIT_TEST_API", "")  # e.g. http://127.0.0.1:58025

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1" or not SMTP.startswith("127.0.0.1:"),
                                reason="requires the task-owned disposable PostgreSQL and a local test SMTP server")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_outbox_consent_suppression_and_real_smtp_delivery(monkeypatch):
    from app.main import app

    s = uuid4().hex[:8]
    opted, cold, quitter = f"opted-{s}@example.com", f"cold-{s}@example.com", f"quit-{s}@example.com"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        await outbound.record_consent(db, opted, "SUBSCRIBED", "form:test", "You may e-mail me.")
        await outbound.record_consent(db, quitter, "SUBSCRIBED", "form:test", "You may e-mail me.")
        a = await outbound.queue(db, to_email=opted.upper(), subject="Hello", body="Offer", purpose="SEQUENCE", dedupe_key=f"seq:{s}:1")
        again = await outbound.queue(db, to_email=opted, subject="Hello", body="Offer", purpose="SEQUENCE", dedupe_key=f"seq:{s}:1")
        no_consent = await outbound.queue(db, to_email=cold, subject="Hi", body="x", purpose="CAMPAIGN", dedupe_key=f"camp:{s}:1")
        manual = await outbound.queue(db, to_email=cold, subject="Your quote", body="Attached", purpose="MANUAL", dedupe_key=f"man:{s}:1")
        late = await outbound.queue(db, to_email=quitter, subject="Hi", body="x", purpose="SEQUENCE", dedupe_key=f"seq:{s}:2")
        inj = await outbound.queue(db, to_email=opted, subject="Hi\r\nBcc: victim@example.com", body="x",
                                   purpose="MANUAL", dedupe_key=f"man:{s}:inj")
        assert "\n" not in inj.subject and "\r" not in inj.subject  # no header injection
        bounced = f"bounce-{s}@example.com"
        await outbound.record_consent(db, bounced, "BOUNCED", "manual:test")
        assert (await outbound.record_consent(db, bounced, "SUBSCRIBED", "form:test")).status == "BOUNCED"
        gone = f"gone-{s}@example.com"
        await outbound.record_consent(db, gone, "UNSUBSCRIBED", "unsubscribe-link")
        assert (await outbound.record_consent(db, gone, "SUBSCRIBED", "form:test")).status == "UNSUBSCRIBED"  # forms never re-subscribe
        assert (await outbound.record_consent(db, gone, "SUBSCRIBED", "manual:x", may_lift_unsubscribe=True)).status == "SUBSCRIBED"
        long_key = "k" * 250
        first = await outbound.queue(db, to_email=opted, subject="x", body="x", purpose="MANUAL", dedupe_key=long_key)
        assert (await outbound.queue(db, to_email=opted, subject="x", body="x", purpose="MANUAL", dedupe_key=long_key)).id == first.id
        first.status = "CANCELLED"
        inj.status = "CANCELLED"
        await db.commit()
        assert again.id == a.id and a.to_email == opted                    # same dedupe key -> one message
        assert (no_consent.status, no_consent.status_reason) == ("SUPPRESSED", "no marketing consent on record")
        assert (manual.status, late.status) == ("QUEUED", "QUEUED")
        ids = (a.id, manual.id, late.id)

        # delivery off: nothing is sent and nothing pretends to be
        monkeypatch.setattr(settings, "CRM_OUTBOUND_EMAIL_ENABLED", False)
        assert (await outbound.deliver_due(db))["sent"] == 0
        first = await db.get(CRMOutboundMessage, ids[0])
        assert first.status == "QUEUED", first.status_reason

    # the quitter unsubscribes through the public one-click endpoint (no login) before delivery
    token = outbound.unsubscribe_token(quitter)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get(f"/api/v1/public/unsubscribe?t={token}")).json()["unsubscribed"] is False  # GET never changes state
        assert (await c.post(f"/api/v1/public/unsubscribe?t={token}")).json()["unsubscribed"] is True
        assert (await c.post(f"/api/v1/public/unsubscribe?t={token[:-2]}xx")).status_code == 404       # tampered token
        from types import SimpleNamespace

        from app.core.deps import get_current_user

        perms = [SimpleNamespace(code=x, module="crm", action=x.split(".")[1], is_active=True) for x in ("crm.view", "crm.edit")]
        editor = SimpleNamespace(id=uuid4(), username=f"ed{s}", is_superuser=False, is_active=True, access_scopes=[],
                                 roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])
        app.dependency_overrides[get_current_user] = lambda: editor
        try:
            r = await c.post("/api/v1/crm/outbox", json={"to_email": "anyone@example.com", "subject": "x", "body": "y"})
            assert r.status_code == 403                                       # no free addresses for record editors
            r = await c.post("/api/v1/crm/outbox", json={"to_email": "a@example.com", "subject": "x\r\nBcc: v@x.com", "body": "y"})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    host, port = SMTP.split(":")
    monkeypatch.setattr(settings, "CRM_OUTBOUND_EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", host)
    monkeypatch.setattr(settings, "SMTP_PORT", int(port))
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    async with AsyncSessionLocal() as db:
        result = await outbound.deliver_due(db)
        assert result["sent"] >= 2 and result["suppressed"] >= 1
        sent, man, quit_msg = [await db.get(CRMOutboundMessage, i) for i in ids]
        assert (sent.status, man.status) == ("SENT", "SENT") and sent.provider_message_id
        assert (quit_msg.status, quit_msg.status_reason) == ("SUPPRESSED", "address is unsubscribed")
        assert (await outbound.deliver_due(db))["sent"] == 0               # nothing is sent twice

        # an unreachable server leaves the message queued for retry, never SENT
        retry = await outbound.queue(db, to_email=opted, subject="Retry", body="x", purpose="SEQUENCE", dedupe_key=f"seq:{s}:3")
        await db.commit()
        monkeypatch.setattr(settings, "SMTP_PORT", 1)
        await outbound.deliver_due(db)
        await db.refresh(retry)
        assert (retry.status, retry.attempts) == ("QUEUED", 1) and retry.status_reason

    if MAILPIT_API:
        msgs = httpx.get(f"{MAILPIT_API}/api/v1/search", params={"query": f"to:{opted}"}).json()["messages"]
        assert len(msgs) == 1
        raw = httpx.get(f"{MAILPIT_API}/api/v1/message/{msgs[0]['ID']}/headers").json()
        assert raw["List-Unsubscribe-Post"] == ["List-Unsubscribe=One-Click"]
        assert outbound.unsubscribe_token(opted) in raw["List-Unsubscribe"][0]
        assert httpx.get(f"{MAILPIT_API}/api/v1/search", params={"query": f"to:{quitter}"}).json()["messages"] == []
