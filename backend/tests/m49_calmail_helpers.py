"""Shared fixtures for the M49.S01.T001-T003 DB tests (run with M49_DB=1 on a disposable PostgreSQL).

Builds, in process: the OAuth simulator (provider_sim.app) with the calendar / shared-mail simulator mounted at /cm,
and a small ERP app that mounts the new routers (the coordinator registers them in module_registry; the tests do not
depend on that) with a header-selected test user. Provider traffic and webhook callbacks both stay in memory.
"""
from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime
from email.message import EmailMessage as Mime
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi import FastAPI, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import provider_http
from app.core.config import settings
from tests.provider_sim import create_app, sim_settings
from tests.provider_sim.calmail_app import calmail_settings, create_calmail_app

M49_DB = os.environ.get("M49_DB") == "1"
requires_db = pytest.mark.skipif(not M49_DB, reason="requires the task-owned disposable PostgreSQL (M49_DB=1)")
SIM = "http://127.0.0.1:8765"
ERP = "http://erp.test"


def make_erp_app() -> FastAPI:
    from app.api.v1.endpoints import (calendar_hooks_public, calendar_subscriptions, meeting_series, meetings,
                                      shared_mailboxes)
    from app.core.deps import get_current_user
    from app.db.session import AsyncSessionLocal
    from app.models.role import Role
    from app.models.user import User

    app = FastAPI()
    for mod, prefix in ((meeting_series, "/api/v1/meeting-series"), (calendar_subscriptions, "/api/v1/calendar-subscriptions"),
                        (calendar_hooks_public, "/api/v1/public/calendar-hooks"), (shared_mailboxes, "/api/v1/shared-mailboxes"),
                        (meetings, "/api/v1/meetings")):
        app.include_router(mod.router, prefix=prefix)

    async def current_user(request: Request):
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                                  .where(User.id == uuid.UUID(request.headers["x-test-user"])))).scalar_one()
            db.expunge(u)
            return u

    app.dependency_overrides[get_current_user] = current_user
    return app


class Env:
    def __init__(self, monkeypatch):
        self.main = create_app()
        st = self.main.state.sim
        self.erp = make_erp_app()

        async def deliver(method, url, headers, body):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.erp)) as c:
                r = await c.request(method, url, headers=headers, content=body)
            return r.status_code, r.text, r.headers.get("content-type", "")

        self.cm = create_calmail_app(token_ok=lambda t: st["access"].get(t), deliver=deliver)
        self.main.mount("/cm", self.cm)
        for k, v in {**sim_settings(SIM), **calmail_settings(SIM)}.items():
            monkeypatch.setattr(settings, k, v)
        monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
        monkeypatch.setattr(settings, "PUBLIC_API_URL", ERP)
        provider_http.set_test_transport(httpx.ASGITransport(app=self.main))

    def use_main_gmail(self, monkeypatch):
        """Personal invitation mail goes to the base simulator (its sent list), calendar / shared mail to /cm."""
        monkeypatch.setattr(settings, "GOOGLE_GMAIL_API_URL", f"{SIM}/gmail/v1")

    async def ctl(self, body: dict):
        async with provider_http.provider_client() as c:
            r = await c.post(f"{SIM}/cm/_control", json=body)
            assert r.status_code == 200, r.text
            return r.json()

    async def main_ctl(self, body: dict):
        async with provider_http.provider_client() as c:
            await c.post(f"{SIM}/_control", json=body)

    async def cm_get(self, path: str):
        async with provider_http.provider_client() as c:
            return (await c.get(f"{SIM}/cm{path}")).json()

    async def notify(self, body: dict) -> dict:
        async with provider_http.provider_client() as c:
            r = await c.post(f"{SIM}/cm/_control/notify", json=body)
            assert r.status_code == 200, r.text
            return r.json()

    def api(self, user) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.erp), base_url=ERP,
                                 headers={"x-test-user": str(user.id)})

    async def connect(self, db, user, provider: str, purpose: str, email: str):
        """OAuth connect of one synthetic account; binds the issued token to that e-mail in the /cm simulator."""
        from app.services import oauth_service as oauth
        from app.services.mail_api_adapters import ensure_mail_account
        await self.main_ctl({"email": {provider: email}})
        await self.ctl({"default_email": {provider: email}})
        url = await oauth.start(db, user.id, provider, purpose)
        parts = urlsplit(url)
        form = {k: v[0] for k, v in parse_qs(parts.query).items()}
        async with provider_http.provider_client() as c:
            r = await c.post(f"{parts.scheme}://{parts.netloc}{parts.path}", data={**form, "decision": "allow"})
        back = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
        conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
        if purpose == "mail":
            await ensure_mail_account(db, conn)
        await db.commit()
        await self.ctl({"identities": {oauth._dec(conn.access_token_enc): email}})
        return conn


@pytest.fixture
def env(monkeypatch):
    e = Env(monkeypatch)
    yield e
    provider_http.set_test_transport(None)


@pytest.fixture(autouse=True)
async def _tables_and_dispose():
    if M49_DB:
        from app.db.base import Base
        from app.db.session import engine
        import app.models.m49_calendar_mail as m
        tables = [t.__table__ for t in (m.MeetingSeries, m.MeetingSeriesOccurrence, m.MeetingSeriesCalendarLink, m.CalendarSubscription,
                                        m.CalendarWebhookReceipt, m.SharedMailbox, m.SharedMailboxMember)]
        from sqlalchemy import text
        async with engine.begin() as c:
            await c.run_sync(lambda s: Base.metadata.create_all(s, tables=tables, checkfirst=True))
            await c.execute(text("TRUNCATE " + ", ".join(t.name for t in tables) + " CASCADE"))   # tests share one database
    yield
    if M49_DB:
        from app.db.session import engine
        await engine.dispose()


async def new_user(db, name: str = "rep", superuser: bool = False):
    from app.models.user import User
    u = User(id=uuid.uuid4(), email=f"{name}-{uuid.uuid4().hex[:8]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}",
             hashed_password="x", full_name=f"Synthetic {name}", is_active=True, is_superuser=superuser)
    db.add(u)
    await db.commit()
    return u


def mime(frm: str, to: str, subject: str, mid: str, body: str = "Synthetic body", attach: bool = False,
         reply_to: str | None = None) -> str:
    m = Mime()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = frm, to, subject, mid
    if reply_to:
        m["In-Reply-To"] = m["References"] = reply_to
    m.set_content(body)
    if attach:
        m.add_attachment(b"synthetic POVU AllClean 1 L price list", maintype="application", subtype="pdf", filename="prices.pdf")
    return base64.b64encode(m.as_bytes()).decode()


def future(days: int = 30, hour: int = 9) -> datetime:
    from datetime import timedelta
    return (datetime.utcnow() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
