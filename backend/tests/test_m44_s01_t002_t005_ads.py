"""M44.S01.T002–T005 ad platform adapters against the local ads simulator (contract tests, no network, no accounts).

Meta: paging cursor, purchase actions → conversions, token expiry (190) → AUTH, user limit (17) → RATE_LIMIT,
validate_only draft in minor units. Google: searchStream batches, micros → currency, developer-token header,
account hierarchy, UNAUTHENTICATED / RESOURCE_EXHAUSTED, validateOnly partial failure. LinkedIn: LinkedIn-Version
and Rest.li headers, paged accounts, campaign names, 403 → PERMISSION, 429 Retry-After, access-tier gating.
TikTok: Access-Token header, page_info paging, code 40105 → AUTH, 40100 → RATE_LIMIT, callback signature.
Not configured → NOT_CONFIGURED; egress off → blocked. DB part (M44_DB=1): sync twice = same rows; guardrail;
idempotent drafts; second-editor approval; publish refused.
"""
import hashlib
import hmac
import os
import time
import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import ads_adapters as ads
from tests.provider_sim.ads_app import ads_sim_settings, create_ads_app

BASE = "http://ads.test"
D1, D2 = date(2026, 11, 21), date(2026, 11, 22)


@pytest.fixture
def sim(monkeypatch):
    app = create_ads_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in ads_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def _fault(provider, kind):
    async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
        await c.post("/_control", json={"faults": {provider: [kind]}})


@pytest.mark.asyncio
async def test_meta_contract(sim):
    m = ads.ADAPTERS["meta"]
    rows = await m.report("1001", D1, D1)
    assert [r.campaign_id for r in rows] == ["m1", "m2"]                     # second page followed
    assert rows[0].spend == Decimal("512.75") and rows[0].conversions == 3 and rows[0].clicks == 25
    assert (await m.accounts())[0]["currency"] == "KES"
    for kind, want in (("auth", "AUTH"), ("rate", "RATE_LIMIT"), ("perm", "PERMISSION")):
        await _fault("meta", kind)
        with pytest.raises(ads.AdsError) as e:
            await m.report("1001", D1, D1)
        assert e.value.kind == want
    ok = await m.validate("1001", {"name": "POVU test", "objective": "OUTCOME_AWARENESS", "daily_budget": "12.50"}, "KES")
    assert ok["provider_checked"] and ok["result"]["success"]
    with pytest.raises(ads.AdsError) as e:
        await m.validate("1001", {"name": "x", "objective": "OUTCOME_AWARENESS", "daily_budget": "0.50"}, "KES")
    assert e.value.kind == "VALIDATION"
    assert ads.minor_units(Decimal("12.50"), "KES") == 1250 and ads.minor_units(Decimal("500"), "JPY") == 500


@pytest.mark.asyncio
async def test_google_contract(sim):
    g = ads.ADAPTERS["google"]
    rows = await g.report("444-555-6666", D1, D2)
    assert [r.spend for r in rows] == [Decimal("1234.56"), Decimal("990")] and rows[1].conversions == Decimal("2.5")
    assert (await g.accounts())[0]["external_id"] == "4445556666"
    await _fault("google", "rate")
    with pytest.raises(ads.AdsError) as e:
        await g.report("4445556666", D1, D2)
    assert e.value.kind == "RATE_LIMIT"
    await _fault("google", "auth")
    with pytest.raises(ads.AdsError) as e:
        await g.report("4445556666", D1, D2)
    assert e.value.kind == "AUTH"
    assert (await g.validate("4445556666", {"name": "n", "objective": "SEARCH", "daily_budget": "20"}, "KES"))["ok"]
    bad = await g.validate("4445556666", {"name": "n", "objective": "SEARCH", "daily_budget": "0.5"}, "KES")
    assert bad["ok"] is False and bad["partial_failure"]


