from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.webhook import EventLog
from app.schemas.webhook import DomainEventEnvelope, PublishEventRequest
from app.services.webhook_service import (
    _event_idempotency_fingerprint,
    _normalize_event_identifier,
)


def test_publish_request_normalizes_and_bounds_event_identifiers():
    request = PublishEventRequest(
        event_code="invoice.posted",
        idempotency_key=" retry-1 ",
        correlation_id=" workflow-7 ",
        causation_id=" event-6 ",
    )

    assert request.idempotency_key == "retry-1"
    assert request.correlation_id == "workflow-7"
    assert request.causation_id == "event-6"
    with pytest.raises(ValidationError):
        PublishEventRequest(event_code="invoice.posted", correlation_id=" ")
    with pytest.raises(ValidationError):
        PublishEventRequest(event_code="invoice.posted", causation_id="x" * 201)
    with pytest.raises(ValidationError):
        PublishEventRequest(event_code="invoice.posted", idempotency_key="x" * 256)


def test_event_log_enforces_event_scoped_idempotency_and_paired_fingerprint():
    unique = next(
        item for item in EventLog.__table__.constraints
        if isinstance(item, UniqueConstraint) and item.name == "uq_webhook_event_idempotency"
    )
    assert [column.name for column in unique.columns] == ["event_code", "idempotency_key"]
    check = next(
        item for item in EventLog.__table__.constraints
        if isinstance(item, CheckConstraint) and item.name == "ck_webhook_event_idempotency_pair"
    )
    assert "idempotency_key IS NULL" in str(check.sqltext)
    assert "idempotency_fingerprint IS NOT NULL" in str(check.sqltext)


def test_fingerprint_is_stable_and_covers_trace_ids_and_request_data():
    values = {
        "event_code": "invoice.posted",
        "payload": {"total": 10, "status": "posted"},
        "reference_type": "invoice",
        "reference_id": "INV-1",
        "actor_id": "user-1",
        "partition_key": "INV-1",
        "correlation_id": "flow-1",
        "causation_id": "event-0",
        "module": None,
    }
    original = _event_idempotency_fingerprint(**values)
    reordered = dict(values, payload={"status": "posted", "total": 10})
    assert _event_idempotency_fingerprint(**reordered) == original
    assert _event_idempotency_fingerprint(**dict(values, causation_id="event-1")) != original
    assert _event_idempotency_fingerprint(**dict(values, payload={"total": 11, "status": "posted"})) != original


def test_service_identifier_normalization_rejects_empty_or_oversized_values():
    assert _normalize_event_identifier(" retry ", name="idempotency_key", max_length=255) == "retry"
    assert _normalize_event_identifier(None, name="correlation_id", max_length=200) is None
    with pytest.raises(ValueError, match="must not be blank"):
        _normalize_event_identifier("  ", name="correlation_id", max_length=200)
    with pytest.raises(ValueError, match="character limit"):
        _normalize_event_identifier("x" * 201, name="causation_id", max_length=200)


def test_domain_envelope_defaults_trace_ids_to_null_for_legacy_compatibility():
    envelope = DomainEventEnvelope.model_validate({
        "id": "040db10f-1fbd-43e8-a51c-bb074891ac64",
        "type": "invoice.posted",
        "module": "finance",
        "schema_version": 1,
        "occurred_at": "2026-10-30T08:15:00Z",
        "actor_id": None,
        "reference": {"type": "invoice", "id": "INV-1"},
        "data": {"status": "posted"},
    })
    assert envelope.correlation_id is None
    assert envelope.causation_id is None
