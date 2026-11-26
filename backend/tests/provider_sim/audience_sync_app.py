"""Local simulator for ad-platform audience lifecycles (M49.S01.T011), shaped like the documented APIs:
Meta custom + lookalike audiences (POST|DELETE <aud>/users, DELETE <aud>, GET <aud>?fields=...), Google Data Manager API
(audienceMembers:ingest / :remove, requestStatus:retrieve) with the Ads API userLists:mutate for the list itself,
LinkedIn DMP segments (BATCH_CREATE users, GET / DELETE segment), TikTok custom audiences (file upload -> create /
update APPEND|REMOVE|REPLACE, min size, get, delete). Every identifier must be a 64-char lower-case hex SHA-256: a raw
e-mail or phone is rejected. Synthetic and local only; tokens are those of ads_app.TOKENS.

Control: POST /_control {"faults": {"meta": ["unknown"|"lost"|"auth"]}, "ready_after": n, "tiktok_min": n,
"meta_lookalike_min": n}. "unknown" = the write is applied but answered 5xx; "lost" = 5xx, nothing applied.
GET /_control/audiences, GET /_control/calls (raw bodies, to prove no raw PII left the ERP).
"""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import re
from typing import Optional

from fastapi import FastAPI, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from tests.provider_sim.ads_app import LI_VERSION, TOKENS

HEX = re.compile(r"^[0-9a-f]{64}$")