@pytest.mark.asyncio
async def test_linkedin_contract(sim, monkeypatch):
    li = ads.ADAPTERS["linkedin"]
    assert [a["external_id"] for a in await li.accounts()] == ["5001", "5002"]          # paged
    rows = await li.report("5001", D1, D1)
    assert rows[0].campaign_name == "POVU B2B Distributors" and rows[0].spend == Decimal("88.40")
    await _fault("linkedin", "perm")
    with pytest.raises(ads.AdsError) as e:
        await li.report("5001", D1, D1)
    assert e.value.kind == "PERMISSION"
    await _fault("linkedin", "rate")
    with pytest.raises(ads.AdsError) as e:
        await li.report("5001", D1, D1)
    assert e.value.kind == "RATE_LIMIT" and e.value.retry_after == 30
    monkeypatch.setattr(settings, "LINKEDIN_ADS_VERSION", "202001")
    with pytest.raises(ads.AdsError) as e:
        await li.accounts()
    assert e.value.kind == "VERSION"
    v = await li.validate("5001", {"name": "n", "objective": "LEAD_GENERATION", "daily_budget": "5"}, "USD")
    assert not v["ok"] and len(v["problems"]) == 2                                      # dev tier + minimum


@pytest.mark.asyncio
async def test_tiktok_contract(sim, monkeypatch):
    t = ads.ADAPTERS["tiktok"]
    rows = await t.report("7001", D1, D2)
    assert [r.day for r in rows] == [D1, D2] and rows[1].spend == Decimal("55.50")
    for kind, want in (("auth", "AUTH"), ("rate", "RATE_LIMIT")):
        await _fault("tiktok", kind)
        with pytest.raises(ads.AdsError) as e:
            await t.report("7001", D1, D2)
        assert e.value.kind == want
    monkeypatch.setattr(settings, "TIKTOK_ADS_APP_SECRET", "sim-secret")
    body, ts = b'{"event":"ad.review"}', int(time.time())
    sig = hmac.new(b"sim-secret", f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    assert ads.verify_tiktok_callback(body, f"t={ts},s={sig}")
    assert not ads.verify_tiktok_callback(body + b" ", f"t={ts},s={sig}")
    assert not ads.verify_tiktok_callback(body, f"t={ts - 3600},s={sig}")


@pytest.mark.asyncio
async def test_not_configured_and_egress_off(monkeypatch):
    monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "")
    with pytest.raises(ads.AdsError) as e:
        await ads.ADAPTERS["meta"].report("1", D1, D1)
    assert e.value.kind == "NOT_CONFIGURED"
    monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "x")
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "off")
    with pytest.raises(provider_http.EgressBlocked):
        await ads.ADAPTERS["meta"].report("1", D1, D1)


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@DB
@pytest.mark.asyncio
async def test_sync_idempotent_and_draft_rules(sim):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from sqlalchemy import func, select
    from app.api.v1.endpoints import ads as ep
    from app.db.session import AsyncSessionLocal
    from app.models.crm import AdAccount, AdCampaignDay
    from app.services import ads_service as svc
    async with AsyncSessionLocal() as db:
        a = AdAccount(provider="google", external_id=f"9{uuid.uuid4().int % 10**9}", name="POVU sim", currency="KES")
        db.add(a)
        await db.flush()
        for _ in range(2):
            await svc.sync(db, a, D1, D2)
        n = (await db.execute(select(func.count()).select_from(AdCampaignDay).where(AdCampaignDay.account_id == a.id))).scalar_one()
        assert n == 2
        await db.commit()
        alice, bob = SimpleNamespace(username="alice", is_superuser=True), SimpleNamespace(username="bob", is_superuser=True)
        body = ep.DraftIn(account_id=a.id, idempotency_key=f"k-{uuid.uuid4().hex[:12]}", name="POVU Juice",
                          objective="SEARCH", daily_budget=Decimal("20"))
        d1 = await ep.create_draft(body, db, alice)
        assert (await ep.create_draft(body, db, alice))["id"] == d1["id"]
        with pytest.raises(HTTPException) as e:
            await ep.create_draft(body.model_copy(update={"idempotency_key": f"k-{uuid.uuid4().hex[:12]}",
                                                          "daily_budget": Decimal("5000")}), db, alice)
        assert e.value.status_code == 422
        did = uuid.UUID(d1["id"])
        await ep.draft_action(did, "request", db, alice)
        with pytest.raises(HTTPException):
            await ep.draft_action(did, "approve", db, alice)
        assert (await ep.draft_action(did, "approve", db, bob))["status"] == "APPROVED"
        assert (await ep.draft_action(did, "validate", db, bob))["validation"]["ok"]
        with pytest.raises(HTTPException) as e:
            await ep.draft_action(did, "publish", db, bob)
        assert e.value.status_code == 403
