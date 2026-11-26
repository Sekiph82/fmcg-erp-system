"""Staff single sign-on (M45.S01.T016). Prefix /api/v1/sso.
Public: status, start, callback. Configuration: superusers only. The client secret is stored encrypted and never
returned."""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookies import set_auth_cookie, set_refresh_cookie
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.crud import audit as audit_crud
from app.models.audit_log import AuditEvent
from app.models.identity import SSOConfig
from app.services import sso_service as sso
from app.services.auth_refresh_tokens import issue_auth_token_pair

router = APIRouter()


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    cfg = await sso.active_config(db)
    return {"oidc": "ACTIVE" if cfg else "NOT_CONFIGURED", "name": cfg.name if cfg else None,
            "enforced": bool(cfg and cfg.enforced), "saml": "NOT_AVAILABLE",
            "saml_note": "SAML 2.0 needs a maintained SAML library (python3-saml/xmlsec), not installed in this stack."}


@router.get("/start")
async def start(next: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    cfg = await sso.active_config(db)
    if cfg is None:
        raise HTTPException(404, "Single sign-on is not configured.")
    try:
        url = await sso.start(db, cfg, next)
    except (sso.SSOError, EgressBlocked) as e:
        raise HTTPException(getattr(e, "status", 503), str(e))
    await db.commit()
    resp = RedirectResponse(url, status_code=302)
    state = url.split("state=", 1)[1].split("&", 1)[0]
    resp.set_cookie("erp_sso_state", state, max_age=600, httponly=True, secure=settings.AUTH_COOKIE_SECURE,
                    samesite="lax", path="/api/v1/sso")        # binds the flow to this browser (login CSRF)
    return resp


@router.get("/callback")
async def callback(request: Request, state: str = "", code: str = "", error: str = "", db: AsyncSession = Depends(get_db)):
    app_url = settings.PUBLIC_APP_URL.rstrip("/")
    if error:
        return RedirectResponse(f"{app_url}/login?sso_error={quote(error[:100])}", status_code=302)
    import hmac as _hmac
    try:
        if not _hmac.compare_digest(request.cookies.get("erp_sso_state", "").encode(), state.encode()):
            raise sso.SSOError(400, "This sign-in was not started in this browser; start again.", "state_not_bound")
        user, claims, redirect_to = await sso.callback(db, state, code)
    except (sso.SSOError, EgressBlocked) as e:
        await db.commit()                                  # keep the used state (replay protection)
        await audit_crud.log_event(db, event_type=AuditEvent.LOGIN_FAILED, target_type="user", target_name="sso",
                                   details={"method": "oidc", "reason": getattr(e, "audit_reason", str(e))},
                                   ip_address=request.client.host if request.client else None)
        await db.commit()
        return RedirectResponse(f"{app_url}/login?sso_error={quote(str(e)[:200])}", status_code=302)
    await audit_crud.log_event(db, event_type=AuditEvent.LOGIN_SUCCESS, actor_id=user.id, actor_email=user.email,
                               target_type="user", target_id=str(user.id), target_name=user.email,
                               details={"method": "oidc", "sub": claims.get("sub")},
                               ip_address=request.client.host if request.client else None)
    pair = await issue_auth_token_pair(db, user.id)
    await db.commit()
    resp = RedirectResponse(app_url + (redirect_to or "/dashboard"), status_code=302)
    set_auth_cookie(resp, pair.access_token)
    set_refresh_cookie(resp, pair.refresh_token)
    return resp


@router.get("/logout-url")
async def logout_url(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Where to send the browser after the ERP logout so the IdP session ends too (if the IdP supports it)."""
    cfg = await sso.active_config(db)
    if cfg is None:
        return {"url": None}
    try:
        meta = await sso.discovery(cfg.issuer)
    except (sso.SSOError, EgressBlocked):
        return {"url": None}
    end = meta.get("end_session_endpoint")
    return {"url": f"{end}?client_id={quote(cfg.client_id)}&post_logout_redirect_uri={quote(settings.PUBLIC_APP_URL)}" if end else None}


def _superuser(u):
    if not u.is_superuser:
        raise HTTPException(403, "Only a superuser configures single sign-on.")


@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _superuser(current_user)
    from sqlalchemy import select
    cfg = await sso.active_config(db) or (await db.execute(select(SSOConfig))).scalars().first()
    if cfg is None:
        return None
    return {"id": str(cfg.id), "name": cfg.name, "issuer": cfg.issuer, "client_id": cfg.client_id, "scopes": cfg.scopes,
            "role_mapping": cfg.role_mapping, "enforced": cfg.enforced, "break_glass": cfg.break_glass, "active": cfg.active,
            "has_secret": bool(cfg.client_secret), "redirect_uri": sso.redirect_uri()}


class ConfigIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    issuer: str = Field(pattern=r"^https?://\S+$", max_length=300)
    client_id: str = Field(min_length=1, max_length=200)
    client_secret: Optional[str] = Field(None, max_length=500)
    scopes: str = Field("openid email profile groups", max_length=200)
    role_mapping: dict[str, str] = Field(default_factory=dict)
    enforced: bool = False
    break_glass: list[str] = Field(default_factory=list)
    active: bool = False


@router.put("/config")
async def put_config(body: ConfigIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from sqlalchemy import select
    from app.services import pat_service as pats
    _superuser(current_user)
    if body.enforced and not body.break_glass:
        raise HTTPException(422, "Name at least one break-glass account before enforcing single sign-on.")
    cfg = (await db.execute(select(SSOConfig))).scalars().first()
    if cfg is None:
        cfg = SSOConfig()
        db.add(cfg)
    for k, v in body.model_dump(exclude={"client_secret"}).items():
        setattr(cfg, k, v)
    if body.client_secret:
        cfg.client_secret = sso.encrypt(body.client_secret)
    cfg.updated_by = current_user.username
    pats.audit(db, current_user, "SSO_CONFIG_CHANGED", "sso", body.issuer,
               {"enforced": body.enforced, "active": body.active, "break_glass": body.break_glass})
    await db.commit()
    return {"ok": True}
