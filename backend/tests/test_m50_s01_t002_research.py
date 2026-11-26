"""M50.S01.T002 search adapter, SSRF-safe fetch, extraction and verification (DB part needs M50_DB=1).

Unit: URL policy (scheme, credentials, private/link-local/loopback, DNS-resolved private), redirects re-checked, size
and content-type limits, redaction, JSON-LD extraction. DB: NOT_CONFIGURED state and no provider call, licensed
search with locale/pagination/provenance, retry on 429, error mapping, egress off = no call, blocked pages are stored
with a reason, conflicting facts, retention purge, RBAC.
"""
import os

import pytest

from app.services import m50_research_service as rs
from tests.m50_s01_common import client_for, ensure_tables, setv, sim_calls, sim_control, staff, use_sim

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    from app.core import provider_http
    provider_http.set_test_transport(None)
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_url_policy(monkeypatch):
    for bad in ("file:///etc/passwd", "ftp://example.com/x", "gopher://x", "http://user:pw@example.com/", "http:///x",
                "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data", "http://127.0.0.1/", "http://[::1]/",
                "http://192.168.1.1/", "http://100.64.0.1/", "http://example.com:8080/"):
        monkeypatch.setattr(rs, "_resolve", lambda h: [h.strip("[]")] if h[0].isdigit() or h.startswith("[") or ":" in h else ["93.184.216.34"])
        with pytest.raises(rs.FetchBlocked):
            await rs.check_url(bad, local=False)
    monkeypatch.setattr(rs, "_resolve", lambda h: ["10.1.2.3"])                      # a public-looking name that resolves private
    with pytest.raises(rs.FetchBlocked):
        await rs.check_url("https://totally-public.example.com/", local=False)
    monkeypatch.setattr(rs, "_resolve", lambda h: ["93.184.216.34", "127.0.0.1"])    # one bad address among good ones
    with pytest.raises(rs.FetchBlocked):
        await rs.check_url("https://rebind.example.com/", local=False)
    monkeypatch.setattr(rs, "_resolve", lambda h: ["93.184.216.34"])
    await rs.check_url("https://example.com/page", local=False)
    monkeypatch.setattr(rs, "_resolve", lambda h: ["127.0.0.1"])
    await rs.check_url("http://127.0.0.1:8765/x", local=True)                         # simulator only in local egress mode
    with pytest.raises(rs.FetchBlocked):
        await rs.check_url("http://127.0.0.1:8765/x", local=False)


def test_redact_and_extract():
    assert rs.redact_url("https://u:p@example.com/a?utm_token=abc&q=1#frag") == "https://example.com/a?utm_token=REDACTED&q=1"
    title, facts = rs.extract_facts('<title> Duka  Moja </title><script type="application/ld+json">{"@type":"LocalBusiness","name":"Duka Moja",'
                                    '"telephone":"0712 345 678","address":{"addressLocality":"Nakuru"}}</script><a href="mailto:a@dukamoja.example.com?x=1">m</a>'
                                    '<a href="tel:+254712345678">t</a><script type="application/ld+json">{broken</script>', "u")
    got = {(f["field"], f["value"]) for f in facts}
    assert title == "Duka Moja" and ("phone", "+254712345678") in got and ("city", "Nakuru") in got and ("email", "a@dukamoja.example.com") in got
    assert sum(1 for f in facts if f["field"] == "phone") == 1            # same number from JSON-LD and tel: is one fact


@pytest.mark.asyncio
async def test_safe_fetch_against_simulator(monkeypatch):
    use_sim(monkeypatch)
    base = "http://127.0.0.1:8765/site"
    got = await rs.safe_fetch(f"{base}/redir-ok")
    assert got["final_url"].endswith("/site/duka-moja") and "Duka Moja" in got["text"]
    for path, why in (("redir-private", "non-public"), ("pdf", "Content type"), ("loop", "redirects"), ("nope", "HTTP 404")):
        with pytest.raises(rs.FetchBlocked, match=why):
            await rs.safe_fetch(f"{base}/{path}")
    setv(monkeypatch, "M50_FETCH_MAX_BYTES", 1000)
    with pytest.raises(rs.FetchBlocked, match="size limit"):
        await rs.safe_fetch(f"{base}/big")
    with pytest.raises(rs.FetchBlocked, match="egress|non-public|Blocked"):        # local egress never reaches a non-simulator host
        await rs.safe_fetch("http://203.0.113.9/x")
    setv(monkeypatch, "PROVIDER_EGRESS", "off")
    with pytest.raises(rs.FetchBlocked, match="egress"):
        await rs.safe_fetch(f"{base}/duka-moja")


@pytest.mark.asyncio
async def test_live_mode_refuses_loopback_and_private_redirect(monkeypatch):
    use_sim(monkeypatch)
    from app.core import provider_http
    setv(monkeypatch, "PROVIDER_EGRESS", "live")
    monkeypatch.setattr(provider_http, "_refuse_internal", lambda h: None)           # egress DNS guard is not under test here
    monkeypatch.setattr(rs, "_resolve", lambda h: [h] if h[0].isdigit() else ["93.184.216.34"])
    with pytest.raises(rs.FetchBlocked, match="non-public"):
        await rs.safe_fetch("https://127.0.0.1/site/duka-moja")
    with pytest.raises(rs.FetchBlocked, match="non-public"):                          # public host redirecting to link-local
        await rs.safe_fetch("https://fixture.example.com/site/redir-private")
    assert (await rs.safe_fetch("https://fixture.example.com/site/duka-moja"))["size"] > 0


