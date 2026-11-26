"""M51.S01.T003 Google Search Console adapter against the local simulator (DB part needs M51_DB=1)."""
import os

import pytest

from app.services import m51_gsc_service as gsc
from tests.m51_s01_seo_common import client_for, connect_google, ensure_tables, setv, sim_calls, sim_control, staff, use_sim

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
P = "/api/v1/seo-pro"
SITE = "https://povu-demo.test/"
BODY = {"site_url": SITE, "start_date": "2026-11-01", "end_date": "2026-11-30", "dimensions": ["query"]}
FULL = ["query", "page", "country", "device", "date"]


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    from app.core import provider_http
    provider_http.set_test_transport(None)
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_build_query_validation():
    ok = gsc.build_query("2026-11-01", "2026-11-30", ["query", "date"], [{"dimension": "country", "expression": "ken"}], 100, 0, "final", "web")
    assert ok["dimensionFilterGroups"][0]["groupType"] == "and" and ok["rowLimit"] == 100
    for args in (("2026-12-01", "2026-11-01", ["query"], [], 10, 0, "final", "web"),
                 ("2026-11-01", "2026-11-30", ["query", "query"], [], 10, 0, "final", "web"),
                 ("2026-11-01", "2026-11-30", ["bogus"], [], 10, 0, "final", "web"),
                 ("2026-11-01", "2026-11-30", ["query"], [], 25001, 0, "final", "web"),
                 ("2026-11-01", "2026-11-30", ["query"], [{"dimension": "country", "expression": "KE"}], 10, 0, "final", "web"),
                 ("2026-11-01", "2026-11-30", ["query"], [], 10, 0, "hourly_all", "web"),
                 ("2024-01-01", "2026-11-30", ["query"], [], 10, 0, "final", "web"), ("nope", "2026-11-30", [], [], 10, 0, "final", "web")):
        with pytest.raises(gsc.GscError):
            gsc.build_query(*args)


async def _user(tag, perms, *purposes):
    from app.db.session import AsyncSessionLocal
    await ensure_tables()
    async with AsyncSessionLocal() as db:
        u = await staff(db, tag, perms)
        for p in purposes:
            await connect_google(db, u.id, p)
        await db.commit()
    return u


@DB
@pytest.mark.asyncio
async def test_not_configured_then_connect_scopes(monkeypatch):
    u = await _user("seo", ("marketing.edit",))
    async with client_for(u) as c:
        st = (await c.get(f"{P}/gsc/state")).json()
        assert st["state"] == "NOT_CONFIGURED" and st["reasons"]
        r = await c.post(f"{P}/gsc/analytics", json=BODY)
        assert r.status_code == 409 and "NOT_CONFIGURED" in r.text
        setv(monkeypatch, "GOOGLE_OAUTH_CLIENT_ID", "x")
        setv(monkeypatch, "GOOGLE_OAUTH_CLIENT_SECRET", "y")
        ro = (await c.get(f"{P}/gsc/connect-url")).json()["authorize_url"]
        rw = (await c.get(f"{P}/gsc/connect-url?write=true")).json()["authorize_url"]
        assert "webmasters.readonly" in ro
        assert "readonly" not in rw and "auth%2Fwebmasters" in rw
    async with client_for(await _user("viewer", ("marketing.view",))) as c:     # view-only persona cannot start a connection
        assert (await c.get(f"{P}/gsc/connect-url")).status_code == 403


@DB
@pytest.mark.asyncio
async def test_analytics_filter_pagination_snapshot_and_incomplete(monkeypatch):
    use_sim(monkeypatch)
    u = await _user("seo", ("marketing.edit",), "searchconsole")
    async with client_for(u) as c:
        assert (await c.get(f"{P}/gsc/state")).json()["state"] == "OK"
        sites = (await c.get(f"{P}/gsc/sites")).json()
        assert {s["site_url"] for s in sites} == {SITE, "sc-domain:povu-demo.test"}
        full = (await c.post(f"{P}/gsc/analytics", json=BODY)).json()
        assert full["source"] == "LOCAL_SIMULATOR" and full["stale"] is False and full["row_count"] == 3
        assert full["rows"][0]["clicks"] >= full["rows"][-1]["clicks"] and 0 <= full["rows"][0]["ctr"] <= 1
        flt = (await c.post(f"{P}/gsc/analytics", json={**BODY, "dimensions": ["query", "country"],
                                                         "filters": [{"dimension": "country", "operator": "equals", "expression": "tza"}]})).json()
        assert flt["row_count"] == 3 and all(r["keys"][1] == "tza" for r in flt["rows"])
        allrows = (await c.post(f"{P}/gsc/analytics", json={**BODY, "dimensions": FULL, "row_limit": 1000})).json()["row_count"]
        paged = (await c.post(f"{P}/gsc/analytics", json={**BODY, "dimensions": FULL, "row_limit": 7, "paginate": True})).json()
        assert allrows == 48 and paged["row_count"] == 48
        one = (await c.post(f"{P}/gsc/analytics", json={**BODY, "dimensions": FULL, "row_limit": 7, "start_row": 46})).json()
        assert one["row_count"] == 2                                   # startRow honoured
        fresh = (await c.post(f"{P}/gsc/analytics", json={**BODY, "data_state": "all"})).json()
        assert fresh["incomplete_from"] == "2026-11-02"                # provider-flagged incomplete data is exposed
        snaps = (await c.get(f"{P}/gsc/snapshots")).json()
        assert snaps and all(s["source"] == "LOCAL_SIMULATOR" for s in snaps)


