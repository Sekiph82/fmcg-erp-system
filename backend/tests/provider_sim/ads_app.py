"""Local ad-platform simulator (M44.S01.T002–T005): synthetic Meta / Google Ads / LinkedIn / TikTok endpoints shaped
like the documented APIs (paging, auth headers, version header, error envelopes, money units). Never a real platform.

Control: POST /_control {"faults": {"meta": ["auth"|"rate"|"perm"|"unknown"|"lost"|"partial"], ...}} queues one-shot
faults per provider; "unknown" = the write is applied but answered with a 5xx (outcome unknown), "lost" = 5xx and
nothing applied, "partial" = Google partial failure. {"tiktok_page_cap": n} forces small /get/ pages.
GET /_control/objects shows the M48 campaign objects created (campaign trees for all four providers).
Synthetic data: two campaigns per account, two days, fixed numbers so tests can assert the mapping.
"""
from __future__ import annotations

import itertools
import json
import re
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

TOKENS = {"meta": "sim-meta-token", "google": "sim-google-ads-token", "linkedin": "sim-li-token", "tiktok": "sim-tt-token"}
DEV_TOKEN, LI_VERSION = "sim-dev-token", "202611"


def ads_sim_settings(base: str) -> dict:
    base = base.rstrip("/")
    return {"META_ADS_API_URL": f"{base}/meta", "META_ADS_ACCESS_TOKEN": TOKENS["meta"],
            "GOOGLE_ADS_API_URL": f"{base}/google", "GOOGLE_ADS_ACCESS_TOKEN": TOKENS["google"],
            "GOOGLE_ADS_DEVELOPER_TOKEN": DEV_TOKEN, "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "111-222-3333",
            "LINKEDIN_ADS_API_URL": f"{base}/linkedin", "LINKEDIN_ADS_ACCESS_TOKEN": TOKENS["linkedin"],
            "LINKEDIN_ADS_VERSION": LI_VERSION, "TIKTOK_ADS_API_URL": f"{base}/tiktok", "TIKTOK_ADS_ACCESS_TOKEN": TOKENS["tiktok"]}


