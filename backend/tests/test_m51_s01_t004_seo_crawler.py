"""M51.S01.T004 technical SEO crawler, vitals (lab vs field), keyword import and competitor comparison (DB part M51_DB=1)."""
import os

import pytest

from app.services import m51_seo_crawler as cr
from tests.m51_s01_seo_common import SIM, client_for, ensure_tables, setv, sim_calls, sim_control, staff, use_sim

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
P = "/api/v1/seo-pro"


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    from app.core import provider_http
    provider_http.set_test_transport(None)
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_parse_html_and_jsonld_validation():
    info = cr.parse_html('<html lang="en"><head><title> A  B </title><meta name="description" content="d"><link rel="canonical" href="/x">'
                         '<link rel="alternate" hreflang="xx_bad" href="/y"><script type="application/ld+json">{"@context":"https://schema.org","@type":"Product"}</script>'
                         '<script type="application/ld+json">{oops</script></head><body><h1>H</h1><img src="a"><img src="b" alt=""><a href="/z"></a></body></html>')
    assert info["title"] == "A B" and info["canonical"] == "/x" and info["h1"] == 1 and info["empty_links"] == 1
    assert [i["alt"] for i in info["imgs"]] == [None, ""]                       # alt="" is valid (decorative), a missing alt is not
    assert len(info["jsonld_errors"]) == 1 and cr.validate_jsonld(info["jsonld"]) == ["Product is missing name"]
    assert not cr.HREFLANG_RE.match("xx_bad") and cr.HREFLANG_RE.match("sw-KE") and cr.HREFLANG_RE.match("x-default")


def test_origin_of():
    assert cr.origin_of("https://WWW.Example.com:8443/a?b=1") == "https://www.example.com:8443"
    for bad in ("ftp://x.com", "https://u:p@x.com", "notaurl"):
        with pytest.raises(cr.CrawlError):
            cr.origin_of(bad)


async def _setup(perms=("marketing.edit",)):
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    await ensure_tables()
    async with AsyncSessionLocal() as db:
        for t in ("m51_seo_sites", "m51_seo_crawls", "m51_keywords"):      # disposable DB: start every test clean
            await db.execute(text(f"DELETE FROM {t}"))
        u = await staff(db, "seo", perms)
        await db.commit()
    return u


async def _allow(c, origin, kind="OWN", note="Owner confirmed in writing", confirm=True):
    return await c.post(f"{P}/sites", json={"origin": origin, "kind": kind, "note": note, "confirm_authorized": confirm})


@DB
@pytest.mark.asyncio
async def test_allow_list_blocks_unauthorized_and_ssrf(monkeypatch):
    use_sim(monkeypatch)
    await sim_control({"reset": True})
    u = await _setup()
    async with client_for(u) as c:
        r = await c.post(f"{P}/crawl", json={"origin": "http://stranger.localhost:8766"})
        assert r.status_code == 403 and await sim_calls() == []                         # nothing fetched
        assert (await _allow(c, "http://stranger.localhost:8766", confirm=False)).status_code == 422
        assert (await _allow(c, "http://src.localhost:8766", kind="AUTHORIZED_SOURCE", note="x")).status_code == 422
        assert (await _allow(c, "http://src.localhost:8766", kind="AUTHORIZED_SOURCE")).status_code == 201
        assert (await c.post(f"{P}/crawl", json={"origin": "http://src.localhost:8766"})).status_code == 403   # sources are not crawled
        assert (await _allow(c, "http://src.localhost:8766", kind="AUTHORIZED_SOURCE")).status_code == 409
        # an allow-listed but internal address is still refused by the SSRF check
        assert (await _allow(c, "http://169.254.169.254")).status_code == 201
        run = (await c.post(f"{P}/crawl", json={"origin": "http://169.254.169.254"})).json()
        assert run["status"] == "FAILED" and ("egress" in run["error"].lower() or "non-public" in run["error"] or "Only local" in run["error"])
        assert await sim_calls() == []
        assert (await c.post(f"{P}/crawl", json={"origin": "ftp://x"})).status_code in (403, 422)
    async with client_for(await _setup(("marketing.view",))) as v:
        assert (await _allow(v, "http://another.localhost:8766")).status_code == 403
        assert (await v.post(f"{P}/crawl", json={"origin": SIM})).status_code == 403
        assert (await v.get(f"{P}/crawls")).status_code == 200


