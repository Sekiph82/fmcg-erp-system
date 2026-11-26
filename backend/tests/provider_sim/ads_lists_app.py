"""Local simulator for ad customer lists and offline conversions (M47.S01.T010), shaped like the documented APIs:
Meta Custom Audiences (act_<id>/customaudiences, <audience>/users) and Conversions API (<pixel>/events); Google Ads
Customer Match (userLists:mutate, offlineUserDataJobs:create / :addOperations / :run) and uploadClickConversions.
It refuses any identifier that is not a 64-character lower-case hex SHA-256, so a raw e-mail or phone fails the test.
Synthetic, local only. Tokens are the ones in ads_app.TOKENS."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from tests.provider_sim.ads_app import DEV_TOKEN, TOKENS

HEX = re.compile(r"^[0-9a-f]{64}$")


def create_lists_app() -> FastAPI:
    app = FastAPI(title="POVU ad lists simulator (synthetic, local only)")
    app.state.calls = []

    def meta_ok(auth: Optional[str]):
        if auth != f"Bearer {TOKENS['meta']}":
            return JSONResponse({"error": {"message": "Invalid OAuth access token.", "code": 190}}, 401)
        return None

    def g_ok(auth: Optional[str], dev: Optional[str]):
        if auth != f"Bearer {TOKENS['google']}" or dev != DEV_TOKEN:
            return JSONResponse([{"error": {"code": 401, "status": "UNAUTHENTICATED", "message": "bad credentials"}}], 401)
        return None

    def bad(values) -> bool:
        return any(v and not HEX.match(v) for v in values)

    @app.post("/meta/{ver}/act_{acct}/customaudiences")
    async def m_aud(ver: str, acct: str, request: Request, authorization: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("meta_audience", body))
        return meta_ok(authorization) or {"id": f"23850{acct}"}

    @app.post("/meta/{ver}/{aud}/users")
    async def m_users(ver: str, aud: str, request: Request, authorization: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("meta_users", body))
        if err := meta_ok(authorization):
            return err
        data = body["payload"]["data"]
        if body["payload"]["schema"] != ["EMAIL", "PHONE"] or bad(v for row in data for v in row):
            return JSONResponse({"error": {"message": "Invalid hashed data", "code": 100}}, 400)
        return {"audience_id": aud, "num_received": len(data), "num_invalid_entries": 0, "session_id": "1"}

    @app.post("/meta/{ver}/{pixel}/events")
    async def m_events(ver: str, pixel: str, request: Request, authorization: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("meta_events", body))
        if err := meta_ok(authorization):
            return err
        if bad(v for e in body["data"] for vs in e["user_data"].values() for v in vs):
            return JSONResponse({"error": {"message": "Invalid user_data", "code": 100}}, 400)
        return {"events_received": len(body["data"]), "fbtrace_id": "sim"}

    @app.post("/google/{ver}/customers/{cid}/userLists:mutate")
    async def g_list(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                     developer_token: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("google_list", body))
        return g_ok(authorization, developer_token) or {"results": [{"resourceName": f"customers/{cid}/userLists/77"}]}

    @app.post("/google/{ver}/customers/{cid}/offlineUserDataJobs:create")
    async def g_job(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                    developer_token: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("google_job", body))
        return g_ok(authorization, developer_token) or {"resourceName": f"customers/{cid}/offlineUserDataJobs/9"}

    @app.post("/google/{ver}/customers/{cid}/offlineUserDataJobs/{job}")
    async def g_job_op(ver: str, cid: str, job: str, request: Request, authorization: Optional[str] = Header(None),
                       developer_token: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("google_" + job.split(":")[-1], body))
        if err := g_ok(authorization, developer_token):
            return err
        if job.endswith(":addOperations"):
            ids = [v for op in body["operations"] for i in op["create"]["userIdentifiers"] for v in i.values()]
            if bad(ids):
                return JSONResponse([{"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "not hashed"}}], 400)
        return {}

    @app.post("/google/{ver}/customers/{cid}:uploadClickConversions")
    async def g_conv(ver: str, cid: str, request: Request, authorization: Optional[str] = Header(None),
                     developer_token: Optional[str] = Header(None)):
        body = await request.json()
        app.state.calls.append(("google_conversions", body))
        if err := g_ok(authorization, developer_token):
            return err
        if bad(v for c in body["conversions"] for i in c["userIdentifiers"] for v in i.values()):
            return {"partialFailureError": {"code": 3, "message": "not hashed"}}
        return {"results": [{"conversionAction": c["conversionAction"]} for c in body["conversions"]]}

    return app
