"""Delegated OAuth 2.0 (authorization code + PKCE) for Google and Microsoft (M43.S00.T004).

Shared adapter boundary for Gmail / Microsoft Graph mail (M43.S01.T001/T002) and Google / Outlook calendars
(M43.S01.T003/T004). Endpoints and client credentials come from settings (entered in Integrations → Provider keys
or .env); the endpoints can point at the local provider simulator (tests/provider_sim) so the real flow runs
without any Google or Microsoft account. Without a client id/secret the provider reports NOT_CONFIGURED and no
connection can start; nothing is ever shown as connected unless a token exchange actually succeeded.

Security: single-use state (10 min) bound to the user who started it, PKCE S256, exact redirect URI, granted
scopes checked, tokens Fernet-encrypted (own key salt), refresh under a row lock, tokens never logged or returned.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.oauth_connection import OAuthConnection, OAuthState

STATE_TTL = timedelta(minutes=10)
REFRESH_MARGIN = timedelta(seconds=60)
CALLBACK_PATH = "/api/v1/integrations/oauth/callback"

SCOPES = {
    ("google", "mail"): ["openid", "email", "https://www.googleapis.com/auth/gmail.readonly",
                         "https://www.googleapis.com/auth/gmail.send"],
    # M49: calendar.freebusy for freeBusy.query; Mail.*.Shared for shared / delegated mailboxes; Calendars.Read.Shared
    # for getSchedule. None of them is in REQUIRED_GRANTS: an older connection keeps working, the new feature says so.
    ("google", "calendar"): ["openid", "email", "https://www.googleapis.com/auth/calendar.events",
                             "https://www.googleapis.com/auth/calendar.freebusy"],
    ("microsoft", "mail"): ["openid", "email", "offline_access", "User.Read", "Mail.ReadWrite", "Mail.Send",
                            "Mail.Read.Shared", "Mail.Send.Shared"],
    ("microsoft", "calendar"): ["openid", "email", "offline_access", "User.Read", "Calendars.ReadWrite",
                                "Calendars.Read.Shared"],
}
# Scopes the provider must actually grant (Google lets the user untick some; Microsoft returns short names).
REQUIRED_GRANTS = {
    ("google", "mail"): {"https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"},
    ("google", "calendar"): {"https://www.googleapis.com/auth/calendar.events"},
    ("microsoft", "mail"): {"mail.readwrite", "mail.send"},
    ("microsoft", "calendar"): {"calendars.readwrite"},
}


class OAuthError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "oauth_error"):
        super().__init__(message)
        self.status_code, self.code = status_code, code


class OAuthReauthRequired(OAuthError):
    def __init__(self, message: str = "The provider refused the stored grant; reconnect the account."):
        super().__init__(message, 409, "reauth_required")


class OAuthTemporaryError(OAuthError):
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, 503, "provider_unavailable")
        self.retry_after = retry_after


def _endpoints(provider: str) -> dict:
    if provider == "google":
        return {"authorize": settings.GOOGLE_OAUTH_AUTH_URL, "token": settings.GOOGLE_OAUTH_TOKEN_URL,
                "revoke": settings.GOOGLE_OAUTH_REVOKE_URL, "userinfo": settings.GOOGLE_OAUTH_USERINFO_URL,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID, "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "extra": {"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"}}
    if provider == "microsoft":
        base = f"{settings.MICROSOFT_LOGIN_BASE_URL.rstrip('/')}/{settings.MICROSOFT_OAUTH_TENANT}/oauth2/v2.0"
        return {"authorize": f"{base}/authorize", "token": f"{base}/token", "revoke": None,
                "userinfo": f"{settings.MICROSOFT_GRAPH_BASE_URL.rstrip('/')}/me",
                "client_id": settings.MICROSOFT_OAUTH_CLIENT_ID, "client_secret": settings.MICROSOFT_OAUTH_CLIENT_SECRET,
                "extra": {"response_mode": "query", "prompt": "select_account"}}
    raise OAuthError("Unknown provider", 404, "unknown_provider")


def is_configured(provider: str) -> bool:
    ep = _endpoints(provider)
    return bool(ep["client_id"] and ep["client_secret"])


def redirect_uri() -> str:
    return (settings.OAUTH_REDIRECT_BASE_URL or settings.PUBLIC_API_URL).rstrip("/") + CALLBACK_PATH


def _cipher():
    from cryptography.fernet import Fernet
    key = hashlib.sha256(b"fmcg-erp:oauth-tokens:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _enc(value: Optional[str]) -> Optional[str]:
    return _cipher().encrypt(value.encode()).decode() if value else None


def _dec(token: Optional[str]) -> str:
    return _cipher().decrypt(token.encode()).decode() if token else ""


def _check(provider: str, purpose: str) -> None:
    if (provider, purpose) not in SCOPES:
        raise OAuthError("Unsupported provider or purpose", 404, "unknown_provider")
    if not is_configured(provider):
        raise OAuthError(f"{provider} OAuth is not configured (no client id/secret). This is a setup step, "
                         "not a connection.", 409, "not_configured")


async def start(db: AsyncSession, user_id, provider: str, purpose: str) -> str:
    """Create a single-use state + PKCE verifier and return the provider consent URL."""
    _check(provider, purpose)
    now = clock.utcnow()
    await db.execute(delete(OAuthState).where(OAuthState.created_at < now - STATE_TTL))
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    db.add(OAuthState(state=state, user_id=user_id, provider=provider, purpose=purpose,
                      code_verifier_enc=_enc(verifier), created_at=now))
    await db.flush()          # visible to complete() in the same transaction as well as after commit
    ep = _endpoints(provider)
    params = {"client_id": ep["client_id"], "response_type": "code", "redirect_uri": redirect_uri(),
              "scope": " ".join(SCOPES[(provider, purpose)]), "state": state,
              "code_challenge": challenge, "code_challenge_method": "S256", **ep["extra"]}
    return f"{ep['authorize']}?{urlencode(params)}"


async def _post_token(provider: str, data: dict) -> dict:
    ep = _endpoints(provider)
    form = {"client_id": ep["client_id"], "client_secret": ep["client_secret"], **data}
    try:
        async with provider_client() as client:
            resp = await client.post(ep["token"], data=form, headers={"Accept": "application/json"})
    except EgressBlocked as e:
        raise OAuthError(str(e), 503, "egress_blocked") from None
    except httpx.HTTPError:
        raise OAuthTemporaryError("The provider could not be reached.") from None
    if resp.status_code == 429 or resp.status_code >= 500:
        ra = resp.headers.get("Retry-After")
        raise OAuthTemporaryError(f"Provider busy ({resp.status_code}).", int(ra) if ra and ra.isdigit() else None)
    try:
        body = resp.json()
    except ValueError:
        raise OAuthError("The provider returned an unreadable token response.", 502, "bad_response") from None
    if resp.status_code >= 400 or "access_token" not in body:
        if body.get("error") == "invalid_grant":
            raise OAuthReauthRequired()
        raise OAuthError(f"Token request refused: {str(body.get('error', resp.status_code))[:80]}", 502, "token_refused")
    return body


def _granted(provider: str, body: dict, requested: list[str]) -> list[str]:
    raw = body.get("scope")
    scopes = raw.split() if isinstance(raw, str) and raw.strip() else list(requested)
    if provider == "microsoft":   # Graph returns short or URL forms; compare on the short lower-case name
        scopes = [s.rsplit("/", 1)[-1] for s in scopes]
    return scopes


async def _account_email(provider: str, access_token: str) -> Optional[str]:
    url = _endpoints(provider)["userinfo"]
    try:
        async with provider_client() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError, EgressBlocked):
        return None
    email = data.get("email") or data.get("mail") or data.get("userPrincipalName")
    return str(email)[:255] if email else None


async def complete(db: AsyncSession, *, state: str, code: Optional[str], error: Optional[str]) -> OAuthConnection:
    """Handle the provider redirect: consume the state once, exchange the code, store the encrypted tokens."""
    if not state:
        raise OAuthError("Missing state", 400, "bad_state")
    row = (await db.execute(delete(OAuthState).where(OAuthState.state == state).returning(
        OAuthState.user_id, OAuthState.provider, OAuthState.purpose, OAuthState.code_verifier_enc,
        OAuthState.created_at))).first()
    if row is None:
        raise OAuthError("Unknown or already used sign-in attempt; start again.", 400, "bad_state")
    user_id, provider, purpose, verifier_enc, created_at = row
    if created_at < clock.utcnow() - STATE_TTL:
        raise OAuthError("The sign-in attempt expired; start again.", 400, "state_expired")
    if error:
        raise OAuthError("Consent was not given at the provider; nothing was connected.", 400,
                         "consent_refused" if error == "access_denied" else "provider_error")
    if not code:
        raise OAuthError("Missing authorization code", 400, "bad_code")
    _check(provider, purpose)
    requested = SCOPES[(provider, purpose)]
    body = await _post_token(provider, {"grant_type": "authorization_code", "code": code,
                                        "redirect_uri": redirect_uri(), "code_verifier": _dec(verifier_enc)})
    granted = _granted(provider, body, requested)
    missing = REQUIRED_GRANTS[(provider, purpose)] - {s.lower() if provider == "microsoft" else s for s in granted}
    if missing:
        raise OAuthError("The provider did not grant every permission this feature needs; reconnect and allow "
                         "all requested permissions.", 400, "scope_missing")
    email = await _account_email(provider, body["access_token"])
    conn = (await db.execute(select(OAuthConnection).where(
        OAuthConnection.user_id == user_id, OAuthConnection.provider == provider,
        OAuthConnection.purpose == purpose).with_for_update())).scalar_one_or_none()
    if conn is None:
        conn = OAuthConnection(id=uuid.uuid4(), user_id=user_id, provider=provider, purpose=purpose)
        db.add(conn)
    elif conn.account_email and email and conn.account_email.lower() != email.lower():
        conn.sync_cursor = None   # a different mailbox/calendar: never continue the old cursor
    conn.status, conn.last_error, conn.scopes, conn.account_email = "CONNECTED", None, granted, email
    conn.access_token_enc = _enc(body["access_token"])
    if body.get("refresh_token"):
        conn.refresh_token_enc = _enc(body["refresh_token"])
    conn.expires_at = clock.utcnow() + timedelta(seconds=int(body.get("expires_in") or 3600))
    _audit(db, user_id, "OAUTH_CONNECTED", conn)
    await db.flush()
    return conn


async def access_token(db: AsyncSession, conn: OAuthConnection) -> str:
    """A valid access token for an API call, refreshed under a row lock when it is about to expire."""
    if conn.status != "CONNECTED" or not conn.access_token_enc:
        raise OAuthReauthRequired("This account is not connected.")
    if conn.expires_at and conn.expires_at - REFRESH_MARGIN > clock.utcnow():
        return _dec(conn.access_token_enc)
    await db.flush()          # sessions run without autoflush: persist a forced expiry before re-reading the row
    locked = (await db.execute(select(OAuthConnection).where(OAuthConnection.id == conn.id)
                               .with_for_update().execution_options(populate_existing=True))).scalar_one()
    if locked.expires_at and locked.expires_at - REFRESH_MARGIN > clock.utcnow():   # another worker refreshed
        return _dec(locked.access_token_enc)
    if not locked.refresh_token_enc:
        locked.status, locked.last_error = "ERROR", "No refresh token; reconnect."
        raise OAuthReauthRequired()
    try:
        body = await _post_token(locked.provider, {"grant_type": "refresh_token",
                                                   "refresh_token": _dec(locked.refresh_token_enc)})
    except OAuthReauthRequired:
        locked.status, locked.last_error = "ERROR", "The provider revoked access; reconnect."
        locked.access_token_enc = None
        raise
    locked.access_token_enc = _enc(body["access_token"])
    if body.get("refresh_token"):            # Microsoft rotates refresh tokens
        locked.refresh_token_enc = _enc(body["refresh_token"])
    locked.expires_at = clock.utcnow() + timedelta(seconds=int(body.get("expires_in") or 3600))
    await db.flush()
    return _dec(locked.access_token_enc)


async def disconnect(db: AsyncSession, conn: OAuthConnection, actor_id) -> None:
    """Revoke at the provider where it offers revocation (Google), then wipe the tokens locally in any case."""
    ep = _endpoints(conn.provider)
    token = _dec(conn.refresh_token_enc) or _dec(conn.access_token_enc)
    revoked_remote = None
    if ep["revoke"] and token:
        try:
            async with provider_client() as client:
                resp = await client.post(ep["revoke"], data={"token": token})
            revoked_remote = resp.status_code == 200
        except (httpx.HTTPError, EgressBlocked):
            revoked_remote = False
    conn.access_token_enc = conn.refresh_token_enc = None
    conn.status, conn.sync_cursor, conn.expires_at = "REVOKED", None, None
    conn.last_error = None if revoked_remote in (True, None) else "Local tokens deleted; provider revocation failed."
    _audit(db, actor_id, "OAUTH_DISCONNECTED", conn, {"provider_revoked": revoked_remote})
    await db.flush()


def _audit(db: AsyncSession, actor_id, event: str, conn: OAuthConnection, details: dict | None = None) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=actor_id, event_type=event, module="integrations", target_type="oauth_connection",
                    target_id=str(conn.id) if conn.id else None, target_name=f"{conn.provider}:{conn.purpose}",
                    details={"account": conn.account_email, "scopes": conn.scopes, **(details or {})}))


def public_view(conn: OAuthConnection) -> dict:
    return {"id": str(conn.id), "provider": conn.provider, "purpose": conn.purpose, "status": conn.status,
            "account_email": conn.account_email, "scopes": conn.scopes or [], "last_error": conn.last_error,
            "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None}
