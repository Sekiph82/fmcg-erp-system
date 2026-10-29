from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from app.models.webhook import DeliveryAttempt, EventLog
from app.schemas.webhook import DomainEventEnvelope
from app.services.webhook_service import (
    _build_event_envelope,
    _canonical_event_payload,
    _evaluate_filter,
    _transform_payload,
    publish_event,
)


def test_envelope_has_canonical_metadata_and_keeps_business_data_opaque():
    event_id = UUID("040db10f-1fbd-43e8-a51c-bb074891ac64")
    occurred_at = datetime(2026, 10, 30, 8, 15, tzinfo=timezone.utc)
    source_data = {"status": "posted", "_event": {"caller": "business-data"}}

    envelope = _build_event_envelope(
        event_id=event_id,
        event_code="invoice.posted",
        module="finance",
        occurred_at=occurred_at,
        payload=source_data,
        reference_type="invoice",
        reference_id="INV-17",
        actor_id="user-2",
    )

    assert envelope == {
        "id": str(event_id),
        "type": "invoice.posted",
        "module": "finance",
        "occurred_at": "2026-10-30T08:15:00Z",
        "actor_id": "user-2",
        "reference": {"type": "invoice", "id": "INV-17"},
        "data": source_data,
    }
    assert source_data == {"status": "posted", "_event": {"caller": "business-data"}}
    assert DomainEventEnvelope.model_validate(envelope).data == source_data


def test_legacy_payload_paths_resolve_into_envelope_data():
    envelope = {
        "id": "040db10f-1fbd-43e8-a51c-bb074891ac64",
        "type": "invoice.posted",
        "module": "finance",
        "occurred_at": "2026-10-30T08:15:00Z",
        "actor_id": None,
        "reference": {"type": "invoice", "id": "INV-17"},
        "data": {"status": "posted", "total": 25},
    }
    assert _evaluate_filter([{"field": "payload.status", "op": "eq", "value": "posted"}], envelope)
    assert _evaluate_filter([{"field": "data.total", "op": "gt", "value": 20}], envelope)
    assert _transform_payload(envelope, {"state": "payload.status", "ref": "reference.id"}) == {
        "state": "posted",
        "ref": "INV-17",
    }


def test_legacy_stored_event_is_read_as_canonical_without_mutating_row():
    event_id = UUID("040db10f-1fbd-43e8-a51c-bb074891ac64")
    created_at = datetime(2026, 10, 30, 8, 15, tzinfo=timezone.utc)
    legacy_payload = {"status": "posted", "_event": {"reference_id": "INV-17"}}
    row = SimpleNamespace(
        id=event_id,
        event_code="invoice.posted",
        module="finance",
        reference_type="invoice",
        reference_id="INV-17",
        actor_id="user-2",
        created_at=created_at,
        payload=legacy_payload,
    )

    normalized = _canonical_event_payload(row)

    assert normalized["id"] == str(event_id)
    assert normalized["occurred_at"] == "2026-10-30T08:15:00Z"
    assert normalized["reference"] == {"type": "invoice", "id": "INV-17"}
    assert normalized["data"] == {"status": "posted"}
    assert legacy_payload == {"status": "posted", "_event": {"reference_id": "INV-17"}}


def test_legacy_business_fields_cannot_be_mistaken_for_an_envelope():
    event_id = UUID("040db10f-1fbd-43e8-a51c-bb074891ac64")
    created_at = datetime(2026, 10, 30, 8, 15, tzinfo=timezone.utc)
    legacy_payload = {
        "id": "business-id",
        "type": "business-type",
        "module": "business-module",
        "occurred_at": "business-time",
        "reference": {"business": "value"},
        "data": {"business": "nested"},
        "_event": {"code": "invoice.posted", "published_at": created_at.isoformat()},
    }
    row = SimpleNamespace(
        id=event_id,
        event_code="invoice.posted",
        module="finance",
        reference_type="invoice",
        reference_id="INV-17",
        actor_id="user-2",
        created_at=created_at,
        payload=legacy_payload,
    )

    normalized = _canonical_event_payload(row)

    assert normalized["id"] == str(event_id)
    assert normalized["type"] == "invoice.posted"
    assert normalized["module"] == "finance"
    assert normalized["reference"] == {"type": "invoice", "id": "INV-17"}
    assert normalized["data"] == {key: value for key, value in legacy_payload.items() if key != "_event"}


def test_publish_stores_envelope_and_filters_using_legacy_payload_alias():
    async def run():
        event_result = Mock()
        event_result.scalar_one_or_none.return_value = None
        matching_subscription = SimpleNamespace(
            id=UUID("949b7ec9-f6ce-477a-a1ed-7de9e5877df7"),
            event_codes=None,
            filter_expression=[{"field": "payload.status", "op": "eq", "value": "posted"}],
        )
        non_matching_subscription = SimpleNamespace(
            id=UUID("8c322bd7-51e4-4935-9875-91fa16a5d6d3"),
            event_codes=["invoice.posted"],
            filter_expression=[{"field": "payload.status", "op": "eq", "value": "void"}],
        )
        subscription_result = Mock()
        subscription_result.scalars.return_value.all.return_value = [matching_subscription, non_matching_subscription]

        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[event_result, subscription_result]),
            add=Mock(),
            flush=AsyncMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        input_payload = {"status": "posted", "amount": 25}
        event_log = await publish_event(
            db,
            "invoice.posted",
            input_payload,
            reference_type="invoice",
            reference_id="INV-17",
            actor_id="user-2",
            module="finance",
        )

        assert isinstance(event_log, EventLog)
        assert event_log.id == UUID(event_log.payload["id"])
        assert event_log.payload["type"] == "invoice.posted"
        assert event_log.payload["module"] == "finance"
        assert event_log.payload["reference"] == {"type": "invoice", "id": "INV-17"}
        assert event_log.payload["actor_id"] == "user-2"
        assert event_log.payload["data"] == input_payload
        assert event_log.created_at.isoformat() == event_log.payload["occurred_at"].replace("Z", "+00:00")
        assert input_payload == {"status": "posted", "amount": 25}
        added = [call.args[0] for call in db.add.call_args_list]
        assert sum(isinstance(obj, DeliveryAttempt) for obj in added) == 1
        db.commit.assert_awaited_once()

    asyncio.run(run())
