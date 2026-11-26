"""M50.S01.T010 SAML 2.0 staff sign-in against the local synthetic test IdP (keys generated here, nothing real).

Unit: the SAML library (python3-saml + xmlsec) loads, SP metadata is valid and carries our entity id and ACS, the IdP
certificate check refuses private keys. DB (M50_DB=1): a correctly signed assertion signs in the pre-provisioned user and maps
groups to roles; refusals: wrong signing key, assertion changed after signing, expired / not-yet-valid, wrong audience,
wrong recipient, unsigned, IdP-initiated (no InResponseTo), request not bound to this browser, unknown user, DOCTYPE/XXE,
replay of the same response and of the same assertion id under a new request; HTTP flow start -> IdP -> ACS with cookies
and audit rows.
"""
import base64
import os
import uuid

import pytest

from app.core.config import settings
from app.services import saml_service as saml
from tests.provider_sim.saml_idp_m50_app import TestIdP, build_app

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
IDP = TestIdP()


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _cfg(**kw):
    from app.models.m50_data_sso import SamlConfig
    base = dict(name="Test IdP", idp_entity_id=IDP.entity_id, idp_sso_url="http://localhost:9440/sso", idp_x509_cert=IDP.cert_pem,
                sp_entity_id=saml.default_sp_entity_id(), role_mapping={"erp-sales": "sales_rep_m50"}, clock_skew_seconds=30, active=True)
    return SamlConfig(**{**base, **kw})


def test_library_present_and_metadata_valid():
    ok, why = saml.available()
    assert ok, why
    xml = saml.metadata_xml(_cfg())
    assert saml.default_sp_entity_id() in xml and saml.acs_url() in xml and "HTTP-POST" in xml
    assert "PRIVATE KEY" not in xml and "AuthnRequestsSigned=\"false\"" in xml


def test_certificate_check():
    info = saml.check_certificate(IDP.cert_pem)
    assert info["expired"] is False and len(info["sha256"]) == 64
    with pytest.raises(ValueError):
        saml.check_certificate(IDP.key_pem)                    # a private key is never accepted
    with pytest.raises(ValueError):
        saml.check_certificate("not a certificate at all")
    assert saml.check_certificate(IDP.cert_pem.replace("-----BEGIN CERTIFICATE-----", "").replace("-----END CERTIFICATE-----", "").replace("\n", ""))["sha256"] == info["sha256"]


async def _setup(db, email, role=None):
    from sqlalchemy import select
    from app.models.m50_data_sso import SamlConfig
    from app.models.role import Role
    from app.models.user import User
    await db.execute(SamlConfig.__table__.delete())
    cfg = _cfg()
    db.add(cfg)
    u = User(username=f"saml-{uuid.uuid4().hex[:6]}", email=email, full_name="Amani Wekesa", hashed_password="x", is_active=True)
    db.add(u)
    if role:
        db.add(Role(name=role, description="m50 test role", is_active=True))
    await db.commit()
    return cfg


async def _login(db, cfg, **kw):
    url, rid = await saml.start(db, cfg)
    await db.commit()
    assert url.startswith("http://localhost:9440/sso?SAMLRequest=")
    resp = IDP.response(acs=saml.acs_url(), audience=cfg.sp_entity_id, in_response_to=kw.pop("irt", rid), **kw)
    return rid, resp


def _S():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db.session import engine
    return async_sessionmaker(engine, expire_on_commit=False)()


