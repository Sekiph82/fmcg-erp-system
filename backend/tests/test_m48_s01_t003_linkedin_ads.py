"""M48.S01.T003 LinkedIn Marketing API (versioned REST) mutation adapter against the local simulator.

Unit: adCampaignGroups → adCampaigns → creatives created DRAFT with LinkedIn-Version + X-Restli-Protocol-Version,
201 + x-restli-id, PARTIAL_UPDATE {"patch":{"$set":...}} for status and budget, read-back, Development tier refused
before anything is sent, no validate-only (local checks only), UNKNOWN create found by name search. DB (M48_DB=1):
full lifecycle over HTTP, UNKNOWN reconciliation.
"""
import os

import pytest

from app.core.config import settings
from app.services import ads_adapters as ads
from tests.m48_ads_support import (DB, ctx, create_chain, fault, full_lifecycle, sim, sim_objects,  # noqa: F401
                                   unknown_then_reconcile)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_linkedin_tree_draft_restli(sim):
    ids = await create_chain("linkedin")
    assert ids["AD"].startswith("urn:li:sponsoredCreative:") and ids["CAMPAIGN"].isdigit()
    objs = await sim_objects("linkedin")
    grp, camp, cre = objs[ids["CAMPAIGN"]]["body"], objs[ids["ADSET"]]["body"], objs[ids["AD"]]["body"]
    assert grp["status"] == "DRAFT" and grp["account"] == "urn:li:sponsoredAccount:5001"
    assert camp["status"] == "DRAFT" and camp["campaignGroup"] == f"urn:li:sponsoredCampaignGroup:{ids['CAMPAIGN']}"
    assert camp["dailyBudget"] == {"amount": "60", "currencyCode": "USD"} and camp["politicalIntent"] == "NOT_POLITICAL"
    assert camp["costType"] == "CPC" and camp["objectiveType"] == "WEBSITE_VISIT"
    assert cre["intendedStatus"] == "DRAFT" and cre["campaign"] == f"urn:li:sponsoredCampaign:{ids['ADSET']}"
    b, a, x = ads.BUILDERS["linkedin"], ads.ADAPTERS["linkedin"], ctx("linkedin")
    req = b.status("AD", ids["AD"], True, x)
    assert req.headers == {"X-RestLi-Method": "PARTIAL_UPDATE"} and "urn%3Ali%3AsponsoredCreative%3A" in req.url
    await ads.send(a, req, safe=False)
    await ads.send(a, b.budget(ids["ADSET"], ctx("linkedin", budget="25")), safe=False)
    body, _ = await ads.send(a, b.read("ADSET", ids["ADSET"], ctx("linkedin", budget="25")), safe=True)
    assert b.parse_read("ADSET", body, ctx("linkedin", budget="25"))["budget_ok"] is True
    body, _ = await ads.send(a, b.read("AD", ids["AD"], x), safe=True)
    assert b.parse_read("AD", body, x)["configured"] == "ACTIVE"


@pytest.mark.asyncio
async def test_linkedin_version_and_tier_refused(sim, monkeypatch):
    b, a = ads.BUILDERS["linkedin"], ads.ADAPTERS["linkedin"]
    monkeypatch.setattr(settings, "LINKEDIN_ADS_ACCESS_TIER", "development")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(a, b.create("CAMPAIGN", ctx("linkedin")), safe=False)
    assert e.value.kind == "PERMISSION" and await sim_objects("linkedin") == {}            # nothing sent
    monkeypatch.setattr(settings, "LINKEDIN_ADS_ACCESS_TIER", "standard")
    monkeypatch.setattr(settings, "LINKEDIN_ADS_VERSION", "202001")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(a, b.create("CAMPAIGN", ctx("linkedin")), safe=False)
    assert e.value.kind == "VERSION" and await sim_objects("linkedin") == {}


@pytest.mark.asyncio
async def test_linkedin_unknown_create_found_by_name(sim):
    x = ctx("linkedin")
    await fault("linkedin", "unknown")
    with pytest.raises(ads.AdsError) as e:
        await ads.send(ads.ADAPTERS["linkedin"], ads.BUILDERS["linkedin"].create("CAMPAIGN", x), safe=False)
    assert e.value.kind == "UNKNOWN"
    gid = await ads.find_created("linkedin", "CAMPAIGN", x)
    assert gid in await sim_objects("linkedin")


def test_linkedin_local_checks_only():
    from decimal import Decimal
    p = ads.check_spec("linkedin", "WEBSITE_VISIT", {"share_urn": "x", "geo_urn": "y", "unit_cost": "0"}, Decimal(5), "USD")
    assert len(p) == 4 and any("USD 10" in s for s in p)
    assert ads.ADAPTERS["linkedin"].supports_validate_only is False


@DB
@pytest.mark.asyncio
async def test_linkedin_lifecycle_http(sim):
    out = await full_lifecycle("linkedin", sim)
    grp = next(o for o in out["objs"].values() if o["kind"] == "group")
    assert grp["body"]["status"] == "PAUSED"
    camp = next(o for o in out["objs"].values() if o["kind"] == "campaign")
    assert camp["body"]["dailyBudget"]["amount"] == "80.00"
    assert out["tree"]["validation"]["provider_checked"] is False                         # no validate-only API


@DB
@pytest.mark.asyncio
async def test_linkedin_unknown_reconciled(sim):
    await unknown_then_reconcile("linkedin")
