from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.models.webhook import EventDefinition, EventDefinitionVersion, EventLog
from app.api.v1.endpoints.webhooks import _event_log_response
from app.schemas.webhook import EventDefinitionUpdate
from app.services.webhook_service import (
    EVENT_JSON_SCHEMA_DRAFT,
    EventPayloadValidationError,
    EventSchemaGovernanceError,
    _normalize_event_schema,
    _validate_event_data,
    publish_event,
    update_event_definition,
)


def test_schema_is_canonicalized_and_checked_without_mutating_input():
    source = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
        "additionalProperties": False,
    }

    normalized = _normalize_event_schema(source)

    assert normalized["$schema"] == EVENT_JSON_SCHEMA_DRAFT
    assert "$schema" not in source
    _validate_event_data(normalized, {"status": "posted"})


def test_schema_history_is_not_cascaded_when_definition_is_deleted():
    fk = next(iter(EventDefinitionVersion.__table__.foreign_keys))
    assert fk.ondelete == "RESTRICT"
    assert "delete" not in EventDefinition.schema_versions.property.cascade


def test_public_event_response_adds_version_to_t001_envelope_without_mutation():
    event_id = UUID("040db10f-1fbd-43e8-a51c-bb074891ac64")
    payload = {
        "id": str(event_id),
        "type": "invoice.posted",
        "module": "finance",
        "occurred_at": "2026-10-30T08:15:00Z",
        "actor_id": None,
        "reference": {"type": "invoice", "id": "INV-17"},
        "data": {"status": "posted"},
    }
    row = SimpleNamespace(
        id=event_id,
        event_code="invoice.posted",
        module="finance",
        reference_type="invoice",
        reference_id="INV-17",
        actor_id=None,
        partition_key="INV-17",
        created_at=datetime(2026, 10, 30, 8, 15, tzinfo=timezone.utc),
        payload=payload,
    )

    response = _event_log_response(row)

    assert response.payload["schema_version"] == 1
    assert response.payload["data"] == {"status": "posted"}
    assert "schema_version" not in payload


@pytest.mark.parametrize(
    "schema, message",
    [
        ({"type": "string"}, "type 'object'"),
        ({"type": "object", "$schema": "https://example.invalid/schema"}, "Draft 2020-12"),
        ({"type": "object", "properties": {"x": {"type": "made-up"}}}, "Invalid JSON Schema"),
        ({"type": "object", "properties": {"x": {"$ref": "https://example.invalid/x"}}}, "local references only"),
    ],
)
def test_invalid_or_remote_schema_is_rejected(schema, message):
    with pytest.raises(EventSchemaGovernanceError, match=message):
        _normalize_event_schema(schema)


def test_payload_failure_does_not_echo_business_value():
    schema = _normalize_event_schema({
        "type": "object",
        "properties": {"amount": {"type": "number"}},
        "required": ["amount"],
    })

    with pytest.raises(EventPayloadValidationError) as error:
        _validate_event_data(schema, {"amount": "sensitive-business-value"})
    assert "amount" in str(error.value)
    assert "sensitive-business-value" not in str(error.value)


def test_schema_change_requires_summary_and_creates_immutable_next_snapshot():
    async def run():
        old_schema = _normalize_event_schema({"type": "object", "properties": {"status": {"type": "string"}}})
        new_schema = {"type": "object", "properties": {"status": {"type": "string"}, "total": {"type": "number"}}}
        definition = SimpleNamespace(
            id=UUID("4eb64175-60bd-4932-a2c2-dd5a1f163748"),
            schema_version=1,
            payload_schema=old_schema,
            event_name="Invoice Posted",
            module="finance",
            description=None,
            active_flag=True,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = definition
        db = SimpleNamespace(
            execute=AsyncMock(return_value=result),
            add=Mock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        with pytest.raises(EventSchemaGovernanceError, match="schema_change_summary"):
            await update_event_definition(
                db,
                definition.id,
                EventDefinitionUpdate(payload_schema=new_schema),
                actor_id="admin-7",
            )
        assert definition.schema_version == 1
        db.add.assert_not_called()

        updated = await update_event_definition(
            db,
            definition.id,
            EventDefinitionUpdate(
                payload_schema=new_schema,
                schema_change_summary="Add optional invoice total",
            ),
            actor_id="admin-7",
        )

        assert updated.schema_version == 2
        assert updated.payload_schema["$schema"] == EVENT_JSON_SCHEMA_DRAFT
        snapshot = db.add.call_args.args[0]
        assert isinstance(snapshot, EventDefinitionVersion)
        assert snapshot.schema_version == 2
        assert snapshot.change_summary == "Add optional invoice total"
        assert snapshot.created_by == "admin-7"
        assert snapshot.payload_schema == updated.payload_schema
        db.commit.assert_awaited_once()

    asyncio.run(run())


def test_metadata_change_does_not_create_schema_version():
    async def run():
        definition = SimpleNamespace(
            id=UUID("4eb64175-60bd-4932-a2c2-dd5a1f163748"),
            schema_version=4,
            payload_schema=None,
            event_name="Old Name",
            module="finance",
            description=None,
            active_flag=True,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = definition
        db = SimpleNamespace(
            execute=AsyncMock(return_value=result),
            add=Mock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        await update_event_definition(
            db,
            definition.id,
            EventDefinitionUpdate(event_name="New Name"),
        )
        assert definition.event_name == "New Name"
        assert definition.schema_version == 4
        db.add.assert_not_called()

    asyncio.run(run())


def test_publish_uses_registered_schema_version_and_rejects_invalid_data_before_writes():
    async def run():
        definition = SimpleNamespace(
            id=UUID("4eb64175-60bd-4932-a2c2-dd5a1f163748"),
            module="finance",
            schema_version=3,
            payload_schema=_normalize_event_schema({
                "type": "object",
                "properties": {"total": {"type": "number"}},
                "required": ["total"],
            }),
        )
        event_result = Mock()
        event_result.scalar_one_or_none.return_value = definition
        subscriptions_result = Mock()
        subscriptions_result.scalars.return_value.all.return_value = []
        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[event_result, subscriptions_result]),
            add=Mock(),
            flush=AsyncMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        event_log = await publish_event(db, "invoice.posted", {"total": 12.5})
        assert isinstance(event_log, EventLog)
        assert event_log.payload["schema_version"] == 3
        assert event_log.payload["data"] == {"total": 12.5}

        invalid_db = SimpleNamespace(
            execute=AsyncMock(return_value=event_result),
            add=Mock(),
            flush=AsyncMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        with pytest.raises(EventPayloadValidationError):
            await publish_event(invalid_db, "invoice.posted", {"total": "sensitive-business-value"})
        invalid_db.add.assert_not_called()
        invalid_db.commit.assert_not_awaited()

    asyncio.run(run())
