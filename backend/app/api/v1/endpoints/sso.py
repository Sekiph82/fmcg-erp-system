"""Staff single sign-on (M45.S01.T016). Prefix /api/v1/sso.
Public: status, start, callback. Configuration: superusers only. The client secret is stored encrypted and never
returned."""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookies import set_auth_cookie, set_refresh_cookie
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.crud import audit as audit_crud
from app.models.audit_log import AuditEvent
from app.models.identity import SSOConfig
from app.models.m50_data_sso import SamlConfig
from app.services import saml_service as saml
from app.services import sso_service as sso
from app.services.auth_refresh_tokens import issue_auth_token_pair

router = APIRouter()


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    cfg = await sso.active_config(db)
    ok, why = saml.available()
    scfg = await saml.active_config(db) if ok else None
    return {"oidc": "ACTIVE" if cfg else "NOT_CONFIGURED", "name": cfg.name if cfg else None,
            "enforced": bool(cfg and cfg.enforced),
            "saml": ("ACTIVE" if scfg else "NOT_CONFIGURED") if ok else "NOT_AVAILABLE", "saml_name": scfg.name if scfg else None,
            "saml_note": why}


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


# ── SAML 2.0 (M50.S01.T010) ────────────────────────────────────────────────────────────────────────────────────────
# Public: GET /saml/metadata, GET /saml/start, POST /saml/acs (assertion signature, audience, recipient, time bounds,
# InResponseTo + browser-bound cookie, replay store). Configuration: superusers only.

SAML_COOKIE = "erp_saml_req"


@router.get("/saml/metadata")
async def saml_metadata(db: AsyncSession = Depends(get_db)):
    """SP metadata (entity id, ACS URL) to hand to the IdP administrator. Only public configuration is in it."""
    from sqlalchemy import select
    cfg = await saml.active_config(db) or (await db.execute(select(SamlConfig))).scalars().first()
    if cfg is None:
        raise HTTPException(404, "SAML single sign-on is not configured.")
    try:
        return Response(saml.metadata_xml(cfg), media_type="application/samlmetadata+xml")
    except sso.SSOError as e:
        raise HTTPException(e.status, str(e))