@DB
@pytest.mark.asyncio
async def test_search_state_pagination_errors_and_retention(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.m50_prospecting import M50ResearchDoc, M50ResearchQuery
    from datetime import timedelta
    await ensure_tables()
    use_sim(monkeypatch)
    async with AsyncSessionLocal() as db:
        viewer = await staff(db, "view", ("crm.view",))
        editor = await staff(db, "edit", ("crm.view", "crm.edit"))
        admin = await staff(db, "adm", ("crm.edit_all",))
        await db.commit()
    body = {"provider": "brave", "enabled": False, "licensed": False, "retention_days": 30, "config": {"country": "KE", "search_lang": "en"}}
    async with client_for(viewer) as c, client_for(editor) as e, client_for(admin) as a:
        assert (await a.put("/api/v1/prospecting-agent/settings/SEARCH", json=body)).status_code == 200
        st = (await c.get("/api/v1/prospecting-agent/state")).json()["search"]
        assert st["state"] == "NOT_CONFIGURED" and len(st["reasons"]) == 2                 # key present; off and unlicensed
        r = await e.post("/api/v1/prospecting-agent/research/search", json={"q": "duka moja"})
        assert r.status_code == 409 and "not configured" in r.json()["detail"] and await sim_calls() == []   # no provider call at all
        assert (await c.post("/api/v1/prospecting-agent/research/search", json={"q": "x"})).status_code == 403
        bad = await a.put("/api/v1/prospecting-agent/settings/SEARCH", json={**body, "enabled": True, "licensed": True})
        assert bad.status_code == 422                                                       # licence basis required
        await a.put("/api/v1/prospecting-agent/settings/SEARCH", json={**body, "enabled": True, "licensed": True,
                                                                        "license_note": "Brave Search API Free plan, owner-confirmed (simulated)"})
        r = (await e.post("/api/v1/prospecting-agent/research/search", json={"q": "Duka Moja Supermarket Nakuru", "page": 0})).json()
        assert [x["rank"] for x in r["results"]][:1] == [1] and len(r["results"]) == 3 and "abc123" not in str(r["results"])
        assert "<strong>" not in r["results"][0]["description"] and "utm_token=REDACTED" in r["results"][0]["url"]
        calls = await sim_calls()
        assert calls[-1]["country"] == "KE" and calls[-1]["offset"] == 0                    # locale from settings, provider page 0
        # retry on 429 then success; persistent failure is mapped and recorded
        await sim_control({"faults": {"brave": ["429"]}})
        assert (await e.post("/api/v1/prospecting-agent/research/search", json={"q": "kibanda stores"})).status_code == 200
        await sim_control({"faults": {"brave": ["429", "429", "429"]}})
        bad = await e.post("/api/v1/prospecting-agent/research/search", json={"q": "kibanda stores"})
        assert bad.status_code == 502 and "rate limit" in bad.json()["detail"]
        assert (await e.post("/api/v1/prospecting-agent/research/search", json={"q": "x", "page": 10})).status_code == 422
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(M50ResearchQuery).where(M50ResearchQuery.status == "ERROR"))).scalars().first() is not None
        q2 = await rs.search(db, "duka moja supermarket nakuru kibanda", "t", page=0, count=2)
        q3 = await rs.search(db, "duka moja supermarket nakuru kibanda", "t", page=1, count=2)
        assert q2.more_available and [x["rank"] for x in q3.results] == [3, 4][:len(q3.results)] and len(q3.results) >= 1
        # fetch + verification
        docs = [await rs.fetch_and_store(db, f"http://127.0.0.1:8765/site/{p}", "t") for p in ("duka-moja", "duka-moja-dir")]
        rec = {x["field"]: x for x in rs.reconcile(docs)}
        assert rec["phone"]["verdict"] == "CORROBORATED" and rec["name"]["verdict"] == "CORROBORATED"
        assert rec["email"]["verdict"] == "SINGLE_SOURCE" and rec["region"]["verdict"] == "UNKNOWN"
        docs.append(await rs.fetch_and_store(db, "http://127.0.0.1:8765/site/duka-moja-conflict", "t"))
        rec = {x["field"]: x for x in rs.reconcile(docs)}
        assert rec["phone"]["verdict"] == "CONFLICT" and {v["value"] for v in rec["city"]["values"]} == {"nakuru", "naivasha"}
        blocked = await rs.fetch_and_store(db, "http://127.0.0.1:8765/site/redir-private", "t")
        assert blocked.status == "BLOCKED" and "non-public" in blocked.reason and blocked.facts == []
        for d in docs[:2]:
            d.expires_at = d.retrieved_at - timedelta(days=1)
        await db.flush()
        assert await rs.purge_expired(db) >= 2
        # egress off: nothing leaves, nothing is paid
        n = len(await sim_calls())
        setv(monkeypatch, "PROVIDER_EGRESS", "off")
        with pytest.raises(rs.ResearchError, match="egress"):
            await rs.search(db, "duka moja", "t")
        setv(monkeypatch, "PROVIDER_EGRESS", "local")
        assert len(await sim_calls()) == n
        await db.rollback()
        assert (await db.execute(select(M50ResearchDoc).limit(1))) is not None
