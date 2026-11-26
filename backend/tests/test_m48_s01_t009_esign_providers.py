"""M48.S01.T009 DocuSign eSignature + Adobe Acrobat Sign adapters against the local provider simulator.

Unit part (no DB): JWT assertion, request shapes, HMAC, adapter lifecycle, decline/expiry/void, 429 retry, lost create
reconciled by our reference, identity check, consent_required. DB part (M48_DB=1): the real app with personas —
readiness, RBAC, only approved quotations, ledger + idempotency, COMPLETED only with the signed document, ERP update,
change-after-send invalidation, signed webhooks (tamper, replay), Adobe client-id verification, cancel. Synthetic only.
"""
import base64
import json
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
BASE = "http://esign.test"
PW = uuid.uuid4().hex + "Aa1!"


def _keys():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub = k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pub


PRIV, PUB = _keys()


@pytest.fixture
def sim(monkeypatch):
    from app.core import provider_http
    from app.services import esign_provider_service as esp
    from tests.provider_sim.esign_app import create_esign_app
    app = create_esign_app()
    app.state.sim["ds_public_key"] = PUB
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    monkeypatch.setattr(esp, "MAX_WAIT", 0.0)
    esp._TOKENS.clear()
    yield app.state.sim
    provider_http.set_test_transport(None)
    esp._TOKENS.clear()


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _ds():
    from app.services.esign_provider_service import DocuSign
    from tests.provider_sim.esign_app import sim_esign_settings
    return DocuSign(sim_esign_settings(BASE)["DOCUSIGN"], {"private_key_pem": PRIV, "connect_hmac_key": "sim-connect-hmac-key"}, "SIMULATED")


def _ad():
    from app.services.esign_provider_service import AdobeSign
    from tests.provider_sim.esign_app import sim_esign_settings
    return AdobeSign(sim_esign_settings(BASE)["ADOBE_SIGN"], {"client_secret": "sim-adobe-secret", "refresh_token": "sim-adobe-refresh"}, "SIMULATED")


def _env(provider="DOCUSIGN"):
    from app.models.m48_esign import ESignEnvelope
    from app.services.esign_provider_service import _pdf
    return ESignEnvelope(provider=provider, idempotency_key=f"povu-{uuid.uuid4().hex}", source_ref="QT-T009 v1",
                         snapshot_pdf=_pdf(["POVU AllClean 1 L | 10 PCS", "Signature: /sig1/"]), signer_name="Amina Duka",
                         signer_email="amina@povu-demo.test", expire_days=14, created_at=datetime.now(timezone.utc))


# ── unit ──────────────────────────────────────────────────────────────────────

def test_jwt_assertion_is_rs256_with_documented_claims():
    import jwt
    a = _ds().assertion(now=1_800_000_000)
    assert jwt.get_unverified_header(a) == {"alg": "RS256", "typ": "JWT"}
    c = jwt.decode(a, PUB, algorithms=["RS256"], audience="esign.test", options={"verify_exp": False, "verify_iat": False})
    assert c == {"iss": "sim-integration-key", "sub": "5f1e2d3c-0000-4000-8000-0000000000u1", "aud": "esign.test",
                 "iat": 1_800_000_000, "exp": 1_800_003_600, "scope": "signature impersonation"}
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(a, _keys()[1], algorithms=["RS256"], audience="esign.test", options={"verify_exp": False, "verify_iat": False})


def test_request_shapes():
    from app.services.esign_provider_service import AdobeSign, DocuSign
    env = _env()
    b = DocuSign.envelope_body(env)
    assert b["status"] == "sent" and base64.b64decode(b["documents"][0]["documentBase64"]) == env.snapshot_pdf
    assert (b["documents"][0]["fileExtension"], b["documents"][0]["documentId"]) == ("pdf", "1")
    s = b["recipients"]["signers"][0]
    assert (s["email"], s["name"], s["recipientId"]) == ("amina@povu-demo.test", "Amina Duka", "1")
    assert s["tabs"]["signHereTabs"][0]["anchorString"] == "/sig1/"
    assert b["customFields"]["textCustomFields"][0] == {"name": "povu_ref", "value": env.idempotency_key, "show": "false", "required": "false"}
    assert b["notification"]["expirations"] == {"expireEnabled": "true", "expireAfter": "14", "expireWarn": "0"}
    a = AdobeSign.agreement_body(env, "tid-1")
    assert a["fileInfos"] == [{"transientDocumentId": "tid-1"}] and a["state"] == "IN_PROCESS" and a["signatureType"] == "ESIGN"
    assert a["participantSetsInfo"] == [{"memberInfos": [{"email": "amina@povu-demo.test"}], "order": 1, "role": "SIGNER"}]
    assert a["externalId"] == {"id": env.idempotency_key} and a["name"].endswith(f"[{env.idempotency_key}]")
    assert a["expirationTime"].endswith("Z")