@DB
@pytest.mark.asyncio
async def test_crawl_fix_recrawl_compare(monkeypatch):
    use_sim(monkeypatch)
    await sim_control({"reset": True})
    u = await _setup()
    async with client_for(u) as c:
        await _allow(c, SIM)
        first = (await c.post(f"{P}/crawl", json={"origin": SIM})).json()
        assert first["status"] == "DONE"
        d1 = (await c.get(f"{P}/crawls/{first['id']}")).json()
        codes = {i["code"] for i in d1["issues"]}
        want = {"BROKEN_LINK", "REDIRECT_CHAIN", "REDIRECT_LOOP", "REDIRECT_EXTERNAL", "DUPLICATE_TITLE", "DUPLICATE_META",
                "CANONICAL_MISSING", "IMG_ALT_MISSING", "JSONLD_INVALID", "SITEMAP_URL_BROKEN", "SITEMAP_URL_NOINDEX",
                "HREFLANG_NO_RETURN", "H1_MULTIPLE", "LINK_TEXT_EMPTY", "ROBOTS_BLOCKED", "NOINDEX"}
        assert want <= codes, want - codes
        assert any(i["code"] == "BROKEN_LINK" and "/missing" in i["detail"] for i in d1["issues"])
        assert "PRIVATE_FETCHED" not in await sim_calls()                              # robots.txt honoured
        assert first["summary"]["robots_txt"] and first["summary"]["errors"] > 0 and not any(p["url"].endswith("/private/x") for p in d1["pages"])
        assert not [i for i in d1["issues"] if "example.com" in i["url"]]               # off-site redirect was not followed

        await sim_control({"fixed": True})                                              # "fix" the synthetic site and crawl again
        second = (await c.post(f"{P}/crawl", json={"origin": SIM})).json()
        assert second["summary"]["errors"] == 0 and second["summary"]["issues"] < first["summary"]["issues"]
        diff = (await c.get(f"{P}/crawls/compare", params={"a": first["id"], "b": second["id"]})).json()
        res = {(i["code"]) for i in diff["resolved"]}
        assert {"BROKEN_LINK", "DUPLICATE_TITLE", "JSONLD_INVALID", "SITEMAP_URL_BROKEN"} <= res
        assert not [i for i in diff["new"] if i["severity"] == "ERROR"] and diff["unchanged"] > 0
        assert len((await c.get(f"{P}/crawls", params={"origin": SIM})).json()) >= 2

        capped = (await c.post(f"{P}/crawl", json={"origin": SIM, "max_pages": 2})).json()
        assert capped["summary"]["pages"] == 2 and capped["summary"]["capped"] is True


@DB
@pytest.mark.asyncio
async def test_vitals_lab_unavailable_field_separate(monkeypatch):
    use_sim(monkeypatch)
    await sim_control({"reset": True})
    u = await _setup()
    monkeypatch.setattr(cr, "lab_tool", lambda: None)
    async with client_for(u) as c:
        await _allow(c, SIM)
        lab = (await c.post(f"{P}/vitals/lab", json={"url": SIM + "/"})).json()
        assert lab["kind"] == "LAB" and lab["state"] == "UNAVAILABLE" and lab["metrics"] is None
        assert (await c.post(f"{P}/vitals/lab", json={"url": "https://other.example.org/"})).status_code == 403
        setv(monkeypatch, "CRUX_API_KEY", "")
        assert (await c.post(f"{P}/vitals/field", json={"url": SIM})).json()["state"] == "NOT_CONFIGURED"
        setv(monkeypatch, "CRUX_API_KEY", "sim-crux-key")
        f = (await c.post(f"{P}/vitals/field", json={"url": SIM, "form_factor": "PHONE"})).json()
        assert f["kind"] == "FIELD" and f["state"] == "OK" and f["metrics"]["largest_contentful_paint"]["p75"] == 2100
        assert f["collection_period"]["lastDate"]["day"] == 24 and "lab" not in f      # field data carries no lab numbers
        assert (await c.post(f"{P}/vitals/field", json={"url": SIM, "form_factor": "WATCH"})).status_code == 422
        await sim_control({"faults": {"crux": ["429"]}})
        assert (await c.post(f"{P}/vitals/field", json={"url": SIM})).json()["state"] == "RATE_LIMITED"
        await _allow(c, "http://nodata.localhost:8766")
        assert (await c.post(f"{P}/vitals/field", json={"url": "http://nodata.localhost:8766"})).json()["state"] == "NO_DATA"


