"""M43.S00.T004 shared integration harness: egress guard and the real OAuth adapter against the local simulator.

Prepared 2026-11-25; executed only at the M43 milestone gate (binding protocol). The DB-backed cases need the
task-owned disposable PostgreSQL (M43_S00_T004_DB=1 + DATABASE_URL at head 20261125_0072); the egress cases run
without a database.
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.core import clock, provider_http
from app.core.config import settings
from tests.provider_sim import create_app, sim_settings

SIM = "http://127.0.0.1:8765"


# ── egress guard (no DB) ────────────────────────────────────────────────────
@pytest.mark.parametrize("mode,url,allowed", [
    ("local", "http://127.0.0.1:8765/google/token", True),
    ("local", "http://sim.povu-demo.test/x", True),
    ("local", "https://oauth2.googleapis.com/token", False),
    ("local", "http://10.0.0.5/token", False),
    ("off", "http://127.0.0.1:8765/x", False),
    ("live", "https://graph.microsoft.com/v1.0/me", True),
    ("live", "http://graph.microsoft.com/v1.0/me", False),
])
def test_egress_policy(monkeypatch, mode, url, allowed):
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", mode)
    if allowed:
        provider_http.check_egress(url)
    else:
        with pytest.raises(provider_http.EgressBlocked):
            provider_http.check_egress(url)


def test_default_mode_is_local_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert provider_http.egress_mode() == "local"
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert provider_http.egress_mode() == "live"


@pytest.mark.asyncio
async def test_client_refuses_real_host_before_sending(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    sent = []
    transport = httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200))
    provider_http.set_test_transport(transport)
    try:
        async with provider_http.provider_client() as c:
            with pytest.raises(provider_http.EgressBlocked):
                await c.get("https://accounts.google.com/")
        assert sent == []
    finally:
        provider_http.set_test_transport(None)


# ── OAuth adapter against the simulator (disposable PostgreSQL) ─────────────
DB = pytest.mark.skipif(os.environ.get("M43_S00_T004_DB") != "1",
                        reason="requires the task-owned disposable PostgreSQL at head 20261125_0072")


@pytest.fixture
def sim(monkeypatch):
    app = create_app()
    for k, v in sim_settings(SIM).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(settings, "PUBLIC_API_URL", "http://127.0.0.1:8000")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture
async def db_user():
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        u = User(id=uuid.uuid4(), email=f"rep-{uuid.uuid4().hex[:8]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}", hashed_password="x",
                 full_name="Synthetic Rep", is_active=True)
        db.add(u)
        await db.commit()
        yield db, u


async def _consent(authorize_url: str, decision: str = "allow") -> dict:
    parts = urlsplit(authorize_url)
    form = {k: v[0] for k, v in parse_qs(parts.query).items()}
    async with provider_http.provider_client() as c:
        r = await c.post(f"{parts.scheme}://{parts.netloc}{parts.path}", data={**form, "decision": decision})
    assert r.status_code == 302
    return {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}


async def _control(body: dict) -> None:
    async with provider_http.provider_client() as c:
        await c.post(f"{SIM}/_control", json=body)


@DB
@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "microsoft"])
async def test_connect_refresh_disconnect(sim, db_user, monkeypatch, provider):
    from app.services import oauth_service as oauth
    db, user = db_user
    url = await oauth.start(db, user.id, provider, "mail")
    q = parse_qs(urlsplit(url).query)
    assert q["code_challenge_method"] == ["S256"] and q["redirect_uri"] == [oauth.redirect_uri()]
    back = await _consent(url)
    conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    await db.commit()
    assert conn.status == "CONNECTED" and conn.account_email == "rep1@povu-demo.test"
    assert "sim-" not in (conn.access_token_enc or "")          # stored encrypted, never in clear
    first = await oauth.access_token(db, conn)
    t0 = clock.utcnow()
    monkeypatch.setattr(clock, "utcnow", lambda: t0 + timedelta(hours=2))   # deterministic expiry
    second = await oauth.access_token(db, conn)
    assert second != first
    await oauth.disconnect(db, conn, user.id)
    await db.commit()
    assert conn.status == "REVOKED" and conn.access_token_enc is None and conn.refresh_token_enc is None
    with pytest.raises(oauth.OAuthReauthRequired):
        await oauth.access_token(db, conn)


@DB
@pytest.mark.asyncio
async def test_state_is_single_use_and_bound(sim, db_user):
    from app.services import oauth_service as oauth
    db, user = db_user
    back = await _consent(await oauth.start(db, user.id, "google", "calendar"))
    await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    with pytest.raises(oauth.OAuthError) as e:                    # replayed callback
        await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    assert e.value.code == "bad_state"


@DB
@pytest.mark.asyncio
async def test_consent_refused_and_scope_missing_connect_nothing(sim, db_user):
    from app.services import oauth_service as oauth
    db, user = db_user
    back = await _consent(await oauth.start(db, user.id, "google", "mail"), decision="deny")
    with pytest.raises(oauth.OAuthError) as e:
        await oauth.complete(db, state=back["state"], code=back.get("code"), error=back.get("error"))
    assert e.value.code == "consent_refused"
    await _control({"drop_scopes": ["https://www.googleapis.com/auth/gmail.send"]})
    back = await _consent(await oauth.start(db, user.id, "google", "mail"))
    with pytest.raises(oauth.OAuthError) as e:
        await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    assert e.value.code == "scope_missing"


@DB
@pytest.mark.asyncio
async def test_provider_throttling_and_revoked_grant(sim, db_user, monkeypatch):
    from app.services import oauth_service as oauth
    db, user = db_user
    back = await _consent(await oauth.start(db, user.id, "microsoft", "calendar"))
    await _control({"faults": {"token": [429]}})
    with pytest.raises(oauth.OAuthTemporaryError) as e:
        await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    assert e.value.retry_after == 2
    back = await _consent(await oauth.start(db, user.id, "microsoft", "calendar"))
    conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    await _control({"faults": {"token": ["invalid_grant"]}})
    t0 = clock.utcnow()
    monkeypatch.setattr(clock, "utcnow", lambda: t0 + timedelta(hours=2))
    with pytest.raises(oauth.OAuthReauthRequired):
        await oauth.access_token(db, conn)
    assert conn.status == "ERROR"


@DB
@pytest.mark.asyncio
async def test_not_configured_never_starts(db_user, monkeypatch):
    from app.services import oauth_service as oauth
    db, user = db_user
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    with pytest.raises(oauth.OAuthError) as e:
        await oauth.start(db, user.id, "google", "mail")
    assert e.value.code == "not_configured" and e.value.status_code == 409


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
