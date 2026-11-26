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
