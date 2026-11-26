"""M51.S01.T005 AEO measurement: sampling statistics, mention/citation analysis, NOT_CONFIGURED, caps (DB part M51_DB=1).
No paid call is ever made: providers are the local simulator or a ScriptedProvider."""
import os

import pytest

from app.services import ai_provider as ai
from app.services import m51_aeo_service as aeo
from tests.m51_s01_seo_common import client_for, ensure_tables, setv, staff

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
P = "/api/v1/seo-pro/aeo"


@pytest.fixture(autouse=True)
async def _cleanup(monkeypatch):
    monkeypatch.setattr(ai, "MAX_RETRY_SLEEP_S", 0.001)
    yield
    monkeypatch.setattr(aeo, "_override", None)
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_wilson_interval():
    assert aeo.wilson(0, 0) == {"rate": None, "low": None, "high": None, "n": 0}
    w = aeo.wilson(5, 10)
    assert w["rate"] == 0.5 and 0.23 < w["low"] < 0.24 and 0.76 < w["high"] < 0.77       # known Wilson 95 % bounds for 5/10
    assert aeo.wilson(0, 10)["low"] == 0 and aeo.wilson(10, 10)["high"] == 1
    big = aeo.wilson(500, 1000)
    assert big["high"] - big["low"] < w["high"] - w["low"]                                # more samples, tighter interval


def test_analyse_mentions_citations_and_locales():
    a = aeo.analyse("Try POVU AllClean (https://www.povu-demo.test/a). Also RivalSoap, see https://rival.example.com/x.",
                    ["POVU"], ["povu-demo.test"], ["RivalSoap", "OtherCo"])
    assert a["brand"] and a["brand_cited"] and a["competitors"] == ["RivalSoap"] and [c["position"] for c in a["citations"]] == [1, 2]
    assert not aeo.analyse("povuland is unrelated", ["POVU"], [], [])["brand"]                       # word boundaries
    assert aeo.analyse("Sabuni bora ni POVU Safi kwa nyumba", ["POVU"], [], [])["brand"]              # sw
    assert aeo.analyse("En iyi temizleyici POVU'dur", ["POVU"], [], [])["brand"]                      # tr: apostrophe suffix
    assert not aeo.analyse("see https://evilpovu-demo.test/x", ["x"], ["povu-demo.test"], [])["brand_cited"]   # suffix trick


async def _setup(perms=("marketing.edit",)):
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    await ensure_tables()
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM m51_aeo_prompt_sets"))
        u = await staff(db, "aeo", perms)
        await db.commit()
    return u


def body(**kw):
    b = {"name": "Home care", "locale": "en", "prompts": ["best hand wash powder in Kenya", "affordable all purpose cleaner"],
         "brand_terms": ["POVU"], "brand_domains": ["povu-demo.test"], "competitor_terms": ["RivalSoap"],
         "provider": "simulator", "samples_per_prompt": 3, "max_calls_per_run": 30, "consent_confirmed": True}
    b.update(kw)
    return b


@DB
@pytest.mark.asyncio
async def test_not_configured_never_invents(monkeypatch):
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(ai, "_instance", ai.MockProvider())
    u = await _setup()
    async with client_for(u) as c:
        for kw, why in ((dict(provider=""), "No answer-engine provider"), (dict(provider="ai_provider"), "mock provider"),
                        (dict(consent_confirmed=False), "owner has not confirmed")):
            sid = (await c.post(f"{P}/sets", json=body(**kw))).json()["id"]
            st = (await c.get(f"{P}/sets/{sid}/state")).json()
            assert st["state"] == "NOT_CONFIGURED" and why in " ".join(st["reasons"]) and "readiness" in st["readiness_note"]
            r = await c.post(f"{P}/sets/{sid}/run")
            assert r.status_code == 409 and "NOT_CONFIGURED" in r.text
            assert (await c.get(f"{P}/sets/{sid}/trend")).json() == []                          # no run, no number
        assert (await c.post(f"{P}/sets", json=body(locale="fr"))).status_code == 422
        setv(monkeypatch, "PROVIDER_EGRESS", "live")
        sid = (await c.post(f"{P}/sets", json=body())).json()["id"]
        assert (await c.get(f"{P}/sets/{sid}/state")).json()["state"] == "NOT_CONFIGURED"        # simulator refused in live mode


