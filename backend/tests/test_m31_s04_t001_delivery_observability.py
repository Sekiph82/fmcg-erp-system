from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.observability import JsonFormatter, metrics_snapshot, record_webhook_delivery
from app.models.webhook import AuthType, DeliveryStatus, HttpMethod
from app.services import webhook_service


def test_delivery_metrics_have_bounded_outcomes_and_cumulative_latency_buckets():
    before = metrics_snapshot()
    record_webhook_delivery("sent", 80)
    record_webhook_delivery("retrying", 1400)
    record_webhook_delivery("failed")
    after = metrics_snapshot()

    assert after["webhook_delivery_attempts_total"]["sent"] == before["webhook_delivery_attempts_total"].get("sent", 0) + 1
    assert after["webhook_delivery_attempts_total"]["retrying"] == before["webhook_delivery_attempts_total"].get("retrying", 0) + 1
    assert after["webhook_delivery_attempts_total"]["failed"] == before["webhook_delivery_attempts_total"].get("failed", 0) + 1
    assert after["webhook_delivery_duration_ms"]["count"] == before["webhook_delivery_duration_ms"]["count"] + 2
    assert after["webhook_delivery_duration_ms"]["buckets"]["le_100_ms"] == before["webhook_delivery_duration_ms"]["buckets"]["le_100_ms"] + 1
    assert after["webhook_delivery_duration_ms"]["buckets"]["le_2500_ms"] == before["webhook_delivery_duration_ms"]["buckets"]["le_2500_ms"] + 2
    with pytest.raises(ValueError, match="outcome"):
        record_webhook_delivery("arbitrary-customer-label", 1)


def test_json_log_formatter_includes_delivery_trace_fields_without_response_data():
    record = logging.LogRecord(
        "app.services.webhook_service",
        logging.INFO,
        __file__,
        42,
        "Webhook delivery attempt completed",
        (),
        None,
    )
    record.event_id = "event-1"
    record.delivery_id = "delivery-1"
    record.subscription_id = "subscription-1"
    record.attempt_no = 2
    record.correlation_id = "workflow-1"
    record.causation_id = "cause-1"
    record.outcome = "sent"
    record.response_status = 204
    record.duration_ms = 23

    formatted = json.loads(JsonFormatter().format(record))

    assert formatted["event_id"] == "event-1"
    assert formatted["delivery_id"] == "delivery-1"
    assert formatted["correlation_id"] == "workflow-1"
    assert formatted["causation_id"] == "cause-1"
    assert formatted["outcome"] == "sent"
    assert "response_body" not in formatted


