"""M48.S01.T004 TikTok API for Business v1.3 ads mutation adapter against the local simulator (not organic posting).

Unit: campaign → adgroup → ad created with operation_status DISABLE, Access-Token header, advertiser_id, budget
in account currency, asset prerequisites (video_id, identity_id), status/update ENABLE/DISABLE, campaign/update
budget, /get/ read-back, code 40002 → VALIDATION, 5xxxx after create → UNKNOWN found through paged /campaign/get/.
DB (M48_DB=1): full lifecycle over HTTP, UNKNOWN reconciliation, lost write retried.
"""
import os

import pytest

from app.services import ads_adapters as ads
from tests.m48_ads_support import (DB, control, ctx, create_chain, fault, full_lifecycle, lost_then_retry, sim,  # noqa: F401
                                   sim_objects, unknown_then_reconcile)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_tiktok_tree_disabled_by_default(sim):
    ids = await create_chain("tiktok")
    objs = await sim_objects("tiktok")
    assert all(objs[ids[lv]]["operation_status"] == "DISABLE" for lv in ads.LEVELS["tiktok"])
    assert objs[ids["CAMPAIGN"]]["budget"] == 60.0 and objs[ids["ADSET"]]["campaign_id"] == ids["CAMPAIGN"]
    calls = (await control("/_control/calls"))
    ad = next(c["json"] for c in calls if c.get("create") == "ad")
    assert ad["creatives"][0]["video_id"] == "v10033g50000povu" and ad["advertiser_id"] == "7001"
    b, a, x = ads.BUILDERS["tiktok"], ads.ADAPTERS["tiktok"], ctx("tiktok")
    await ads.send(a, b.status("AD", ids["AD"], True, x), safe=False)
    data, _ = await ads.send(a, b.read("AD", ids["AD"], x), safe=True)
    assert b.parse_read("AD", data, x)["configured"] == "ENABLE"
    await ads.send(a, b.budget(ids["CAMPAIGN"], ctx("tiktok", budget="90")), safe=False)
    data, _ = await ads.send(a, b.read("CAMPAIGN", ids["CAMPAIGN"], ctx("tiktok", budget="90")), safe=True)
    assert b.parse_read("CAMPAIGN", data, ctx("tiktok", budget="90"))["budget_ok"] is True


@pytest.mark.asyncio
async def test_tiktok_asset_prerequisite_and_error_mapping(sim):
    ids = await create_chain("tiktok")
    x = ctx("tiktok", ids=ids)
    x["spec"] = {**x["spec"], "video_id": ""}
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["tiktok"], ads.BUILDERS["tiktok"].create("AD", x), safe=False)
    assert e.value.kind == "VALIDATION"                                                  # code 40002
    assert any("video_id" in p for p in ads.check_spec("tiktok", "TRAFFIC", x["spec"], ads.Decimal(60), "KES"))


@pytest.mark.asyncio
async def test_tiktok_unknown_found_through_paging(sim):
    for i in range(3):                                   # other campaigns on earlier pages
        await create_chain("tiktok", tag=f"povu-other{i:05d}")
    await control("/_control", {"tiktok_page_cap": 2})
    x = ctx("tiktok", tag="povu-target0001", name="POVU target (povu-target0001)")
    await fault("tiktok", "unknown")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["tiktok"], ads.BUILDERS["tiktok"].create("CAMPAIGN", x), safe=False)
    assert e.value.kind == "UNKNOWN"
    cid = await ads.find_created("tiktok", "CAMPAIGN", x)
    assert (await sim_objects("tiktok"))[cid]["name"].endswith("(povu-target0001)")


@DB
@pytest.mark.asyncio
async def test_tiktok_lifecycle_http(sim):
    out = await full_lifecycle("tiktok", sim)
    camp = next(o for o in out["objs"].values() if o["kind"] == "campaign")
    assert camp["operation_status"] == "DISABLE" and camp["budget"] == 80.0


@DB
@pytest.mark.asyncio
async def test_tiktok_unknown_reconciled_and_lost_retried(sim):
    await unknown_then_reconcile("tiktok")
    await lost_then_retry("tiktok")


# ── M48.S01.T020: provider minimum budgets refused before approval ────────────────────────────────────────────

def test_tiktok_minimum_in_account_currency_and_guardrail(monkeypatch):
    from decimal import Decimal
    from app.core.config import settings
    spec = ads.check_spec("tiktok", "TRAFFIC", ctx("tiktok")["spec"], Decimal(40), "KES")
    assert len(spec) == 1 and "below the minimum" in spec[0] and "50 KES" in spec[0] and "not verified" in spec[0]
    assert ads.check_spec("tiktok", "TRAFFIC", ctx("tiktok")["spec"], Decimal(50), "KES") == []
    assert ads.check_spec("linkedin", "WEBSITE_VISIT", ctx("linkedin")["spec"], Decimal(5), "KES") == []   # USD rule only
    assert any("USD 10" in p or "10 USD" in p for p in ads.check_spec("linkedin", "WEBSITE_VISIT", ctx("linkedin")["spec"], Decimal(5), "USD"))
    monkeypatch.setattr(settings, "ADS_MAX_DAILY_BUDGET", 30.0)
    p = ads.check_spec("tiktok", "TRAFFIC", ctx("tiktok")["spec"], Decimal(30), "KES")
    assert any("owner must raise the guardrail" in x for x in p)
    import asyncio
    assert asyncio.run(ads.TikTokAds().validate("7001", {"daily_budget": "40"}, "KES"))["ok"] is False   # legacy drafts too


@DB
@pytest.mark.asyncio
async def test_tiktok_below_minimum_refused_before_approval(sim):
    import uuid
    from app.db.session import AsyncSessionLocal
    from app.models.m48_ads import AdCampaignNode
    from tests.m48_ads_support import campaign_body, client, login, setup_account
    p = await setup_account("tiktok")
    async with client() as ca:
        await login(ca, p["author"])
        r = await ca.post("/api/v1/ads/campaigns", json=campaign_body("tiktok", p["account"], "POVU Low budget", budget="40"))
        assert r.status_code == 422 and "below the minimum" in r.text, r.text                   # refused at create
        prov = next(x for x in (await ca.get("/api/v1/ads/providers")).json() if x["provider"] == "tiktok")
        assert prov["min_daily_budget"] == 50.0 and prov["min_budget_currency"] is None and prov["guardrail"] == 1000.0
        rid = (await ca.post("/api/v1/ads/campaigns", json=campaign_body("tiktok", p["account"], "POVU Ok budget"))).json()["id"]
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/budget", json={"daily_budget": "40"})
        assert r.status_code == 422 and "below the minimum" in r.text                         # new version refused
        async with AsyncSessionLocal() as db:                    # a draft stored below the minimum (e.g. before T020)
            root = await db.get(AdCampaignNode, uuid.UUID(rid))
            root.daily_budget = 40
            await db.commit()
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/approvals", json={"action": "SUBMIT"})
        assert r.status_code == 422 and "fix before approval" in r.text, r.text               # never approvable
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/validate")
        assert r.json()["validation"]["ok"] is False and "below the minimum" in " ".join(r.json()["validation"]["problems"])
    assert await sim_objects("tiktok") == {}