@router.get("/saml/start")
async def saml_start(next: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    cfg = await saml.active_config(db)
    if cfg is None:
        raise HTTPException(404, "SAML single sign-on is not configured.")
    try:
        url, rid = await saml.start(db, cfg, next)
    except sso.SSOError as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    resp = RedirectResponse(url, status_code=302)
    # the IdP posts back cross-site: SameSite=None needs Secure; on plain-http local development Lax works for a same-site IdP
    resp.set_cookie(SAML_COOKIE, rid, max_age=600, httponly=True, secure=settings.AUTH_COOKIE_SECURE,
                    samesite="none" if settings.AUTH_COOKIE_SECURE else "lax", path="/api/v1/sso/saml")
    return resp


@router.post("/saml/acs")
async def saml_acs(request: Request, db: AsyncSession = Depends(get_db)):
    app_url = settings.PUBLIC_APP_URL.rstrip("/")
    form = await request.form()
    response_b64 = str(form.get("SAMLResponse") or "")
    ip = request.client.host if request.client else None
    try:
        user, info, redirect_to = await saml.acs(db, response_b64, request.cookies.get(SAML_COOKIE, ""))
    except sso.SSOError as e:
        await db.commit()                                  # keep the burned request id (replay protection)
        await audit_crud.log_event(db, event_type=AuditEvent.LOGIN_FAILED, target_type="user", target_name="sso",
                                   details={"method": "saml", "reason": e.audit_reason[:300]}, ip_address=ip)
        await db.commit()
        return RedirectResponse(f"{app_url}/login?sso_error={quote(str(e)[:200])}", status_code=303)
    await audit_crud.log_event(db, event_type=AuditEvent.LOGIN_SUCCESS, actor_id=user.id, actor_email=user.email,
                               target_type="user", target_id=str(user.id), target_name=user.email,
                               details={"method": "saml", "assertion_id": info["assertion_id"]}, ip_address=ip)
    pair = await issue_auth_token_pair(db, user.id)
    await db.commit()
    resp = RedirectResponse(app_url + (redirect_to or "/dashboard"), status_code=303)
    set_auth_cookie(resp, pair.access_token)
    set_refresh_cookie(resp, pair.refresh_token)
    resp.delete_cookie(SAML_COOKIE, path="/api/v1/sso/saml")
    return resp


def _saml_out(cfg: SamlConfig) -> dict:
    cert = saml.check_certificate(cfg.idp_x509_cert)
    return {"id": str(cfg.id), "name": cfg.name, "idp_entity_id": cfg.idp_entity_id, "idp_sso_url": cfg.idp_sso_url,
            "sp_entity_id": cfg.sp_entity_id, "email_attribute": cfg.email_attribute, "groups_attribute": cfg.groups_attribute,
            "role_mapping": cfg.role_mapping, "clock_skew_seconds": cfg.clock_skew_seconds, "active": cfg.active,
            "certificate": cert, "acs_url": saml.acs_url(), "metadata_url": settings.PUBLIC_API_URL.rstrip("/") + saml.METADATA_PATH}


@router.get("/saml/config")
async def get_saml_config(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _superuser(current_user)
    from sqlalchemy import select
    cfg = (await db.execute(select(SamlConfig))).scalars().first()
    ok, why = saml.available()
    return {"library": {"available": ok, "detail": why}, "config": _saml_out(cfg) if cfg else None,
            "defaults": {"sp_entity_id": saml.default_sp_entity_id(), "acs_url": saml.acs_url()}}


class SamlConfigIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    idp_entity_id: str = Field(min_length=1, max_length=300)
    idp_sso_url: str = Field(pattern=r"^https://\S+$|^http://(localhost|127\.0\.0\.1|\[::1\])[:/]\S*$", max_length=500)
    idp_x509_cert: Optional[str] = Field(None, min_length=20, max_length=10000)     # omitted = keep the stored certificate
    sp_entity_id: Optional[str] = Field(None, max_length=300)
    email_attribute: str = Field("email", max_length=100)
    groups_attribute: str = Field("groups", max_length=100)
    role_mapping: dict[str, str] = Field(default_factory=dict)
    clock_skew_seconds: int = Field(60, ge=0, le=120)
    active: bool = False


@router.put("/saml/config")
async def put_saml_config(body: SamlConfigIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from sqlalchemy import select
    from app.services import pat_service as pats
    _superuser(current_user)
    cfg = (await db.execute(select(SamlConfig))).scalars().first()
    pem_in = body.idp_x509_cert or (cfg.idp_x509_cert if cfg else None)
    if not pem_in:
        raise HTTPException(422, "Paste the IdP's signing certificate.")
    try:
        cert = saml.check_certificate(pem_in)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if cert["expired"] and body.active:
        raise HTTPException(422, "The IdP certificate has expired; ask the identity provider for the current one.")
    if cfg is None:
        cfg = SamlConfig()
        db.add(cfg)
    for k, v in body.model_dump(exclude={"sp_entity_id", "idp_x509_cert"}).items():
        setattr(cfg, k, v)
    cfg.idp_x509_cert = saml.pem(pem_in)
    cfg.sp_entity_id = body.sp_entity_id or saml.default_sp_entity_id()
    cfg.updated_by = current_user.username
    pats.audit(db, current_user, "SAML_CONFIG_CHANGED", "sso", body.idp_entity_id,
               {"active": body.active, "cert_sha256": cert["sha256"], "role_mapping_keys": sorted(body.role_mapping)})
    await db.commit()
    await db.refresh(cfg)
    return _saml_out(cfg)
