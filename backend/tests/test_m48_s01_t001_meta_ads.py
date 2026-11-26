"""M48.S01.T001 Meta Marketing API mutation adapter against the local simulator (no network, no accounts, no spend).

Unit: campaign → ad set → ad creative → ad payloads (PAUSED, special_ad_categories, minor units, targeting, creative
reference), validate_only creates nothing, rate limit retried without a duplicate, 5xx after create → UNKNOWN and
found by read-back, IN_PROCESS read-back, fail-closed LIVE gate. DB (M48_DB=1): full lifecycle over HTTP with
personas, approvals bound to version/hash, caps, cross-account refusal, UNKNOWN reconciliation, lost write retried.
"""
import json
import os
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import ads_adapters as ads
from tests.m48_ads_support import (DB, client, ctx, create_chain, fault, full_lifecycle, login, lost_then_retry, setup_account,
                                   sim, sim_objects, unknown_then_reconcile)  # noqa: F401  (sim is a fixture)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_meta_tree_payloads_paused_minor_units(sim):
    ids = await create_chain("meta")
    objs = await sim_objects("meta")
    camp, adset, cre, ad = (objs[ids[lv]] for lv in ("CAMPAIGN", "ADSET", "CREATIVE", "AD"))
    assert camp["status"] == "PAUSED" and camp["objective"] == "OUTCOME_TRAFFIC" and camp["daily_budget"] == "6000"
    assert json.loads(camp["special_ad_categories"]) == [] and camp["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert adset["status"] == "PAUSED" and adset["campaign_id"] == ids["CAMPAIGN"] and adset["optimization_goal"] == "LINK_CLICKS"
    assert json.loads(adset["targeting"]) == {"geo_locations": {"countries": ["KE"]}}
    spec = json.loads(cre["object_story_spec"])
    assert spec["page_id"] == "100200300" and spec["link_data"]["link"].startswith("https://povu-demo.test/")
    assert ad["status"] == "PAUSED" and json.loads(ad["creative"]) == {"creative_id": ids["CREATIVE"]}
    assert ads.minor_units(Decimal("60"), "KES") == 6000 and ads.minor_units(Decimal("60"), "JPY") == 60
    b = ads.BUILDERS["meta"]
    body, _ = await ads.send(ads.ADAPTERS["meta"], b.read("AD", ids["AD"], ctx("meta")), safe=True)
    assert b.parse_read("AD", body, ctx("meta"))["status"] == "IN_PROCESS"            # delayed review state first
    body, _ = await ads.send(ads.ADAPTERS["meta"], b.read("AD", ids["AD"], ctx("meta")), safe=True)
    assert b.parse_read("AD", body, ctx("meta"))["status"] == "PAUSED"
    await ads.send(ads.ADAPTERS["meta"], b.status("CAMPAIGN", ids["CAMPAIGN"], True, ctx("meta")), safe=False)
    assert (await sim_objects("meta"))[ids["CAMPAIGN"]]["status"] == "ACTIVE"
    await ads.send(ads.ADAPTERS["meta"], b.budget(ids["CAMPAIGN"], ctx("meta", budget="75.50")), safe=False)
    assert (await sim_objects("meta"))[ids["CAMPAIGN"]]["daily_budget"] == "7550"


@pytest.mark.asyncio
async def test_meta_validate_only_creates_nothing(sim):
    req = ads.BUILDERS["meta"].create("CAMPAIGN", ctx("meta"), validate_only=True)
    body, _ = await ads.send(ads.ADAPTERS["meta"], req, safe=True)
    assert body == {"success": True} and await sim_objects("meta") == {}
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["meta"], ads.BUILDERS["meta"].create("CAMPAIGN", ctx("meta", budget="0.50"),
                                                                        validate_only=True), safe=True)
    assert e.value.kind == "VALIDATION"


