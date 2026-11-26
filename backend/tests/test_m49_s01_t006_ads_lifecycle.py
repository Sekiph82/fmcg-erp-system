"""M49.S01.T006 unified advertising lifecycle: cross-account tree, wizard description, approved edits through the M48
ledger (names and schedules, documented fields only), schedule read-back, reconciliation, per-node reporting, role and
cross-account refusals. Local ads simulator, synthetic POVU data. Needs the disposable PostgreSQL: M49_DB=1."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.services import ads_adapters as ads
from tests.m48_ads_support import campaign_body, client, fault, full_lifecycle, login, sim, sim_objects  # noqa: F401
from tests.m49_audience_support import M49, mount

API = "/api/v1/ads-lifecycle"
mount()
LEVEL = {"meta": "ADSET", "google": "CAMPAIGN", "linkedin": "ADSET", "tiktok": "ADSET"}
START, END = "2026-12-07", "2026-12-31"


@pytest.fixture(autouse=True)
async def _dispose():
    yield
    await engine.dispose()


def node_of(tree: dict, acct: str, level: str) -> dict:
    row = next(a for a in tree["accounts"] if a["account"]["id"] == acct)
    return next(n for c in row["campaigns"] for n in c["nodes"] if n["level"] == level)


@M49
async def test_t006_wizard_lists_types_and_what_is_not_offered(sim):
    from tests.m48_ads_support import setup_account
    p = await setup_account("meta")
    async with client() as ca:
        await login(ca, p["author"])
        w = {x["provider"]: x for x in (await ca.get(f"{API}/wizard")).json()}
    assert set(w) == {"meta", "google", "linkedin", "tiktok"}
    for prov, x in w.items():
        assert x["objectives"] == list(ads.OBJECTIVES[prov]) and [lv["level"] for lv in x["levels"]] == list(ads.LEVELS[prov])
        assert x["not_offered"] and all(f["key"] and f["label"] for f in x["fields"])
    assert w["linkedin"]["editable"]["CAMPAIGN"] == ["end_date", "name"] and "immutable" in w["linkedin"]["editable_note"]
    assert w["google"]["editable"]["AD"] == []


@M49
@pytest.mark.parametrize("provider", ["meta", "google", "linkedin", "tiktok"])
async def test_t006_tree_edit_schedule_readback_reconcile_report(provider, sim):
    res = await full_lifecycle(provider, sim)            # create → validate → approve → paused submit → resume → pause → budget
    p, level = res["people"], LEVEL[provider]
    acct = p["account"]
    new_name = f"POVU AllClean {provider} spring"
    fields = {"name": new_name, "end_date": END} if provider == "linkedin" else {"name": new_name, "start_date": START, "end_date": END}
    async with client() as ca, client() as cb, client() as ci, client() as co:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        await login(ci, p["intruder"])
        await login(co, p["outsider"])

        # cross-account / role refusals are visible, not hidden
        assert (await co.get(f"{API}/tree")).status_code == 403
        t = (await ci.get(f"{API}/tree")).json()
        row = next(a for a in t["accounts"] if a["account"]["id"] == acct)
        assert row["member"] is False and "not a member" in row["refusal"] and row["campaigns"] == []
        t = (await ca.get(f"{API}/tree")).json()
        row = next(a for a in t["accounts"] if a["account"]["id"] == acct)
        assert row["member"] and row["controls"]["activated"] is False and row["controls"]["daily_cap"] == 500
        assert "ADS_LIVE_MUTATIONS is off." in row["controls"]["live_blockers"]                   # activation switch + cap stay visible
        camp = row["campaigns"][0]
        assert [n["level"] for n in camp["nodes"]] == list(ads.LEVELS[provider])
        node = node_of(t, acct, level)
        assert node["provider_id"] and "name" in node["editable"] and node["edit_disabled"] is None
        assert (await ci.post(f"{API}/nodes/{node['id']}/edits", json={"name": "x"})).status_code == 403          # not a member
        assert (await cb.post(f"{API}/nodes/{node['id']}/edits", json={"name": "x"})).status_code == 403          # approver cannot edit

        # only documented updatable fields
        if provider == "linkedin":
            r = await ca.post(f"{API}/nodes/{node['id']}/edits", json={"start_date": START})
            assert r.status_code == 422 and "cannot be edited" in r.text and "immutable" in r.text, r.text
        ad_node = node_of(t, acct, "AD")
        if provider in ("google", "linkedin", "tiktok"):
            r = await ca.post(f"{API}/nodes/{ad_node['id']}/edits", json={"name": "y"})
            assert r.status_code == 422 and "cannot be edited" in r.text, r.text
            assert ad_node["edit_disabled"] and ad_node["editable"] == []
        assert (await ca.post(f"{API}/nodes/{node['id']}/edits", json={"start_date": "not-a-date"})).status_code == 422

        # edit → approval → apply, with read-back
        r = await ca.post(f"{API}/nodes/{node['id']}/edits", json={k: v for k, v in fields.items()})
        assert r.status_code == 201, r.text
        eid = r.json()["id"]
        assert (await ca.post(f"{API}/edits/{eid}/apply")).status_code == 409                       # not approved
        assert (await ca.post(f"{API}/edits/{eid}/decide", json={"ok": True})).status_code == 403   # author cannot approve
        assert (await cb.post(f"{API}/edits/{eid}/decide", json={"ok": True})).status_code == 200
        before = len(await sim_objects(provider))
        r = await ca.post(f"{API}/edits/{eid}/apply")
        assert r.status_code == 200, r.text
        e = r.json()
        assert e["status"] == "APPLIED" and e["read_back"]["diffs"] == [] and e["mode"] == "SIMULATED"
        assert e["read_back"]["observed"]["end_date"] == END
        assert len(await sim_objects(provider)) == before
        seen = [o for o in (await sim_objects(provider)).values() if new_name in str(o)]
        assert seen, "the simulated provider holds the edited object"
        led = (await ca.get(f"/api/v1/ads/campaigns/{camp['id']}/mutations")).json()
        edit_rows = [m for m in led if m["operation"] == "EDIT"]
        assert len(edit_rows) == 1 and edit_rows[0]["state"] == "SUCCEEDED" and edit_rows[0]["mode"] == "SIMULATED"
        assert "Authorization" not in str(edit_rows) and "Access-Token" not in str(edit_rows)
        assert (await ca.post(f"{API}/edits/{eid}/apply")).status_code == 409                       # single use
        node = node_of((await ca.get(f"{API}/tree")).json(), acct, level)
        assert node["name"] == new_name and node["edits"][-1]["status"] == "APPLIED"

        # live read-back of the object
        r = await ca.post(f"{API}/nodes/{node['id']}/readback")
        assert r.status_code == 200 and r.json()["observed"]["end_date"] == END and r.json()["observed"]["name"].startswith(new_name)

        # unknown outcome: applied at the provider, answer lost → UNKNOWN, never re-sent, reconciled by read-back
        r = await ca.post(f"{API}/nodes/{node['id']}/edits", json={"name": f"{new_name} v2"})
        eid2 = r.json()["id"]
        assert (await cb.post(f"{API}/edits/{eid2}/decide", json={"ok": True})).status_code == 200
        await fault(provider, "unknown")
        r = await ca.post(f"{API}/edits/{eid2}/apply")
        assert r.status_code == 504 and "UNKNOWN" in r.text, r.text
        t = (await ca.get(f"{API}/tree")).json()
        assert node_of(t, acct, level)["edits"][-1]["status"] == "UNKNOWN"
        r = await ca.post(f"{API}/edits/{eid2}/apply")
        assert r.status_code == 409 and "reconcile" in r.text.lower()
        r = await ca.post(f"{API}/edits/{eid2}/reconcile")
        assert r.status_code == 200 and r.json()["status"] == "APPLIED", r.text
        led = (await ca.get(f"/api/v1/ads/campaigns/{camp['id']}/mutations")).json()
        assert [m["state"] for m in led if m["operation"] == "EDIT"] == ["SUCCEEDED", "SUCCEEDED"]

        # a rejected edit never reaches the provider
        eid3 = (await ca.post(f"{API}/nodes/{node['id']}/edits", json={"name": "Rejected name"})).json()["id"]
        assert (await cb.post(f"{API}/edits/{eid3}/decide", json={"ok": False})).json()["status"] == "REJECTED"
        assert (await ca.post(f"{API}/edits/{eid3}/apply")).status_code == 409
        assert not [o for o in (await sim_objects(provider)).values() if "Rejected name" in str(o)]

        # reporting per node: the existing sync reports campaign level only; other nodes say so
        report_level = "ADSET" if provider == "linkedin" else "CAMPAIGN"
        rn = node_of(t, acct, report_level)
        assert rn["report"]["available"] and rn["report"]["rows"] == 0 and "Sync reporting" in rn["report"]["note"]
        from app.models.crm import AdCampaignDay
        async with AsyncSessionLocal() as db:
            db.add(AdCampaignDay(account_id=uuid.UUID(acct), campaign_id=rn["provider_id"].replace(":", "/").rsplit("/", 1)[-1],
                                 campaign_name="POVU AllClean", day=date.today() - timedelta(days=1), impressions=1000, clicks=50,
                                 spend=25.5, conversions=2))
            await db.commit()
        t = (await ca.get(f"{API}/tree")).json()
        rep = node_of(t, acct, report_level)["report"]
        assert rep["impressions"] == 1000 and rep["clicks"] == 50 and rep["spend"] == 25.5 and rep["ctr"] == 0.05
        other = next(n for n in node_of_all(t, acct) if n["level"] != report_level)
        assert other["report"]["available"] is False and "campaign level" in other["report"]["reason"]

        # not yet on the provider → the draft editor, not a provider edit
        r = await ca.post("/api/v1/ads/campaigns", json=campaign_body(provider, acct, f"POVU Draft {uuid.uuid4().hex[:4]}"))
        assert r.status_code == 201, r.text
        draft = next(n for n in r.json()["nodes"] if n["level"] == level)
        r = await ca.post(f"{API}/nodes/{draft['id']}/edits", json={"name": "Draft rename"})
        assert r.status_code == 409 and "Not on the provider yet" in r.text


def node_of_all(tree: dict, acct: str) -> list:
    row = next(a for a in tree["accounts"] if a["account"]["id"] == acct)
    return [n for c in row["campaigns"] for n in c["nodes"]]
