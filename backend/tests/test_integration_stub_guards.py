"""Stub integrations never report fabricated success; bank and IoT routes enforce permissions."""
import hashlib
import hmac
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.bank_api import router as bank_api_router
from app.api.v1.endpoints.bank_reconciliation import router as bank_rec_router
from app.api.v1.endpoints.integrations import router as integrations_router
from app.core import callback_security, integration_capabilities
from app.core.deps import get_current_user, get_db
from app.core.module_registry import PUBLIC_ROUTES


def _user(*codes):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(id=uuid.uuid4(), is_superuser=False, full_name="u", username="u", email="u@example.invalid",
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


class _NoDB:
    """Any database use fails the test: guarded paths must reject before touching data."""

    def __getattr__(self, name):
        raise AssertionError(f"database used: {name}")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(integrations_router, prefix="/integrations")
    app.include_router(bank_api_router, prefix="/bank-api")
    app.include_router(bank_rec_router, prefix="/bank-reconciliation")

    async def _db():
        yield _NoDB()

    app.dependency_overrides[get_db] = _db

    def as_(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    return as_


def test_crm_and_ecommerce_sync_refuse_instead_of_fabricating(client):
    c = client(_user("integrations.edit"))
    crm = c.post("/integrations/crm/sync/customers", json={"direction": "PUSH"})
    assert crm.status_code == 501 and crm.json()["detail"]["status"] == "STUB_ONLY"
    orders = c.post("/integrations/ecommerce/import-orders", json={"platform": "SHOPIFY"})
    assert orders.status_code == 501
    inventory = c.post("/integrations/ecommerce/sync-inventory", params={"platform": "WOOCOMMERCE"})
    assert inventory.status_code == 501


def test_bank_routes_need_finance_permissions(client):
    assert client(_user()).get("/bank-reconciliation/accounts").status_code == 403
    assert client(_user()).get("/bank-api/connections").status_code == 403
    assert client(_user("finance.view")).post("/bank-api/connections", json={}).status_code == 403


def test_bank_mock_sync_is_blocked_in_production(client, monkeypatch):
    monkeypatch.setattr(integration_capabilities.settings, "ENVIRONMENT", "production")
    r = client(_user("finance.view", "finance.edit")).post(f"/bank-api/connections/{uuid.uuid4()}/sync")
    assert r.status_code == 503 and "simulated" in r.json()["detail"]


def test_legacy_iot_event_ingest_needs_permission(client):
    r = client(_user("integrations.view")).post("/integrations/iot/events", json={"machine_id": "M1", "event_type": "RUN"})
    assert r.status_code == 403


# ── provider callback verification and scoped finance access ────────────────

def _callback_app():
    from fastapi import Depends

    app = FastAPI()

    @app.post("/mpesa", dependencies=[Depends(callback_security.verify_mpesa_callback)])
    async def mpesa():
        return {"ok": True}

    @app.post("/meta", dependencies=[Depends(callback_security.verify_meta_signature)])
    async def meta(request_body: dict):
        return request_body

    return TestClient(app)


def test_mpesa_callback_requires_the_shared_token(monkeypatch):
    c = _callback_app()
    monkeypatch.setattr(callback_security.settings, "MPESA_CALLBACK_SECRET", "s3cret-callback-token")
    assert c.post("/mpesa").status_code == 403
    assert c.post("/mpesa", params={"token": "wrong"}).status_code == 403
    assert c.post("/mpesa", params={"token": "s3cret-callback-token"}).status_code == 200
    monkeypatch.setattr(callback_security.settings, "MPESA_CALLBACK_SECRET", "")
    monkeypatch.setattr(callback_security.settings, "ENVIRONMENT", "production")
    assert c.post("/mpesa").status_code == 503


def test_whatsapp_webhook_requires_a_valid_meta_signature(monkeypatch):
    c = _callback_app()
    monkeypatch.setattr(callback_security.settings, "WHATSAPP_APP_SECRET", "meta-app-secret")
    body = b'{"entry": []}'
    good = "sha256=" + hmac.new(b"meta-app-secret", body, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json"}
    assert c.post("/meta", content=body, headers=headers).status_code == 403
    assert c.post("/meta", content=body, headers=headers | {"X-Hub-Signature-256": "sha256=00"}).status_code == 403
    ok = c.post("/meta", content=body, headers=headers | {"X-Hub-Signature-256": good})
    assert ok.status_code == 200 and ok.json() == {"entry": []}  # body still readable after verification


def test_scoped_finance_roles_reach_bank_routes(client):
    # Only the permission guard is exercised; the handler's DB access fails afterwards on purpose.
    with pytest.raises(AssertionError, match="database used"):
        client(_user("finance.view_own_scope")).get("/bank-reconciliation/accounts")
    assert client(_user("finance.view_all")).post("/bank-api/connections", json={}).status_code in {403, 422}


def test_supplier_password_reset_is_not_public():
    assert ("/supplier-portal/auth/reset-password", "POST") not in PUBLIC_ROUTES
