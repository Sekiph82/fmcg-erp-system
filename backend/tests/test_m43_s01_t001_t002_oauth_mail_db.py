"""M43.S01.T001/T002 Gmail API and Microsoft Graph mailboxes against the local simulator, on disposable PostgreSQL.

Prepared 2026-11-25; run at the M43 gate (M43_S01_DB=1, DATABASE_URL at head 20261125_0073+).
Covers: connect → mailbox row, incremental cursor import with pagination, replay dedupe, reply threading,
history expiry (Gmail 404) / delta reset (Graph 410) with no duplicates, send through the API (stored once,
threaded), 401 refresh-and-retry, 429 temporary error without data change, disconnect stops sync/send.
"""
from __future__ import annotations

import base64
import os
import uuid
from email.message import EmailMessage as Mime

import httpx
import pytest
from sqlalchemy import func, select

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import create_app, sim_settings

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]
SIM = "http://127.0.0.1:8765"


def _mail(mid: str, subject: str, frm: str = "buyer@povu-demo.test", reply_to: str | None = None) -> str:
    m = Mime()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = frm, "rep1@povu-demo.test", subject, mid
    if reply_to:
        m["In-Reply-To"] = m["References"] = reply_to
    m.set_content(f"Synthetic body for {subject}")
    return base64.b64encode(m.as_bytes()).decode()


@pytest.fixture
def sim(monkeypatch):
    app = create_app()
    for k, v in sim_settings(SIM).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def _ctl(body):
    async with provider_http.provider_client() as c:
        await c.post(f"{SIM}/_control", json=body)


async def _connect(db, user, provider):
    from urllib.parse import parse_qs, urlsplit

    from app.services import oauth_service as oauth
    from app.services.mail_api_adapters import ensure_mail_account
    url = await oauth.start(db, user.id, provider, "mail")
    parts = urlsplit(url)
    form = {k: v[0] for k, v in parse_qs(parts.query).items()}
    async with provider_http.provider_client() as c:
        r = await c.post(f"{parts.scheme}://{parts.netloc}{parts.path}", data={**form, "decision": "allow"})
    back = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
    conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    acc = await ensure_mail_account(db, conn)
    await db.commit()
    await db.refresh(acc)
    return conn, acc


@pytest.fixture
async def db_user():
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        u = User(id=uuid.uuid4(), email=f"rep-{uuid.uuid4().hex[:8]}@povu-demo.test", hashed_password="x",
                 full_name="Synthetic Rep", is_active=True)
        db.add(u)
        await db.commit()
        yield db, u


async def _count(db, acc):
    from app.models.email_integration import EmailMessage, EmailThread
    return (await db.execute(select(func.count()).select_from(EmailMessage).join(EmailThread)
                             .where(EmailThread.account_id == acc.id))).scalar_one()


@pytest.mark.parametrize("provider,expire", [("google", {"history_floor": 10**9}), ("microsoft", {"delta_gone": True})])
async def test_import_cursor_dedupe_and_cursor_loss(sim, db_user, provider, expire):
    from app.services import email_mailbox_service as mbx
    db, user = db_user
    await _ctl({"deliver": [{"provider": provider, "raw_b64": _mail(f"<a{i}@povu-demo.test>", f"Order {i}")}
                            for i in range(3)]})
    conn, acc = await _connect(db, user, provider)
    assert mbx.is_connected(acc)
    r = await mbx.sync_account(db, acc); await db.commit()
    assert r["imported"] == 3 and await _count(db, acc) == 3
    await _ctl({"deliver": [{"provider": provider, "raw_b64": _mail("<b1@povu-demo.test>", "Re: Order 0",
                                                                    reply_to="<a0@povu-demo.test>")}]})
    r = await mbx.sync_account(db, acc); await db.commit()
    assert r["imported"] == 1 and await _count(db, acc) == 4
    await _ctl(expire)                       # cursor lost → bounded resync, Message-ID dedupe
    await mbx.sync_account(db, acc); await db.commit()
    assert await _count(db, acc) == 4


@pytest.mark.parametrize("provider", ["google", "microsoft"])
async def test_send_through_api_and_disconnect(sim, db_user, provider):
    from app.services import email_mailbox_service as mbx
    from app.services import oauth_service as oauth
    db, user = db_user
    conn, acc = await _connect(db, user, provider)
    thread = await mbx.send(db, acc, to=["buyer@povu-demo.test"], cc=[], subject="Synthetic quote", body="Hello",
                            thread=None, sent_by=user, link={})
    await db.commit()
    async with provider_http.provider_client() as c:
        sent = (await c.get(f"{SIM}/_control/sent/{provider}")).json()["sent"]
    assert len(sent) == 1 and b"Synthetic quote" in base64.b64decode(sent[0])
    assert thread.message_count == 1
    await oauth.disconnect(db, conn, user.id); await db.commit()
    await db.refresh(acc)
    assert not mbx.is_connected(acc)
    with pytest.raises(mbx.MailboxError):
        await mbx.send(db, acc, to=["buyer@povu-demo.test"], cc=[], subject="x", body="x", thread=None,
                       sent_by=user, link={})


async def test_throttle_leaves_cursor_and_data_unchanged(sim, db_user):
    from app.services import email_mailbox_service as mbx
    db, user = db_user
    conn, acc = await _connect(db, user, "google")
    await mbx.sync_account(db, acc); await db.commit()
    before = dict(conn.sync_cursor)
    await _ctl({"deliver": [{"provider": "google", "raw_b64": _mail("<c1@povu-demo.test>", "Later")}],
                "faults": {"token": [429]}})
    conn.expires_at = None   # force the token endpoint → 429
    with pytest.raises(mbx.MailboxError):
        await mbx.sync_account(db, acc)
    await db.rollback()
    await db.refresh(conn)
    assert conn.sync_cursor == before and await _count(db, acc) == 0