@DB
@pytest.mark.asyncio
async def test_simulated_runs_trend_uncertainty_and_provenance(monkeypatch):
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    u = await _setup()
    async with client_for(u) as c:
        locales = {}
        for loc, prompts in (("en", ["best hand wash powder", "affordable all purpose cleaner"]), ("sw", ["sabuni bora ya kuoshea mikono"]), ("tr", ["en iyi el yıkama tozu"])):
            locales[loc] = (await c.post(f"{P}/sets", json=body(locale=loc, prompts=prompts, name=f"Home care {loc}"))).json()["id"]
        sid = locales["en"]
        r1 = (await c.post(f"{P}/sets/{sid}/run")).json()
        s = r1["summary"]
        assert r1["source"] == "SIMULATED" and r1["status"] == "DONE" and r1["calls"] == 6 == s["samples"]
        assert r1["model"] == "aeo-sim" and r1["model_version"] and s["low_sample"] is True and s["locale"] == "en"
        m = s["brand_mention"]
        assert m["n"] == 6 and 0 <= m["low"] <= m["rate"] <= m["high"] <= 1 and m["high"] - m["low"] > 0.2        # wide CI at n=6
        assert set(s["competitors"]) == {"RivalSoap"} and s["competitors"]["RivalSoap"]["rate"] == 1.0
        assert "not a search ranking" in s["note"]
        det = (await c.get(f"{P}/runs/{r1['id']}")).json()
        assert len(det["answers"]) == 6 and all(a["citations"] for a in det["answers"])
        assert sum(a["brand"] for a in det["answers"]) == round(m["rate"] * 6)
        await c.post(f"{P}/sets/{sid}/run")
        tr = (await c.get(f"{P}/sets/{sid}/trend")).json()
        assert len(tr) == 2 and tr[0]["at"] <= tr[1]["at"] and all(t["source"] == "SIMULATED" and t["model"] for t in tr)
        for loc in ("sw", "tr"):                                                                    # localized sets keep their own series
            assert (await c.post(f"{P}/sets/{locales[loc]}/run")).json()["summary"]["locale"] == loc
            assert len((await c.get(f"{P}/sets/{locales[loc]}/trend")).json()) == 1
        assert len((await c.get(f"{P}/sets/{sid}/runs")).json()) == 2


@DB
@pytest.mark.asyncio
async def test_caps_failures_and_rbac(monkeypatch):
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    u = await _setup()
    async with client_for(u) as c:
        big = (await c.post(f"{P}/sets", json=body(samples_per_prompt=10, max_calls_per_run=5))).json()["id"]
        r = await c.post(f"{P}/sets/{big}/run")
        assert r.status_code == 422 and "per-run cap" in r.text
        ok = (await c.post(f"{P}/sets", json=body(prompts=["a question"], samples_per_prompt=1))).json()["id"]
        setv(monkeypatch, "AEO_MONTHLY_CALL_CAP", 0)
        st = (await c.get(f"{P}/sets/{ok}/state")).json()
        assert st["state"] == "NOT_CONFIGURED" and "monthly call cap" in " ".join(st["reasons"])
        setv(monkeypatch, "AEO_MONTHLY_CALL_CAP", 100000)
        # provider failure is counted, never turned into a result
        bad = ai.ScriptedProvider(script=[500] * 20)
        monkeypatch.setattr(aeo, "_override", bad)
        failed = (await c.post(f"{P}/sets/{ok}/run")).json()
        assert failed["status"] == "FAILED" and failed["calls"] == 0 and failed["summary"]["brand_mention"]["rate"] is None
        assert (await c.get(f"{P}/sets/{ok}/trend")).json() == []
        # a scripted provider (no network) with a fixed answer is measured exactly
        monkeypatch.setattr(aeo, "_override", ai.ScriptedProvider(reply=lambda p: "Use POVU AllClean https://povu-demo.test/x"))
        good = (await c.post(f"{P}/sets/{ok}/run")).json()
        assert good["summary"]["brand_mention"]["rate"] == 1.0 and good["summary"]["brand_citation"]["rate"] == 1.0
        assert good["model"] == "scripted-v1"
    async with client_for(await _setup(("marketing.view",))) as v:
        assert (await v.post(f"{P}/sets", json=body())).status_code == 403
        assert (await v.get(f"{P}/sets")).status_code == 200