@DB
@pytest.mark.asyncio
async def test_signed_assertion_signs_in_and_every_tamper_is_refused():
    from app.services.sso_service import SSOError
    email = f"amani-{uuid.uuid4().hex[:6]}@povu-demo.test"
    role = f"sales_rep_m50_{uuid.uuid4().hex[:4]}"
    async with _S() as db:
        cfg = await _setup(db, email, role)
        cfg.role_mapping = {"erp-sales": role}
        await db.commit()
        rid, resp = await _login(db, cfg, email=email, groups=("erp-sales",))
        user, info, redirect = await saml.acs(db, resp, rid)
        await db.commit()
        assert user.email == email and redirect == "/dashboard" and info["assertion_id"].startswith("_")
        from sqlalchemy import select
        from app.models.user import User
        from sqlalchemy.orm import selectinload
        u = (await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))).scalar_one()
        assert role in {r.name for r in u.roles}                                  # group -> role mapping
        # the very same response again: the request id is burned
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, rid)
        assert e.value.audit_reason == "saml_request_replay"
        await db.commit()
        # same assertion id presented under a NEW request: assertion replay
        aid = "_" + uuid.uuid4().hex
        rid2, r1 = await _login(db, cfg, email=email, assertion_id=aid)
        await saml.acs(db, r1, rid2)
        await db.commit()
        rid3, r2 = await _login(db, cfg, email=email, assertion_id=aid)
        with pytest.raises(SSOError) as e:
            await saml.acs(db, r2, rid3)
        assert e.value.audit_reason == "saml_assertion_replay"
        await db.commit()
        refusals = {
            "wrong_key": "saml_rejected", "modified_after_signing": "saml_rejected", "expired": "saml_rejected",
            "not_yet": "saml_rejected", "wrong_audience": "saml_rejected", "wrong_recipient": "saml_rejected"}
        for tamper, reason in refusals.items():
            rid, resp = await _login(db, cfg, email=email, tamper=tamper)
            with pytest.raises(SSOError) as e:
                await saml.acs(db, resp, rid)
            assert e.value.audit_reason.startswith(reason) and e.value.status == 401, (tamper, e.value.audit_reason)
            await db.commit()
        # unsigned assertion
        rid, resp = await _login(db, cfg, email=email, sign=False)
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, rid)
        assert e.value.audit_reason.startswith("saml_rejected") and "signed" in e.value.audit_reason.lower() and e.value.status == 401
        await db.commit()
        # wrong issuer
        rid, resp = await _login(db, cfg, email=email, issuer="https://rogue-idp.example/metadata")
        with pytest.raises(SSOError):
            await saml.acs(db, resp, rid)
        await db.commit()
        # IdP-initiated: no InResponseTo
        _rid, resp = await _login(db, cfg, email=email, irt=None)
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, "anything")
        assert e.value.audit_reason == "saml_no_in_response_to"
        # response answers a request, but from another browser (cookie differs)
        rid, resp = await _login(db, cfg, email=email)
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, "somebody-elses-request")
        assert e.value.audit_reason == "saml_not_bound"
        # a request id that we never issued
        resp = IDP.response(acs=saml.acs_url(), audience=cfg.sp_entity_id, in_response_to="_forged", email=email)
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, "_forged")
        assert e.value.audit_reason == "saml_unknown_request"
        # unknown ERP user (valid signature, nobody provisioned)
        rid, resp = await _login(db, cfg, email=f"stranger-{uuid.uuid4().hex[:5]}@povu-demo.test")
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, rid)
        assert e.value.audit_reason == "unknown_user"
        await db.commit()
        # DOCTYPE / entity expansion is never parsed
        rid, _ = await _login(db, cfg, email=email)
        evil = base64.b64encode(f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><Response InResponseTo="{rid}">&x;</Response>'.encode()).decode()
        with pytest.raises(SSOError) as e:
            await saml.acs(db, evil, rid)
        assert e.value.audit_reason == "saml_no_in_response_to"
        await db.commit()
        # expired request (older than 10 minutes)
        rid, resp = await _login(db, cfg, email=email)
        from app.models.m50_data_sso import SamlRequest
        from datetime import datetime, timedelta, timezone
        (await db.get(SamlRequest, rid)).created_at = datetime.now(timezone.utc) - timedelta(minutes=11)
        await db.commit()
        with pytest.raises(SSOError) as e:
            await saml.acs(db, resp, rid)
        assert e.value.audit_reason == "saml_request_expired"
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_http_flow_start_idp_acs_with_cookies_and_audit(monkeypatch):
    """GET /sso/saml/start -> test IdP page -> POST the signed response to /sso/saml/acs; cookies and audit rows."""
    import re
    import httpx
    from sqlalchemy import select
    from fastapi import FastAPI
    from app.api.v1.endpoints import sso
    from app.models.audit_log import AuditLog
    app = FastAPI()                      # the SSO router alone: the public paths are allow-listed by the coordinator (PUBLIC_ROUTES)
    app.include_router(sso.router, prefix="/api/v1/sso")
    email = f"amani-{uuid.uuid4().hex[:6]}@povu-demo.test"
    async with _S() as db:
        await _setup(db, email)
    idp_app = build_app(IDP)
    idp_app.state.control.update(email=email, groups=[], tamper="none")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as erp, \
            httpx.AsyncClient(transport=httpx.ASGITransport(app=idp_app), base_url="http://localhost:9440") as idp:
        st = (await erp.get("/api/v1/sso/status")).json()
        assert st["saml"] == "ACTIVE"
        assert "EntityDescriptor" in (await erp.get("/api/v1/sso/saml/metadata")).text
        start = await erp.get("/api/v1/sso/saml/start")
        assert start.status_code == 302 and "erp_saml_req" in start.headers["set-cookie"] and "httponly" in start.headers["set-cookie"].lower()
        page = await idp.get(start.headers["location"].replace("http://localhost:9440", ""))
        resp_b64 = re.search(r'name="SAMLResponse" value="([^"]+)"', page.text).group(1)
        # a browser that did not start the flow (no cookie) is refused
        erp.cookies.clear()
        bad = await erp.post("/api/v1/sso/saml/acs", data={"SAMLResponse": resp_b64})
        assert bad.status_code == 303 and "sso_error" in bad.headers["location"]
        # (the request id is burned by the failed attempt: start again for the real login)
        start = await erp.get("/api/v1/sso/saml/start")
        page = await idp.get(start.headers["location"].replace("http://localhost:9440", ""))
        resp_b64 = re.search(r'name="SAMLResponse" value="([^"]+)"', page.text).group(1)
        ok = await erp.post("/api/v1/sso/saml/acs", data={"SAMLResponse": resp_b64})
        assert ok.status_code == 303 and ok.headers["location"].endswith("/dashboard")
        assert any("access" in c.lower() or "token" in c.lower() for c in ok.headers.get_list("set-cookie"))
        again = await erp.post("/api/v1/sso/saml/acs", data={"SAMLResponse": resp_b64})
        assert again.status_code == 303 and "sso_error" in again.headers["location"]            # replay refused
    async with _S() as db:
        rows = (await db.execute(select(AuditLog).where(AuditLog.event_type.in_(["LOGIN_SUCCESS", "LOGIN_FAILED"]))
                                 .order_by(AuditLog.created_at.desc()).limit(10))).scalars().all()
        methods = {(r.event_type, (r.details or {}).get("method")) for r in rows}
        assert ("LOGIN_SUCCESS", "saml") in methods and ("LOGIN_FAILED", "saml") in methods