def test_snapshot_pdf_is_deterministic():
    from app.services.esign_provider_service import _pdf, _sha
    lines = [f"line {i} (POVU Hand Wash Powder 1 kg Pouch)" for i in range(120)]
    one, two = _pdf(lines), _pdf(lines)
    assert one.startswith(b"%PDF-1.4") and one.rstrip().endswith(b"%%EOF") and _sha(one) == _sha(two)
    assert b"/Count 3" in one and _pdf(lines[:-1]) != one


def test_connect_hmac_matches_docs_and_detects_tamper():
    import hashlib
    import hmac as _h
    from app.services.esign_provider_service import docusign_hmac
    body = b'{"event":"envelope-completed","data":{"envelopeId":"x"}}\r\n'
    want = base64.b64encode(_h.new(b"k3y", body, hashlib.sha256).digest()).decode()
    assert docusign_hmac("k3y", body) == want == docusign_hmac('"k3y"', body)     # quotes stripped as documented
    assert docusign_hmac("k3y", body + b" ") != want


@pytest.mark.asyncio
async def test_docusign_adapter_lifecycle_and_faults(sim):
    from app.services.esign_provider_service import ProviderError
    ds = _ds()
    env = _env()
    sim["delay"] = 3600
    env.provider_ref = await ds.create(env)
    assert sim["assertions"][0]["header"]["alg"] == "RS256"
    assert (await ds.status(env)) == ("sent", "SENT", True)
    sim["faults"]["ds_status"] = [429, 500]                 # retried with backoff
    assert (await ds.status(env))[1] == "SENT"
    sim["strip_ref"] = True                                 # identity: a record without our reference is not ours
    assert (await ds.status(env))[2] is False
    sim["strip_ref"] = False
    await ds.cancel(env, "Customer asked for a new version")
    assert (await ds.status(env))[1] == "VOIDED"
    with pytest.raises(ProviderError) as e:                 # void again: documented invalid state
        await ds.cancel(env, "again")
    assert e.value.definite and "ENVELOPE_CANNOT_VOID" in str(e.value)
    for outcome, want in (("decline", "DECLINED"), ("expire", "EXPIRED"), ("complete", "COMPLETED")):
        sim.update(delay=0.0, outcome=outcome)
        x = _env()
        x.provider_ref = await ds.create(x)
        assert (await ds.status(x))[1] == want
    signed, cert = await ds.documents(x)
    assert signed.startswith(x.snapshot_pdf) and cert.startswith(b"%PDF-")
    # a create whose answer is lost is unknown, then found by our custom field
    sim["faults"]["ds_create"] = ["lost"]
    y = _env()
    with pytest.raises(ProviderError) as e:
        await ds.create(y)
    assert not e.value.definite
    y.provider_ref = await ds.find(y)
    assert y.provider_ref and (await ds.status(y))[2]
    sim["faults"]["ds_create"] = [500, 500]                 # a create is never retried on 5xx
    with pytest.raises(ProviderError) as e:
        await ds.create(_env())
    assert not e.value.definite and sim["faults"]["ds_create"] == [500]


@pytest.mark.asyncio
async def test_docusign_consent_required(sim):
    from app.services.esign_provider_service import ProviderError
    sim["consent"] = False
    with pytest.raises(ProviderError) as e:
        await _ds().create(_env())
    assert e.value.definite and "consent_required" in str(e.value)


