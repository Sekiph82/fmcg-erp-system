"""M45.S01.T016 staff single sign-on: OpenID Connect authorization code + PKCE (S256).

- Discovery from {issuer}/.well-known/openid-configuration; all calls go through provider_http (egress policy).
- Each start stores state, nonce and the PKCE verifier; the callback uses a state once and within 10 minutes
  (replays and stale states are refused).
- The ID token must be signed by a key from the provider's JWKS (RS256/ES256), with the configured issuer,
  audience = client id, a valid expiry and the stored nonce; the e-mail must be verified.
- Only pre-provisioned, active ERP users are signed in (matched by e-mail); unknown or disabled users are refused.
  Role mapping adds the ERP roles mapped from the token's groups claim; it never removes roles.
- Enforced SSO: password login is refused for everyone except the configured break-glass usernames.
- SAML 2.0: not offered: no maintained SAML library is available in this stack (python3-saml/xmlsec are not
  installed); reported as NOT_AVAILABLE.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import provider_client
from app.models.identity import SSOConfig, SSOState

STATE_TTL = timedelta(minutes=10)
CALLBACK_PATH = "/api/v1/sso/callback"


class SSOError(Exception):
    def __init__(self, status: int, msg: str, audit_reason: str = ""):
        super().__init__(msg)
        self.status = status
        self.audit_reason = audit_reason or msg


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cipher():
    from cryptography.fernet import Fernet
    key = hashlib.sha256(b"fmcg-erp:sso-client-secret:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().encrypt(v.encode()).decode() if v else None


def decrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().decrypt(v.encode()).decode() if v else None


def redirect_uri() -> str:
    return settings.PUBLIC_API_URL.rstrip("/") + CALLBACK_PATH


async def active_config(db: AsyncSession) -> Optional[SSOConfig]:
    return (await db.execute(select(SSOConfig).where(SSOConfig.active.is_(True)).order_by(SSOConfig.updated_at.desc()))).scalars().first()


async def discovery(issuer: str) -> dict:
    async with provider_client() as c:
        r = await c.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
    if r.status_code != 200:
        raise SSOError(502, "The identity provider's discovery document could not be read.")
    meta = r.json()
    if meta.get("issuer", "").rstrip("/") != issuer.rstrip("/"):
        raise SSOError(502, "Discovery issuer does not match the configured issuer.")
    return meta


async def start(db: AsyncSession, cfg: SSOConfig, redirect_to: Optional[str] = None) -> str:
    meta = await discovery(cfg.issuer)
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    st = SSOState(state=secrets.token_urlsafe(32), config_id=cfg.id, nonce=secrets.token_urlsafe(24), verifier=verifier,
                  redirect_to=redirect_to if (redirect_to or "").startswith("/dashboard") else "/dashboard")
    db.add(st)
    await db.flush()
    q = {"response_type": "code", "client_id": cfg.client_id, "redirect_uri": redirect_uri(), "scope": cfg.scopes,
         "state": st.state, "nonce": st.nonce, "code_challenge": challenge, "code_challenge_method": "S256"}
    return meta["authorization_endpoint"] + "?" + urlencode(q)


async def _verify_id_token(meta: dict, cfg: SSOConfig, id_token: str, nonce: str) -> dict:
    async with provider_client() as c:
        jwks = (await c.get(meta["jwks_uri"])).json()
    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.PyJWTError:
        raise SSOError(401, "Malformed ID token.")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise SSOError(401, "ID token signed with an unknown key.")
    try:
        claims = jwt.decode(id_token, jwt.PyJWK(key).key, algorithms=["RS256", "ES256"], audience=cfg.client_id,
                            issuer=cfg.issuer, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
    except jwt.PyJWTError as e:
        raise SSOError(401, f"ID token rejected: {e}")
    if not secrets.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise SSOError(401, "ID token nonce does not match (possible replay).")
    return claims


async def callback(db: AsyncSession, state: str, code: str):
    """→ (user, claims). Raises SSOError for every refusal."""
    from sqlalchemy.orm import selectinload
    from app.models.role import Role
    from app.models.user import User
    st = await db.get(SSOState, state, with_for_update=True) if state else None
    if st is None:
        raise SSOError(400, "Unknown sign-in request.", "unknown_state")
    if st.used_at is not None:
        raise SSOError(400, "This sign-in link was already used.", "state_replay")
    st.used_at = _now()
    await db.flush()
    if st.created_at < _now() - STATE_TTL:
        raise SSOError(400, "This sign-in request expired; start again.", "state_expired")
    cfg = await db.get(SSOConfig, st.config_id)
    if cfg is None or not cfg.active:
        raise SSOError(403, "Single sign-on is not active.")
    meta = await discovery(cfg.issuer)
    async with provider_client() as c:
        r = await c.post(meta["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(), "client_id": cfg.client_id,
            "client_secret": decrypt(cfg.client_secret) or "", "code_verifier": st.verifier})
    if r.status_code != 200 or "id_token" not in r.json():
        raise SSOError(401, "The identity provider refused the sign-in code.", "token_exchange_failed")
    claims = await _verify_id_token(meta, cfg, r.json()["id_token"], st.nonce)
    email = str(claims.get("email") or "").strip().lower()
    if not email or claims.get("email_verified") is False:
        raise SSOError(403, "The identity provider did not confirm an e-mail address.", "no_verified_email")
    from sqlalchemy import func
    user = (await db.execute(select(User).options(selectinload(User.roles)).where(func.lower(User.email) == email))).scalar_one_or_none()
    if user is None:
        raise SSOError(403, "No ERP account exists for this e-mail. Ask an administrator to create it first.", "unknown_user")
    if not user.is_active:
        raise SSOError(403, "This ERP account is disabled.", "inactive_user")
    mapped = {cfg.role_mapping[g] for g in claims.get("groups") or [] if g in (cfg.role_mapping or {})}
    if mapped:
        have = {r.name for r in user.roles}
        for role in (await db.execute(select(Role).where(Role.name.in_(mapped - have), Role.is_active.is_(True)))).scalars():
            user.roles.append(role)
    return user, claims, st.redirect_to


async def password_allowed(db: AsyncSession, user) -> bool:
    """Enforced SSO blocks password login except for the break-glass accounts."""
    cfg = await active_config(db)
    if cfg is None or not cfg.enforced:
        return True
    return user.username in (cfg.break_glass or [])