def create_ads_app() -> FastAPI:
    app = FastAPI(title="POVU ads simulator (synthetic, local only)")
    st: dict = {"faults": {}, "calls": [], "objs": {}, "tt_page_cap": 1000}
    seq = itertools.count(1001)

    def fault(p: str) -> Optional[str]:
        q = st["faults"].get(p) or []
        return q.pop(0) if q else None

    def gate_fault(p: str, keep: str = "") -> Optional[str]:
        """Pop the next fault unless it is one a write handler consumes itself (unknown / lost / partial)."""
        q = st["faults"].get(p) or []
        if q and q[0] in keep.split():
            return None
        return fault(p)

    def new_id(prefix: str) -> str:
        return f"{prefix}{next(seq)}"

    @app.post("/_control")
    async def control(request: Request):
        body = await request.json()
        for k, v in (body.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        if "tiktok_page_cap" in body:
            st["tt_page_cap"] = int(body["tiktok_page_cap"])
        return {"ok": True}

    @app.get("/_control/objects")
    async def objects():
        return st["objs"]

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    # ── Meta ───────────────────────────────────────────────────────────
    def meta_err(code: int, status: int, msg: str):
        return JSONResponse({"error": {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "sim"}}, status)

    def meta_gate(authorization: Optional[str], keep: str = ""):
        f = gate_fault("meta", keep)
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
        rows = ([{"campaign_id": "m2", "campaign_name": "POVU Hand Wash Powder Launch", "impressions": "800", "clicks": "16",
                  "spend": "320.50", "date_start": "2026-11-21", "date_stop": "2026-11-21"}] if page2 else
                [{"campaign_id": "m1", "campaign_name": "POVU AllClean Awareness", "impressions": "1000", "clicks": "25",
                  "spend": "512.75", "actions": [{"action_type": "purchase", "value": "3"},
                                                 {"action_type": "link_click", "value": "25"}],
                  "date_start": "2026-11-21", "date_stop": "2026-11-21"}])
        paging = {} if page2 else {"cursors": {"after": "c2"},
                                   "next": str(request.url.include_query_params(after="c2").remove_query_params("time_range"))}
        return {"data": rows, "paging": paging}

    # Meta campaign tree (M48): act_<id>/{campaigns,adsets,adcreatives,ads} create (+ validate_only), /<id> update and
    # read, list with name filtering. Objects live in st["objs"]; ads report effective_status IN_PROCESS on first read.
    META_EDGES = {"campaigns": "campaign", "adsets": "adset", "adcreatives": "creative", "ads": "ad"}
    ODAX = {"OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT", "OUTCOME_LEADS", "OUTCOME_SALES",
            "OUTCOME_APP_PROMOTION"}

    def meta_validate(kind: str, f: dict, acct: str) -> Optional[str]:
        objs = st["objs"]
        try:
            if kind == "campaign":
                if f.get("objective") not in ODAX:
                    return "Invalid parameter: objective"
                if not isinstance(json.loads(f.get("special_ad_categories", "x")), list):
                    return "special_ad_categories must be a list"
                if f.get("daily_budget") is not None and int(f["daily_budget"]) < 100:
                    return "Invalid parameter: daily_budget too low"
            elif kind == "adset":
                if (objs.get(f.get("campaign_id")) or {}).get("kind") != "campaign":
                    return "Invalid parameter: campaign_id"
                if not json.loads(f.get("targeting", "{}")).get("geo_locations") or not f.get("optimization_goal"):
                    return "Invalid parameter: targeting"
            elif kind == "creative":
                spec = json.loads(f.get("object_story_spec", "{}"))
                if not spec.get("page_id") or not str(spec.get("link_data", {}).get("link", "")).startswith("https://"):
                    return "Invalid parameter: object_story_spec"
            elif kind == "ad":
                if (objs.get(f.get("adset_id")) or {}).get("kind") != "adset":
                    return "Invalid parameter: adset_id"
                if (objs.get(json.loads(f.get("creative", "{}")).get("creative_id")) or {}).get("kind") != "creative":
                    return "Invalid parameter: creative"
        except (ValueError, TypeError):
            return "Invalid JSON parameter"
        if kind != "creative" and f.get("status") not in ("PAUSED", "ACTIVE"):
            return "Invalid parameter: status"
        if not f.get("name"):
            return "Invalid parameter: name"
        return None

    @app.post("/meta/{ver}/act_{acct}/{edge}")
    async def meta_create(ver: str, acct: str, edge: str, request: Request, authorization: Optional[str] = Header(None)):
        if edge not in META_EDGES:
            return meta_err(100, 404, "Unknown edge")
        err = meta_gate(authorization, keep="unknown lost")
        if err:
            return err
        form = dict(await request.form())
        kind = META_EDGES[edge]
        st["calls"].append({"provider": "meta", "edge": edge, "form": form})
        bad = meta_validate(kind, form, acct)
        if bad:
            return meta_err(100, 400, bad)
        if "validate_only" in str(form.get("execution_options", "")):
            return {"success": True}
        f = fault("meta")
        if f == "lost":
            return meta_err(2, 503, "Service temporarily unavailable")
        oid = new_id("238")
        st["objs"][oid] = {"kind": kind, "provider": "meta", "acct": acct, "reads": 0, **form}
        if f == "unknown":                     # created, but the answer is lost
            return meta_err(2, 500, "An unexpected error has occurred. Please retry your request later.")
        return {"id": oid}

    @app.get("/meta/{ver}/act_{acct}/{edge}")
    async def meta_list(ver: str, acct: str, edge: str, request: Request, authorization: Optional[str] = Header(None)):
        err = meta_gate(authorization)
        if err:
            return err
        flt = json.loads(request.query_params.get("filtering") or "[]")
        want = next((x["value"] for x in flt if x.get("field") == "name" and x.get("operator") == "CONTAIN"), "")
        rows = [{"id": k, "name": o["name"], "status": o.get("status")} for k, o in st["objs"].items()
                if o.get("provider") == "meta" and o["acct"] == acct and o["kind"] == META_EDGES.get(edge)
                and want in o.get("name", "")]
        return {"data": rows, "paging": {}}

    @app.post("/meta/{ver}/{oid}")
    async def meta_update(ver: str, oid: str, request: Request, authorization: Optional[str] = Header(None)):
        err = meta_gate(authorization, keep="unknown lost")
        if err:
            return err
        o = st["objs"].get(oid)
        if not o or o.get("provider") != "meta":
            return meta_err(100, 400, "Unsupported post request. Object does not exist")
        form = dict(await request.form())
        st["calls"].append({"provider": "meta", "update": oid, "form": form})
        if "status" in form and form["status"] not in ("PAUSED", "ACTIVE", "ARCHIVED"):
            return meta_err(100, 400, "Invalid parameter: status")
        f = fault("meta")
        if f == "lost":
            return meta_err(2, 503, "Service temporarily unavailable")
        o.update({k: v for k, v in form.items() if k in ("status", "daily_budget", "name")})
        if f == "unknown":
            return meta_err(2, 500, "An unexpected error has occurred. Please retry your request later.")
        return {"success": True}

    @app.get("/meta/{ver}/{oid}")
    async def meta_read(ver: str, oid: str, fields: str = "", authorization: Optional[str] = Header(None)):
        err = meta_gate(authorization)
        if err:
            return err
        o = st["objs"].get(oid)
        if not o or o.get("provider") != "meta":
            return meta_err(100, 400, "Object does not exist")
        o["reads"] += 1
        eff = "IN_PROCESS" if o["kind"] == "ad" and o["reads"] == 1 else o.get("status", "ACTIVE")
        out = {"id": oid, "name": o["name"], "status": o.get("status", "ACTIVE"), "effective_status": eff}
        if o.get("daily_budget"):
            out["daily_budget"] = str(o["daily_budget"])
        return {k: v for k, v in out.items() if k in fields.split(",") or k == "id"}

    # ── Google Ads ─────────────────────────────────────────────────────
    def g_err(status: int, code: str, msg: str):
        return JSONResponse([{"error": {"code": status, "message": msg, "status": code}}], status)

    def g_gate(authorization, dev, keep: str = ""):
        f = gate_fault("google", keep)
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

    # Google Ads (M48): <service>:mutate for campaignBudgets / campaigns / adGroups / adGroupAds (create + update with
    # updateMask), googleAds:mutate with temporary ids, validateOnly (never stores), partialFailure, googleAds:search.
    G_COLL = {"campaignBudgets": "campaign_budget", "campaigns": "campaign", "adGroups": "ad_group", "adGroupAds": "ad_group_ad"}
    G_OPS = {"campaignBudgetOperation": "campaignBudgets", "campaignOperation": "campaigns",
             "adGroupOperation": "adGroups", "adGroupAdOperation": "adGroupAds"}

    def g_check(kind: str, r: dict, cid: str, pending: dict) -> Optional[str]:
        def exists(rn, k):
            o = pending.get(rn) or st["objs"].get(rn)
            return bool(o) and o["kind"] == k and rn.startswith(f"customers/{cid}/")
        if kind == "campaign_budget":
            return None if int(r.get("amountMicros") or 0) >= 1_000_000 else "Budget amount too small"
        if r.get("status") not in ("PAUSED", "ENABLED"):
            return "status must be PAUSED or ENABLED"
        if kind == "campaign":
            if not exists(r.get("campaignBudget", ""), "campaign_budget"):
                return "Resource was not found: campaignBudget"
            if r.get("advertisingChannelType") != "SEARCH" or "manualCpc" not in r:
                return "Unsupported campaign settings"
            if any(o["kind"] == "campaign" and o.get("name") == r.get("name") for o in [*st["objs"].values(), *pending.values()]):
                return "DUPLICATE_CAMPAIGN_NAME"
        if kind == "ad_group" and not exists(r.get("campaign", ""), "campaign"):
            return "Resource was not found: campaign"
        if kind == "ad_group_ad":
            if not exists(r.get("adGroup", ""), "ad_group"):
                return "Resource was not found: adGroup"
            rsa = (r.get("ad") or {}).get("responsiveSearchAd") or {}
            hs, ds = rsa.get("headlines") or [], rsa.get("descriptions") or []
            if not 3 <= len(hs) <= 15 or not 2 <= len(ds) <= 4 or any(len(h["text"]) > 30 for h in hs) \
                    or any(len(d["text"]) > 90 for d in ds) or not (r["ad"].get("finalUrls") or [""])[0].startswith("https://"):
                return "Responsive search ad is not valid"
        return None

    def g_rn(cid: str, coll: str, r: dict) -> str:
        if coll == "adGroupAds":
            return f"customers/{cid}/adGroupAds/{r['adGroup'].rsplit('/', 1)[-1]}~{next(seq)}"
        return f"customers/{cid}/{coll}/{next(seq)}"

    @app.post("/google/{ver}/customers/{cid}/{svc}:mutate")
    async def g_mutate(ver: str, cid: str, svc: str, request: Request, authorization: Optional[str] = Header(None),
                       developer_token: Optional[str] = Header(None)):
        err = g_gate(authorization, developer_token, keep="unknown lost partial")
        if err:
            return err
        body = await request.json()
        st["calls"].append({"provider": "google", "service": svc, "body": body})
        validate, partial = bool(body.get("validateOnly")), bool(body.get("partialFailure"))
        if svc == "googleAds":       # GoogleAdsService.Mutate: mutateOperations, temporary ids resolved in order
            if not validate:
                return g_err(400, "INVALID_ARGUMENT", "This simulator models googleAds:mutate with validateOnly only.")
            ops = [(G_OPS[k], v) for op in body.get("mutateOperations") or [] for k, v in op.items()]
        elif svc in G_COLL:
            ops = [(svc, op) for op in body.get("operations") or []]
        else:
            return g_err(404, "NOT_FOUND", "Unknown service")
        f = fault("google")
        if f == "lost":
            return g_err(503, "UNAVAILABLE", "The service is currently unavailable.")
        pending, results, errors = {}, [], []
        for i, (coll, op) in enumerate(ops):
            kind = G_COLL[coll]
            if "create" in op:
                r = dict(op["create"])
                bad = "Simulated partial failure" if f == "partial" else g_check(kind, r, cid, pending)
                if not bad:
                    rn = r.pop("resourceName", None) if svc == "googleAds" else None
                    real = g_rn(cid, coll, r)
                    pending[rn or real] = {"kind": kind, "provider": "google", **r}
                    results.append({"resourceName": real})
            elif "update" in op:
                r = op["update"]
                o = st["objs"].get(r.get("resourceName", ""))
                mask = [m.strip() for m in str(op.get("updateMask", "")).split(",") if m.strip()]
                bad = ("Resource was not found" if not o or o["kind"] != kind else "updateMask is required" if not mask
                       else "status must be PAUSED or ENABLED" if "status" in mask and r.get("status") not in ("PAUSED", "ENABLED")
                       else None)
                if not bad:
                    if not validate:
                        o.update({m: r[m] for m in mask if m in r})
                    results.append({"resourceName": r["resourceName"]})
            else:
                bad = "Operation not supported"
            if bad:
                errors.append({"message": bad, "location": {"fieldPathElements": [{"fieldName": "operations", "index": i}]}})
                if not partial or svc == "googleAds":
                    return g_err(400, "INVALID_ARGUMENT", bad)
                results.append({})
        if not validate:
            st["objs"].update({k: v for k, v in pending.items() if not k.split("/")[-1].startswith("-")})
        if f == "unknown":
            return g_err(500, "INTERNAL", "Internal error encountered.")
        if validate:
            return {"partialFailureError": {"code": 3, "message": errors[0]["message"], "details": [{"errors": errors}]}} if errors else {}
        out = {"results": results}
        if errors:
            out["partialFailureError"] = {"code": 3, "message": errors[0]["message"], "details": [{"errors": errors}]}
        return out

    @app.post("/google/{ver}/customers/{cid}/googleAds:search")
    async def g_gaql(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                     developer_token: Optional[str] = Header(None)):
        err = g_gate(authorization, developer_token)
        if err:
            return err
        q = (await request.json())["query"]
        res = re.search(r"FROM (\w+)", q).group(1)
        key = {"campaign_budget": "campaignBudget", "campaign": "campaign", "ad_group": "adGroup", "ad_group_ad": "adGroupAd"}[res]
        rows = [(rn, o) for rn, o in st["objs"].items() if o.get("provider") == "google" and o["kind"] == res
                and rn.startswith(f"customers/{cid}/")]
        if m := re.search(r"\.resource_name = '([^']+)'", q):
            rows = [(rn, o) for rn, o in rows if rn == m.group(1)]
        elif m := re.search(r"\.name LIKE '%(.+)%'", q):
            rows = [(rn, o) for rn, o in rows if m.group(1) in (o.get("name") or "")]
        elif m := re.search(r"ad_group_ad\.ad_group = '([^']+)'", q):
            rows = [(rn, o) for rn, o in rows if o.get("adGroup") == m.group(1)]
        out = []
        for rn, o in rows:
            v = {"resourceName": rn, "status": o.get("status", "ENABLED")}
            if "name" in o:
                v["name"] = o["name"]
            if res == "campaign_budget":
                v["amountMicros"] = str(o["amountMicros"])
            out.append({key: v})
        return {"results": out, "fieldMask": "status"}

    # ── LinkedIn ───────────────────────────────────────────────────────
    def li_gate(authorization, version, keep: str = ""):
        f = gate_fault("linkedin", keep)
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

    # LinkedIn campaign tree (M48): adCampaignGroups / adCampaigns / creatives under adAccounts/<id>. Create → 201 +
    # x-restli-id; PARTIAL_UPDATE → 204; get; search by name / campaignGroup; creatives q=criteria&campaigns=List(...).
    LI_KIND = {"adCampaignGroups": "group", "adCampaigns": "campaign", "creatives": "creative"}

    def li_objs(acct: str, kind: str) -> list[tuple[str, dict]]:
        return [(k, o) for k, o in st["objs"].items() if o.get("provider") == "linkedin" and o["acct"] == acct and o["kind"] == kind]

    def li_err(status: int, msg: str):
        return JSONResponse({"status": status, "message": msg}, status)

    def li_search_values(url: str, field: str) -> list[str]:
        m = re.search(field + r":\(values:List\(([^)]*)\)\)", url)
        return [unquote(v) for v in m.group(1).split(",")] if m else []

    @app.get("/linkedin/rest/adAccounts/{acct}/adCampaigns")
    async def li_campaigns(acct: str, request: Request, authorization: Optional[str] = Header(None),
                           linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        groups = li_search_values(str(request.url), "campaignGroup")
        if groups:
            return {"elements": [{"id": int(k), **o["body"]} for k, o in li_objs(acct, "campaign")
                                 if o["body"].get("campaignGroup") in groups], "metadata": {}}
        return {"elements": [{"id": 701, "name": "POVU B2B Distributors"}]}

    @app.get("/linkedin/rest/adAccounts/{acct}/adCampaignGroups")
    async def li_groups(acct: str, request: Request, authorization: Optional[str] = Header(None),
                        linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        names = li_search_values(str(request.url), "name")
        return {"elements": [{"id": int(k), **o["body"]} for k, o in li_objs(acct, "group")
                             if not names or o["body"].get("name") in names], "metadata": {}}

    @app.get("/linkedin/rest/adAccounts/{acct}/creatives")
    async def li_creatives(acct: str, request: Request, authorization: Optional[str] = Header(None),
                           linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        if request.query_params.get("q") != "criteria":
            return li_err(400, "Missing q=criteria")
        m = re.search(r"campaigns=List\(([^)]*)\)", str(request.url))
        camps = [unquote(v) for v in m.group(1).split(",")] if m else []
        return {"elements": [{"id": k, **o["body"]} for k, o in li_objs(acct, "creative")
                             if not camps or o["body"].get("campaign") in camps], "metadata": {}}

    @app.post("/linkedin/rest/adAccounts/{acct}/{coll}")
    async def li_create(acct: str, coll: str, request: Request, authorization: Optional[str] = Header(None),
                        linkedin_version: Optional[str] = Header(None), x_restli_protocol_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version, keep="unknown lost")
        if err:
            return err
        if coll not in LI_KIND or x_restli_protocol_version != "2.0.0":
            return li_err(400, "Invalid Rest.li request")
        body, kind = await request.json(), LI_KIND[coll]
        st["calls"].append({"provider": "linkedin", "collection": coll, "json": body})
        urn_acct = f"urn:li:sponsoredAccount:{acct}"
        ids = {k for k, _ in li_objs(acct, {"group": "group", "campaign": "group", "creative": "campaign"}[kind])}
        if kind == "group":
            bad = (body.get("account") != urn_acct or not body.get("name") or body.get("status") not in ("ACTIVE", "DRAFT")
                   or not (body.get("runSchedule") or {}).get("start"))
        elif kind == "campaign":
            bad = (body.get("account") != urn_acct or body.get("campaignGroup", "").rsplit(":", 1)[-1] not in ids
                   or body.get("politicalIntent") not in ("POLITICAL", "NOT_POLITICAL", "NOT_DECLARED")
                   or body.get("status") not in ("ACTIVE", "DRAFT", "PAUSED") or body.get("costType") not in ("CPM", "CPC", "CPV")
                   or not (body.get("dailyBudget") or {}).get("amount") or not body.get("targetingCriteria"))
        else:
            bad = (body.get("campaign", "").rsplit(":", 1)[-1] not in ids
                   or not str((body.get("content") or {}).get("reference", "")).startswith("urn:li:")
                   or body.get("intendedStatus") not in ("ACTIVE", "DRAFT", "PAUSED"))
        if bad:
            return li_err(422, f"Invalid {coll} entity")
        f = fault("linkedin")
        if f == "lost":
            return li_err(503, "Service unavailable")
        oid = str(next(seq))
        key = f"urn:li:sponsoredCreative:{oid}" if kind == "creative" else oid
        st["objs"][key] = {"kind": kind, "provider": "linkedin", "acct": acct, "body": body}
        if f == "unknown":
            return li_err(500, "Internal server error")
        return Response(status_code=201, headers={"x-restli-id": key})

    @app.post("/linkedin/rest/adAccounts/{acct}/{coll}/{oid}")
    async def li_update(acct: str, coll: str, oid: str, request: Request, authorization: Optional[str] = Header(None),
                        linkedin_version: Optional[str] = Header(None), x_restli_method: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version, keep="unknown lost")
        if err:
            return err
        o = st["objs"].get(oid)
        if not o or o.get("provider") != "linkedin" or o["acct"] != acct or LI_KIND.get(coll) != o["kind"]:
            return li_err(404, "Entity not found")
        if x_restli_method != "PARTIAL_UPDATE":
            return li_err(400, "X-RestLi-Method PARTIAL_UPDATE required")
        patch = ((await request.json()).get("patch") or {}).get("$set") or {}
        st["calls"].append({"provider": "linkedin", "update": oid, "set": patch})
        field = "intendedStatus" if o["kind"] == "creative" else "status"
        if field in patch and patch[field] not in ("ACTIVE", "PAUSED", "ARCHIVED", "DRAFT", "PENDING_DELETION"):
            return li_err(422, "Invalid status")
        f = fault("linkedin")
        if f == "lost":
            return li_err(503, "Service unavailable")
        o["body"].update(patch)
        if f == "unknown":
            return li_err(500, "Internal server error")
        return Response(status_code=204)

    @app.get("/linkedin/rest/adAccounts/{acct}/{coll}/{oid}")
    async def li_get(acct: str, coll: str, oid: str, authorization: Optional[str] = Header(None),
                     linkedin_version: Optional[str] = Header(None)):
        err = li_gate(authorization, linkedin_version)
        if err:
            return err
        o = st["objs"].get(oid)
        if not o or o.get("provider") != "linkedin" or o["acct"] != acct:
            return li_err(404, "Entity not found")
        out = {"id": oid if o["kind"] == "creative" else int(oid), **o["body"]}
        if o["kind"] == "creative":
            out["isServing"] = o["body"].get("intendedStatus") == "ACTIVE"
        else:
            out["servingStatuses"] = ["RUNNABLE"] if o["body"].get("status") == "ACTIVE" else ["STOPPED"]
        return out

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
                     "metrics": {"campaign_name": "POVU AllClean Challenge", "spend": "60.00", "impressions": "5000",
                                 "clicks": "90", "conversion": "6"}}],
                2: [{"dimensions": {"campaign_id": "t1", "stat_time_day": "2026-11-22 00:00:00"},
                     "metrics": {"campaign_name": "POVU AllClean Challenge", "spend": "55.50", "impressions": "4200",
                                 "clicks": "70", "conversion": "4"}}]}
        return {"code": 0, "message": "OK", "request_id": "sim",
                "data": {"list": rows.get(page, []), "page_info": {"page": page, "page_size": 1, "total_number": 2, "total_page": 2}}}

    # TikTok campaign tree (M48): campaign | adgroup | ad  /create/ /update/ /status/update/ /get/ (filtering,
    # page/page_size, page_info). HTTP 200 + code; 40002 = parameter error, 50000 = server error (write unknown).
    TT_OBJ = {"REACH", "TRAFFIC", "VIDEO_VIEWS", "LEAD_GENERATION", "ENGAGEMENT", "APP_PROMOTION", "WEB_CONVERSIONS",
              "PRODUCT_SALES"}

    def tt(code: int, msg: str, data: Optional[dict] = None) -> dict:
        return {"code": code, "message": msg, "request_id": f"sim-{next(seq)}", "data": data or {}}

    def tt_gate(token: Optional[str], keep: str = "") -> Optional[dict]:
        f = gate_fault("tiktok", keep)
        if token != TOKENS["tiktok"] or f == "auth":
            return tt(40105, "Access token has expired")
        if f == "rate":
            return tt(40100, "Requests made too frequently")
        return None

    def tt_objs(adv: str, kind: str) -> dict:
        return {k: o for k, o in st["objs"].items() if o.get("provider") == "tiktok" and o["adv"] == adv and o["kind"] == kind}

    @app.post("/tiktok/open_api/v1.3/{kind}/create/")
    async def tt_create(kind: str, request: Request, access_token: Optional[str] = Header(None)):
        err = tt_gate(access_token, keep="unknown lost")
        if err:
            return err
        b = await request.json()
        st["calls"].append({"provider": "tiktok", "create": kind, "json": b})
        adv = str(b.get("advertiser_id") or "")
        if kind == "campaign":
            bad = (not b.get("campaign_name") or b.get("objective_type") not in TT_OBJ
                   or b.get("budget_mode") not in ("BUDGET_MODE_DAY", "BUDGET_MODE_TOTAL", "BUDGET_MODE_INFINITE")
                   or (b.get("budget_mode") == "BUDGET_MODE_DAY" and float(b.get("budget") or 0) < 50))
        elif kind == "adgroup":
            bad = (b.get("campaign_id") not in tt_objs(adv, "campaign") or not b.get("location_ids")
                   or not b.get("optimization_goal") or not b.get("billing_event") or not b.get("adgroup_name"))
        elif kind == "ad":
            c = (b.get("creatives") or [{}])[0]
            bad = (b.get("adgroup_id") not in tt_objs(adv, "adgroup") or not c.get("video_id") or not c.get("identity_id")
                   or not c.get("ad_text") or not str(c.get("landing_page_url", "")).startswith("https://"))
        else:
            return tt(40002, "Unknown object")
        if not adv or bad:
            return tt(40002, f"Invalid parameters for {kind}/create")
        if b.get("operation_status", "ENABLE") not in ("ENABLE", "DISABLE"):
            return tt(40002, "Invalid operation_status")
        f = fault("tiktok")
        if f == "lost":
            return tt(50002, "Service is busy, please retry")      # TikTok-style server error, nothing created
        oid = str(7_000_000_000 + next(seq))
        name = b.get(f"{kind}_name") or (b.get("creatives") or [{}])[0].get("ad_name")
        st["objs"][oid] = {"kind": kind, "provider": "tiktok", "adv": adv, "name": name,
                           "operation_status": b.get("operation_status", "ENABLE"), "budget": b.get("budget"),
                           "campaign_id": b.get("campaign_id"), "adgroup_id": b.get("adgroup_id")}
        if f == "unknown":
            return tt(50000, "System error")
        return tt(0, "OK", {"ad_ids": [oid]} if kind == "ad" else {f"{kind}_id": oid})

    @app.post("/tiktok/open_api/v1.3/{kind}/status/update/")
    async def tt_status(kind: str, request: Request, access_token: Optional[str] = Header(None)):
        err = tt_gate(access_token, keep="unknown lost")
        if err:
            return err
        b = await request.json()
        st["calls"].append({"provider": "tiktok", "status": kind, "json": b})
        objs = tt_objs(str(b.get("advertiser_id") or ""), kind)
        ids = b.get(f"{kind}_ids") or []
        if not ids or any(i not in objs for i in ids) or b.get("operation_status") not in ("ENABLE", "DISABLE", "DELETE"):
            return tt(40002, "Invalid parameters for status/update")
        f = fault("tiktok")
        if f == "lost":
            return tt(50002, "Service is busy, please retry")
        for i in ids:
            objs[i]["operation_status"] = b["operation_status"]
        if f == "unknown":
            return tt(50000, "System error")
        return tt(0, "OK", {f"{kind}_ids": ids})

    @app.post("/tiktok/open_api/v1.3/{kind}/update/")
    async def tt_update(kind: str, request: Request, access_token: Optional[str] = Header(None)):
        err = tt_gate(access_token, keep="unknown lost")
        if err:
            return err
        b = await request.json()
        st["calls"].append({"provider": "tiktok", "update": kind, "json": b})
        o = tt_objs(str(b.get("advertiser_id") or ""), kind).get(str(b.get(f"{kind}_id")))
        if not o or ("budget" in b and float(b["budget"]) < 50):
            return tt(40002, "Invalid parameters for update")
        f = fault("tiktok")
        if f == "lost":
            return tt(50002, "Service is busy, please retry")
        o.update({k: b[k] for k in ("budget",) if k in b})
        if f == "unknown":
            return tt(50000, "System error")
        return tt(0, "OK", {f"{kind}_id": b.get(f"{kind}_id")})

    @app.get("/tiktok/open_api/v1.3/{kind}/get/")
    async def tt_get(kind: str, advertiser_id: str = "", filtering: str = "{}", page: int = 1, page_size: int = 10,
                     access_token: Optional[str] = Header(None)):
        err = tt_gate(access_token)
        if err:
            return err
        flt = json.loads(filtering or "{}")
        rows = []
        for k, o in tt_objs(advertiser_id, kind).items():
            if f"{kind}_ids" in flt and k not in flt[f"{kind}_ids"]:
                continue
            if "campaign_ids" in flt and kind != "campaign" and o.get("campaign_id") not in flt["campaign_ids"]:
                continue
            if "adgroup_ids" in flt and kind == "ad" and o.get("adgroup_id") not in flt["adgroup_ids"]:
                continue
            row = {f"{kind}_id": k, "operation_status": o["operation_status"], ("ad_name" if kind == "ad" else f"{kind}_name"): o["name"]}
            if o.get("budget") is not None:
                row["budget"] = o["budget"]
            rows.append(row)
        size = max(1, min(page_size, 1000, st["tt_page_cap"]))
        total_page = max(1, -(-len(rows) // size))
        return tt(0, "OK", {"list": rows[(page - 1) * size: page * size],
                            "page_info": {"page": page, "page_size": size, "total_number": len(rows), "total_page": total_page}})

    # ── M44.S01.T006 organic posting (Facebook Page, Instagram, LinkedIn posts, TikTok Content Posting) ─────
    def page_gate(authorization):
        f = fault("social")
        if authorization != f"Bearer {SOCIAL_TOKENS['meta']}" or f == "auth":
            return meta_err(190, 401, "Error validating access token")
        if f == "perm":
            return meta_err(200, 403, "(#200) Requires pages_manage_posts permission")
        return None

    @app.post("/meta/{ver}/{node}/feed")
    async def page_feed(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        st["calls"].append({"provider": "facebook", "form": form})
        return {"id": f"{node}_{len(st['calls'])}"}

    @app.post("/meta/{ver}/{node}/photos")
    async def page_photo(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if not str(form.get("url", "")).startswith("https://"):
            return meta_err(100, 400, "Invalid image URL")
        st["calls"].append({"provider": "facebook-photo", "form": form})
        return {"id": "ph1", "post_id": f"{node}_ph1"}

    @app.post("/meta/{ver}/{node}/media")
    async def ig_media(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if len(form.get("caption", "")) > 2200:
            return meta_err(100, 400, "Caption too long")
        st["calls"].append({"provider": "instagram-container", "form": form})
        return {"id": "container-1"}

    @app.post("/meta/{ver}/{node}/media_publish")
    async def ig_publish(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err = page_gate(authorization)
        if err:
            return err
        form = dict(await request.form())
        if form.get("creation_id") != "container-1":
            return meta_err(100, 400, "Unknown creation_id")
        st["calls"].append({"provider": "instagram", "form": form})
        return {"id": "ig-media-1"}

    @app.post("/linkedin/rest/posts")
    async def li_post(request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None)):
        if authorization != f"Bearer {SOCIAL_TOKENS['linkedin']}":
            return JSONResponse({"status": 401, "message": "Invalid access token"}, 401)
        if linkedin_version != LI_VERSION:
            return JSONResponse({"status": 426, "message": "Requested version is not active"}, 426)
        body = await request.json()
        if not body.get("author", "").startswith("urn:li:organization:") or len(body.get("commentary", "")) > 3000:
            return JSONResponse({"status": 422, "message": "Invalid post"}, 422)
        st["calls"].append({"provider": "linkedin", "json": body})
        return Response(status_code=201, headers={"x-restli-id": "urn:li:share:9001"})

    @app.post("/tiktok-social/v2/post/publish/video/init/")
    async def tt_post(request: Request, authorization: Optional[str] = Header(None)):
        if authorization != f"Bearer {SOCIAL_TOKENS['tiktok']}":
            return JSONResponse({"data": {}, "error": {"code": "access_token_invalid", "message": "The access token is invalid"}}, 401)
        body = await request.json()
        if body["post_info"].get("privacy_level") != "SELF_ONLY":
            return JSONResponse({"data": {}, "error": {"code": "unaudited_client_can_only_post_to_private_accounts",
                                                      "message": "Unaudited clients can only post privately"}}, 403)
        st["calls"].append({"provider": "tiktok", "json": body})
        return {"data": {"publish_id": "v_pub_url~1"}, "error": {"code": "ok", "message": ""}}

    # ── M44.S01.T013 Send API (Messenger / Instagram via the page) and a Slack incoming-webhook stub ─────
    @app.post("/meta/{ver}/{node}/messages")
    async def send_message(ver: str, node: str, request: Request, authorization: Optional[str] = Header(None)):
        err = page_gate(authorization)
        if err:
            return err
        body = await request.json()
        if body.get("messaging_type") != "RESPONSE" or not (body.get("recipient") or {}).get("id"):
            return meta_err(100, 400, "Invalid parameter")
        if len((body.get("message") or {}).get("text", "")) > 2000:
            return meta_err(100, 400, "Message too long")
        st["calls"].append({"provider": "messenger", "node": node, "json": body})
        return {"recipient_id": body["recipient"]["id"], "message_id": f"m_sim_{len(st['calls'])}"}

    @app.post("/slack/hook")
    async def slack_hook(request: Request):
        if fault("slack") == "down":
            return Response("service_unavailable", status_code=503)
        body = await request.json()
        if not body.get("text"):
            return Response("no_text", status_code=400)
        st["calls"].append({"provider": "slack", "json": body})
        return Response("ok", media_type="text/plain")

    return app


SOCIAL_TOKENS = {"meta": "sim-page-token", "linkedin": "sim-li-social", "tiktok": "sim-tt-social"}


def social_sim_settings(base: str) -> dict:
    base = base.rstrip("/")
    return {"META_ADS_API_URL": f"{base}/meta", "META_PAGE_ACCESS_TOKEN": SOCIAL_TOKENS["meta"],
            "LINKEDIN_ADS_API_URL": f"{base}/linkedin", "LINKEDIN_ADS_VERSION": LI_VERSION,
            "LINKEDIN_SOCIAL_ACCESS_TOKEN": SOCIAL_TOKENS["linkedin"], "TIKTOK_SOCIAL_API_URL": f"{base}/tiktok-social",
            "TIKTOK_SOCIAL_ACCESS_TOKEN": SOCIAL_TOKENS["tiktok"], "SOCIAL_PUBLISHING_ENABLED": True}
