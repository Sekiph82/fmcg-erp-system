"""M48.S01.T002 Google Ads API mutation adapter against the local simulator (no network, no accounts, no spend).

Unit: campaignBudgets → campaigns → adGroups → adGroupAds :mutate with resource-name chaining, PAUSED, micros,
partialFailure handling, googleAds:mutate validateOnly over the whole tree creates nothing, EU political declaration
from v20, status/budget updates with updateMask, GAQL read-back, UNKNOWN create found by GAQL. DB (M48_DB=1): full
lifecycle over HTTP, UNKNOWN reconciliation, lost write retried.
"""
import os

import pytest

from app.core.config import settings
from app.services import ads_adapters as ads
from tests.m48_ads_support import (DB, ctx, create_chain, fault, full_lifecycle, lost_then_retry, sim, sim_objects,  # noqa: F401
                                   unknown_then_reconcile)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_google_tree_resource_names_paused_micros(sim):
    ids = await create_chain("google")
    assert ids["BUDGET"].startswith("customers/4445556666/campaignBudgets/")
    assert ids["AD"].startswith(f"customers/4445556666/adGroupAds/{ids['ADSET'].rsplit('/', 1)[-1]}~")
    objs = await sim_objects("google")
    assert objs[ids["BUDGET"]]["amountMicros"] == "60000000"
    camp = objs[ids["CAMPAIGN"]]
    assert camp["status"] == "PAUSED" and camp["campaignBudget"] == ids["BUDGET"] and camp["advertisingChannelType"] == "SEARCH"
    assert objs[ids["ADSET"]]["cpcBidMicros"] == "12500000" and objs[ids["ADSET"]]["status"] == "PAUSED"
    assert objs[ids["AD"]]["status"] == "PAUSED" and len(objs[ids["AD"]]["ad"]["responsiveSearchAd"]["headlines"]) == 3
    b, a = ads.BUILDERS["google"], ads.ADAPTERS["google"]
    x = ctx("google")
    await ads.send(a, b.status("CAMPAIGN", ids["CAMPAIGN"], True, x), safe=False)
    body, _ = await ads.send(a, b.read("CAMPAIGN", ids["CAMPAIGN"], x), safe=True)
    assert b.parse_read("CAMPAIGN", body, x)["configured"] == "ENABLED"
    await ads.send(a, b.budget(ids["BUDGET"], ctx("google", budget="80")), safe=False)
    body, _ = await ads.send(a, b.read("BUDGET", ids["BUDGET"], ctx("google", budget="80")), safe=True)
    assert b.parse_read("BUDGET", body, ctx("google", budget="80"))["budget_ok"] is True
    req = b.status("ADSET", ids["ADSET"], False, x)
    assert req.json["operations"][0]["updateMask"] == "status" and req.json["partialFailure"] is True


@pytest.mark.asyncio
async def test_google_validate_only_tree_creates_nothing(sim):
    b = ads.BUILDERS["google"]
    names = {lv: f"POVU {lv} (povu-v)" for lv in ads.LEVELS["google"]}
    req = b.validate_tree(ctx("google"), names)
    assert req.json["validateOnly"] is True and len(req.json["mutateOperations"]) == 4
    assert req.json["mutateOperations"][1]["campaignOperation"]["create"]["campaignBudget"].endswith("/campaignBudgets/-1")
    body, _ = await ads.send(ads.ADAPTERS["google"], req, safe=True)
    assert body == {} and await sim_objects("google") == {}
    bad = ctx("google")
    bad["spec"] = {**bad["spec"], "headlines": ["only one"]}
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["google"], b.validate_tree(bad, names), safe=True)
    assert e.value.kind == "VALIDATION" and await sim_objects("google") == {}


@pytest.mark.asyncio
async def test_google_partial_failure_is_definitive(sim):
    b = ads.BUILDERS["google"]
    await fault("google", "partial")
    body, h = await ads.send(ads.ADAPTERS["google"], b.create("BUDGET", ctx("google")), safe=False)
    with pytest.raises(ads.AdsError) as e:
        b.parse_create("BUDGET", body, h)
    assert e.value.kind == "VALIDATION" and await sim_objects("google") == {}


@pytest.mark.asyncio
async def test_google_eu_political_declaration_by_version(monkeypatch):
    b = ads.BUILDERS["google"]
    x = ctx("google", ids={"BUDGET": "customers/1/campaignBudgets/1"})
    monkeypatch.setattr(settings, "GOOGLE_ADS_API_VERSION", "v18")
    assert "containsEuPoliticalAdvertising" not in b.resource("CAMPAIGN", x)
    monkeypatch.setattr(settings, "GOOGLE_ADS_API_VERSION", "v22")
    assert b.resource("CAMPAIGN", x)["containsEuPoliticalAdvertising"] == "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"


@pytest.mark.asyncio
async def test_google_unknown_create_found_by_gaql(sim):
    x = ctx("google")
    await fault("google", "unknown")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["google"], ads.BUILDERS["google"].create("BUDGET", x), safe=False)
    assert e.value.kind == "UNKNOWN"
    rn = await ads.find_created("google", "BUDGET", x)
    assert rn and rn in await sim_objects("google")


@DB
@pytest.mark.asyncio
async def test_google_lifecycle_http(sim):
    out = await full_lifecycle("google", sim)
    budget = next(o for o in out["objs"].values() if o["kind"] == "campaign_budget")
    assert budget["amountMicros"] == "80000000"
    camp = next(o for o in out["objs"].values() if o["kind"] == "campaign")
    assert camp["status"] == "PAUSED"


@DB
@pytest.mark.asyncio
async def test_google_unknown_reconciled_and_lost_retried(sim):
    await unknown_then_reconcile("google")
    await lost_then_retry("google")
