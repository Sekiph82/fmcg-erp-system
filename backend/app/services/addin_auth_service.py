"""M50.S01.T011 sign-in for the Gmail and Outlook CRM add-ins: OAuth 2.0 authorization-code grant with PKCE (RFC 7636, S256)
issued by the ERP itself (RFC 6749 sections 4.1 / 6; RFC 6819 and OAuth 2.0 Security BCP for the controls below).

Flow: the add-in (host gmail | outlook) makes a code verifier, opens the ERP consent page (a signed-in staff user approves
the scopes), the ERP issues a one-time code (60 s) bound to the PKCE challenge, the host and the origin that asked, and the
add-in exchanges code + verifier for a short-lived access token (15 min) and a rotating refresh token (8 h). Tokens travel
only in Authorization headers and JSON bodies, never in URLs; only SHA-256 hashes are stored.

Controls: host binding (X-Addin-Host must equal the grant's host), origin binding (an Outlook browser request must carry the
grant's origin; a Gmail grant, which is server-to-server, must carry none), scopes addin.read / addin.write (write only for
users who may edit CRM), refresh-token reuse revokes the whole grant, revocation by the user (or a superuser) and by the
add-in's own sign-out, a disabled user's tokens stop working at once, per-grant rate limit.
"""
from __future__ import annotations

import base64
import hashlib
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m50_data_sso import AddinGrant

HOSTS = ("gmail", "outlook")
SCOPES = ("addin.read", "addin.write")
CODE_TTL, ACCESS_TTL, REFRESH_TTL = timedelta(seconds=60), timedelta(minutes=15), timedelta(hours=8)
RATE_PER_MIN = 120
_hits: dict = defaultdict(deque)
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
GMAIL_ORIGIN = "gmail-addon"          # Apps Script calls the API server to server: no browser origin exists


def _now() -> datetime:
    return datetime.now(timezone.utc)