@DB
@pytest.mark.asyncio
async def test_quota_backoff_stale_and_permission(monkeypatch):
    use_sim(monkeypatch)
    u = await _user("seo", ("marketing.edit",), "searchconsole")
    import random
    body = {**BODY, "dimensions": ["device"], "row_limit": random.randint(2000, 24000)}   # unique query: no snapshot from an earlier run
    async with client_for(u) as c:
        await sim_control({"faults": {"gsc": ["429", "429", "429"]}})
        r = await c.post(f"{P}/gsc/analytics", json=body)
        assert r.status_code == 429 and r.json()["detail"]["code"] == "quota"       # nothing stored yet: no invented data
        await sim_control({"faults": {"gsc": ["429"]}})                             # recovers on the retry
        ok = await c.post(f"{P}/gsc/analytics", json=body)
        assert ok.status_code == 200 and ok.json()["stale"] is False
        await sim_control({"faults": {"gsc": ["503", "503", "503"]}})
        st = (await c.post(f"{P}/gsc/analytics", json=body)).json()
        assert st["stale"] is True and st["stale_reason"] and st["rows"] == ok.json()["rows"]
        denied = await c.post(f"{P}/gsc/analytics", json={**body, "site_url": "https://not-mine.example.com/"})
        assert denied.status_code == 403 and denied.json()["detail"]["code"] == "permission_denied"
        assert (await c.post(f"{P}/gsc/analytics", json={**body, "site_url": "not a site"})).status_code == 422


@DB
@pytest.mark.asyncio
async def test_sitemap_submission_two_person_and_status(monkeypatch):
    use_sim(monkeypatch)
    a = await _user("reqr", ("marketing.edit",), "searchconsole_edit")
    b = await _user("appr", ("marketing.edit",), "searchconsole_edit")
    feed = "https://povu-demo.test/sitemap.xml"
    async with client_for(a) as ca, client_for(b) as cb:
        sub = (await ca.post(f"{P}/gsc/submissions", json={"site_url": SITE, "feedpath": feed})).json()
        assert sub["status"] == "PENDING" and "sitemap_put" not in await sim_calls()
        assert (await ca.post(f"{P}/gsc/submissions/{sub['id']}/decide", json={"approve": True})).status_code == 403   # same person
        assert "sitemap_put" not in await sim_calls()
        await sim_control({"scope_rw": False})
        failed = (await cb.post(f"{P}/gsc/submissions/{sub['id']}/decide", json={"approve": True})).json()
        assert failed["status"] == "FAILED" and "permission" in failed["result"].lower()
        await sim_control({"scope_rw": True})
        sub2 = (await ca.post(f"{P}/gsc/submissions", json={"site_url": SITE, "feedpath": feed})).json()
        done = (await cb.post(f"{P}/gsc/submissions/{sub2['id']}/decide", json={"approve": True})).json()
        assert done["status"] == "SUBMITTED" and done["source"] == "LOCAL_SIMULATOR" and done["decided_by"] == b.username
        status = (await ca.get(f"{P}/gsc/sitemaps/status", params={"site_url": SITE, "feedpath": feed})).json()
        assert status["isPending"] is True and status["path"] == feed      # provider's own state, not "published"
        assert len((await ca.get(f"{P}/gsc/sitemaps", params={"site_url": SITE})).json()) == 1
        sub3 = (await ca.post(f"{P}/gsc/submissions", json={"site_url": SITE, "feedpath": feed})).json()
        assert (await cb.post(f"{P}/gsc/submissions/{sub3['id']}/decide", json={"approve": False})).json()["status"] == "REJECTED"
    async with client_for(await _user("viewer", ("marketing.view",))) as v:
        assert (await v.post(f"{P}/gsc/submissions", json={"site_url": SITE, "feedpath": feed})).status_code == 403


@DB
@pytest.mark.asyncio
async def test_url_inspection(monkeypatch):
    use_sim(monkeypatch)
    u = await _user("seo", ("marketing.view",), "searchconsole")
    async with client_for(u) as c:
        r = (await c.post(f"{P}/gsc/inspect", json={"site_url": SITE, "url": SITE + "products"})).json()
        assert r["summary"]["verdict"] == "PASS" and r["summary"]["coverageState"] and r["source"] == "LOCAL_SIMULATOR"
        assert (await c.post(f"{P}/gsc/inspect", json={"site_url": SITE, "url": "https://other.example.com/x"})).status_code == 400
