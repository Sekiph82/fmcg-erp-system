from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from app.core.deps import get_current_active_superuser
from app.models.webhook import AuthType
from app.schemas.webhook import (
    InboundEndpointCreate,
    InboundEndpointOut,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionUpdate,
)
from app.services import webhook_service
from app.api.v1.endpoints import webhooks
from app.core.config import Settings


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Database:
    def __init__(self, values):
        self.values = iter(values)
        self.added = []
        self.committed = False
        self.refreshed = []

    async def execute(self, statement):
        return _Result(next(self.values))

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        self.refreshed.append(value)


def test_hmac_secrets_are_validated_and_outputs_never_include_credentials():
    with pytest.raises(ValueError, match="at least 32"):
        SubscriptionCreate(
            name="short",
            endpoint_url="https://example.invalid/hook",
            auth_type=AuthType.HMAC,
            secret_key="too-short",
        )
    with pytest.raises(ValueError, match="at least 32"):
        InboundEndpointCreate(
            name="short",
            endpoint_path="short",
            auth_type=AuthType.HMAC,
            secret_key="too-short",
        )

    assert "secret_key" not in SubscriptionOut.model_fields
    assert "secret_key" not in InboundEndpointOut.model_fields
    response = SubscriptionOut.model_validate(
        SimpleNamespace(
            id=uuid4(),
            name="synthetic",
            endpoint_url="https://example.invalid/hook",
            http_method="POST",
            headers={"Authorization": "credential", "X-Trace": "value"},
            auth_type=AuthType.HMAC,
            secret_version=2,
            previous_secret_expires_at=None,
            filter_expression=None,
            event_codes=None,
            transform_template=None,
            max_retries=5,
            timeout_seconds=30,
            active_flag=True,
            created_at=datetime.now(timezone.utc),
        )
    )
    assert response.model_dump()["headers"] == {
        "Authorization": "[REDACTED]",
        "X-Trace": "[REDACTED]",
    }


def test_secret_envelope_round_trips_and_legacy_rows_remain_readable():
    plaintext = "s" * 40
    stored = webhook_service._store_webhook_secret(plaintext)
    assert stored.startswith(webhook_service.WEBHOOK_SECRET_ENVELOPE_PREFIX)
    assert stored != plaintext
    assert webhook_service._read_webhook_secret(stored) == plaintext
    assert webhook_service._read_webhook_secret(plaintext) == plaintext
    assert webhook_service._store_webhook_secret(stored) == stored


def test_dedicated_encryption_key_survives_application_auth_key_rotation(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "WEBHOOK_SECRET_ENCRYPTION_KEY", "w" * 48)
    monkeypatch.setattr(settings, "SECRET_KEY", "first-auth-key")
    stored = webhook_service._store_webhook_secret("private-webhook-secret")
    assert stored.startswith("enc:v2:")
    monkeypatch.setattr(settings, "SECRET_KEY", "second-auth-key")
    assert webhook_service._read_webhook_secret(stored) == "private-webhook-secret"


@pytest.mark.parametrize("weak_key", ["a" * 64, "password" * 8])
def test_production_rejects_weak_dedicated_webhook_encryption_keys(weak_key):
    with pytest.raises(ValueError, match="WEBHOOK_SECRET_ENCRYPTION_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="A7f0B6d2C9e5H1k8M4q0T6w3Z9c5F2j7N1r8V4x0P6s3D9g5K2m7Q1t8W4y0B6e3",
            WEBHOOK_SECRET_ENCRYPTION_KEY=weak_key,
        )


def test_inbound_hmac_accepts_current_and_grace_secret_but_enforces_timestamp_window():
    current_secret = "c" * 40
    previous_secret = "p" * 40
    now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    endpoint = SimpleNamespace(
        auth_type=AuthType.HMAC,
        secret_key=webhook_service._store_webhook_secret(current_secret),
        previous_secret_key=webhook_service._store_webhook_secret(previous_secret),
        previous_secret_expires_at=now + timedelta(hours=1),
        secret_version=2,
    )
    body = b'{"event":"test"}'
    timestamp = str(int(now.timestamp()))

    assert webhook_service.verify_inbound_signature(
        endpoint, body, webhook_service._sign_payload(current_secret, body, timestamp), timestamp, now
    )
    assert webhook_service.verify_inbound_signature(
        endpoint, body, webhook_service._sign_payload(previous_secret, body, timestamp), timestamp, now
    )
    assert not webhook_service.verify_inbound_signature(
        endpoint, body, webhook_service._sign_payload(current_secret, body, timestamp), str(int(now.timestamp()) - 301), now
    )
    assert not webhook_service.verify_inbound_signature(
        endpoint, body, webhook_service._sign_payload(current_secret, body, timestamp), "not-a-timestamp", now
    )
    assert not webhook_service.verify_inbound_signature(
        endpoint, body, "sha256=irrelevant", "9" * 5000, now
    )
    assert not webhook_service.verify_inbound_signature(
        endpoint, body, webhook_service._sign_payload(previous_secret, body, timestamp), timestamp, now + timedelta(hours=2)
    )


