"""Local OpenID Connect provider for tests (M45.S01.T016). No real IdP account.

Implements discovery, /authorize (auto-consents as the user given in ?login_hint=, records the PKCE challenge),
/token (checks client, redirect_uri and the PKCE verifier; one use per code) and /jwks. ID tokens are RS256 with a
key generated per app instance. /_control lets a test tamper with the next token (wrong nonce/audience/key/expiry).
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

ISSUER = "http://idp.test"


def create_oidc_app(client_id: str = "erp-client", client_secret: str = "sim-secret") -> FastAPI:
    app = FastAPI()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "k1", "use": "sig", "alg": "RS256"})
    codes: dict[str, dict] = {}
    state = {"tamper": None, "users": {}}

    @app.get("/.well-known/openid-configuration")
    async def disco():
        return {"issuer": ISSUER, "authorization_endpoint": f"{ISSUER}/authorize", "token_endpoint": f"{ISSUER}/token",
                "jwks_uri": f"{ISSUER}/jwks", "end_session_endpoint": f"{ISSUER}/logout",
                "code_challenge_methods_supported": ["S256"], "id_token_signing_alg_values_supported": ["RS256"]}

    @app.get("/jwks")
    async def jwks():
        return {"keys": [pub]}

    @app.post("/_control")
    async def control(body: dict):
        state["tamper"] = body.get("tamper")
        state["users"].update(body.get("users") or {})
        return {"ok": True}

    @app.get("/authorize")
    async def authorize(request: Request):
        q = request.query_params
        if q.get("client_id") != client_id or q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
            raise HTTPException(400, "bad authorize request")
        code = secrets.token_urlsafe(16)
        codes[code] = {"challenge": q["code_challenge"], "nonce": q.get("nonce"), "redirect_uri": q["redirect_uri"],
                       "email": q.get("login_hint")}
        return RedirectResponse(q["redirect_uri"] + "?" + urlencode({"code": code, "state": q["state"]}), status_code=302)

    @app.post("/token")
    async def token(grant_type: str = Form(...), code: str = Form(...), redirect_uri: str = Form(...),
                    client_id_: str = Form(..., alias="client_id"), client_secret_: str = Form("", alias="client_secret"),
                    code_verifier: str = Form(...)):
        c = codes.pop(code, None)
        if grant_type != "authorization_code" or c is None or client_id_ != client_id or client_secret_ != client_secret:
            raise HTTPException(400, "invalid_grant")
        if redirect_uri != c["redirect_uri"]:
            raise HTTPException(400, "redirect_uri mismatch")
        if base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode() != c["challenge"]:
            raise HTTPException(400, "PKCE verification failed")
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": client_id, "sub": hashlib.sha256((c["email"] or "").encode()).hexdigest()[:20],
                  "iat": now, "exp": now + 300, "nonce": c["nonce"], "email": c["email"], "email_verified": True,
                  "groups": state["users"].get(c["email"], {}).get("groups", [])}
        signer, kid = key, "k1"
        t = state["tamper"]
        if t == "nonce":
            claims["nonce"] = "not-the-nonce"
        elif t == "aud":
            claims["aud"] = "someone-else"
        elif t == "expired":
            claims["exp"] = now - 60
        elif t == "key":
            signer = other
        elif t == "unverified":
            claims["email_verified"] = False
        state["tamper"] = None
        return {"access_token": secrets.token_urlsafe(16), "token_type": "Bearer", "expires_in": 300,
                "id_token": jwt.encode(claims, signer, algorithm="RS256", headers={"kid": kid})}

    return app