def create_audience_sync_app() -> FastAPI:
    app = FastAPI(title="POVU audience sync simulator (synthetic, local only)")
    st = {"faults": {}, "calls": [], "aud": {}, "files": {}, "reqs": {}, "ready_after": 1, "tiktok_min": 1000, "meta_min": 100}
    seq = itertools.count(5001)
    app.state.st = st

    def fault(p: str) -> Optional[str]:
        q = st["faults"].get(p) or []
        return q.pop(0) if q else None

    def rec(kind: str, body) -> None:
        st["calls"].append({"kind": kind, "body": body})

    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        for k, v in (b.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        for k in ("ready_after", "tiktok_min"):
            if k in b:
                st[k] = int(b[k])
        if "meta_lookalike_min" in b:
            st["meta_min"] = int(b["meta_lookalike_min"])
        return {"ok": True}

    @app.get("/_control/audiences")
    async def audiences():
        return {k: {**{x: v[x] for x in ("provider", "acct", "kind", "name", "deleted")}, "members": sorted(v["members"])}
                for k, v in st["aud"].items()}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    def new_aud(provider: str, acct: str, name: str, kind: str = "CUSTOM", oid: Optional[str] = None) -> str:
        aid = oid or str(next(seq))
        st["aud"][aid] = {"provider": provider, "acct": acct, "kind": kind, "name": name, "members": set(), "reads": 0, "deleted": False}
        return aid

    def get_aud(aid: str, provider: str) -> Optional[dict]:
        a = st["aud"].get(aid)
        return a if a and a["provider"] == provider and not a["deleted"] else None

    def bad(values) -> bool:
        return any(v and not HEX.match(v) for v in values)

    # ── Meta ─────────────────────────────────────────────────────────
    def m_err(status: int, code: int, msg: str):
        return JSONResponse({"error": {"message": msg, "code": code}}, status)

    def m_gate(auth: Optional[str], keep: bool = False):
        f = None if keep else fault("meta")
        if auth != f"Bearer {TOKENS['meta']}" or f == "auth":
            return m_err(401, 190, "Invalid OAuth access token.")
        return None

    @app.post("/meta/{ver}/act_{acct}/customaudiences")
    async def m_create(ver: str, acct: str, request: Request, authorization: Optional[str] = Header(None)):
        b = await request.json()
        rec("meta_create", b)
        if err := m_gate(authorization, keep=True):
            return err
        f = fault("meta")
        if f == "lost":
            return m_err(503, 2, "Service temporarily unavailable")
        if b.get("subtype") == "LOOKALIKE":
            src = get_aud(str(b.get("origin_audience_id")), "meta")
            spec = b.get("lookalike_spec") or {}
            if src is None or "country" in spec or "location_spec" in spec or not 0.01 <= float(spec.get("ratio", 0)) <= 0.20:
                return m_err(400, 100, "Invalid lookalike_spec / origin_audience_id (v27.0: no country or location_spec)")
            if len(src["members"]) < st["meta_min"]:
                return m_err(400, 100, "Seed audience has fewer than 100 members")
            aid = new_aud("meta", acct, b.get("name", ""), "LOOKALIKE")
        elif b.get("subtype") == "CUSTOM" and b.get("customer_file_source") and b.get("name"):
            aid = new_aud("meta", acct, b["name"])
        else:
            return m_err(400, 100, "Invalid parameter")
        if f == "unknown":
            return m_err(500, 2, "An unexpected error has occurred.")
        return {"id": aid}

    @app.get("/meta/{ver}/act_{acct}/customaudiences")
    async def m_list(ver: str, acct: str, authorization: Optional[str] = Header(None)):
        if err := m_gate(authorization, keep=True):
            return err
        return {"data": [{"id": k, "name": a["name"]} for k, a in st["aud"].items()
                         if a["provider"] == "meta" and a["acct"] == acct and not a["deleted"]]}

    async def m_users(aud: str, request: Request, authorization, remove: bool):
        b = await request.json()
        rec("meta_users_" + ("remove" if remove else "add"), b)
        if err := m_gate(authorization, keep=True):
            return err
        a = get_aud(aud, "meta")
        data = (b.get("payload") or {}).get("data")
        if a is None or (b.get("payload") or {}).get("schema") != ["EMAIL", "PHONE"] or data is None or len(data) > 10000 or bad(v for r in data for v in r):
            return m_err(400, 100, "Invalid hashed data or audience")
        f = fault("meta")
        if f == "lost":
            return m_err(503, 2, "Service temporarily unavailable")
        for email, _ in data:
            (a["members"].discard if remove else a["members"].add)(email) if email else None
        if f == "unknown":
            return m_err(500, 2, "An unexpected error has occurred.")
        return {"audience_id": aud, "num_received": len(data), "num_invalid_entries": 0}

    @app.post("/meta/{ver}/{aud}/users")
    async def m_add(ver: str, aud: str, request: Request, authorization: Optional[str] = Header(None)):
        return await m_users(aud, request, authorization, False)

    @app.delete("/meta/{ver}/{aud}/users")
    async def m_rm(ver: str, aud: str, request: Request, authorization: Optional[str] = Header(None)):
        return await m_users(aud, request, authorization, True)

    @app.delete("/meta/{ver}/{aud}")
    async def m_del(ver: str, aud: str, authorization: Optional[str] = Header(None)):
        rec("meta_delete", aud)
        if err := m_gate(authorization, keep=True):
            return err
        a = get_aud(aud, "meta")
        if a is None:
            return m_err(400, 100, "Unsupported delete request. Object does not exist")
        a["deleted"] = True
        return {"success": True}

    @app.get("/meta/{ver}/{aud}")
    async def m_get(ver: str, aud: str, fields: str = "", authorization: Optional[str] = Header(None)):
        if err := m_gate(authorization, keep=True):
            return err
        a = get_aud(aud, "meta")
        if a is None:
            return m_err(400, 100, "Object does not exist")
        a["reads"] += 1
        ready = a["reads"] > st["ready_after"]
        return {"id": aud, "operation_status": {"code": 200, "description": "Normal"},
                "delivery_status": {"code": 200 if ready else 300, "description": "This audience is ready for use." if ready else "Populating"},
                "approximate_count_lower_bound": len(a["members"]) if ready else -1}

    # ── Google: list via Ads API, members via Data Manager API ───────
    def g_err(status: int, code: str, msg: str):
        return JSONResponse([{"error": {"code": status, "message": msg, "status": code}}], status)

    def g_gate(auth: Optional[str]):
        if auth != f"Bearer {TOKENS['google']}":
            return g_err(401, "UNAUTHENTICATED", "Request is missing required authentication credential.")
        return None

    @app.post("/google/{ver}/customers/{cid}/userLists:mutate")
    async def g_list(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None)):
        b = await request.json()
        rec("google_userlist", b)
        if err := g_gate(authorization):
            return err
        op = (b.get("operations") or [{}])[0]
        f = fault("google")
        if f == "lost":
            return g_err(503, "UNAVAILABLE", "unavailable")
        if "create" in op:
            if not op["create"].get("name") or "crmBasedUserList" not in op["create"]:
                return g_err(400, "INVALID_ARGUMENT", "name and crmBasedUserList required")
            rn = f"customers/{cid}/userLists/{new_aud('google', cid, op['create']['name'])}"
            st["aud"][rn.rsplit('/', 1)[-1]]["rn"] = rn
            if f == "unknown":
                return g_err(500, "INTERNAL", "Internal error encountered.")
            return {"results": [{"resourceName": rn}]}
        a = get_aud(str(op.get("update", {}).get("resourceName", "")).rsplit("/", 1)[-1], "google")
        if a is None or op.get("update", {}).get("membershipStatus") != "CLOSED" or op.get("updateMask") != "membershipStatus":
            return g_err(400, "INVALID_ARGUMENT", "unsupported update")
        a["deleted"] = True
        return {"results": [{"resourceName": op["update"]["resourceName"]}]}

    async def dm(request: Request, authorization, remove: bool):
        b = await request.json()
        rec("google_dm_" + ("remove" if remove else "ingest"), b)
        if err := g_gate(authorization):
            return err
        dest = (b.get("destinations") or [{}])[0]
        a = get_aud(str(dest.get("productDestinationId")), "google")
        ams = b.get("audienceMembers") or []
        ids = [v for m in ams for i in m.get("userData", {}).get("userIdentifiers", []) for v in i.values()]
        if (a is None or dest.get("operatingAccount", {}).get("accountType") != "GOOGLE_ADS" or b.get("encoding") != "HEX"
                or not ams or len(ams) > 10000 or bad(ids) or not all(ids)):
            return g_err(400, "INVALID_ARGUMENT", "invalid destination, encoding or identifiers")
        if not remove and ((b.get("termsOfService") or {}).get("customerMatchTermsOfServiceStatus") != "ACCEPTED"
                           or any((m.get("consent") or {}).get("adUserData") != "CONSENT_GRANTED" for m in ams)):
            return g_err(400, "INVALID_ARGUMENT", "terms of service must be ACCEPTED and consent granted")
        f = fault("google")
        if f == "lost":
            return g_err(503, "UNAVAILABLE", "unavailable")
        for m in ams:
            em = m["userData"]["userIdentifiers"][0].get("emailAddress")
            (a["members"].discard if remove else a["members"].add)(em)
        rid = f"req-{next(seq)}"
        st["reqs"][rid] = {"reads": 0}
        if f == "unknown":
            return g_err(500, "INTERNAL", "Internal error encountered.")
        return {"requestId": rid}

    @app.post("/datamanager/v1/audienceMembers:ingest")
    async def dm_in(request: Request, authorization: Optional[str] = Header(None)):
        return await dm(request, authorization, False)

    @app.post("/datamanager/v1/audienceMembers:remove")
    async def dm_rm(request: Request, authorization: Optional[str] = Header(None)):
        return await dm(request, authorization, True)

    @app.get("/datamanager/v1/requestStatus:retrieve")
    async def dm_status(requestId: str = "", authorization: Optional[str] = Header(None)):
        if err := g_gate(authorization):
            return err
        r = st["reqs"].get(requestId)
        if r is None:
            return g_err(404, "NOT_FOUND", "unknown request id")
        r["reads"] += 1
        return {"requestStatusPerDestination": [{"requestStatus": "SUCCESS" if r["reads"] > st["ready_after"] else "PROCESSING"}]}

    # ── LinkedIn DMP segments ────────────────────────────────────────
    def li_err(status: int, msg: str):
        return JSONResponse({"message": msg, "status": status}, status)

    def li_gate(auth, version, proto, keep=False):
        f = None if keep else fault("linkedin")
        if auth != f"Bearer {TOKENS['linkedin']}" or f == "auth":
            return li_err(401, "Invalid access token")
        if version != LI_VERSION or proto != "2.0.0":
            return li_err(426, "Missing or sunset Linkedin-Version / X-Restli-Protocol-Version")
        return None

    @app.post("/linkedin/rest/dmpSegments")
    async def li_create(request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None),
                        x_restli_protocol_version: Optional[str] = Header(None)):
        b = await request.json()
        rec("linkedin_create", b)
        if err := li_gate(authorization, linkedin_version, x_restli_protocol_version, keep=True):
            return err
        if (not b.get("name") or not str(b.get("account", "")).startswith("urn:li:sponsoredAccount:") or b.get("type") != "USER"
                or b.get("sourcePlatform") not in ("DIRECT_API", "AGENCY_API", "PARTNER_API")
                or b.get("destinations") != [{"destination": "LINKEDIN"}]):
            return li_err(400, "Invalid DMP segment")
        f = fault("linkedin")
        if f == "lost":
            return li_err(503, "Service unavailable")
        aid = new_aud("linkedin", b["account"].rsplit(":", 1)[-1], b["name"])
        if f == "unknown":
            return li_err(500, "Internal server error")
        return Response(status_code=201, headers={"x-restli-id": aid})

    @app.get("/linkedin/rest/dmpSegments")
    async def li_find(request: Request, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None),
                      x_restli_protocol_version: Optional[str] = Header(None)):
        if err := li_gate(authorization, linkedin_version, x_restli_protocol_version, keep=True):
            return err
        acct = request.query_params.get("account", "").rsplit(":", 1)[-1]
        return {"elements": [{"id": int(k), "name": a["name"]} for k, a in st["aud"].items()
                             if a["provider"] == "linkedin" and a["acct"] == acct and not a["deleted"]]}

    @app.post("/linkedin/rest/dmpSegments/{sid}/users")
    async def li_users(sid: str, request: Request, authorization: Optional[str] = Header(None),
                       linkedin_version: Optional[str] = Header(None), x_restli_protocol_version: Optional[str] = Header(None),
                       x_restli_method: Optional[str] = Header(None)):
        b = await request.json()
        rec("linkedin_users", b)
        if err := li_gate(authorization, linkedin_version, x_restli_protocol_version, keep=True):
            return err
        a = get_aud(sid, "linkedin")
        els = b.get("elements")
        if a is None or x_restli_method != "BATCH_CREATE" or not isinstance(els, list) or len(els) > 5000:
            return li_err(400, "Invalid batch request")
        f = fault("linkedin")
        if f == "lost":
            return li_err(503, "Service unavailable")
        out = []
        for el in els:
            ids = el.get("userIds") or []
            if el.get("action") not in ("ADD", "REMOVE") or not ids or any(i.get("idType") != "SHA256_EMAIL" or not HEX.match(i.get("idValue", "")) for i in ids):
                out.append({"status": 400, "error": {"message": "Validation failed", "status": 400}})
                continue
            h = ids[0]["idValue"]
            (a["members"].add if el["action"] == "ADD" else a["members"].discard)(h)
            out.append({"status": 201})
        if f == "unknown":
            return li_err(500, "Internal server error")
        return {"elements": out}

    @app.get("/linkedin/rest/dmpSegments/{sid}")
    async def li_get(sid: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None),
                     x_restli_protocol_version: Optional[str] = Header(None)):
        if err := li_gate(authorization, linkedin_version, x_restli_protocol_version, keep=True):
            return err
        a = get_aud(sid, "linkedin")
        if a is None:
            return li_err(404, "Entity not found")
        a["reads"] += 1
        return {"id": int(sid), "name": a["name"], "inputCount": len(a["members"]),
                "destinations": [{"status": "READY" if a["reads"] > st["ready_after"] else "BUILDING"}]}

    @app.delete("/linkedin/rest/dmpSegments/{sid}")
    async def li_del(sid: str, authorization: Optional[str] = Header(None), linkedin_version: Optional[str] = Header(None),
                     x_restli_protocol_version: Optional[str] = Header(None)):
        rec("linkedin_delete", sid)
        if err := li_gate(authorization, linkedin_version, x_restli_protocol_version, keep=True):
            return err
        a = get_aud(sid, "linkedin")
        if a is None:
            return li_err(404, "Entity not found")
        a["deleted"] = True
        return Response(status_code=204)

    # ── TikTok ───────────────────────────────────────────────────────
    def tt(code: int, msg: str, data=None):
        return JSONResponse({"code": code, "message": msg, "data": data or {}})

    def tt_gate(token, keep=False):
        f = None if keep else fault("tiktok")
        if token != TOKENS["tiktok"] or f == "auth":
            return tt(40105, "Access token is incorrect")
        return None

    @app.post("/tiktok/open_api/v1.3/dmp/custom_audience/file/upload/")
    async def tt_upload(advertiser_id: str = Form(""), file_signature: str = Form(""), file: UploadFile = None,
                        access_token: Optional[str] = Header(None)):
        if err := tt_gate(access_token, keep=True):
            return err
        raw = await file.read()
        if hashlib.md5(raw).hexdigest() != file_signature:
            return tt(40002, "file_signature does not match the file")
        rows = list(csv.reader(io.StringIO(raw.decode())))
        if rows[0][:1] != ["email_SHA256"] or any(bad(r) or not r[0] for r in rows[1:]):
            return tt(40002, "File must be SHA256 hashed with header email_SHA256[,phone_SHA256]")
        path = f"dmp/{next(seq)}.csv"
        st["files"][path] = {"adv": advertiser_id, "emails": [r[0] for r in rows[1:]]}
        rec("tiktok_upload", {"rows": rows})
        return tt(0, "OK", {"file_path": path})

    def tt_files(b: dict) -> Optional[list]:
        fs = [st["files"].get(p) for p in b.get("file_paths") or []]
        return None if not fs or len(fs) > 50 or any(f is None or f["adv"] != str(b.get("advertiser_id")) for f in fs) else [e for f in fs for e in f["emails"]]

    @app.post("/tiktok/open_api/v1.3/dmp/custom_audience/create/")
    async def tt_create(request: Request, access_token: Optional[str] = Header(None)):
        b = await request.json()
        rec("tiktok_create", b)
        if err := tt_gate(access_token, keep=True):
            return err
        emails = tt_files(b)
        if emails is None or not b.get("custom_audience_name"):
            return tt(40002, "Invalid file_paths or name")
        f = fault("tiktok")
        if f == "lost":
            return tt(50002, "Service is busy")
        aid = new_aud("tiktok", str(b["advertiser_id"]), b["custom_audience_name"])
        st["aud"][aid]["members"].update(emails)
        if f == "unknown":
            return tt(50000, "System error")
        return tt(0, "OK", {"custom_audience_id": aid})

    @app.post("/tiktok/open_api/v1.3/dmp/custom_audience/update/")
    async def tt_update(request: Request, access_token: Optional[str] = Header(None)):
        b = await request.json()
        rec("tiktok_update", b)
        if err := tt_gate(access_token, keep=True):
            return err
        a, emails = get_aud(str(b.get("custom_audience_id")), "tiktok"), tt_files(b)
        if a is None or emails is None or b.get("action") not in ("APPEND", "REMOVE", "REPLACE"):
            return tt(40002, "Invalid audience, file_paths or action")
        new = (a["members"] | set(emails) if b["action"] == "APPEND" else a["members"] - set(emails) if b["action"] == "REMOVE" else set(emails))
        if b["action"] != "APPEND" and len(new) < st["tiktok_min"]:
            return tt(40002, f"Resulting audience size {len(new)} is below the minimum {st['tiktok_min']}")
        f = fault("tiktok")
        if f == "lost":
            return tt(50002, "Service is busy")
        a["members"] = new
        if f == "unknown":
            return tt(50000, "System error")
        return tt(0, "OK")

    @app.post("/tiktok/open_api/v1.3/dmp/custom_audience/delete/")
    async def tt_delete(request: Request, access_token: Optional[str] = Header(None)):
        b = await request.json()
        rec("tiktok_delete", b)
        if err := tt_gate(access_token, keep=True):
            return err
        for i in b.get("custom_audience_ids") or []:
            a = get_aud(str(i), "tiktok")
            if a is None:
                return tt(40002, "Audience not found")
            a["deleted"] = True
        return tt(0, "OK")

    @app.get("/tiktok/open_api/v1.3/dmp/custom_audience/get/")
    async def tt_get(advertiser_id: str = "", custom_audience_ids: str = "[]", access_token: Optional[str] = Header(None)):
        import json
        if err := tt_gate(access_token, keep=True):
            return err
        rows = []
        for i in json.loads(custom_audience_ids):
            a = get_aud(str(i), "tiktok")
            if a is not None and a["acct"] == advertiser_id:
                a["reads"] += 1
                ready = a["reads"] > st["ready_after"]
                rows.append({"custom_audience_id": str(i), "name": a["name"], "is_valid": ready, "cover_num": len(a["members"]) if ready else 0})
        return tt(0, "OK", {"list": rows})

    return app
