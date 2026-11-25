"""OAuth 2.0 authorization server simulator for Google and Microsoft identity (M43.S00.T004).

Contracts followed (public documentation, 2026-11-25):
- Google: authorization endpoint /o/oauth2/v2/auth, token endpoint (authorization_code + PKCE S256, refresh_token),
  revoke endpoint (POST token=...), OpenID userinfo {"email": ...}; error=access_denied on refusal; invalid_grant.
- Microsoft identity platform v2.0: /{tenant}/oauth2/v2.0/authorize and /token (refresh tokens rotate),
  Graph GET /me {"mail", "userPrincipalName"}; no revoke endpoint for delegated tokens.

Fault injection through /_control lets contract tests exercise 429/500/invalid_grant, consent refusal, partial
scope grants, short-lived tokens and replayed codes deterministically.
"""
from __future__ import annotations

import base64
import hashlib
import html
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response


def sim_settings(base: str) -> dict:
    """Settings that point the ERP's OAuth adapter at a simulator served at ``base``."""
    base = base.rstrip("/")
    return {
        "GOOGLE_OAUTH_CLIENT_ID": "sim-google-client", "GOOGLE_OAUTH_CLIENT_SECRET": "sim-google-secret",
        "GOOGLE_OAUTH_AUTH_URL": f"{base}/google/o/oauth2/v2/auth",
        "GOOGLE_OAUTH_TOKEN_URL": f"{base}/google/token", "GOOGLE_OAUTH_REVOKE_URL": f"{base}/google/revoke",
        "GOOGLE_OAUTH_USERINFO_URL": f"{base}/google/userinfo",
        "MICROSOFT_OAUTH_CLIENT_ID": "sim-ms-client", "MICROSOFT_OAUTH_CLIENT_SECRET": "sim-ms-secret",
        "MICROSOFT_OAUTH_TENANT": "common", "MICROSOFT_LOGIN_BASE_URL": f"{base}/microsoft",
        "MICROSOFT_GRAPH_BASE_URL": f"{base}/graph/v1.0",
        "GOOGLE_GMAIL_API_URL": f"{base}/gmail/v1",
        "GOOGLE_CALENDAR_API_URL": f"{base}/calendar/v3",
    }


CLIENTS = {"google": ("sim-google-client", "sim-google-secret"), "microsoft": ("sim-ms-client", "sim-ms-secret")}


