"""Local ad-platform simulator (M44.S01.T002–T005): synthetic Meta / Google Ads / LinkedIn / TikTok endpoints shaped
like the documented APIs (paging, auth headers, version header, error envelopes, money units). Never a real platform.

Control: POST /_control {"faults": {"meta": ["auth"|"rate"|"perm"], ...}} queues one-shot faults per provider.
Synthetic data: two campaigns per account, two days, fixed numbers so tests can assert the mapping.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

TOKENS = {"meta": "sim-meta-token", "google": "sim-google-ads-token", "linkedin": "sim-li-token", "tiktok": "sim-tt-token"}
DEV_TOKEN, LI_VERSION = "sim-dev-token", "202410"


def ads_sim_settings(base: str) -> dict:
    base = base.rstrip("/")
    return {"META_ADS_API_URL": f"{base}/meta", "META_ADS_ACCESS_TOKEN": TOKENS["meta"],
            "GOOGLE_ADS_API_URL": f"{base}/google", "GOOGLE_ADS_ACCESS_TOKEN": TOKENS["google"],
            "GOOGLE_ADS_DEVELOPER_TOKEN": DEV_TOKEN, "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "111-222-3333",
            "LINKEDIN_ADS_API_URL": f"{base}/linkedin", "LINKEDIN_ADS_ACCESS_TOKEN": TOKENS["linkedin"],
            "LINKEDIN_ADS_VERSION": LI_VERSION, "TIKTOK_ADS_API_URL": f"{base}/tiktok", "TIKTOK_ADS_ACCESS_TOKEN": TOKENS["tiktok"]}


def create_ads_app() -> FastAPI:
    app = FastAPI(title="POVU ads simulator (synthetic, local only)")
    st: dict = {"faults": {}, "calls": []}

    def fault(p: str) -> Optional[str]:
        q = st["faults"].get(p) or []
        return q.pop(0) if q else None

    @app.post("/_control")
    async def control(request: Request):
        body = await request.json()
        for k, v in (body.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        return {"ok": True}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    # ── Meta ───────────────────────────────────────────────────────────
    def meta_err(code: int, status: int, msg: str):
        return JSONResponse({"error": {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "sim"}}, status)

    def meta_gate(authorization: Optional[str]):
        f = fault("meta")
        if authorization != f"Bearer {TOKENS['meta']}" or f == "auth":
            return meta_err(190, 401, "Error validating access token: Session has expired.")
        if f == "rate":
            return meta_err(17, 400, "User request limit reached")
        if f == "perm":
            return meta_err(200, 403, "Permissions error")
        return None

    @app.get("/meta/{ver}/me/adaccounts")
    async def meta_accounts(ver: str, authorization: Optional[str] = Header(None)):
        return meta_gate(authorization) or {"data": [{"account_id": "1001", "name": "POVU Synthetic Meta", "currency": "KES",
                                                      "timezone_name": "Africa/Nairobi", "id": "act_1001"}], "paging": {}}

    @app.get("/meta/{ver}/act_{acct}/insights")
    async def meta_insights(ver: str, acct: str, request: Request, authorization: Optional[str] = Header(None)):
        err = meta_gate(authorization)
        if err:
            return err
        page2 = request.query_params.get("after") == "c2"
        rows = ([{"campaign_id": "m2", "campaign_name": "POVU Water Launch", "impressions": "800", "clicks": "16",
                  "spend": "320.50", "date_start": "2026-11-21", "date_stop": "2026-11-21"}] if page2 else
                [{"campaign_id": "m1", "campaign_name": "POVU Juice Awareness", "impressions": "1000", "clicks": "25",
                  "spend": "512.75", "actions": [{"action_type": "purchase", "value": "3"},
                                                 {"action_type": "link_click", "value": "25"}],
                  "date_start": "2026-11-21", "date_stop": "2026-11-21"}])
        paging = {} if page2 else {"cursors": {"after": "c2"},
                                   "next": str(request.url.include_query_params(after="c2").remove_query_params("time_range"))}
        return {"data": rows, "paging": paging}

    @app.post("/meta/{ver}/act_{acct}/campaigns")
    async def meta_create(ver: str, acct: str, request: Request, authorization: Optional[str] = Header(None)):
        err = meta_gate(authorization)
        if err:
            return err
        form = await request.form()
        st["calls"].append({"provider": "meta", "form": dict(form)})
        if "validate_only" not in str(form.get("execution_options", "")):
            return meta_err(100, 400, "Simulator refuses real creation")
        if int(form.get("daily_budget", 0)) < 100:
            return meta_err(100, 400, "Invalid parameter: daily_budget too low")
        return {"success": True}

    # ── Google Ads ─────────────────────────────────────────────────────
    def g_err(status: int, code: str, msg: str):
        return JSONResponse([{"error": {"code": status, "message": msg, "status": code}}], status)

    def g_gate(authorization, dev):
        f = fault("google")
        if authorization != f"Bearer {TOKENS['google']}" or f == "auth":
            return g_err(401, "UNAUTHENTICATED", "Request is missing required authentication credential.")
        if dev != DEV_TOKEN:
            return g_err(403, "PERMISSION_DENIED", "The developer token is not approved.")
        if f == "rate":
            return g_err(429, "RESOURCE_EXHAUSTED", "Too many requests.")
        return None

    @app.post("/google/{ver}/customers/{cid}/googleAds:searchStream")
    async def g_search(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                       developer_token: Optional[str] = Header(None)):
        err = g_gate(authorization, developer_token)
        if err:
            return err
        q = (await request.json())["query"]
        if "FROM customer_client" in q:
            return [{"results": [{"customerClient": {"id": "4445556666", "descriptiveName": "POVU Synthetic Google",
                                                     "currencyCode": "KES", "timeZone": "Africa/Nairobi", "manager": False}}]}]
        return [{"results": [{"campaign": {"id": "g1", "name": "POVU Search Brand"}, "segments": {"date": "2026-11-21"},
                              "metrics": {"impressions": "2000", "clicks": "80", "costMicros": "1234560000", "conversions": 4.0}}]},
                {"results": [{"campaign": {"id": "g1", "name": "POVU Search Brand"}, "segments": {"date": "2026-11-22"},
                              "metrics": {"impressions": "1500", "clicks": "50", "costMicros": "990000000", "conversions": 2.5}}]}]

    @app.post("/google/{ver}/customers/{cid}/campaignBudgets:mutate")
    async def g_mutate(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                       developer_token: Optional[str] = Header(None)):
        err = g_gate(authorization, developer_token)
        if err:
            return err
        body = await request.json()
        st["calls"].append({"provider": "google", "body": body})
        if not body.get("validateOnly"):
            return g_err(400, "INVALID_ARGUMENT", "Simulator refuses real mutation")
        micros = int(body["operations"][0]["create"]["amountMicros"])
        if micros < 1_000_000:
            return {"partialFailureError": {"code": 3, "message": "Budget amount too small"}}
        return {"results": []}

    # ── LinkedIn ───────────────────────────────────────────────────────
    def li_gate(authorization, version):
        f = fault("linkedin")
        if authorization != f"Bearer {TOKENS['linkedin']}" or f == "auth":
            return JSONResponse({"status": 401, "serviceErrorCode": 65601, "message": "The token used in the request has expired"}, 401)
        if version != LI_VERSION:
            return JSONResponse({"status": 426, "message": "Requested version is not active"}, 426)
        if f == "perm":
            return JSONResponse({"status": 403, "message": "Not enough permissions to access: adAnalytics"}, 403)
        if f == "rate":
            return JSONResponse({"status": 429, "message": "Resource level throttle limit reached"}, 429, headers={"Retry-After": "30"})
        return None

    @app.get("/linkedin/rest/adAccounts")
    async def li_accounts(start: int = 0, count: int = 100, authorization: Optional[str] = Header(None),
                          linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        allx = [{"id": 5001, "name": "POVU Synthetic LinkedIn A", "currency": "USD"},
                {"id": 5002, "name": "POVU Synthetic LinkedIn B", "currency": "USD"}]
        return {"elements": allx[start:start + 1], "paging": {"start": start, "count": 1, "total": len(allx)}}

    @app.get("/linkedin/rest/adAccounts/{acct}/adCampaigns")
    async def li_campaigns(acct: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        return li_gate(authorization, linkedin_version) or {"elements": [{"id": 701, "name": "POVU B2B Distributors"}]}

    @app.get("/linkedin/rest/adAnalytics")
    async def li_analytics(request: Request, authorization: Optional[str] = Header(None),
                           linkedin_version: Optional[str] = Header(None),
                           x_restli_protocol_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        if x_restli_protocol_version != "2.0.0" or "List(urn%3Ali%3AsponsoredAccount%3A" not in str(request.url):
            return JSONResponse({"status": 400, "message": "Invalid Rest.li query"}, 400)
        return {"elements": [{"pivotValues": ["urn:li:sponsoredCampaign:701"],
                              "dateRange": {"start": {"year": 2026, "month": 11, "day": 21}, "end": {"year": 2026, "month": 11, "day": 21}},
                              "impressions": 640, "clicks": 12, "costInLocalCurrency": "88.40", "externalWebsiteConversions": 1}],
                "paging": {"start": 0, "count": 10, "total": 1}}

    # ── TikTok ─────────────────────────────────────────────────────────
    @app.get("/tiktok/open_api/v1.3/report/integrated/get/")
    async def tt_report(page: int = 1, access_token: Optional[str] = Header(None)):
        f = fault("tiktok")
        if access_token != TOKENS["tiktok"] or f == "auth":
            return {"code": 40105, "message": "Access token has expired", "request_id": "sim", "data": {}}
        if f == "rate":
            return {"code": 40100, "message": "Requests made too frequently", "request_id": "sim", "data": {}}
        rows = {1: [{"dimensions": {"campaign_id": "t1", "stat_time_day": "2026-11-21 00:00:00"},
                     "metrics": {"campaign_name": "POVU Juice Challenge", "spend": "60.00", "impressions": "5000",
                                 "clicks": "90", "conversion": "6"}}],
                2: [{"dimensions": {"campaign_id": "t1", "stat_time_day": "2026-11-22 00:00:00"},
                     "metrics": {"campaign_name": "POVU Juice Challenge", "spend": "55.50", "impressions": "4200",
                                 "clicks": "70", "conversion": "4"}}]}
        return {"code": 0, "message": "OK", "request_id": "sim",
                "data": {"list": rows.get(page, []), "page_info": {"page": page, "page_size": 1, "total_number": 2, "total_page": 2}}}

    return app
