"""M47.S01.T003 surface-audit fixes (no database needed).

/metrics is not public and labels requests by route template (customer link tokens never appear); approvals need the
step's role and a second person; chatter needs module rights and ignores a body-supplied author; JSON bodies are capped;
production refuses a weak initial admin password.
"""
from types import SimpleNamespace
import uuid

import httpx
import pytest


def _client(host="127.0.0.1"):
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(host, 1234)), base_url="http://erp.test")


@pytest.mark.asyncio
async def test_metrics_private_and_token_free(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    async with _client("203.0.113.9") as remote:
        assert (await remote.get("/metrics")).status_code == 404
        await remote.get("/api/v1/public/docs/SECRET-TOKEN-abc123")       # a token URL
    async with _client() as local:
        body = (await local.get("/metrics")).json()
    assert not any("SECRET-TOKEN" in k for k in body["requests_by_route"])
    monkeypatch.setattr(settings, "METRICS_TOKEN", "m-token-123")
    async with _client("203.0.113.9") as remote:
        assert (await remote.get("/metrics")).status_code == 404
        assert (await remote.get("/metrics", headers={"Authorization": "Bearer m-token-123"})).status_code == 200


def test_approval_decider_rules():
    from fastapi import HTTPException
    from app.services.approval_service import ApprovalStatus, check_decider
    requester = uuid.uuid4()
    req = SimpleNamespace(current_level=1, requested_by_id=requester,
                          steps=[SimpleNamespace(level=1, status=ApprovalStatus.PENDING, required_role="Finance Manager")])
    role = lambda n: SimpleNamespace(name=n, is_active=True)  # noqa: E731
    with pytest.raises(HTTPException) as e:
        check_decider(req, SimpleNamespace(id=uuid.uuid4(), is_superuser=False, roles=[role("Sales Rep")]))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException):
        check_decider(req, SimpleNamespace(id=requester, is_superuser=False, roles=[role("finance manager")]))   # own request
    check_decider(req, SimpleNamespace(id=uuid.uuid4(), is_superuser=False, roles=[role("finance manager")]))
    check_decider(req, None)                                              # internal callers that already checked


def test_chatter_module_scope():
    from app.api.v1.endpoints.chatter import _may
    rep = SimpleNamespace(is_superuser=False, access_scopes=[],
                          roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                                                 permissions=[SimpleNamespace(code="crm.view", is_active=True)])])
    assert _may(rep, "crm_record") and _may(rep, "free_note")
    assert not _may(rep, "invoice") and not _may(rep, "employee")


@pytest.mark.asyncio
async def test_json_body_cap():
    from app.core import input_sanitizer
    async with _client() as c:
        big = b'{"x":"' + b"a" * (input_sanitizer.JSON_BODY_MAX_BYTES + 10) + b'"}'
        r = await c.post("/api/v1/public/chat/sessions", content=big, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_production_refuses_weak_admin_password():
    from app.core.config import Settings
    from tests.test_hardening import _PROD_BASE
    with pytest.raises(ValueError, match="INITIAL_ADMIN_PASSWORD"):
        Settings(**{**_PROD_BASE, "INITIAL_ADMIN_PASSWORD": "Admin1234!"})
    Settings(**{**_PROD_BASE, "INITIAL_ADMIN_PASSWORD": "Unique-Povu-Pass-2026"})