@pytest.mark.asyncio
async def test_delivery_propagates_trace_ids_and_records_safe_response(monkeypatch, caplog):
    event_id = uuid4()
    attempt_id = uuid4()
    subscription_id = uuid4()
    envelope = {
        "id": str(event_id),
        "type": "inventory.adjusted",
        "module": "inventory",
        "schema_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "actor_id": None,
        "correlation_id": "workflow-trace-1",
        "causation_id": "parent-event-1",
        "reference": {"type": "inventory", "id": "synthetic-1"},
        "data": {"quantity": 4},
    }
    event = SimpleNamespace(
        id=event_id,
        event_code="inventory.adjusted",
        module="inventory",
        payload=envelope,
        created_at=datetime.now(timezone.utc),
    )
    attempt = SimpleNamespace(
        id=attempt_id,
        status=DeliveryStatus.PENDING,
        attempt_no=1,
        subscription_id=subscription_id,
        response_status=None,
        response_body=None,
        error_message=None,
        attempted_at=None,
        duration_ms=None,
    )
    subscription = SimpleNamespace(
        id=subscription_id,
        endpoint_url="https://example.invalid/webhook",
        http_method=HttpMethod.POST,
        timeout_seconds=5,
        headers={"X-API-Key": "synthetic-header-secret"},
        auth_type=AuthType.NONE,
        secret_key=None,
        transform_template=None,
        max_retries=1,
    )

    class _Response:
        status_code = 204
        text = "peer echoed synthetic-header-secret"

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, _method, _url, *, content, headers):
            assert content
            assert headers["X-Correlation-ID"] == "workflow-trace-1"
            assert headers["X-Causation-ID"] == "parent-event-1"
            return _Response()

    class _Database:
        async def flush(self):
            return None

    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", lambda **_kwargs: _Client())
    before = metrics_snapshot()["webhook_delivery_attempts_total"].get("sent", 0)
    with caplog.at_level(logging.INFO, logger="app.services.webhook_service"):
        await webhook_service._deliver_attempt(_Database(), attempt, event, subscription)

    assert attempt.status == DeliveryStatus.SENT
    assert "synthetic-header-secret" not in attempt.response_body
    assert "[REDACTED]" in attempt.response_body
    assert metrics_snapshot()["webhook_delivery_attempts_total"]["sent"] == before + 1
    delivery_record = next(record for record in caplog.records if record.getMessage() == "Webhook delivery attempt completed")
    assert delivery_record.event_id == str(event_id)
    assert delivery_record.delivery_id == str(attempt_id)
    assert delivery_record.correlation_id == "workflow-trace-1"
    assert delivery_record.causation_id == "parent-event-1"
    assert not hasattr(delivery_record, "response_body")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("max_retries", "expected_status", "failure_stage", "expected_error"),
    [
        (0, DeliveryStatus.DEAD_LETTER, "request", "ConnectError"),
        (1, DeliveryStatus.RETRYING, "request", "ConnectError"),
        (0, DeliveryStatus.DEAD_LETTER, "secret", "WebhookSecretRotationError"),
    ],
)
async def test_request_failures_are_counted_and_logged_without_exception_text(
    monkeypatch, caplog, max_retries, expected_status, failure_stage, expected_error
):
    event_id = uuid4()
    attempt_id = uuid4()
    subscription_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        event_code="inventory.adjusted",
        module="inventory",
        payload={"quantity": 2},
        created_at=datetime.now(timezone.utc),
        reference_type=None,
        reference_id=None,
        actor_id=None,
    )
    attempt = SimpleNamespace(
        id=attempt_id,
        status=DeliveryStatus.PENDING,
        attempt_no=1,
        subscription_id=subscription_id,
        response_status=None,
        response_body=None,
        error_message=None,
        attempted_at=None,
        duration_ms=None,
    )
    subscription = SimpleNamespace(
        id=subscription_id,
        endpoint_url="https://example.invalid/webhook?token=synthetic-private-value",
        http_method=HttpMethod.POST,
        timeout_seconds=5,
        headers={},
        auth_type=AuthType.HMAC if failure_stage == "secret" else AuthType.NONE,
        secret_key="enc:v2:invalid-ciphertext" if failure_stage == "secret" else None,
        transform_template=None,
        max_retries=max_retries,
    )

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, *_args, **_kwargs):
            assert failure_stage == "request"
            raise webhook_service.httpx.ConnectError("synthetic-private-value")

    class _Database:
        async def flush(self):
            return None

    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", lambda **_kwargs: _Client())
    before_counts = metrics_snapshot()["webhook_delivery_attempts_total"].copy()
    with caplog.at_level(logging.WARNING, logger="app.services.webhook_service"):
        await webhook_service._deliver_attempt(_Database(), attempt, event, subscription)

    assert attempt.status == expected_status
    assert attempt.error_message == f"Delivery preparation/request failed ({expected_error})"
    assert "synthetic-private-value" not in attempt.error_message
    after_counts = metrics_snapshot()["webhook_delivery_attempts_total"]
    assert after_counts[expected_status.value] == before_counts.get(expected_status.value, 0) + 1
    delivery_record = next(record for record in caplog.records if record.getMessage() == "Webhook delivery attempt completed")
    assert delivery_record.outcome == expected_status.value
    assert delivery_record.error_type == expected_error
    assert "synthetic-private-value" not in delivery_record.getMessage()
