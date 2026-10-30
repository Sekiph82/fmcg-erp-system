from __future__ import annotations

import time
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.v1.endpoints import webhooks
from app.core.config import settings
from app.core.deps import get_current_active_superuser, get_current_user
from app.db.session import get_db
from app.models.webhook import AuthType
from app.schemas.webhook import InboundEndpointCreate
from app.services import webhook_service


PUBLIC_CALLBACK = "/inbound/{endpoint_path:path}"


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(webhooks.router, prefix="/webhooks")

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db
    return app


def test_every_internal_event_api_route_requires_superuser_except_signed_partner_callback():
    routes = [route for route in webhooks.router.routes if isinstance(route, APIRoute)]
    assert any(route.path == PUBLIC_CALLBACK for route in routes)

    unguarded = []
    for route in routes:
        if route.path == PUBLIC_CALLBACK:
            assert all(
                dependency.call is not get_current_active_superuser
                for dependency in route.dependant.dependencies
            )
            continue
        if not any(
            dependency.call is get_current_active_superuser
            for dependency in route.dependant.dependencies
        ):
            unguarded.append(f"{','.join(sorted(route.methods or []))} {route.path}")

    assert not unguarded, "Internal event APIs missing superuser guard: " + "; ".join(unguarded)


def test_internal_event_api_returns_401_without_session_and_403_for_non_superuser():
    app = _app()
    with TestClient(app) as client:
        unauthenticated = client.get("/webhooks/dashboard")
    assert unauthenticated.status_code == 401

    app = _app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_superuser=False)
    with TestClient(app) as client:
        forbidden = client.get("/webhooks/events")
    assert forbidden.status_code == 403


def test_event_publish_uses_authenticated_actor_instead_of_client_supplied_actor(monkeypatch):
    actor_id = uuid4()
    actor = SimpleNamespace(id=actor_id, is_superuser=True)
    observed = {}
    event = SimpleNamespace(
        id=uuid4(),
        event_code="inventory.adjusted",
        module="inventory",
        reference_type=None,
        reference_id=None,
        payload={"id": "synthetic-event", "data": {"quantity": 1}},
        actor_id=str(actor_id),
        partition_key=None,
        created_at=datetime.now(timezone.utc),
    )

    async def fake_publish_event(_db, *_args, **kwargs):
        observed.update(kwargs)
        return event

    monkeypatch.setattr(webhooks.svc, "publish_event", fake_publish_event)
    app = _app()
    app.dependency_overrides[get_current_active_superuser] = lambda: actor

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/events/publish",
            json={
                "event_code": "inventory.adjusted",
                "payload": {"quantity": 1},
                "actor_id": "impersonated-owner",
            },
        )

    assert response.status_code == 201
    assert observed["actor_id"] == str(actor_id)
    assert observed["actor_id"] != "impersonated-owner"


def test_production_rejects_inbound_endpoint_without_authentication(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    try:
        InboundEndpointCreate(name="synthetic", endpoint_path="synthetic")
    except ValueError as exc:
        assert "require authentication in production" in str(exc)
    else:
        raise AssertionError("Production must reject an unauthenticated inbound endpoint")


def test_partner_hmac_callback_works_without_an_erp_session(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    secret = "synthetic-partner-secret-with-at-least-32-chars"
    endpoint = SimpleNamespace(
        auth_type=AuthType.HMAC,
        secret_key=secret,
        previous_secret_key=None,
        previous_secret_expires_at=None,
        secret_version=1,
        handler_module="synthetic_partner",
        receive_count=0,
        last_received_at=None,
    )
    db = SimpleNamespace(commit=_async_noop)

    async def get_endpoint(_db, endpoint_path):
        assert endpoint_path == "synthetic"
        return endpoint

    async def stage_event(*_args, **_kwargs):
        return None

    monkeypatch.setattr(webhooks.svc, "get_inbound_endpoint_by_path", get_endpoint)
    monkeypatch.setattr(webhooks.svc, "stage_event", stage_event)
    app = _app()

    async def fake_db():
        yield db

    app.dependency_overrides[get_db] = fake_db
    body = b'{"event":"synthetic"}'
    timestamp = str(int(time.time()))
    signature = webhook_service._sign_payload(secret, body, timestamp)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/inbound/synthetic",
            content=body,
            headers={
                "X-Webhook-Signature": signature,
                "X-Webhook-Timestamp": timestamp,
                "Idempotency-Key": "synthetic-delivery-1",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"received": True, "endpoint": "synthetic"}
    assert endpoint.receive_count == 1


async def _async_noop():
    return None
