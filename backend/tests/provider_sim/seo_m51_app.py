"""Local simulator for M51.S01.T003/T004: Google Search Console API, URL Inspection API, Chrome UX Report API and a
synthetic website to crawl (synthetic data only, in memory, never a real provider).

Contracts followed (docs checked 2026-11-26):
- Search Console API v3  POST /gsc/webmasters/v3/sites/{siteUrl}/searchAnalytics/query  (body: startDate, endDate,
  dimensions, dimensionFilterGroups[{groupType: and, filters[{dimension, operator, expression}]}], rowLimit<=25000,
  startRow, dataState; response rows[{keys, clicks, impressions, ctr, position}], responseAggregationType, metadata)
  GET /sites, GET /sites/{siteUrl}/sitemaps, GET|PUT /sites/{siteUrl}/sitemaps/{feedpath}   (PUT needs scope webmasters)
  https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- URL Inspection  POST /gsc/v1/urlInspection/index:inspect {inspectionUrl, siteUrl, languageCode} → {inspectionResult}
  https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- CrUX  POST /crux/v1/records:queryRecord?key=  {origin|url, formFactor, metrics} → record.metrics.*.percentiles.p75,
  histogram, collectionPeriod; the no-data answer (404) is an assumption.  https://developer.chrome.com/docs/crux/api
The bearer token's scope is read from the token text: tokens containing "ro" are read-only (PUT sitemap → 403).
Control: POST /_control {"faults": {"gsc": ["429","429"], "crux": ["429"]}, "fixed": true|false, "scope_rw": bool},
GET /_control/calls.
Synthetic site at / (state "broken" has a deliberate set of SEO defects; "fixed" removes them).
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import unquote

from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

CRUX_KEY = "sim-crux-key"
SITE = "https://povu-demo.test/"


def sim_settings(base: str = "http://127.0.0.1:8766") -> dict:
    return {"GSC_API_BASE": f"{base}/gsc/webmasters/v3", "GSC_INSPECT_URL": f"{base}/gsc/v1/urlInspection/index:inspect",
            "CRUX_API_KEY": CRUX_KEY, "CRUX_API_URL": f"{base}/crux/v1/records:queryRecord", "M51_BACKOFF_BASE": 0.001}


QUERIES = ["povu allclean", "hand wash powder", "povu soap"]
PAGES = ["https://povu-demo.test/", "https://povu-demo.test/products"]
FIX = [{"query": q, "page": p, "country": c, "device": d, "date": f"2026-11-{day:02d}",
        "clicks": (i + 1) * (day % 4 + 1), "impressions": (i + 1) * 40 + day, "position": 3.0 + i}
       for i, (q, p, c, d) in enumerate([(q, p, c, d) for q in QUERIES for p in PAGES for c in ("ken", "tza") for d in ("MOBILE", "DESKTOP")])
       for day in (1, 2)]


def _site(fixed: bool, base: str) -> dict:
    bad_title = "POVU" if not fixed else None
    ld_ok = '{"@context":"https://schema.org","@type":"Organization","name":"POVU Demo","url":"https://povu-demo.test/"}'
    ld_bad = '{"@context":"https://schema.org","@type":"Organization"'
    pages = {
        "/": f'<html lang="en"><head><title>POVU AllClean home cleaning</title><meta name="description" content="POVU home care products for every household in East Africa.">'
             f'<meta name="viewport" content="width=device-width"><link rel="canonical" href="{base}/">'
             f'<link rel="alternate" hreflang="en" href="{base}/"><link rel="alternate" hreflang="sw" href="{base}/sw">'
             f'<script type="application/ld+json">{ld_ok}</script></head><body><h1>POVU AllClean</h1>'
             f'<a href="/products">Products</a> <a href="/about">About</a> <a href="/old">Old</a>'
             + ('' if fixed else '<a href="/missing">Gone</a> <a href="/private/x">Private</a> <a href="/loop">Loop</a> <a href="/out">Out</a> <a href="/empty"></a>')
             + ('<img src="/a.png" alt="Bottle">' if fixed else '<img src="/a.png">') + '</body></html>',
        "/products": f'<html lang="en"><head><title>{"POVU products" if fixed else "POVU"}</title>'
                     f'<meta name="description" content="{"All POVU products" if fixed else "POVU home care products for every household in East Africa."}">'
                     f'<meta name="viewport" content="x">{"<link rel=canonical href=" + base + "/products>" if fixed else ""}'
                     f'<script type="application/ld+json">{ld_ok if fixed else ld_bad}</script></head><body><h1>Products</h1><h1>More</h1></body></html>',
        "/about": f'<html lang="en"><head><title>{"About POVU" if fixed else "POVU"}</title><meta name="description" content="About POVU, a home care brand from Kenya."><meta name="viewport" content="x">'
                  f'<link rel="canonical" href="{base}/about"></head><body><h1>About</h1></body></html>',
        "/sw": '<html lang="sw"><head><title>POVU Nyumbani</title><meta name="description" content="Bidhaa za POVU za usafi wa nyumbani kwa kila familia.">'
               '<meta name="viewport" content="x"><link rel="canonical" href="/sw"></head><body><h1>POVU</h1></body></html>',
        "/noindexed": '<html lang="en"><head><title>Draft</title><meta name="robots" content="noindex"><meta name="viewport" content="x"></head><body><h1>Draft</h1></body></html>',
    }
    if fixed:
        pages["/sw"] = pages["/sw"].replace('<link rel="canonical"', f'<link rel="alternate" hreflang="en" href="{base}/"><link rel="canonical"')
    return pages


def create_app() -> FastAPI:
    app = FastAPI(title="POVU SEO/GSC/CrUX simulator (synthetic, local only)")
    st: dict = {}

    def reset():
        st.clear()
        st.update(faults=defaultdict(list), fixed=False, calls=[], sitemaps={}, rw=True)
    reset()

    def fault(kind: str):
        q = st["faults"][kind]
        if not q:
            return None
        f = q.pop(0)
        return JSONResponse({"error": {"code": int(f), "message": "simulated"}}, int(f), headers={"Retry-After": "0"})

    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        if b.get("reset"):
            reset()
        for k, v in (b.get("faults") or {}).items():
            st["faults"][k] = list(v)
        if "fixed" in b:
            st["fixed"] = bool(b["fixed"])
        if "scope_rw" in b:
            st["rw"] = bool(b["scope_rw"])
        return {"ok": True}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    # ── Search Console ──────────────────────────────────────────────────────────────────────────
    def auth(h):
        return bool(h and h.startswith("Bearer ") and len(h) > 10)

    @app.get("/gsc/webmasters/v3/sites")
    async def sites(authorization: str = Header(None)):
        st["calls"].append("sites")
        if not auth(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        return {"siteEntry": [{"siteUrl": SITE, "permissionLevel": "siteOwner"}, {"siteUrl": "sc-domain:povu-demo.test", "permissionLevel": "siteFullUser"}]}

    @app.post("/gsc/webmasters/v3/sites/{site:path}/searchAnalytics/query")
    async def query(site: str, request: Request, authorization: str = Header(None)):
        st["calls"].append("query")
        if not auth(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        if (f := fault("gsc")):
            return f
        site = unquote(site)
        if site not in (SITE, "sc-domain:povu-demo.test"):
            return JSONResponse({"error": {"code": 403, "message": "User does not have sufficient permission for site"}}, 403)
        b = await request.json()
        if not b.get("startDate") or not b.get("endDate") or b.get("rowLimit", 1000) > 25000:
            return JSONResponse({"error": {"code": 400, "message": "Invalid value"}}, 400)
        dims = b.get("dimensions", [])
        rows = [r for r in FIX if b["startDate"] <= r["date"] <= b["endDate"]]
        for g in b.get("dimensionFilterGroups", []):
            for f in g["filters"]:
                op, ex, d = f.get("operator", "equals"), f["expression"], f["dimension"]
                rows = [r for r in rows if {"equals": r[d].lower() == ex.lower(), "contains": ex.lower() in r[d].lower(),
                                           "notEquals": r[d].lower() != ex.lower(), "notContains": ex.lower() not in r[d].lower()}.get(op, True)]
        agg: dict = {}
        for r in rows:
            k = tuple(r[d] for d in dims)
            a = agg.setdefault(k, {"clicks": 0, "impressions": 0, "pos": 0.0, "n": 0})
            a["clicks"] += r["clicks"]
            a["impressions"] += r["impressions"]
            a["pos"] += r["position"] * r["impressions"]
            a["n"] += r["impressions"]
        out = [{"keys": list(k), "clicks": a["clicks"], "impressions": a["impressions"],
                "ctr": round(a["clicks"] / a["impressions"], 4), "position": round(a["pos"] / a["n"], 2)} for k, a in agg.items()]
        out.sort(key=(lambda x: x["keys"]) if "date" in dims else (lambda x: -x["clicks"]))
        s, n = b.get("startRow", 0), b.get("rowLimit", 1000)
        res = {"rows": out[s:s + n], "responseAggregationType": "auto"}
        if str(b.get("dataState", "final")).lower() == "all":
            res["metadata"] = {"first_incomplete_date": "2026-11-02"}
        return res

    @app.get("/gsc/webmasters/v3/sites/{site:path}/sitemaps/{feed:path}")
    async def sitemap_get(site: str, feed: str, authorization: str = Header(None)):
        st["calls"].append("sitemap_get")
        got = st["sitemaps"].get(unquote(feed))
        if got is None:
            return JSONResponse({"error": {"code": 404, "message": "Sitemap not found"}}, 404)
        return got

    @app.get("/gsc/webmasters/v3/sites/{site:path}/sitemaps")
    async def sitemap_list(site: str, authorization: str = Header(None)):
        st["calls"].append("sitemap_list")
        return {"sitemap": list(st["sitemaps"].values())}

    @app.put("/gsc/webmasters/v3/sites/{site:path}/sitemaps/{feed:path}")
    async def sitemap_put(site: str, feed: str, authorization: str = Header(None)):
        st["calls"].append("sitemap_put")
        if not st["rw"]:
            return JSONResponse({"error": {"code": 403, "message": "Insufficient scope"}}, 403)
        feed = unquote(feed)
        st["sitemaps"][feed] = {"path": feed, "isPending": True, "isSitemapsIndex": False, "lastSubmitted": "2026-11-26T08:00:00Z", "warnings": "0", "errors": "0"}
        return Response(status_code=200)

    @app.post("/gsc/v1/urlInspection/index:inspect")
    async def inspect(request: Request, authorization: str = Header(None)):
        st["calls"].append("inspect")
        if (f := fault("gsc")):
            return f
        b = await request.json()
        if not b.get("inspectionUrl", "").startswith(b.get("siteUrl", "\0").rstrip("/")) and not b.get("siteUrl", "").startswith("sc-domain:"):
            return JSONResponse({"error": {"code": 400, "message": "inspectionUrl is not under siteUrl"}}, 400)
        return {"inspectionResult": {"inspectionResultLink": "https://search.google.test/x", "indexStatusResult": {
            "verdict": "PASS", "coverageState": "Submitted and indexed", "robotsTxtState": "ALLOWED", "indexingState": "INDEXING_ALLOWED",
            "lastCrawlTime": "2026-11-20T10:00:00Z", "pageFetchState": "SUCCESSFUL", "googleCanonical": b["inspectionUrl"], "userCanonical": b["inspectionUrl"]}}}

    # ── CrUX ────────────────────────────────────────────────────────────────────────────────────
    @app.post("/crux/v1/records:queryRecord")
    async def crux(request: Request, key: str = ""):
        st["calls"].append("crux")
        if key != CRUX_KEY:
            return JSONResponse({"error": {"code": 400, "message": "API key not valid"}}, 400)
        if (f := fault("crux")):
            return f
        b = await request.json()
        target = b.get("origin") or b.get("url") or ""
        if "nodata" in target:
            return JSONResponse({"error": {"code": 404, "message": "chrome ux report data not found"}}, 404)
        hist = [{"start": 0, "end": 2500, "density": 0.8}, {"start": 2500, "end": 4000, "density": 0.15}, {"start": 4000, "density": 0.05}]
        return {"record": {"key": {k: v for k, v in b.items() if k in ("origin", "url", "formFactor")},
                           "metrics": {"largest_contentful_paint": {"histogram": hist, "percentiles": {"p75": 2100}},
                                       "interaction_to_next_paint": {"histogram": hist, "percentiles": {"p75": 180}}},
                           "collectionPeriod": {"firstDate": {"year": 2026, "month": 10, "day": 28}, "lastDate": {"year": 2026, "month": 11, "day": 24}}}}

    # ── synthetic website ───────────────────────────────────────────────────────────────────────
    @app.get("/robots.txt")
    async def robots(request: Request):
        st["calls"].append("robots")
        return PlainTextResponse(f"User-agent: *\nDisallow: /private/\nSitemap: {str(request.base_url).rstrip('/')}/sitemap.xml\n")

    @app.get("/sitemap.xml")
    async def sitemap(request: Request):
        b = str(request.base_url).rstrip("/")
        urls = ["/", "/products", "/about", "/sw"] + ([] if st["fixed"] else ["/ghost", "/noindexed"])
        return Response("<?xml version='1.0'?><urlset>" + "".join(f"<url><loc>{b}{u}</loc></url>" for u in urls) + "</urlset>", media_type="application/xml")

    @app.get("/old")
    async def old():
        return RedirectResponse("/old2", 301)

    @app.get("/old2")
    async def old2():
        return RedirectResponse("/products", 301)

    @app.get("/loop")
    async def loop():
        return RedirectResponse("/loop", 302)

    @app.get("/out")
    async def out():
        return RedirectResponse("https://example.com/elsewhere", 302)

    @app.get("/empty")
    async def empty():
        return HTMLResponse("<html lang=en><head><title>Empty</title></head><body><h1>x</h1></body></html>")

    @app.get("/private/x")
    async def private():
        st["calls"].append("PRIVATE_FETCHED")
        return HTMLResponse("<html><head><title>secret</title></head></html>")

    @app.get("/{path:path}")
    async def page(path: str, request: Request):
        st["calls"].append("page:/" + path)
        pages = _site(st["fixed"], str(request.base_url).rstrip("/"))
        html = pages.get("/" + path)
        if html is None:
            return HTMLResponse("<html><body>Not found</body></html>", 404)
        return HTMLResponse(html)

    return app