@pytest.mark.asyncio
async def test_adobe_adapter_lifecycle_paging_and_decline(sim):
    from app.services.esign_provider_service import ProviderError
    ad = _ad()
    sim["delay"] = 3600
    envs = []
    for _ in range(3):
        e = _env("ADOBE_SIGN")
        e.provider_ref = await ad.create(e)
        envs.append(e)
    assert (await ad.status(envs[0])) == ("OUT_FOR_SIGNATURE", "SENT", True)
    await ad.cancel(envs[0], "Price list changed")
    assert (await ad.status(envs[0]))[1] == "CANCELLED"     # recalled by us, not declined
    sim["faults"]["ad_create"] = ["lost"]
    lost = _env("ADOBE_SIGN")
    with pytest.raises(ProviderError):
        await ad.create(lost)
    assert await ad.find(lost) is not None                  # found on page 2 (page size 2) by name + reference
    assert await ad.find(_env("ADOBE_SIGN")) is None
    for outcome, want in (("decline", "DECLINED"), ("expire", "EXPIRED"), ("complete", "COMPLETED")):
        sim.update(delay=0.0, outcome=outcome)
        x = _env("ADOBE_SIGN")
        x.provider_ref = await ad.create(x)
        assert (await ad.status(x))[1] == want
    signed, audit = await ad.documents(x)
    assert signed.startswith(b"%PDF-") and audit.startswith(b"%PDF-")
    sim["adobe_refresh"] = "rotated-elsewhere"
    from app.services import esign_provider_service as esp
    esp._TOKENS.clear()
    with pytest.raises(ProviderError) as e:
        await ad.status(x)
    assert e.value.definite


# ── DB: the real app with personas ────────────────────────────────────────────

async def _user(db, perms: tuple, tag: str):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password=hash_password(PW), is_active=True)
    role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
            await db.flush()
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    await db.flush()
    return u


async def _world():
    from app.db.session import AsyncSessionLocal
    from app.models.master import Product, ProductCategory
    from app.models.sales import Customer
    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        admin = await _user(db, ("esign.view", "esign.cancel", "esign.admin"), "esadmin")
        rep = await _user(db, ("sales.view", "sales.edit", "esign.view", "esign.request"), "rep")
        outsider = await _user(db, ("sales.view", "esign.view"), "outsider")
        prod = Product(sku=f"POVU-ALC-1L-{s}", name="POVU AllClean 1 L", category=ProductCategory.HOUSEHOLD)
        cust = Customer(code=f"ES-{s}", name="POVU Duka Nairobi", currency="KES", email=f"duka{s}@povu-demo.test")
        db.add_all([prod, cust])
        await db.commit()
        return {"admin": admin.username, "rep": rep.username, "outsider": outsider.username, "rep_id": rep.id,
                "product": prod.id, "customer": cust.id}


async def _quote(w, status="SENT"):
    from app.db.session import AsyncSessionLocal
    from app.models.quotation import Quotation, QuotationLine, QuoteStatus
    async with AsyncSessionLocal() as db:
        q = Quotation(quote_no=f"QT-T009-{uuid.uuid4().hex[:6]}", customer_id=w["customer"], status=QuoteStatus(status),
                      quote_date=date.today(), currency="KES", created_by_id=w["rep_id"], total_amount=Decimal("1200"),
                      tax_amount=Decimal("192"), grand_total=Decimal("1392"))
        db.add(q)
        await db.flush()
        db.add(QuotationLine(quote_id=q.id, line_no=1, product_id=w["product"], qty=Decimal("10"), unit_price=Decimal("120"),
                             discount_pct=Decimal("0"), tax_rate=Decimal("16"), line_total=Decimal("1392")))
        await db.commit()
        return q.id


async def _quote_status(qid):
    from app.db.session import AsyncSessionLocal
    from app.models.quotation import Quotation
    async with AsyncSessionLocal() as db:
        return (await db.get(Quotation, qid)).status.value


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


def _hooks():
    """The public callback router (registration + PUBLIC_ROUTES are the coordinator's shared change)."""
    from fastapi import FastAPI
    from app.api.v1.endpoints import esign_connect_public
    app = FastAPI()
    app.include_router(esign_connect_public.router, prefix="/api/v1/public/esign")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


async def _configure(c, provider):
    from tests.provider_sim.esign_app import sim_esign_settings
    secrets = ({"private_key_pem": PRIV, "connect_hmac_key": "sim-connect-hmac-key"} if provider == "DOCUSIGN"
               else {"client_secret": "sim-adobe-secret", "refresh_token": "sim-adobe-refresh"})
    r = await c.put(f"/api/v1/esign/providers/{provider}", json={"settings": sim_esign_settings(BASE)[provider], "secrets": secrets})
    assert r.status_code == 200, r.text
    return r.json()


def _send_body(provider, qid):
    return {"provider": provider, "source_type": "QUOTATION", "source_id": str(qid), "signer_name": "Amina Duka",
            "signer_email": "amina@example.com", "expire_days": 14}


