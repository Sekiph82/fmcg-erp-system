"""Local simulator for the M50.S01 external data adapters (synthetic, in-memory, never a real provider).

Contracts followed (docs checked 2026-11-26):
- Brave Search API  GET /brave/res/v1/web/search  header X-Subscription-Token; params q, count (<=20), offset (<=9),
  country, search_lang; 200 {"query": {"more_results_available"}, "web": {"results": [{title,url,description}]}};
  401 bad token, 422 bad params, 429 with Retry-After.
  https://api-dashboard.search.brave.com/app/documentation/web-search/query
- People Data Labs Company Enrichment v5  GET /pdl/v5/company/enrich  header X-Api-Key; name / website, min_likelihood;
  200 {"status": 200, "likelihood": 1-10, ...Company Schema}; 404 {"status": 404, "error": {"type": "not_found"}};
  401, 402 (no credits), 429.
  https://docs.peopledatalabs.com/docs/reference-company-enrichment-api
- Fixture pages /site/* for the safe-fetch tests: JSON-LD organisation pages (agreeing and conflicting), an oversized
  page, a PDF, redirects to a link-local address and to a good page, a redirect loop.
Control: POST /_control {"faults": {"brave": ["429"], "pdl": ["402"]}}, GET /_control/calls.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

BRAVE_KEY, PDL_KEY = "sim-brave-key", "sim-pdl-key"


def sim_settings(base: str = "http://127.0.0.1:8765") -> dict:
    return {"BRAVE_SEARCH_API_KEY": BRAVE_KEY, "BRAVE_SEARCH_BASE_URL": f"{base}/brave/res/v1/web/search",
            "PDL_API_KEY": PDL_KEY, "PDL_BASE_URL": f"{base}/pdl"}


def ld(name, phone, city, email=None) -> str:
    node = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": name, "telephone": phone,
            "address": {"@type": "PostalAddress", "addressLocality": city}}
    if email:
        node["email"] = email
    return f'<html><head><title>{name} | Home</title><script type="application/ld+json">{json.dumps(node)}</script></head><body>{name}</body></html>'


WEB = [  # (title, path, description) in rank order
    ("Duka Moja Supermarket - Nakuru", "/site/duka-moja", "Duka Moja Supermarket, a retail outlet in Nakuru stocking home care and Rivalsoap products."),
    ("Duka Moja Supermarket on a directory", "/site/duka-moja-dir", "Directory listing for Duka Moja Supermarket, Nakuru."),
    ("Kibanda Fresh Stores | Nakuru", "/site/kibanda", "Kibanda Fresh Stores sells household goods in Nakuru."),
    ("Mtaani Cleaning Wholesalers - Eldoret", "/site/mtaani", "Wholesale cleaning supplies, Eldoret."),
    ("Unrelated page about weather", "/site/weather", "Rain expected this week."),
]
PDL = {"duka moja supermarket": {"name": "Duka Moja Supermarket", "website": "dukamoja.example.com", "industry": "retail",
                                 "employee_count": 42, "founded": 2011, "linkedin_url": "linkedin.com/company/duka-moja-sim",
                                 "location": {"locality": "Nakuru", "region": "Nakuru County", "country": "kenya"}, "likelihood": 8},
       "weak match ltd": {"name": "Weak Match Ltd", "industry": "retail", "likelihood": 3, "location": {"locality": "Mombasa"}}}


def create_app() -> FastAPI:
    app = FastAPI(title="POVU M50 prospecting simulator")
    st: dict = {"faults": {}, "calls": []}

    def fault(area: str):
        q = st["faults"].get(area) or []
        return q.pop(0) if q else None

    @app.post("/_control")
    async def control(req: Request):
        body = await req.json()
        if body.get("reset"):
            st.update(faults={}, calls=[])
        st["faults"].update({k: list(v) for k, v in (body.get("faults") or {}).items()})
        return {"ok": True}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    @app.get("/brave/res/v1/web/search")
    async def brave(q: str = "", count: int = 20, offset: int = 0, country: str = "", search_lang: str = "",
                    x_subscription_token: str = Header("")):
        st["calls"].append({"api": "brave", "q": q, "offset": offset, "count": count, "country": country})
        if x_subscription_token != BRAVE_KEY:
            return JSONResponse({"type": "ErrorResponse", "error": {"code": "SUBSCRIPTION_TOKEN_INVALID", "status": 401}}, 401)
        if count > 20 or offset > 9 or not q:
            return JSONResponse({"type": "ErrorResponse", "error": {"code": "VALIDATION", "status": 422}}, 422)
        f = fault("brave")
        if f == "429":
            return JSONResponse({"type": "ErrorResponse", "error": {"code": "RATE_LIMITED", "status": 429}}, 429, headers={"Retry-After": "0"})
        if f == "500":
            return Response(status_code=500)
        words = {w for w in q.lower().split() if len(w) > 2}
        hits = [(t, p, d) for t, p, d in WEB if words & set((t + " " + d).lower().replace("-", " ").split())]
        page = hits[offset * count:(offset + 1) * count] if count < len(hits) or offset else hits
        more = (offset + 1) * count < len(hits)
        return {"type": "search", "query": {"original": q, "more_results_available": more},
                "web": {"type": "search", "results": [{"title": t, "url": f"http://127.0.0.1:8765{p}?utm_token=abc123", "description": f"<strong>{d}</strong>"}
                                                       for t, p, d in page]}}

    @app.get("/pdl/v5/company/enrich")
    async def pdl(name: str = "", website: str = "", min_likelihood: int = 2, x_api_key: str = Header("")):
        st["calls"].append({"api": "pdl", "name": name, "website": website, "min_likelihood": min_likelihood})
        if x_api_key != PDL_KEY:
            return JSONResponse({"status": 401, "error": {"type": "invalid_api_key", "message": "Invalid API key"}}, 401)
        f = fault("pdl")
        if f == "402":
            return JSONResponse({"status": 402, "error": {"type": "payment_required"}}, 402)
        if f == "429":
            return JSONResponse({"status": 429, "error": {"type": "too_many_requests"}}, 429, headers={"Retry-After": "0"})
        rec = PDL.get(name.lower())
        if not (name or website):
            return JSONResponse({"status": 400, "error": {"type": "invalid_request_error"}}, 400)
        if rec is None or rec["likelihood"] < min_likelihood:
            return JSONResponse({"status": 404, "error": {"type": "not_found", "message": "No records were found matching your request"}}, 404)
        return {"status": 200, **rec}

    @app.get("/site/duka-moja", response_class=HTMLResponse)
    async def p1():
        return ld("Duka Moja Supermarket", "+254 712 345 678", "Nakuru", "info@dukamoja.example.com")

    @app.get("/site/duka-moja-dir", response_class=HTMLResponse)
    async def p2():
        return ld("Duka Moja Supermarket", "0712345678", "Nakuru")

    @app.get("/site/duka-moja-conflict", response_class=HTMLResponse)
    async def p3():
        return ld("Duka Moja Supermarket", "0799000111", "Naivasha")

    @app.get("/site/kibanda", response_class=HTMLResponse)
    async def p4():
        return ld("Kibanda Fresh Stores", "0722000222", "Nakuru")

    @app.get("/site/big", response_class=HTMLResponse)
    async def big():
        return "<html><body>" + "x" * 5000 + "</body></html>"

    @app.get("/site/pdf")
    async def pdf():
        return Response(b"%PDF-1.4", media_type="application/pdf")

    @app.get("/site/redir-private")
    async def redir_private():
        return RedirectResponse("http://169.254.169.254/latest/meta-data/", 302)

    @app.get("/site/redir-ok")
    async def redir_ok():
        return RedirectResponse("/site/duka-moja", 302)

    @app.get("/site/loop")
    async def loop():
        return RedirectResponse("/site/loop", 302)

    return app