def test_legacy_signature_compatibility_is_timing_safe_and_unsupported_auth_fails_closed():
    secret = "l" * 40
    endpoint = SimpleNamespace(
        auth_type=AuthType.HMAC,
        secret_key=secret,
        previous_secret_key=None,
        previous_secret_expires_at=None,
        secret_version=1,
    )
    body = b"legacy body"
    legacy = webhook_service.hmac.new(secret.encode(), body, webhook_service.hashlib.sha256).hexdigest()
    assert webhook_service.verify_inbound_signature(endpoint, body, f"sha256={legacy}")
    assert not webhook_service.verify_inbound_signature(endpoint, body, "sha256=bad")
    endpoint.auth_type = AuthType.BASIC
    assert not webhook_service.verify_inbound_signature(endpoint, body, legacy)


def test_reserved_custom_headers_cannot_override_signature_or_delivery_identity():
    headers = {"X-Webhook-Timestamp": "server-value", "Authorization": "server-auth"}
    webhook_service._apply_custom_headers(
        headers,
        {
            "x-webhook-timestamp": "attacker-value",
            "authorization": "attacker-auth",
            "X-Custom-Trace": "trace-1",
        },
    )
    assert headers["X-Webhook-Timestamp"] == "server-value"
    assert headers["Authorization"] == "server-auth"
    assert headers["X-Custom-Trace"] == "trace-1"
    response = webhook_service._redact_auth_values(
        "Authorization: server-auth; signature: sha256=private",
        {"Authorization": "server-auth", "X-Webhook-Signature": "sha256=private"},
    )
    assert "server-auth" not in response
    assert "sha256=private" not in response
    echoed_custom_credential = webhook_service._redact_auth_values(
        "echoed token x-api-private-123",
        {"X-API-Key": "x-api-private-123"},
        {"X-API-Key": "x-api-private-123"},
    )
    assert "x-api-private-123" not in echoed_custom_credential
    assert "[REDACTED]" in echoed_custom_credential


def test_webhook_configuration_and_rotation_routes_require_superuser():
    guarded = {
        "/subscriptions",
        "/subscriptions/{sub_id}",
        "/subscriptions/{sub_id}/test",
        "/subscriptions/{sub_id}/rotate-secret",
        "/inbound-endpoints",
        "/inbound-endpoints/{endpoint_id}/rotate-secret",
    }
    routes = {
        route.path: route
        for route in webhooks.router.routes
        if isinstance(route, APIRoute) and route.path in guarded
    }
    assert set(routes) == guarded
    for route in routes.values():
        assert any(
            dependency.call is get_current_active_superuser
            for dependency in route.dependant.dependencies
        ), route.path


@pytest.mark.asyncio
async def test_rotation_encrypts_replacement_audits_without_secret_and_returns_new_value_once(monkeypatch):
    old_secret = "o" * 40
    target = SimpleNamespace(
        id=uuid4(),
        name="synthetic HMAC endpoint",
        auth_type=AuthType.HMAC,
        secret_key=webhook_service._store_webhook_secret(old_secret),
        previous_secret_key=None,
        previous_secret_expires_at=None,
        secret_version=1,
    )
    actor = SimpleNamespace(id=None, email="synthetic@example.invalid", full_name="Synthetic admin")
    db = _Database([target])
    new_secret = "n" * 43
    monkeypatch.setattr(webhook_service.secrets, "token_urlsafe", lambda _size: new_secret)

    result = await webhook_service.rotate_subscription_secret(db, target.id, actor)

    assert result["secret_key"] == new_secret
    assert result["secret_version"] == 2
    assert result["previous_secret_expires_at"] > datetime.now(timezone.utc)
    assert webhook_service._read_webhook_secret(target.secret_key) == new_secret
    assert webhook_service._read_webhook_secret(target.previous_secret_key) == old_secret
    assert target.secret_key != new_secret
    assert db.committed
    audit = next(item for item in db.added if item.event_type == "WEBHOOK_SECRET_ROTATED")
    assert audit.details["previous_secret_expires_at"]
    assert new_secret not in str(audit.details)
    assert old_secret not in str(audit.before_value)
    assert new_secret not in str(audit.after_value)

    second_db = _Database([target])
    with pytest.raises(webhook_service.WebhookSecretRotationError, match="grace period"):
        await webhook_service.rotate_subscription_secret(second_db, target.id, actor)
    assert target.secret_version == 2
    assert not second_db.committed


@pytest.mark.asyncio
async def test_rotation_refuses_non_hmac_secrets_without_mutating_them():
    target = SimpleNamespace(id=uuid4(), auth_type=AuthType.BEARER, secret_key="legacy-token")
    db = _Database([target])

    with pytest.raises(webhook_service.WebhookSecretRotationError):
        await webhook_service.rotate_subscription_secret(db, target.id, actor=None)

    assert target.secret_key == "legacy-token"
    assert not db.committed
    assert not db.added


@pytest.mark.asyncio
async def test_switch_to_hmac_rejects_short_existing_basic_secret():
    target = SimpleNamespace(
        id=uuid4(),
        auth_type=AuthType.BASIC,
        secret_key="legacy-short-token",
        auth_user="synthetic-user",
        secret_version=1,
        previous_secret_key=None,
        previous_secret_expires_at=None,
    )
    db = _Database([target])

    with pytest.raises(webhook_service.WebhookSecretRotationError, match="at least 32"):
        await webhook_service.update_subscription(
            db,
            target.id,
            SubscriptionUpdate(auth_type=AuthType.HMAC),
            actor=None,
        )
    assert target.auth_type == AuthType.BASIC
    assert not db.committed