def h(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def allowed_origins(host: str) -> set[str]:
    """Origins that may start a sign-in. Outlook's task pane is a page of the ERP itself; extra origins only by setting."""
    if host == "gmail":
        return {GMAIL_ORIGIN}
    app = urlsplit(settings.PUBLIC_APP_URL)
    extra = getattr(settings, "ADDIN_ALLOWED_ORIGINS", None) or []
    return {f"{app.scheme}://{app.netloc}", *[o.rstrip("/") for o in extra]}


def can_authorize(user) -> tuple[bool, bool]:
    """→ (may read, may write) from the user's CRM rights."""
    from app.core.access_control import has_any_permission
    write = user.is_superuser or has_any_permission(user, ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region"))
    read = write or has_any_permission(user, ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region"))
    return bool(read), bool(write)


async def authorize(db: AsyncSession, user, host: str, challenge: str, origin: str, scopes: list[str]) -> dict:
    if host not in HOSTS:
        raise HTTPException(422, "host must be gmail or outlook.")
    if not CHALLENGE_RE.match(challenge or ""):
        raise HTTPException(422, "code_challenge must be a base64url SHA-256 (43 characters).")
    origin = (origin or "").rstrip("/")
    if origin not in allowed_origins(host):
        raise HTTPException(403, "This origin may not sign the add-in in.")
    read, write = can_authorize(user)
    if not read:
        raise HTTPException(403, "Your account has no CRM access to share with the add-in.")
    if set(scopes) - set(SCOPES):
        raise HTTPException(422, f"Scopes must be among {', '.join(SCOPES)}.")
    want = set(scopes) or set(SCOPES)
    granted = sorted(s for s in want if s == "addin.read" or write)
    await db.execute(AddinGrant.__table__.delete().where(
        AddinGrant.access_hash.is_(None), AddinGrant.code_expires_at < _now() - timedelta(minutes=10)))
    pending = (await db.execute(select(AddinGrant.id).where(AddinGrant.user_id == user.id, AddinGrant.access_hash.is_(None),
                                                            AddinGrant.code_expires_at > _now()))).all()
    if len(pending) >= 10:
        raise HTTPException(429, "Too many unfinished sign-ins; wait a minute.")
    code = secrets.token_urlsafe(32)
    db.add(AddinGrant(user_id=user.id, host=host, origin=origin, scopes=granted, code_hash=h(code), code_challenge=challenge,
                      code_expires_at=_now() + CODE_TTL))
    await db.flush()
    return {"code": code, "expires_in": int(CODE_TTL.total_seconds()), "scopes": granted}


def _issue(g: AddinGrant) -> dict:
    access, refresh = "povua_" + secrets.token_urlsafe(32), "povur_" + secrets.token_urlsafe(32)
    now = _now()
    g.prev_refresh_hash = g.refresh_hash                        # kept to recognise a stolen, already-rotated refresh token
    g.access_hash, g.access_expires_at = h(access), now + ACCESS_TTL
    g.refresh_hash, g.refresh_expires_at = h(refresh), now + REFRESH_TTL
    g.code_hash = g.code_challenge = None
    return {"access_token": access, "token_type": "Bearer", "expires_in": int(ACCESS_TTL.total_seconds()), "refresh_token": refresh,
            "scope": " ".join(g.scopes)}


async def exchange(db: AsyncSession, code: str, verifier: str, host: str) -> dict:
    bad = HTTPException(400, {"error": "invalid_grant", "detail": "The sign-in code is invalid, used or expired."})
    if not VERIFIER_RE.match(verifier or "") or host not in HOSTS:
        raise bad
    g = (await db.execute(select(AddinGrant).where(AddinGrant.code_hash == h(code or "")).with_for_update())).scalar_one_or_none()
    if g is None or g.code_expires_at is None or g.code_expires_at < _now() or g.revoked_at is not None or g.host != host:
        raise bad
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    if not secrets.compare_digest(challenge, g.code_challenge or ""):
        g.code_hash = None                                         # a wrong verifier burns the code
        await db.commit()
        raise bad
    return _issue(g)


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    g = (await db.execute(select(AddinGrant).where(AddinGrant.refresh_hash == h(refresh_token or "")).with_for_update())).scalar_one_or_none()
    if g is None:
        # a refresh token that was already rotated out: treat as theft and revoke the grant it belonged to
        old = (await db.execute(select(AddinGrant).where(AddinGrant.prev_refresh_hash == h(refresh_token or ""),
                                                         AddinGrant.revoked_at.is_(None)))).scalar_one_or_none() if refresh_token else None
        if old is not None:
            await revoke(db, old, "refresh_reuse")
            await db.commit()
        raise HTTPException(401, {"error": "invalid_grant", "detail": "Refresh token invalid."})
    if g.revoked_at is not None or g.refresh_expires_at < _now():
        raise HTTPException(401, {"error": "invalid_grant", "detail": "Refresh token expired or revoked."})
    return _issue(g)


async def revoke(db: AsyncSession, g: AddinGrant, reason: str) -> None:
    g.revoked_at, g.revoked_reason = _now(), reason[:40]
    g.access_hash = g.refresh_hash = g.code_hash = None          # prev_refresh_hash stays: it still identifies a replayed token


def _rate(g: AddinGrant) -> None:
    q, cut = _hits[g.id], time.monotonic() - 60
    while q and q[0] < cut:
        q.popleft()
    if len(q) >= RATE_PER_MIN:
        raise HTTPException(429, "Rate limit reached for this add-in session; try again in a minute.", headers={"Retry-After": "60"})
    q.append(time.monotonic())


async def authenticate(db: AsyncSession, raw: str, scope: str, host: Optional[str], origin: Optional[str]):
    """→ (user with roles loaded, grant). 401 bad/expired/revoked token, 403 host/origin/scope mismatch."""
    from sqlalchemy.orm import selectinload
    from app.models.role import Role
    from app.models.user import User
    www = {"WWW-Authenticate": 'Bearer error="invalid_token"'}
    g = (await db.execute(select(AddinGrant).where(AddinGrant.access_hash == h(raw)))).scalar_one_or_none() if raw else None
    if g is None or g.revoked_at is not None or g.access_expires_at is None or g.access_expires_at <= _now():
        raise HTTPException(401, "Invalid, revoked or expired add-in token.", headers=www)
    if (host or "").lower() != g.host:
        raise HTTPException(403, "This token belongs to a different add-in host.")
    if g.host == "gmail":
        if origin:
            raise HTTPException(403, "A browser origin is not allowed for the Gmail add-on.")
    elif origin and origin.rstrip("/") != g.origin:
        raise HTTPException(403, "This token was issued to a different origin.")
    if scope not in g.scopes:
        raise HTTPException(403, f"This sign-in does not have the {scope} scope.")
    user = (await db.execute(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                             .options(selectinload(User.roles).selectinload(Role.access_scopes))
                             .options(selectinload(User.access_scopes)).where(User.id == g.user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "The user is disabled.", headers=www)
    _rate(g)
    g.last_used_at = _now()
    return user, g