def create_app() -> FastAPI:
    app = FastAPI(title="POVU provider simulator (synthetic, local only)")
    st: dict = {}

    def reset() -> None:
        st.clear()
        st.update(codes={}, access={}, refresh={}, faults={"token": [], "userinfo": []}, deny=False,
                  email={"google": "rep1@povu-demo.test", "microsoft": "rep1@povu-demo.test"},
                  expires_in=3600, drop_scopes=[], issued=0, revoked=[],
                  # M43.S01.T001/T002 mailboxes: {"google"|"microsoft": [{"id", "raw", "hid"}]}, sent raw MIME
                  mail={"google": [], "microsoft": []}, sent={"google": [], "microsoft": []}, hid=1000,
                  history_floor=0, delta_gone=False, page_size=2,
                  # M43.S01.T003/T004 calendars: {"google"|"microsoft": {event_id: event}}, change counter
                  cal={"google": {}, "microsoft": {}}, cal_ver=0, cal_token_gone=False)
    reset()

    def fault(kind: str) -> Optional[JSONResponse]:
        q = st["faults"].get(kind) or []
        if not q:
            return None
        f = q.pop(0)
        if f == 429:
            return JSONResponse({"error": "rate_limited"}, 429, headers={"Retry-After": "2"})
        if f == 500:
            return JSONResponse({"error": "server_error"}, 500)
        return JSONResponse({"error": f, "error_description": f"simulated {f}"}, 400)

    # ── control plane (tests only) ──────────────────────────────────────────
    @app.post("/_control")
    async def control(request: Request):
        body = await request.json()
        for k in ("deny", "expires_in", "drop_scopes"):
            if k in body:
                st[k] = body[k]
        for k, v in (body.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        st["email"].update(body.get("email") or {})
        for k in ("history_floor", "delta_gone", "page_size"):
            if k in body:
                st[k] = body[k]
        if "cal_token_gone" in body:
            st["cal_token_gone"] = body["cal_token_gone"]
        for e in body.get("calendar") or []:     # {"provider", "id", "start", "end", "cancelled"?, "free"?}
            st["cal_ver"] += 1
            ev = st["cal"][e["provider"]].setdefault(e["id"], {"id": e["id"]})
            ev.update({k: v for k, v in e.items() if k != "provider"}, ver=st["cal_ver"])
        for m in body.get("deliver") or []:      # inbound mail: {"provider", "raw_b64"}
            st["hid"] += 1
            st["mail"][m["provider"]].append({"id": f"m{st['hid']}", "raw": base64.b64decode(m["raw_b64"]),
                                              "hid": st["hid"]})
        return {"ok": True}

    @app.get("/_control/sent/{provider}")
    async def control_sent(provider: str):
        return {"sent": [base64.b64encode(r).decode() for r in st["sent"][provider]]}

    @app.post("/_control/reset")
    async def control_reset():
        reset()
        return {"ok": True}

    @app.get("/_control/state")
    async def control_state():
        return {"issued": st["issued"], "revoked": list(st["revoked"]), "open_codes": len(st["codes"]),
                "live_refresh_tokens": len(st["refresh"])}

    # ── authorization endpoint (consent screen) ─────────────────────────────
    async def authorize(provider: str, request: Request):
        q = dict(request.query_params)
        if q.get("client_id") != CLIENTS[provider][0] or q.get("code_challenge_method") != "S256" \
                or not q.get("code_challenge") or q.get("response_type") != "code":
            return HTMLResponse("<h1>invalid_request</h1>", 400)
        hidden = "".join(f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(v)}">' for k, v in q.items())
        return HTMLResponse(
            f"<!doctype html><title>Simulated {provider} consent</title><h1>Simulated {provider} consent (synthetic)</h1>"
            f"<p>Requested: {html.escape(q.get('scope', ''))}</p><form method=post>{hidden}"
            f"<button name=decision value=allow>Allow</button> <button name=decision value=deny>Deny</button></form>")

    async def consent(provider: str, request: Request):
        form = dict(await request.form())
        redirect_uri, state = form.get("redirect_uri", ""), form.get("state", "")
        if form.get("decision") != "allow" or st["deny"]:
            return RedirectResponse(f"{redirect_uri}?{urlencode({'error': 'access_denied', 'state': state})}", 302)
        code = secrets.token_urlsafe(24)
        granted = [s for s in form.get("scope", "").split() if s not in st["drop_scopes"]]
        st["codes"][code] = {"provider": provider, "redirect_uri": redirect_uri, "challenge": form.get("code_challenge"),
                             "scope": granted}
        return RedirectResponse(f"{redirect_uri}?{urlencode({'code': code, 'state': state})}", 302)

    def issue(provider: str, scope: list[str]) -> dict:
        at, rt = "sim-at-" + secrets.token_urlsafe(16), "sim-rt-" + secrets.token_urlsafe(16)
        st["access"][at] = provider
        st["refresh"][rt] = {"provider": provider, "scope": scope}
        st["issued"] += 1
        return {"access_token": at, "refresh_token": rt, "expires_in": st["expires_in"], "token_type": "Bearer",
                "scope": " ".join(scope)}

    async def token(provider: str, request: Request):
        if (f := fault("token")) is not None:
            return f
        form = dict(await request.form())
        if (form.get("client_id"), form.get("client_secret")) != CLIENTS[provider]:
            return JSONResponse({"error": "invalid_client"}, 401)
        if form.get("grant_type") == "authorization_code":
            c = st["codes"].pop(form.get("code", ""), None)   # single use: a replayed code is unknown
            if c is None or c["provider"] != provider or c["redirect_uri"] != form.get("redirect_uri"):
                return JSONResponse({"error": "invalid_grant"}, 400)
            digest = base64.urlsafe_b64encode(hashlib.sha256(form.get("code_verifier", "").encode()).digest())
            if digest.rstrip(b"=").decode() != c["challenge"]:
                return JSONResponse({"error": "invalid_grant", "error_description": "PKCE mismatch"}, 400)
            return issue(provider, c["scope"])
        if form.get("grant_type") == "refresh_token":
            r = st["refresh"].get(form.get("refresh_token", ""))
            if r is None or r["provider"] != provider:
                return JSONResponse({"error": "invalid_grant"}, 400)
            body = issue(provider, r["scope"])
            if provider == "google":           # Google keeps the refresh token; Microsoft rotates it
                st["refresh"].pop(body["refresh_token"])
                body.pop("refresh_token")
            else:
                st["refresh"].pop(form["refresh_token"])
            return body
        return JSONResponse({"error": "unsupported_grant_type"}, 400)

    def bearer_ok(provider: str, authorization: Optional[str]) -> bool:
        tok = (authorization or "").removeprefix("Bearer ").strip()
        return st["access"].get(tok) == provider

    # Google
    @app.get("/google/o/oauth2/v2/auth")
    async def g_auth(request: Request):
        return await authorize("google", request)

    @app.post("/google/o/oauth2/v2/auth")
    async def g_consent(request: Request):
        return await consent("google", request)

    @app.post("/google/token")
    async def g_token(request: Request):
        return await token("google", request)

    @app.post("/google/revoke")
    async def g_revoke(token: str = Form("")):
        hit = st["refresh"].pop(token, None) or st["access"].pop(token, None)
        if hit is None:
            return JSONResponse({"error": "invalid_token"}, 400)
        st["revoked"].append("google")
        return {}

    @app.get("/google/userinfo")
    async def g_userinfo(authorization: Optional[str] = Header(None)):
        if (f := fault("userinfo")) is not None:
            return f
        if not bearer_ok("google", authorization):
            return JSONResponse({"error": "invalid_token"}, 401)
        return {"email": st["email"]["google"], "email_verified": True}

    # Microsoft identity platform + Graph /me
    @app.get("/microsoft/{tenant}/oauth2/v2.0/authorize")
    async def m_auth(tenant: str, request: Request):
        return await authorize("microsoft", request)

    @app.post("/microsoft/{tenant}/oauth2/v2.0/authorize")
    async def m_consent(tenant: str, request: Request):
        return await consent("microsoft", request)

    @app.post("/microsoft/{tenant}/oauth2/v2.0/token")
    async def m_token(tenant: str, request: Request):
        return await token("microsoft", request)

    @app.get("/graph/v1.0/me")
    async def m_me(authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        return {"mail": st["email"]["microsoft"], "userPrincipalName": st["email"]["microsoft"]}

    # ── Gmail API v1 (subset: profile, messages.list/get raw, history.list, messages.send) ──────
    def g_auth_ok(authorization):
        return bearer_ok("google", authorization)

    @app.get("/gmail/v1/users/me/profile")
    async def gm_profile(authorization: Optional[str] = Header(None)):
        if not g_auth_ok(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        return {"emailAddress": st["email"]["google"], "historyId": str(st["hid"])}

    @app.get("/gmail/v1/users/me/messages")
    async def gm_list(maxResults: int = 100, authorization: Optional[str] = Header(None)):
        if not g_auth_ok(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        msgs = list(reversed(st["mail"]["google"]))[:maxResults]
        return {"messages": [{"id": m["id"], "threadId": m["id"]} for m in msgs], "resultSizeEstimate": len(msgs)}

    @app.get("/gmail/v1/users/me/messages/{mid}")
    async def gm_get(mid: str, authorization: Optional[str] = Header(None)):
        if not g_auth_ok(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        m = next((x for x in st["mail"]["google"] if x["id"] == mid), None)
        if m is None:
            return JSONResponse({"error": {"code": 404}}, 404)
        return {"id": mid, "raw": base64.urlsafe_b64encode(m["raw"]).decode().rstrip("=")}

    @app.get("/gmail/v1/users/me/history")
    async def gm_history(startHistoryId: int, pageToken: Optional[str] = None,
                         authorization: Optional[str] = Header(None)):
        if not g_auth_ok(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        if startHistoryId < st["history_floor"]:
            return JSONResponse({"error": {"code": 404, "message": "Requested entity was not found."}}, 404)
        newer = [m for m in st["mail"]["google"] if m["hid"] > startHistoryId]
        off = int(pageToken or 0)
        page = newer[off:off + st["page_size"]]
        body = {"history": [{"id": str(m["hid"]), "messagesAdded": [{"message": {"id": m["id"]}}]} for m in page],
                "historyId": str(st["hid"])}
        if off + st["page_size"] < len(newer):
            body["nextPageToken"] = str(off + st["page_size"])
        return body

    @app.post("/gmail/v1/users/me/messages/send")
    async def gm_send(request: Request, authorization: Optional[str] = Header(None)):
        if not g_auth_ok(authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        raw = base64.urlsafe_b64decode((await request.json())["raw"] + "==")
        st["sent"]["google"].append(raw)
        return {"id": f"s{len(st['sent']['google'])}", "threadId": "t1", "labelIds": ["SENT"]}

    # ── Microsoft Graph mail (subset: inbox delta, $value, sendMail MIME) ───────────────────────
    @app.get("/graph/v1.0/me/mailFolders/inbox/messages/delta")
    async def ms_delta(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        q = request.query_params
        if q.get("$deltatoken") and st["delta_gone"]:
            st["delta_gone"] = False
            return JSONResponse({"error": {"code": "syncStateNotFound"}}, 410)
        since = int(q.get("$deltatoken") or 0)
        newer = [m for m in st["mail"]["microsoft"] if m["hid"] > since]
        off = int(q.get("$skiptoken") or 0)
        page = newer[off:off + st["page_size"]]
        base = str(request.base_url).rstrip("/") + "/graph/v1.0/me/mailFolders/inbox/messages/delta"
        body = {"value": [{"id": m["id"]} for m in page]}
        if off + st["page_size"] < len(newer):
            body["@odata.nextLink"] = f"{base}?$skiptoken={off + st['page_size']}&$deltatoken={since}" if since                 else f"{base}?$skiptoken={off + st['page_size']}"
        else:
            body["@odata.deltaLink"] = f"{base}?$deltatoken={st['hid']}"
        return body

    @app.get("/graph/v1.0/me/messages/{mid}/$value")
    async def ms_value(mid: str, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        m = next((x for x in st["mail"]["microsoft"] if x["id"] == mid), None)
        if m is None:
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        return Response(m["raw"], media_type="message/rfc822")

    @app.post("/graph/v1.0/me/sendMail")
    async def ms_send(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        st["sent"]["microsoft"].append(base64.b64decode(await request.body()))
        return Response(status_code=202)

    # -- Google Calendar v3 (primary calendar events: list with syncToken, insert, patch, delete) --
    def g_event_out(e: dict) -> dict:
        if e.get("cancelled"):
            return {"id": e["id"], "status": "cancelled"}
        out = {"id": e["id"], "status": "confirmed", "etag": str(e["ver"]),
               "start": {"dateTime": e["start"]}, "end": {"dateTime": e["end"]},
               "transparency": "transparent" if e.get("free") else "opaque"}
        if e.get("povu"):
            out["extendedProperties"] = {"private": {"povuMeetingId": e["povu"]}}
        if e.get("hangoutLink"):
            out["hangoutLink"] = e["hangoutLink"]
        return out

    @app.get("/calendar/v3/calendars/primary/events")
    async def gc_list(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("google", authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        q = request.query_params
        if q.get("syncToken") and st["cal_token_gone"]:
            st["cal_token_gone"] = False
            return JSONResponse({"error": {"code": 410, "message": "Sync token is no longer valid"}}, 410)
        since = int(q.get("syncToken") or 0)
        evs = [g_event_out(e) for e in st["cal"]["google"].values()
               if e["ver"] > since and (since or not e.get("cancelled"))]
        return {"items": evs, "nextSyncToken": str(st["cal_ver"])}

    def _cal_write(prov: str, body: dict, eid: Optional[str] = None) -> dict:
        st["cal_ver"] += 1
        eid = eid or f"{prov[0]}ev{st['cal_ver']}"
        ev = st["cal"][prov].setdefault(eid, {"id": eid})
        if prov == "google":
            priv = (body.get("extendedProperties") or {}).get("private") or {}
            ev.update(start=body["start"]["dateTime"], end=body["end"]["dateTime"], povu=priv.get("povuMeetingId"))
            if body.get("conferenceData"):
                ev["hangoutLink"] = f"https://meet.google.com/sim-{st['cal_ver']}"
        else:
            ev.update(start=body["start"]["dateTime"] + "+00:00", end=body["end"]["dateTime"] + "+00:00",
                      tx=body.get("transactionId"), teams=bool(body.get("isOnlineMeeting")))
        ev.update(ver=st["cal_ver"], cancelled=False)
        return ev

    @app.post("/calendar/v3/calendars/primary/events")
    async def gc_insert(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("google", authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        return g_event_out(_cal_write("google", await request.json()))

    @app.patch("/calendar/v3/calendars/primary/events/{eid}")
    async def gc_patch(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("google", authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        if eid not in st["cal"]["google"] or st["cal"]["google"][eid].get("cancelled"):
            return JSONResponse({"error": {"code": 404}}, 404)
        return g_event_out(_cal_write("google", await request.json(), eid))

    @app.delete("/calendar/v3/calendars/primary/events/{eid}")
    async def gc_delete(eid: str, authorization: Optional[str] = Header(None)):
        if not bearer_ok("google", authorization):
            return JSONResponse({"error": {"code": 401}}, 401)
        if eid not in st["cal"]["google"]:
            return JSONResponse({"error": {"code": 404}}, 404)
        st["cal_ver"] += 1
        st["cal"]["google"][eid].update(cancelled=True, ver=st["cal_ver"])
        return Response(status_code=204)

    # -- Microsoft Graph events + calendarView delta --
    def _utc7(v: str) -> str:
        return datetime.fromisoformat(v).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000")

    def m_event_out(e: dict) -> dict:
        if e.get("cancelled"):
            return {"id": e["id"], "@removed": {"reason": "deleted"}}
        out = {"id": e["id"], "start": {"dateTime": _utc7(e["start"]), "timeZone": "UTC"},
               "end": {"dateTime": _utc7(e["end"]), "timeZone": "UTC"},
               "showAs": "free" if e.get("free") else "busy", "@odata.etag": str(e["ver"]),
               "transactionId": e.get("tx")}
        if e.get("teams"):
            out["onlineMeeting"] = {"joinUrl": f"https://teams.microsoft.com/l/meetup-join/sim-{e['ver']}"}
        return out

    @app.get("/graph/v1.0/me/calendarView/delta")
    async def mc_delta(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        q = request.query_params
        if q.get("$deltatoken") and st["cal_token_gone"]:
            st["cal_token_gone"] = False
            return JSONResponse({"error": {"code": "syncStateNotFound"}}, 410)
        since = int(q.get("$deltatoken") or 0)
        evs = [m_event_out(e) for e in st["cal"]["microsoft"].values()
               if e["ver"] > since and (since or not e.get("cancelled"))]
        base = str(request.base_url).rstrip("/") + "/graph/v1.0/me/calendarView/delta"
        return {"value": evs, "@odata.deltaLink": f"{base}?$deltatoken={st['cal_ver']}"}

    @app.post("/graph/v1.0/me/events")
    async def mc_insert(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        body = await request.json()
        same = next((e for e in st["cal"]["microsoft"].values()
                     if body.get("transactionId") and e.get("tx") == body["transactionId"]), None)
        return JSONResponse(m_event_out(same or _cal_write("microsoft", body)), 201)

    @app.patch("/graph/v1.0/me/events/{eid}")
    async def mc_patch(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        if eid not in st["cal"]["microsoft"] or st["cal"]["microsoft"][eid].get("cancelled"):
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        return m_event_out(_cal_write("microsoft", await request.json(), eid))

    @app.delete("/graph/v1.0/me/events/{eid}")
    async def mc_delete(eid: str, authorization: Optional[str] = Header(None)):
        if not bearer_ok("microsoft", authorization):
            return JSONResponse({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        if eid not in st["cal"]["microsoft"]:
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        st["cal_ver"] += 1
        st["cal"]["microsoft"][eid].update(cancelled=True, ver=st["cal_ver"])
        return Response(status_code=204)

    app.state.sim = st
    return app