@pytest.mark.asyncio
async def test_meta_rate_limit_retried_once_no_duplicate(sim):
    await fault("meta", "rate")
    await create_chain("meta")
    assert len(await sim_objects("meta")) == 4


@pytest.mark.asyncio
async def test_meta_unknown_create_found_by_readback(sim):
    await fault("meta", "unknown")
    x = ctx("meta")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["meta"], ads.BUILDERS["meta"].create("CAMPAIGN", x), safe=False)
    assert e.value.kind == "UNKNOWN"
    found = await ads.find_created("meta", "CAMPAIGN", x)
    assert found in await sim_objects("meta") and len(await sim_objects("meta")) == 1


def test_live_gate_fail_closed(monkeypatch):
    from app.services import ads_service as svc
    acct = SimpleNamespace(provider="meta")
    monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "x")
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    g = svc.gate(acct, None)
    assert g["mode"] == "SIMULATED" and g["transport"] == "http" and len(g["reasons"]) == 3
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
    monkeypatch.setenv("ADS_LIVE_MUTATIONS", "true")
    assert svc.gate(acct, SimpleNamespace(activated=False))["mode"] == "SIMULATED"
    assert svc.gate(acct, SimpleNamespace(activated=True))["mode"] == "LIVE"
    monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "")
    g = svc.gate(acct, SimpleNamespace(activated=True))
    assert g["mode"] == "SIMULATED" and g["transport"] == "offline"


def test_spec_checks_and_objectives():
    p = ads.check_spec("meta", "OUTCOME_SALES", {"link": "http://x"}, Decimal(10), "KES")
    assert any("not offered" in x for x in p) and any("https" in x for x in p) and len(p) == 5


@DB
@pytest.mark.asyncio
async def test_meta_lifecycle_http(sim):
    out = await full_lifecycle("meta", sim)
    camp = next(o for o in out["objs"].values() if o["kind"] == "campaign")
    assert camp["status"] == "PAUSED" and camp["daily_budget"] == "8000"                # v3 pushed in minor units


@DB
@pytest.mark.asyncio
async def test_meta_unknown_reconciled_and_lost_retried(sim):
    await unknown_then_reconcile("meta")
    await lost_then_retry("meta")


@DB
@pytest.mark.asyncio
async def test_meta_admin_controls(sim):
    import uuid
    from app.api.v1.endpoints import ads as ep
    from app.db.session import AsyncSessionLocal
    p = await setup_account("meta")
    async with client() as ca:
        await login(ca, p["author"])
        r = await ca.put(f"/api/v1/ads/accounts/{p['account']}/controls", json={"daily_cap": "1", "monthly_cap": "10"})
        assert r.status_code == 403                                                        # admins only
        assert (await ca.post(f"/api/v1/ads/accounts/{p['account']}/activation", json={"active": True})).status_code == 403
    boss = SimpleNamespace(id=None, username="admin", email=None, full_name=None, is_superuser=True)
    async with AsyncSessionLocal() as db:
        out = await ep.activation(uuid.UUID(p["account"]), ep.ActivationIn(active=True), db, boss)
    assert out["activated"] and out["mode"] == "SIMULATED"                                 # flag + egress still off
    assert "ADS_LIVE_MUTATIONS is off." in out["live_blockers"]