@DB
@pytest.mark.asyncio
async def test_docusign_flow_rbac_completion_evidence_and_webhooks(sim):
    w = await _world()
    async with _client() as ca, _client() as cr, _client() as co, _hooks() as hooks:
        await _login(ca, w["admin"])
        await _login(cr, w["rep"])
        await _login(co, w["outsider"])
        assert (await cr.put("/api/v1/esign/providers/DOCUSIGN", json={"settings": {}})).status_code == 403
        cfg = await _configure(ca, "DOCUSIGN")
        assert cfg["ready"] and cfg["mode"] == "SIMULATED" and cfg["secrets_set"] == {"private_key_pem": True, "connect_hmac_key": True}
        assert "PRIVATE KEY" not in json.dumps(cfg)
        rd = {p["provider"]: p for p in (await co.get("/api/v1/esign/providers")).json()}
        assert rd["LOCAL"]["mode"] == "LOCAL" and "not provider-certified" in rd["LOCAL"]["label"]
        settings_view = (await co.get("/api/v1/cpq/settings")).json()["signature_providers"]
        assert settings_view["DOCUSIGN"] == "READY (SIMULATED)" and settings_view["LOCAL"] == "READY"

        draft = await _quote(w, "DRAFT")
        assert (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", draft))).status_code == 409
        qid = await _quote(w)
        assert (await co.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", qid))).status_code == 403
        sim["delay"] = 3600
        r = await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", qid))
        assert r.status_code == 201, r.text
        env = r.json()
        assert env["status"] == "SENT" and env["mode"] == "SIMULATED" and env["provider_ref"] and not env["provider_certified"]
        assert [t["status"] for t in env["timeline"]] == ["CLAIMED", "SENT"]
        assert (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", qid))).status_code == 409   # one open request
        snap = await cr.get(f"/api/v1/esign/providers/envelopes/{env['id']}/files/snapshot")
        assert snap.status_code == 200 and snap.content.startswith(b"%PDF") and snap.headers["x-content-sha256"] == env["snapshot_sha256"]
        assert env["source_fingerprint"].encode() in snap.content and b"POVU AllClean 1 L" in snap.content
        assert (await cr.get(f"/api/v1/esign/providers/envelopes/{env['id']}/files/signed")).status_code == 404   # not signed yet

        # the simulator completes; the signed callback only triggers a read-back
        sim["envelopes"][env["provider_ref"]]["delay"] = 0.0
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_sim_app_of(sim)), base_url=BASE) as s:
            await s.post("/_control/tick")
            cbs = (await s.get("/_control/outbox")).json()["callbacks"]
        done = next(c for c in cbs if b"envelope-completed" in base64.b64decode(c["body_b64"]))
        body, headers = base64.b64decode(done["body_b64"]), done["headers"]
        bad = await hooks.post("/api/v1/public/esign/docusign", content=body.replace(b"completed", b"declined"), headers=headers)
        assert bad.status_code == 401                                          # tampered body
        assert (await hooks.post("/api/v1/public/esign/docusign", content=body,
                                 headers={**headers, "X-DocuSign-Signature-1": "AAAA"})).status_code == 401
        ok = await hooks.post("/api/v1/public/esign/docusign", content=body, headers=headers)
        assert ok.status_code == 200 and ok.json()["status"] == "COMPLETED", ok.text
        again = await hooks.post("/api/v1/public/esign/docusign", content=body, headers=headers)
        assert again.json() == {"duplicate": True}                             # replay: acted on once

        got = (await cr.get(f"/api/v1/esign/providers/envelopes/{env['id']}")).json()
        assert got["status"] == "COMPLETED" and got["provider_certified"] is False
        assert got["evidence_label"] == "Simulated provider evidence — not certified" and "accepted" in got["erp_applied"]
        assert await _quote_status(qid) == "ACCEPTED"
        for kind, key in (("signed", "signed_sha256"), ("evidence", "evidence_sha256")):
            f = await cr.get(f"/api/v1/esign/providers/envelopes/{env['id']}/files/{kind}")
            assert f.status_code == 200 and f.headers["x-content-sha256"] == got[key] and f.headers["x-evidence-status"] == "simulated"
        assert (await cr.post(f"/api/v1/esign/providers/envelopes/{env['id']}/cancel", json={"reason": "too late"})).status_code == 403


def _sim_app_of(st):
    """The simulator app whose state is ``st`` (the transport installed by the fixture)."""
    from app.core import provider_http
    return provider_http._test_transport.app


@DB
@pytest.mark.asyncio
async def test_completed_requires_signed_document_and_change_after_send_invalidates(sim):
    from app.db.session import AsyncSessionLocal
    from app.models.quotation import QuotationLine
    from sqlalchemy import select
    w = await _world()
    async with _client() as ca, _client() as cr:
        await _login(ca, w["admin"])
        await _login(cr, w["rep"])
        await _configure(ca, "DOCUSIGN")
        sim.update(delay=0.0)
        qid = await _quote(w)
        env = (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", qid))).json()
        sim["faults"]["ds_docs"] = ["nopdf", "nopdf"]
        r = (await cr.post(f"/api/v1/esign/providers/envelopes/{env['id']}/reconcile")).json()
        assert r["status"] != "COMPLETED" and "not PDFs" in r["error"] and r["signed_sha256"] is None
        assert await _quote_status(qid) == "SENT"
        r = (await cr.post(f"/api/v1/esign/providers/envelopes/{env['id']}/reconcile")).json()
        assert r["status"] == "COMPLETED" and r["signed_sha256"]

        # a quotation changed after it was sent: the request is void, the provider envelope voided, nothing accepted
        sim.update(delay=3600)
        q2 = await _quote(w)
        env2 = (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", q2))).json()
        async with AsyncSessionLocal() as db:
            ln = (await db.execute(select(QuotationLine).where(QuotationLine.quote_id == q2))).scalar_one()
            ln.unit_price = Decimal("99")
            await db.commit()
        r = (await cr.post(f"/api/v1/esign/providers/envelopes/{env2['id']}/reconcile")).json()
        assert r["status"] == "INVALIDATED" and "changed" in r["error"]
        assert sim["envelopes"][env2["provider_ref"]]["status"] == "voided" and await _quote_status(q2) == "SENT"

        # a create whose answer was lost: UNKNOWN, then reconciled by our reference (never sent twice)
        sim["faults"]["ds_create"] = ["lost"]
        q3 = await _quote(w)
        env3 = (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", q3))).json()
        assert env3["status"] == "UNKNOWN" and env3["provider_ref"] is None
        assert (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", q3))).status_code == 409
        r = (await cr.post(f"/api/v1/esign/providers/envelopes/{env3['id']}/reconcile")).json()
        assert r["status"] == "SENT" and r["provider_ref"] and len(sim["envelopes"]) == 3


@DB
@pytest.mark.asyncio
async def test_adobe_flow_idempotency_client_id_decline_expire_cancel(sim):
    w = await _world()
    async with _client() as ca, _client() as cr, _hooks() as hooks:
        await _login(ca, w["admin"])
        await _login(cr, w["rep"])
        await _configure(ca, "ADOBE_SIGN")
        ok = await hooks.get("/api/v1/public/esign/adobe-sign", headers={"X-AdobeSign-ClientId": "sim-adobe-client"})
        assert ok.status_code == 200 and ok.headers["x-adobesign-clientid"] == "sim-adobe-client" and ok.json() == {"xAdobeSignClientId": "sim-adobe-client"}
        assert (await hooks.get("/api/v1/public/esign/adobe-sign", headers={"X-AdobeSign-ClientId": "someone-else"})).status_code == 401

        sim.update(delay=3600, outcome="decline")
        qid = await _quote(w)
        key = {"Idempotency-Key": f"povu-ui-{uuid.uuid4().hex[:12]}"}
        a = (await cr.post("/api/v1/esign/providers/send", json=_send_body("ADOBE_SIGN", qid), headers=key)).json()
        b = (await cr.post("/api/v1/esign/providers/send", json=_send_body("ADOBE_SIGN", qid), headers=key)).json()
        assert a["id"] == b["id"] and a["status"] == "SENT" and len(sim["agreements"]) == 1
        sim["agreements"][a["provider_ref"]]["delay"] = 0.0
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_sim_app_of(sim)), base_url=BASE) as s:
            await s.post("/_control/tick")
            cb = (await s.get("/_control/outbox")).json()["callbacks"][0]
        body = base64.b64decode(cb["body_b64"])
        assert (await hooks.post("/api/v1/public/esign/adobe-sign", content=body, headers={"X-AdobeSign-ClientId": "forged"})).status_code == 401
        r = await hooks.post("/api/v1/public/esign/adobe-sign", content=body, headers=cb["headers"])
        assert r.status_code == 200 and r.json()["status"] == "DECLINED" and r.headers["x-adobesign-clientid"] == "sim-adobe-client"
        assert (await hooks.post("/api/v1/public/esign/adobe-sign", content=body, headers=cb["headers"])).json()["duplicate"] is True
        assert await _quote_status(qid) == "SENT"                            # a decline accepts nothing

        sim.update(delay=0.0, outcome="expire")
        q2 = await _quote(w)
        e2 = (await cr.post("/api/v1/esign/providers/send", json=_send_body("ADOBE_SIGN", q2))).json()
        assert (await cr.post(f"/api/v1/esign/providers/envelopes/{e2['id']}/reconcile")).json()["status"] == "EXPIRED"

        sim.update(delay=3600, outcome="complete")
        q3 = await _quote(w)
        e3 = (await cr.post("/api/v1/esign/providers/send", json=_send_body("ADOBE_SIGN", q3))).json()
        assert (await cr.post(f"/api/v1/esign/providers/envelopes/{e3['id']}/cancel", json={"reason": "wrong signer"})).status_code == 403
        c = await ca.post(f"/api/v1/esign/providers/envelopes/{e3['id']}/cancel", json={"reason": "wrong signer"})
        assert c.status_code == 200 and c.json()["status"] == "CANCELLED"
        assert sim["agreements"][e3["provider_ref"]]["status"] == "CANCELLED"
        lst = (await cr.get("/api/v1/esign/providers/envelopes", params={"source_type": "QUOTATION", "source_id": str(q3)})).json()
        assert [x["status"] for x in lst] == ["CANCELLED"] and lst[0]["timeline"][-1]["via"] == "user"


@DB
@pytest.mark.asyncio
async def test_envelope_reads_and_contract_sends_respect_record_scope(sim):
    """Review fix: esign.view alone does not open envelopes of quotations/contracts outside the caller's scope."""
    from app.db.session import AsyncSessionLocal
    from app.models.contracts import Contract
    w = await _world()
    async with AsyncSessionLocal() as db:
        blind = (await _user(db, ("esign.view", "esign.request", "esign.cancel", "procurement.edit"), "blind")).username
        con = Contract(contract_code=f"CT-T009-{uuid.uuid4().hex[:6]}", contract_name="POVU AllClean supply", contract_type="SUPPLY",
                       party_type="CUSTOMER", party_id=w["customer"], start_date=date.today(), status="APPROVED", currency="KES",
                       notes="Supply of POVU AllClean 1 L")
        db.add(con)
        await db.commit()
    async with _client() as ca, _client() as cr, _client() as cb:
        await _login(ca, w["admin"])
        await _login(cr, w["rep"])
        await _login(cb, blind)
        await _configure(ca, "DOCUSIGN")
        sim.update(delay=3600)
        qid = await _quote(w)
        env = (await cr.post("/api/v1/esign/providers/send", json=_send_body("DOCUSIGN", qid))).json()
        base = f"/api/v1/esign/providers/envelopes/{env['id']}"
        # out of scope (no sales view of the quotation): nothing listed, 404 on get / files / reconcile / cancel
        assert env["id"] not in [e["id"] for e in (await cb.get("/api/v1/esign/providers/envelopes")).json()]
        for path in ("", "/files/snapshot"):
            assert (await cb.get(base + path)).status_code == 404
        assert (await cb.post(base + "/reconcile")).status_code == 404
        assert (await cb.post(base + "/cancel", json={"reason": "not mine"})).status_code == 404
        # in scope: the rep; and the e-signature admin sees all
        assert env["id"] in [e["id"] for e in (await cr.get("/api/v1/esign/providers/envelopes")).json()]
        assert (await cr.get(base)).status_code == 200
        f = await cr.get(base + "/files/snapshot")
        assert f.status_code == 200 and f.content.startswith(b"%PDF")
        assert env["id"] in [e["id"] for e in (await ca.get("/api/v1/esign/providers/envelopes")).json()]
        assert (await ca.get(base + "/files/snapshot")).status_code == 200
        # contract send: an edit right without sight of the contract is refused; the rep (sales view + edit) may send
        body = {**_send_body("DOCUSIGN", con.id), "source_type": "CONTRACT"}
        assert (await cb.post("/api/v1/esign/providers/send", json=body)).status_code == 403
        sent = await cr.post("/api/v1/esign/providers/send", json=body)
        assert sent.status_code == 201 and sent.json()["status"] == "SENT", sent.text
        assert sent.json()["id"] not in [e["id"] for e in (await cb.get("/api/v1/esign/providers/envelopes")).json()]
