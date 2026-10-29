"""M31.S02.T002 event-schema and version-history checks; disposable PostgreSQL only."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.webhook import EventDefinition, EventDefinitionVersion, EventLog
from app.schemas.webhook import EventDefinitionCreate, EventDefinitionUpdate
from app.services.webhook_service import (
    EventPayloadValidationError,
    create_event_definition,
    list_event_definition_versions,
    publish_event,
    update_event_definition,
)


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m31_s02_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M31_S02_T002_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Run only against this task's explicitly named disposable PostgreSQL database.")
    expected = os.environ.get("M31_S02_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing database access unless DATABASE_URL matches the exact loopback M31.S02.T002 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m31_s02_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m31_s02_t001_0123456789abcdef0123")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
async def test_migration_backfilled_preexisting_definition_version_one():
    _require_task_owned_database()
    raw_id = os.environ.get("M31_S02_T002_LEGACY_DEFINITION_ID")
    raw_code = os.environ.get("M31_S02_T002_LEGACY_EVENT_CODE")
    if not raw_id or not raw_code:
        pytest.skip("The isolated migration runner did not seed a pre-versioning event definition.")

    async with AsyncSessionLocal() as db:
        definition = await db.get(EventDefinition, UUID(raw_id))
        assert definition is not None
        assert definition.event_code == raw_code
        assert definition.schema_version == 1
        versions = await list_event_definition_versions(db, definition.id)
        assert len(versions) == 1
        assert versions[0].schema_version == 1
        assert versions[0].payload_schema["required"] == ["status"]
        assert "Baseline snapshot migrated" in versions[0].change_summary


@pytest.mark.asyncio(loop_scope="session")
async def test_schema_versions_are_immutable_and_enforced_for_published_events():
    _require_task_owned_database()
    event_code = f"test.m31.s02.t002.{uuid4().hex}"
    initial_schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
        "additionalProperties": False,
    }
    next_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "total": {"type": "number"},
        },
        "required": ["status", "total"],
        "additionalProperties": False,
    }
    definition_id = None

    try:
        async with AsyncSessionLocal() as db:
            definition = await create_event_definition(
                db,
                EventDefinitionCreate(
                    event_code=event_code,
                    event_name="Synthetic versioned test event",
                    module="testing",
                    payload_schema=initial_schema,
                ),
                actor_id="synthetic-admin",
            )
            definition_id = definition.id
            assert definition.schema_version == 1
            assert definition.payload_schema["$schema"].endswith("draft/2020-12/schema")

            first_event = await publish_event(db, event_code, {"status": "draft"})
            assert first_event.payload["schema_version"] == 1

            with pytest.raises(EventPayloadValidationError):
                await publish_event(db, event_code, {"status": "draft", "unexpected": "synthetic"})

            definition = await update_event_definition(
                db,
                definition.id,
                EventDefinitionUpdate(
                    payload_schema=next_schema,
                    schema_change_summary="Require total on test invoices",
                ),
                actor_id="synthetic-admin",
            )
            assert definition.schema_version == 2
            second_event = await publish_event(db, event_code, {"status": "posted", "total": 12.5})
            assert second_event.payload["schema_version"] == 2

            versions = await list_event_definition_versions(db, definition.id)
            assert [version.schema_version for version in versions] == [1, 2]
            assert versions[0].payload_schema["required"] == ["status"]
            assert versions[1].payload_schema["required"] == ["status", "total"]
            assert versions[1].created_by == "synthetic-admin"
            assert await db.scalar(
                select(func.count()).select_from(EventLog).where(EventLog.event_code == event_code)
            ) == 2
    finally:
        if definition_id is not None:
            async with AsyncSessionLocal() as cleanup_db:
                await cleanup_db.execute(delete(EventLog).where(EventLog.event_code == event_code))
                await cleanup_db.execute(
                    delete(EventDefinitionVersion).where(EventDefinitionVersion.event_def_id == definition_id)
                )
                await cleanup_db.execute(delete(EventDefinition).where(EventDefinition.id == definition_id))
                await cleanup_db.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_event_schema_api_exposes_version_history_and_safe_validation_errors():
    _require_task_owned_database()
    event_code = f"test.m31.s02.t002.api.{uuid4().hex}"
    actor = {"id": uuid4(), "is_superuser": True}
    definition_id = None
    original_overrides = dict(app.dependency_overrides)

    async def override_db():
        async with AsyncSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**actor)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/webhooks/event-definitions", json={
                "event_code": event_code,
                "event_name": "Synthetic API schema event",
                "module": "testing",
                "payload_schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                    "additionalProperties": False,
                },
            })
            assert created.status_code == 201, created.text
            definition_id = created.json()["id"]
            assert created.json()["schema_version"] == 1

            old_event_id = uuid4()
            async with AsyncSessionLocal() as db:
                db.add(EventLog(
                    id=old_event_id,
                    event_def_id=UUID(definition_id),
                    event_code=event_code,
                    module="testing",
                    payload={
                        "id": str(old_event_id),
                        "type": event_code,
                        "module": "testing",
                        "occurred_at": "2026-10-30T08:15:00Z",
                        "actor_id": None,
                        "reference": {"type": None, "id": None},
                        "data": {"status": "legacy"},
                    },
                ))
                await db.commit()

            actor["is_superuser"] = False
            denied = await client.put(f"/api/v1/webhooks/event-definitions/{definition_id}", json={"event_name": "Forbidden"})
            assert denied.status_code == 403
            actor["is_superuser"] = True

            invalid_schema_change = await client.put(
                f"/api/v1/webhooks/event-definitions/{definition_id}",
                json={"payload_schema": {"type": "object", "properties": {"status": {"type": "number"}}}},
            )
            assert invalid_schema_change.status_code == 422
            assert "schema_change_summary" in invalid_schema_change.json()["detail"]

            updated = await client.put(
                f"/api/v1/webhooks/event-definitions/{definition_id}",
                json={
                    "payload_schema": {
                        "type": "object",
                        "properties": {"status": {"type": "string"}, "total": {"type": "number"}},
                        "required": ["status", "total"],
                    },
                    "schema_change_summary": "Require total for API test event",
                },
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["schema_version"] == 2

            invalid_event = await client.post(
                "/api/v1/webhooks/events/publish",
                json={"event_code": event_code, "payload": {"status": "posted", "total": "private-value"}},
            )
            assert invalid_event.status_code == 422
            assert "private-value" not in invalid_event.text

            valid_event = await client.post(
                "/api/v1/webhooks/events/publish",
                json={"event_code": event_code, "payload": {"status": "posted", "total": 12.5}},
            )
            assert valid_event.status_code == 201, valid_event.text
            assert valid_event.json()["payload"]["schema_version"] == 2
            assert valid_event.json()["payload"]["data"] == {"status": "posted", "total": 12.5}

            history = await client.get(f"/api/v1/webhooks/event-definitions/{definition_id}/versions")
            assert history.status_code == 200, history.text
            assert [version["schema_version"] for version in history.json()] == [1, 2]

            old_event_detail = await client.get(f"/api/v1/webhooks/events/{old_event_id}")
            assert old_event_detail.status_code == 200, old_event_detail.text
            assert old_event_detail.json()["payload"]["schema_version"] == 1
            old_event_list = await client.get("/api/v1/webhooks/events", params={"event_code": event_code})
            assert old_event_list.status_code == 200, old_event_list.text
            listed_old_event = next(item for item in old_event_list.json() if item["id"] == str(old_event_id))
            assert listed_old_event["payload"]["schema_version"] == 1
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        if definition_id is not None:
            async with AsyncSessionLocal() as cleanup_db:
                definition_uuid = UUID(definition_id)
                await cleanup_db.execute(delete(EventLog).where(EventLog.event_code == event_code))
                await cleanup_db.execute(
                    delete(EventDefinitionVersion).where(EventDefinitionVersion.event_def_id == definition_uuid)
                )
                await cleanup_db.execute(delete(EventDefinition).where(EventDefinition.id == definition_uuid))
                await cleanup_db.commit()