@DB
@pytest.mark.asyncio
async def test_lab_runs_when_tool_present(monkeypatch):
    use_sim(monkeypatch)
    await sim_control({"reset": True})
    u = await _setup()
    from tests.test_m51_s01_t011_review_fixes import fake_playwright
    fake_playwright(monkeypatch, {"lcp": 1900, "cls": 0.01})
    async with client_for(u) as c:
        await _allow(c, SIM)
        lab = (await c.post(f"{P}/vitals/lab", json={"url": SIM + "/"})).json()
        assert lab["state"] == "OK" and lab["tool"] == "playwright" and lab["metrics"]["lcp_ms"] == 1900


@DB
@pytest.mark.asyncio
async def test_keyword_import_coverage_and_competitor(monkeypatch):
    use_sim(monkeypatch)
    await sim_control({"reset": True})
    u = await _setup()
    csv_ok = "keyword,volume,difficulty,cpc,locale,intent\npovu allclean,900,30,0.4,en,commercial\n=cmd|' /c calc'!A1,10,5,0.1,en,\nsabuni ya povu,50,20,,sw,\nbad row,abc,1,1,en,\npovu allclean,1,1,1,en,\n"
    async with client_for(u) as c:
        await _allow(c, SIM)
        out = (await c.post(f"{P}/keywords/import", json={"csv_text": csv_ok, "source": "povu-demo-csv"})).json()
        assert out["imported"] == 3 and out["rejected_count"] == 1 and out["rejected"][0]["line"] == 5
        kws = {k["keyword"] for k in (await c.get(f"{P}/keywords")).json()}
        assert "povu allclean" in kws and not any(k.startswith(("=", "+", "-", "@")) for k in kws)    # formula injection stripped
        assert (await c.post(f"{P}/keywords/import", json={"csv_text": "keyword,evil\na,b", "source": "x1"})).status_code == 422
        assert (await c.post(f"{P}/keywords/import", json={"csv_text": csv_ok, "source": "x"})).status_code == 422
        provs = {p["id"]: p["state"] for p in (await c.get(f"{P}/keywords/providers")).json()}
        assert provs == {"csv": "OK", "paid_api": "UNVERIFIED"}
        crawl = (await c.post(f"{P}/crawl", json={"origin": SIM})).json()
        cov = {k["keyword"]: k for k in (await c.get(f"{P}/keywords/coverage/{crawl['id']}")).json()}
        assert cov["povu allclean"]["covered"] is True and cov["sabuni ya povu"]["covered"] is False

        own = SIM + "/about"
        cmp_ = (await c.post(f"{P}/competitor/compare", json={"own_url": own, "competitor_text": "Rival detergent powder offers stain removal and fragrance."})).json()
        assert cmp_["own"]["words"] > 0 and "detergent" in cmp_["terms_only_in_other"]
        assert (await c.post(f"{P}/competitor/compare", json={"own_url": own, "competitor_url": "https://rival.example.com/"})).status_code == 403
        assert (await c.post(f"{P}/competitor/compare", json={"own_url": own})).status_code == 422
        await _allow(c, "http://localhost:8766", kind="AUTHORIZED_SOURCE")
        ok = (await c.post(f"{P}/competitor/compare", json={"own_url": own, "competitor_url": "http://localhost:8766/products"})).json()
        assert ok["other"]["words"] > 0
