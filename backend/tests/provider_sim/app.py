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
from typing import Optional
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


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
    }


CLIENTS = {"google": ("sim-google-client", "sim-google-secret"), "microsoft": ("sim-ms-client", "sim-ms-secret")}


def create_app() -> FastAPI:
    app = FastAPI(title="POVU provider simulator (synthetic, local only)")
    st: dict = {}

    def reset() -> None:
        st.clear()
        st.update(codes={}, access={}, refresh={}, faults={"token": [], "userinfo": []}, deny=False,
                  email={"google": "rep1@povu-demo.test", "microsoft": "rep1@povu-demo.test"},
                  expires_in=3600, drop_scopes=[], issued=0, revoked=[])
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
        return {"ok": True}

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

    app.state.sim = st
    return app