@DB
@pytest.mark.asyncio
async def test_offline_simulation_without_credentials(sim, monkeypatch):
    """No credentials: nothing is sent at all; ids are SIM-…, state says SIMULATED; edit supersedes approval."""
    from tests.m48_ads_support import approve, campaign_body
    monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "")
    p = await setup_account("meta")
    async with client() as ca, client() as cb:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        r = await ca.post("/api/v1/ads/campaigns", json=campaign_body("meta", p["account"], "POVU Offline"))
        rid = r.json()["id"]
        assert r.json()["transport"] == "offline"
        await approve(ca, cb, rid, "SUBMIT")
        r = await ca.patch(f"/api/v1/ads/campaigns/{rid}", json={"name": "POVU Offline v2"})
        assert r.status_code == 200 and r.json()["status"] == "DRAFT"
        assert [a["status"] for a in r.json()["approvals"]] == ["SUPERSEDED"]
        assert (await ca.patch(f"/api/v1/ads/campaigns/{rid}", json={"spec": {"bogus": "1"}})).status_code == 422
        await approve(ca, cb, rid, "SUBMIT")
        t = (await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")).json()
        assert t["status"] == "PAUSED" and t["mode"] == "SIMULATED"
        assert all(n["provider_id"].startswith("SIM-") and n["provider_status"] == "SIMULATED PAUSED" for n in t["nodes"])
        await approve(ca, cb, rid, "RESUME")
        t = (await ca.post(f"/api/v1/ads/campaigns/{rid}/resume")).json()
        assert t["status"] == "ACTIVE" and t["nodes"][0]["provider_status"] == "SIMULATED ACTIVE"
        led = (await ca.get(f"/api/v1/ads/campaigns/{rid}/mutations")).json()
        assert all(m["response"] == {"simulated": True, "sent": False} for m in led)
    assert await sim_objects("meta") == {}


# ── review fixes (commit 933ffaf): live pause never faked; in-flight PENDING not reconciled; per-tree lock ──────

async def _live_tree_active(monkeypatch):
    """A tree created and resumed through the simulator, then marked LIVE (as if created with live switches on)."""
    import uuid
    from app.db.session import AsyncSessionLocal
    from app.models.m48_ads import AdCampaignNode
    from sqlalchemy import update
    from tests.m48_ads_support import approve, campaign_body
    p = await setup_account("meta")
    ca, cb = client(), client()
    await login(ca, p["author"])
    await login(cb, p["approver"])
    rid = (await ca.post("/api/v1/ads/campaigns", json=campaign_body("meta", p["account"], "POVU Live pause"))).json()["id"]
    await approve(ca, cb, rid, "SUBMIT")
    assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")).status_code == 200
    await approve(ca, cb, rid, "RESUME")
    t = (await ca.post(f"/api/v1/ads/campaigns/{rid}/resume")).json()
    assert t["status"] == "ACTIVE"
    async with AsyncSessionLocal() as db:
        u = uuid.UUID(rid)
        await db.execute(update(AdCampaignNode).where((AdCampaignNode.id == u) | (AdCampaignNode.root_id == u)).values(mode="LIVE"))
        await db.commit()
    camp_pid = next(n["provider_id"] for n in t["nodes"] if n["level"] == "CAMPAIGN")
    return ca, cb, rid, camp_pid


@DB
@pytest.mark.asyncio
async def test_live_pause_with_live_gated_off_really_sends(sim, monkeypatch):
    """ADS_LIVE_MUTATIONS off, account not activated, LIVE tree: pause must reach the provider transport."""
    from app.core import provider_http
    from tests.provider_sim.ads_app import ads_sim_settings
    ca, cb, rid, camp_pid = await _live_tree_active(monkeypatch)
    try:
        assert (await sim_objects("meta"))[camp_pid]["status"] == "ACTIVE"
        # live egress (the https host is routed to the in-process simulator; DNS check bypassed for the test host)
        monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
        monkeypatch.setattr(provider_http, "_refuse_internal", lambda host: None)
        for k, v in ads_sim_settings("https://ads.test").items():
            monkeypatch.setattr(settings, k, v)
        monkeypatch.delenv("ADS_LIVE_MUTATIONS", raising=False)
        t = (await ca.get("/api/v1/ads/campaigns")).json()
        t = next(x for x in t if x["id"] == rid)
        assert t["mode"] == "LIVE" and t["transport"] == "http" and "ADS_LIVE_MUTATIONS is off." in t["live_blockers"]
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/resume")).status_code == 409      # going live stays refused
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/pause")
        assert r.status_code == 200, r.text
        assert (await sim_objects("meta"))[camp_pid]["status"] == "PAUSED"                  # really reached the provider
        top = next(n for n in r.json()["nodes"] if n["level"] == "CAMPAIGN")
        assert top["provider_status"] == "PAUSED" and "SIMULATED" not in (top["provider_status"] or "")
        last = (await ca.get(f"/api/v1/ads/campaigns/{rid}/mutations")).json()[-1]
        assert last["operation"] == "STATUS" and last["mode"] == "LIVE" and last["state"] == "SUCCEEDED"
        assert last.get("response") != {"simulated": True, "sent": False}
    finally:
        await ca.aclose()
        await cb.aclose()


@DB
@pytest.mark.asyncio
async def test_live_pause_refused_when_provider_unreachable(sim, monkeypatch):
    """LIVE tree, egress not live (or no credentials): pause refused clearly, nothing recorded as done."""
    ca, cb, rid, camp_pid = await _live_tree_active(monkeypatch)
    try:
        before = (await ca.get(f"/api/v1/ads/campaigns/{rid}/mutations")).json()
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/pause")                                # egress is local
        assert r.status_code == 409 and "Nothing was sent" in r.text, r.text
        monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
        monkeypatch.setattr(settings, "META_ADS_ACCESS_TOKEN", "")
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/pause")                                # no credentials
        assert r.status_code == 409 and "credentials" in r.text, r.text
        assert (await sim_objects("meta"))[camp_pid]["status"] == "ACTIVE"
        assert (await ca.get(f"/api/v1/ads/campaigns/{rid}/mutations")).json() == before       # no fake SUCCEEDED
        t = next(x for x in (await ca.get("/api/v1/ads/campaigns")).json() if x["id"] == rid)
        assert t["status"] == "ACTIVE"
    finally:
        await ca.aclose()
        await cb.aclose()


@DB
@pytest.mark.asyncio
async def test_fresh_pending_not_reconciled_and_tree_lock(sim):
    import uuid
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from app.db.session import AsyncSessionLocal
    from app.models.m48_ads import AdCampaignNode, AdMutation
    from app.services import ads_service as svc
    from tests.m48_ads_support import approve, campaign_body
    p = await setup_account("meta")
    async with client() as ca, client() as cb:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        rid = (await ca.post("/api/v1/ads/campaigns", json=campaign_body("meta", p["account"], "POVU In flight"))).json()["id"]
        await approve(ca, cb, rid, "SUBMIT")
        async with AsyncSessionLocal() as db:                 # a create claimed by another worker, still in flight
            root = await db.get(AdCampaignNode, uuid.UUID(rid))
            row = AdMutation(account_id=root.account_id, node_id=root.id, operation="CREATE", idempotency_key=f"{root.id}:CREATE",
                             request_hash="x" * 64, mode="SIMULATED", state="PENDING", request={}, created_by=p["author"])
            db.add(row)
            await db.commit()
            mid = row.id
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")
        assert r.status_code == 200, r.text
        async with AsyncSessionLocal() as db:
            assert (await db.get(AdMutation, mid)).state == "PENDING"                         # left alone
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")).status_code == 409    # not re-sent either
        assert await sim_objects("meta") == {}
        # older than the grace period → reconciled by read-back (nothing exists → FAILED, safe to retry)
        async with AsyncSessionLocal() as db:
            await db.execute(update(AdMutation).where(AdMutation.id == mid).values(
                updated_at=datetime.now(timezone.utc) - svc.CLAIM_GRACE - timedelta(seconds=5)))
            await db.commit()
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")).status_code == 200
        async with AsyncSessionLocal() as db:
            assert (await db.get(AdMutation, mid)).state == "FAILED"
            # a second operation on the same tree while one holds the lock is refused
            root = await db.get(AdCampaignNode, uuid.UUID(rid))
            async with svc.root_lock(db, root):
                r = await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")
                assert r.status_code == 409 and "in progress" in r.text
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")).status_code == 200  # lock released
