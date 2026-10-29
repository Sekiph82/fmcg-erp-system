"""Webhook / Event Engine service."""
from __future__ import annotations
import hashlib
import hmac
import json
import time
from copy import deepcopy
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import (
    AuthType, DeliveryAttempt, DeliveryStatus, EventDefinition, EventDefinitionVersion,
    EventLog, HttpMethod, InboundEndpoint, Subscription,
)
from app.schemas.webhook import (
    DomainEventEnvelope, DomainEventReference, EventDefinitionCreate, EventDefinitionUpdate, InboundEndpointCreate,
    PublishEventRequest, ReplayRequest, SubscriptionCreate, SubscriptionUpdate,
)

MAX_RESPONSE_BODY = 2000       # truncate stored response body
BACKOFF_BASE = 60              # base seconds for exponential backoff
MAX_PAYLOAD_BYTES = 1_048_576  # 1 MB
EVENT_JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"


class EventSchemaGovernanceError(ValueError):
    """An event schema is invalid or its change lacks governance metadata."""


class EventPayloadValidationError(ValueError):
    """Business data does not conform to its registered event schema."""


class EventIdempotencyConflictError(ValueError):
    """An idempotency key was reused for a different event request."""


class EventIdentifierValidationError(ValueError):
    """An event tracing or idempotency identifier is invalid."""


def _build_event_envelope(
    *,
    event_id: UUID,
    event_code: str,
    module: str,
    occurred_at: datetime,
    payload: Dict[str, Any],
    schema_version: int = 1,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the canonical event contract without modifying caller-owned data."""
    return DomainEventEnvelope(
        id=event_id,
        type=event_code,
        module=module,
        schema_version=schema_version,
        occurred_at=occurred_at,
        actor_id=actor_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        reference=DomainEventReference(type=reference_type, id=reference_id),
        data=payload,
    ).model_dump(mode="json")


def _canonical_event_payload(event_log: EventLog) -> Dict[str, Any]:
    """Return canonical output for current rows and normalize legacy rows on read."""
    payload = event_log.payload if isinstance(event_log.payload, dict) else {}
    if (
        {"id", "type", "module", "occurred_at", "reference", "data"}.issubset(payload)
        and "_event" not in payload
        and payload.get("id") == str(event_log.id)
        and payload.get("type") == event_log.event_code
        and payload.get("module") == event_log.module
        and isinstance(payload.get("reference"), dict)
        and isinstance(payload.get("data"), dict)
    ):
        versioned_payload = dict(payload)
        versioned_payload.setdefault("schema_version", 1)
        versioned_payload.setdefault("correlation_id", None)
        versioned_payload.setdefault("causation_id", None)
        return versioned_payload

    legacy_metadata = payload.get("_event") if isinstance(payload.get("_event"), dict) else {}
    occurred_at = event_log.created_at or legacy_metadata.get("published_at") or datetime.now(timezone.utc)
    if isinstance(occurred_at, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    data = {key: value for key, value in payload.items() if key != "_event"}
    return _build_event_envelope(
        event_id=event_log.id,
        event_code=event_log.event_code,
        module=event_log.module,
        schema_version=1,
        occurred_at=occurred_at,
        payload=data,
        reference_type=event_log.reference_type or legacy_metadata.get("reference_type"),
        reference_id=event_log.reference_id or legacy_metadata.get("reference_id"),
        actor_id=event_log.actor_id or legacy_metadata.get("actor_id"),
    )


def _normalize_event_schema(schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Validate and canonicalize the supported JSON Schema draft without remote refs."""
    if schema is None:
        return None
    if not isinstance(schema, dict):
        raise EventSchemaGovernanceError("Event payload schema must be a JSON object.")
    normalized = deepcopy(schema)
    declared_draft = normalized.get("$schema")
    if declared_draft not in (None, EVENT_JSON_SCHEMA_DRAFT):
        raise EventSchemaGovernanceError("Event schemas must use JSON Schema Draft 2020-12.")
    normalized["$schema"] = EVENT_JSON_SCHEMA_DRAFT
    if normalized.get("type") != "object":
        raise EventSchemaGovernanceError("Event payload schemas must declare type 'object'.")

    def reject_remote_refs(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("$ref", "$dynamicRef", "$recursiveRef"):
                reference = value.get(key)
                if isinstance(reference, str) and not reference.startswith("#"):
                    raise EventSchemaGovernanceError(
                        "Event schemas may use local references only; remote references are disabled."
                    )
            for child in value.values():
                reject_remote_refs(child)
        elif isinstance(value, list):
            for child in value:
                reject_remote_refs(child)

    reject_remote_refs(normalized)
    try:
        Draft202012Validator.check_schema(normalized)
    except SchemaError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise EventSchemaGovernanceError(f"Invalid JSON Schema near '{path}'.") from exc
    return normalized


def _validate_event_data(schema: Optional[Dict[str, Any]], data: Dict[str, Any]) -> None:
    normalized = _normalize_event_schema(schema)
    if normalized is None:
        return
    errors = sorted(
        Draft202012Validator(normalized).iter_errors(data),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "$"
        keyword = errors[0].validator or "schema"
        raise EventPayloadValidationError(
            f"Event payload does not match its declared schema at '{path}' ({keyword})."
        )


def _normalize_event_identifier(value: Optional[str], *, name: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EventIdentifierValidationError(f"{name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise EventIdentifierValidationError(f"{name} must not be blank.")
    if len(normalized) > max_length:
        raise EventIdentifierValidationError(f"{name} exceeds the {max_length}-character limit.")
    return normalized


def _event_idempotency_fingerprint(
    *, event_code: str, payload: Dict[str, Any], reference_type: Optional[str],
    reference_id: Optional[str], actor_id: Optional[str], partition_key: Optional[str],
    correlation_id: Optional[str], causation_id: Optional[str], module: Optional[str],
) -> str:
    request = {
        "event_code": event_code,
        "payload": payload,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "actor_id": actor_id,
        "partition_key": partition_key,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "module": module,
    }
    canonical = json.dumps(request, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _same_idempotent_request(event_log: EventLog, fingerprint: str) -> bool:
    return event_log.idempotency_fingerprint == fingerprint


# ── Seeded event definitions ──────────────────────────────────────────────────

STANDARD_EVENTS = [
    ("record.created", "Record Created", "system"),
    ("record.updated", "Record Updated", "system"),
    ("record.deleted", "Record Deleted", "system"),
    ("status.changed", "Status Changed", "system"),
    ("approval.completed", "Approval Completed", "system"),
    ("payment.posted", "Payment Posted", "finance"),
    ("inventory.moved", "Inventory Moved", "inventory"),
    ("shipment.dispatched", "Shipment Dispatched", "logistics"),
    ("user.logged_in", "User Logged In", "auth"),
    ("sales_order.confirmed", "Sales Order Confirmed", "sales"),
    ("purchase_order.acknowledged", "Purchase Order Acknowledged", "procurement"),
    ("invoice.approved", "Invoice Approved", "finance"),
    ("production_order.completed", "Production Order Completed", "production"),
    ("quality.inspection_failed", "Quality Inspection Failed", "quality"),
    ("two_fa.failed", "2FA Failed", "security"),
]


async def seed_event_definitions(db: AsyncSession) -> None:
    created: List[EventDefinition] = []
    for code, name, module in STANDARD_EVENTS:
        existing = await db.execute(
            select(EventDefinition).where(EventDefinition.event_code == code)
        )
        if existing.scalar_one_or_none():
            continue
        definition = EventDefinition(event_code=code, event_name=name, module=module)
        db.add(definition)
        created.append(definition)
    await db.flush()
    for definition in created:
        db.add(EventDefinitionVersion(
            event_def_id=definition.id,
            schema_version=definition.schema_version,
            payload_schema=definition.payload_schema,
            change_summary="Initial seeded event definition; payload schema not declared",
        ))
    await db.commit()


# ── Event Definitions CRUD ────────────────────────────────────────────────────

async def list_event_definitions(
    db: AsyncSession,
    module: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> List[EventDefinition]:
    q = select(EventDefinition).order_by(EventDefinition.module, EventDefinition.event_code)
    if active_only:
        q = q.where(EventDefinition.active_flag == True)  # noqa: E712
    if module:
        q = q.where(EventDefinition.module == module)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_event_definition(
    db: AsyncSession,
    data: EventDefinitionCreate,
    *,
    actor_id: Optional[str] = None,
) -> EventDefinition:
    values = data.model_dump()
    values["payload_schema"] = _normalize_event_schema(values.get("payload_schema"))
    obj = EventDefinition(**values, schema_version=1)
    db.add(obj)
    await db.flush()
    db.add(EventDefinitionVersion(
        event_def_id=obj.id,
        schema_version=obj.schema_version,
        payload_schema=obj.payload_schema,
        change_summary="Initial event definition and schema snapshot",
        created_by=actor_id,
    ))
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_event_definition(
    db: AsyncSession,
    definition_id: UUID,
    data: EventDefinitionUpdate,
    *,
    actor_id: Optional[str] = None,
) -> Optional[EventDefinition]:
    result = await db.execute(
        select(EventDefinition)
        .where(EventDefinition.id == definition_id)
        .with_for_update()
    )
    definition = result.scalar_one_or_none()
    if definition is None:
        return None

    changes = data.model_dump(exclude_unset=True)
    change_summary = changes.pop("schema_change_summary", None)
    schema_was_supplied = "payload_schema" in changes
    if schema_was_supplied:
        normalized_schema = _normalize_event_schema(changes["payload_schema"])
        if normalized_schema != definition.payload_schema:
            if not change_summary or not change_summary.strip():
                raise EventSchemaGovernanceError(
                    "A non-empty schema_change_summary is required when changing an event schema."
                )
            definition.schema_version += 1
            definition.payload_schema = normalized_schema
            db.add(EventDefinitionVersion(
                event_def_id=definition.id,
                schema_version=definition.schema_version,
                payload_schema=normalized_schema,
                change_summary=change_summary.strip(),
                created_by=actor_id,
            ))
        changes.pop("payload_schema")

    for field in ("event_name", "module", "description", "active_flag"):
        if field in changes and changes[field] is not None:
            setattr(definition, field, changes[field])
    await db.commit()
    await db.refresh(definition)
    return definition


async def list_event_definition_versions(
    db: AsyncSession,
    definition_id: UUID,
) -> Optional[List[EventDefinitionVersion]]:
    definition = await db.get(EventDefinition, definition_id)
    if definition is None:
        return None
    result = await db.execute(
        select(EventDefinitionVersion)
        .where(EventDefinitionVersion.event_def_id == definition_id)
        .order_by(EventDefinitionVersion.schema_version)
    )
    return list(result.scalars().all())


# ── Event publishing ──────────────────────────────────────────────────────────

async def publish_event(
    db: AsyncSession,
    event_code: str,
    payload: Dict[str, Any],
    *,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    partition_key: Optional[str] = None,
    module: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> EventLog:
    """Publish an event. Creates EventLog and queues DeliveryAttempts for matching subscriptions."""
    idempotency_key = _normalize_event_identifier(idempotency_key, name="idempotency_key", max_length=255)
    correlation_id = _normalize_event_identifier(correlation_id, name="correlation_id", max_length=200)
    causation_id = _normalize_event_identifier(causation_id, name="causation_id", max_length=200)
    fingerprint = None
    if idempotency_key is not None:
        fingerprint = _event_idempotency_fingerprint(
            event_code=event_code,
            payload=payload,
            reference_type=reference_type,
            reference_id=reference_id,
            actor_id=actor_id,
            partition_key=partition_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            module=module,
        )
        existing_result = await db.execute(
            select(EventLog).where(
                EventLog.event_code == event_code,
                EventLog.idempotency_key == idempotency_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            if not _same_idempotent_request(existing, fingerprint):
                raise EventIdempotencyConflictError(
                    "This idempotency key was already used for a different event request."
                )
            existing._idempotency_replayed = True
            return existing

    # Resolve event def
    def_result = await db.execute(
        select(EventDefinition).where(EventDefinition.event_code == event_code)
    )
    event_def = def_result.scalar_one_or_none()
    resolved_module = module or (event_def.module if event_def else "unknown")
    if event_def:
        _validate_event_data(event_def.payload_schema, payload)
    resolved_schema_version = event_def.schema_version if event_def else 1

    event_id = uuid4()
    occurred_at = datetime.now(timezone.utc)
    envelope = _build_event_envelope(
        event_id=event_id,
        event_code=event_code,
        module=resolved_module,
        occurred_at=occurred_at,
        payload=payload,
        schema_version=resolved_schema_version,
        reference_type=reference_type,
        reference_id=reference_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )

    event_log = EventLog(
        id=event_id,
        event_def_id=event_def.id if event_def else None,
        event_code=event_code,
        module=resolved_module,
        reference_type=reference_type,
        reference_id=reference_id,
        payload=envelope,
        actor_id=actor_id,
        partition_key=partition_key or reference_id,
        created_at=occurred_at,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
    )
    if idempotency_key is not None:
        insert_result = await db.execute(
            postgresql_insert(EventLog)
            .values(
                id=event_log.id,
                event_def_id=event_log.event_def_id,
                event_code=event_log.event_code,
                module=event_log.module,
                reference_type=event_log.reference_type,
                reference_id=event_log.reference_id,
                payload=event_log.payload,
                actor_id=event_log.actor_id,
                partition_key=event_log.partition_key,
                created_at=event_log.created_at,
                idempotency_key=event_log.idempotency_key,
                idempotency_fingerprint=event_log.idempotency_fingerprint,
            )
            .on_conflict_do_nothing(index_elements=[EventLog.event_code, EventLog.idempotency_key])
            .returning(EventLog)
        )
        inserted_event = insert_result.scalar_one_or_none()
        if inserted_event is None:
            duplicate_result = await db.execute(
                select(EventLog).where(
                    EventLog.event_code == event_code,
                    EventLog.idempotency_key == idempotency_key,
                )
            )
            duplicate = duplicate_result.scalar_one_or_none()
            if duplicate is None:
                raise RuntimeError("The idempotency conflict row was not visible after insert arbitration.")
            if not _same_idempotent_request(duplicate, fingerprint):
                raise EventIdempotencyConflictError(
                    "This idempotency key was already used for a different event request."
                )
            duplicate._idempotency_replayed = True
            return duplicate
        event_log = inserted_event
    else:
        db.add(event_log)
        await db.flush()

    # Queue delivery attempts for matching active subscriptions
    subs_result = await db.execute(
        select(Subscription).where(Subscription.active_flag == True)  # noqa: E712
    )
    subscriptions = list(subs_result.scalars().all())

    for sub in subscriptions:
        # Filter by event_codes if subscription specifies them
        if sub.event_codes and event_code not in sub.event_codes:
            continue
        # Evaluate filter_expression
        if not _evaluate_filter(sub.filter_expression, envelope):
            continue
        attempt = DeliveryAttempt(
            event_log_id=event_log.id,
            subscription_id=sub.id,
            attempt_no=1,
            status=DeliveryStatus.PENDING,
        )
        db.add(attempt)

    await db.commit()
    await db.refresh(event_log)
    return event_log


# ── Filter evaluation ─────────────────────────────────────────────────────────

def _get_nested(data: Dict, path: str) -> Any:
    """Resolve dot-notation path in dict. payload.status → data['payload']['status']"""
    parts = path.split(".")
    cur = data
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _event_data_path(payload: Dict[str, Any], path: str) -> str:
    """Keep legacy payload.* filters/templates working against envelope.data."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return path
    if path.startswith("payload."):
        return "data." + path[len("payload."):]
    if path and path.split(".", 1)[0] not in payload:
        return "data." + path
    return path


def _evaluate_filter(filter_expr: Optional[List], payload: Dict) -> bool:
    """All rules must pass (AND logic). No rules = pass."""
    if not filter_expr:
        return True
    for rule in filter_expr:
        field = rule.get("field", "")
        op = rule.get("op", "eq")
        expected = rule.get("value")
        actual = _get_nested(payload, _event_data_path(payload, field))
        try:
            if op == "eq" and actual != expected:
                return False
            elif op == "ne" and actual == expected:
                return False
            elif op == "gt" and not (actual is not None and actual > expected):
                return False
            elif op == "lt" and not (actual is not None and actual < expected):
                return False
            elif op == "contains" and (actual is None or str(expected) not in str(actual)):
                return False
            elif op == "in" and actual not in (expected if isinstance(expected, list) else [expected]):
                return False
        except Exception:
            return False
    return True


# ── Payload transformation ────────────────────────────────────────────────────

def _transform_payload(payload: Dict, template: Optional[Dict]) -> Dict:
    """Remap fields. template = {output_field: input_path}"""
    if not template:
        return payload
    result = {}
    for out_key, in_path in template.items():
        result[out_key] = _get_nested(payload, _event_data_path(payload, in_path))
    return result


# ── HMAC signing ──────────────────────────────────────────────────────────────

def _sign_payload(secret: str, body: bytes, timestamp: str) -> str:
    message = f"{timestamp}.".encode() + body
    sig = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ── HTTP delivery ─────────────────────────────────────────────────────────────

async def _deliver_attempt(
    db: AsyncSession, attempt: DeliveryAttempt, event_log: EventLog, sub: Subscription
) -> None:
    """Execute one HTTP delivery attempt and record result."""
    payload = _transform_payload(_canonical_event_payload(event_log), sub.transform_template)
    body_bytes = json.dumps(payload).encode()

    if len(body_bytes) > MAX_PAYLOAD_BYTES:
        attempt.status = DeliveryStatus.FAILED
        attempt.error_message = "Payload exceeds 1MB limit"
        attempt.attempted_at = datetime.now(timezone.utc)
        await db.flush()
        return

    timestamp = str(int(time.time()))
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event_log.event_code,
        "X-Webhook-Event-Id": str(event_log.id),
        "X-Webhook-Delivery-Id": str(attempt.id),
        "X-Webhook-Timestamp": timestamp,
    }

    # Merge custom headers
    if sub.headers:
        headers.update(sub.headers)

    # Auth
    if sub.auth_type == AuthType.BEARER and sub.secret_key:
        headers["Authorization"] = f"Bearer {sub.secret_key}"
    elif sub.auth_type == AuthType.BASIC and sub.auth_user and sub.secret_key:
        creds = b64encode(f"{sub.auth_user}:{sub.secret_key}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
    elif sub.auth_type == AuthType.HMAC and sub.secret_key:
        headers["X-Webhook-Signature"] = _sign_payload(sub.secret_key, body_bytes, timestamp)

    start = time.monotonic()
    attempt.attempted_at = datetime.now(timezone.utc)
    attempt.request_payload = payload

    try:
        async with httpx.AsyncClient(timeout=sub.timeout_seconds) as client:
            method = sub.http_method.value
            resp = await client.request(method, sub.endpoint_url, content=body_bytes, headers=headers)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        attempt.response_status = resp.status_code
        attempt.response_body = resp.text[:MAX_RESPONSE_BODY]
        attempt.duration_ms = elapsed_ms

        if 200 <= resp.status_code < 300:
            attempt.status = DeliveryStatus.SENT
        else:
            _schedule_retry(attempt, sub)

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        attempt.duration_ms = elapsed_ms
        attempt.error_message = str(exc)[:500]
        _schedule_retry(attempt, sub)

    await db.flush()


def _schedule_retry(attempt: DeliveryAttempt, sub: Subscription) -> None:
    if attempt.attempt_no >= sub.max_retries:
        attempt.status = DeliveryStatus.DEAD_LETTER
    else:
        attempt.status = DeliveryStatus.RETRYING
        backoff = BACKOFF_BASE * (2 ** (attempt.attempt_no - 1))   # exponential backoff
        attempt.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=min(backoff, 3600))


# ── Deliver pending events ────────────────────────────────────────────────────

async def process_pending_deliveries(db: AsyncSession, limit: int = 50) -> int:
    """Process PENDING delivery attempts. Called by background endpoint or cron."""
    result = await db.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.status == DeliveryStatus.PENDING)
        .order_by(DeliveryAttempt.created_at)
        .limit(limit)
    )
    attempts = list(result.scalars().all())
    if not attempts:
        return 0

    for attempt in attempts:
        event_log_r = await db.execute(select(EventLog).where(EventLog.id == attempt.event_log_id))
        event_log = event_log_r.scalar_one_or_none()
        sub_r = await db.execute(select(Subscription).where(Subscription.id == attempt.subscription_id))
        sub = sub_r.scalar_one_or_none()
        if not event_log or not sub:
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = "Event log or subscription not found"
            continue
        await _deliver_attempt(db, attempt, event_log, sub)

    await db.commit()
    return len(attempts)


async def process_retry_deliveries(db: AsyncSession, limit: int = 50) -> int:
    """Process RETRYING deliveries whose next_retry_at has passed."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DeliveryAttempt)
        .where(
            and_(
                DeliveryAttempt.status == DeliveryStatus.RETRYING,
                DeliveryAttempt.next_retry_at <= now,
            )
        )
        .order_by(DeliveryAttempt.next_retry_at)
        .limit(limit)
    )
    attempts = list(result.scalars().all())
    if not attempts:
        return 0

    for attempt in attempts:
        # Create a new attempt record (increment attempt_no)
        event_log_r = await db.execute(select(EventLog).where(EventLog.id == attempt.event_log_id))
        event_log = event_log_r.scalar_one_or_none()
        sub_r = await db.execute(select(Subscription).where(Subscription.id == attempt.subscription_id))
        sub = sub_r.scalar_one_or_none()
        if not event_log or not sub:
            attempt.status = DeliveryStatus.FAILED
            continue
        new_attempt = DeliveryAttempt(
            event_log_id=attempt.event_log_id,
            subscription_id=attempt.subscription_id,
            attempt_no=attempt.attempt_no + 1,
            status=DeliveryStatus.PENDING,
        )
        db.add(new_attempt)
        # Mark old attempt as failed (superseded by new)
        attempt.status = DeliveryStatus.FAILED
        attempt.error_message = (attempt.error_message or "") + " [retry spawned]"
        await db.flush()
        await _deliver_attempt(db, new_attempt, event_log, sub)

    await db.commit()
    return len(attempts)


# ── Replay ────────────────────────────────────────────────────────────────────

async def replay_events(db: AsyncSession, data: ReplayRequest) -> int:
    """Re-queue delivery attempts for events matching criteria."""
    q = select(EventLog).order_by(EventLog.created_at)

    if data.event_ids:
        q = q.where(EventLog.id.in_(data.event_ids))
    if data.event_code:
        q = q.where(EventLog.event_code == data.event_code)
    if data.from_dt:
        q = q.where(EventLog.created_at >= data.from_dt)
    if data.to_dt:
        q = q.where(EventLog.created_at <= data.to_dt)

    result = await db.execute(q.limit(200))
    events = list(result.scalars().all())

    # Subscriptions to replay to
    if data.subscription_ids:
        subs_r = await db.execute(
            select(Subscription).where(
                and_(Subscription.id.in_(data.subscription_ids), Subscription.active_flag == True)  # noqa: E712
            )
        )
    else:
        subs_r = await db.execute(
            select(Subscription).where(Subscription.active_flag == True)  # noqa: E712
        )
    subs = list(subs_r.scalars().all())

    count = 0
    for event in events:
        for sub in subs:
            if sub.event_codes and event.event_code not in sub.event_codes:
                continue
            attempt = DeliveryAttempt(
                event_log_id=event.id,
                subscription_id=sub.id,
                attempt_no=1,
                status=DeliveryStatus.PENDING,
                error_message="[replayed]",
            )
            db.add(attempt)
            count += 1

    await db.commit()
    return count


# ── Subscription CRUD ─────────────────────────────────────────────────────────

async def list_subscriptions(
    db: AsyncSession,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscription]:
    q = select(Subscription).order_by(desc(Subscription.created_at))
    if active_only:
        q = q.where(Subscription.active_flag == True)  # noqa: E712
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_subscription(db: AsyncSession, sub_id: UUID) -> Optional[Subscription]:
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    return result.scalar_one_or_none()


async def create_subscription(db: AsyncSession, data: SubscriptionCreate) -> Subscription:
    sub = Subscription(**data.model_dump())
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def update_subscription(
    db: AsyncSession, sub_id: UUID, data: SubscriptionUpdate
) -> Optional[Subscription]:
    sub = await get_subscription(db, sub_id)
    if not sub:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(sub, field, val)
    await db.commit()
    await db.refresh(sub)
    return sub


async def delete_subscription(db: AsyncSession, sub_id: UUID) -> bool:
    sub = await get_subscription(db, sub_id)
    if not sub:
        return False
    await db.delete(sub)
    await db.commit()
    return True


async def test_subscription(db: AsyncSession, sub_id: UUID) -> Dict[str, Any]:
    """Send a test ping to subscription endpoint."""
    sub = await get_subscription(db, sub_id)
    if not sub:
        return {"success": False, "error": "Subscription not found"}

    test_payload = _build_event_envelope(
        event_id=uuid4(),
        event_code="test.ping",
        module="system",
        occurred_at=datetime.now(timezone.utc),
        payload={"message": "Webhook test from FMCG ERP"},
    )
    body_bytes = json.dumps(test_payload).encode()
    timestamp = str(int(time.time()))
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "X-Webhook-Event": "test.ping",
        "X-Webhook-Test": "true",
        "X-Webhook-Timestamp": timestamp,
    }
    if sub.auth_type == AuthType.BEARER and sub.secret_key:
        headers["Authorization"] = f"Bearer {sub.secret_key}"
    elif sub.auth_type == AuthType.HMAC and sub.secret_key:
        headers["X-Webhook-Signature"] = _sign_payload(sub.secret_key, body_bytes, timestamp)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(sub.endpoint_url, content=body_bytes, headers=headers)
        return {"success": 200 <= resp.status_code < 300, "status_code": resp.status_code, "response": resp.text[:500]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Delivery queries ──────────────────────────────────────────────────────────

async def list_deliveries(
    db: AsyncSession,
    subscription_id: Optional[UUID] = None,
    event_log_id: Optional[UUID] = None,
    status: Optional[DeliveryStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DeliveryAttempt]:
    q = select(DeliveryAttempt).order_by(desc(DeliveryAttempt.created_at))
    if subscription_id:
        q = q.where(DeliveryAttempt.subscription_id == subscription_id)
    if event_log_id:
        q = q.where(DeliveryAttempt.event_log_id == event_log_id)
    if status:
        q = q.where(DeliveryAttempt.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def manual_retry_delivery(db: AsyncSession, delivery_id: UUID) -> Optional[DeliveryAttempt]:
    result = await db.execute(select(DeliveryAttempt).where(DeliveryAttempt.id == delivery_id))
    old = result.scalar_one_or_none()
    if not old:
        return None
    event_log_r = await db.execute(select(EventLog).where(EventLog.id == old.event_log_id))
    event_log = event_log_r.scalar_one_or_none()
    sub_r = await db.execute(select(Subscription).where(Subscription.id == old.subscription_id))
    sub = sub_r.scalar_one_or_none()
    if not event_log or not sub:
        return None
    new_attempt = DeliveryAttempt(
        event_log_id=old.event_log_id,
        subscription_id=old.subscription_id,
        attempt_no=old.attempt_no + 1,
        status=DeliveryStatus.PENDING,
        error_message="[manual retry]",
    )
    db.add(new_attempt)
    old.status = DeliveryStatus.FAILED
    await db.flush()
    await _deliver_attempt(db, new_attempt, event_log, sub)
    await db.commit()
    return new_attempt


# ── Inbound Endpoints ─────────────────────────────────────────────────────────

async def list_inbound_endpoints(db: AsyncSession) -> List[InboundEndpoint]:
    result = await db.execute(select(InboundEndpoint).order_by(InboundEndpoint.endpoint_path))
    return list(result.scalars().all())


async def create_inbound_endpoint(db: AsyncSession, data: InboundEndpointCreate) -> InboundEndpoint:
    obj = InboundEndpoint(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_inbound_endpoint_by_path(db: AsyncSession, path: str) -> Optional[InboundEndpoint]:
    result = await db.execute(
        select(InboundEndpoint).where(
            and_(InboundEndpoint.endpoint_path == path, InboundEndpoint.active_flag == True)  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


def verify_inbound_signature(endpoint: InboundEndpoint, body: bytes, sig_header: Optional[str]) -> bool:
    if endpoint.auth_type == AuthType.NONE:
        return True
    if endpoint.auth_type == AuthType.HMAC:
        if not endpoint.secret_key or not sig_header:
            return False
        # Support both timestamp-prefixed and raw HMAC
        expected = hmac.new(endpoint.secret_key.encode(), body, hashlib.sha256).hexdigest()
        received = sig_header.replace("sha256=", "")
        return hmac.compare_digest(expected, received)
    if endpoint.auth_type == AuthType.BEARER:
        if not endpoint.secret_key or not sig_header:
            return False
        return hmac.compare_digest(endpoint.secret_key, sig_header.replace("Bearer ", ""))
    return True


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    t24h = now - timedelta(hours=24)
    t7d = now - timedelta(days=7)

    events_24h_r = await db.execute(select(func.count()).where(EventLog.created_at >= t24h))
    events_24h = events_24h_r.scalar_one()

    events_7d_r = await db.execute(select(func.count()).where(EventLog.created_at >= t7d))
    events_7d = events_7d_r.scalar_one()

    deliveries_24h_r = await db.execute(
        select(func.count()).where(DeliveryAttempt.created_at >= t24h)
    )
    deliveries_24h = deliveries_24h_r.scalar_one()

    sent_24h_r = await db.execute(
        select(func.count()).where(
            and_(DeliveryAttempt.status == DeliveryStatus.SENT, DeliveryAttempt.created_at >= t24h)
        )
    )
    sent_24h = sent_24h_r.scalar_one()
    success_rate = (sent_24h / deliveries_24h * 100) if deliveries_24h > 0 else 100.0

    pending_r = await db.execute(
        select(func.count()).where(DeliveryAttempt.status.in_([DeliveryStatus.PENDING, DeliveryStatus.RETRYING]))
    )
    pending = pending_r.scalar_one()

    dead_r = await db.execute(
        select(func.count()).where(DeliveryAttempt.status == DeliveryStatus.DEAD_LETTER)
    )
    dead = dead_r.scalar_one()

    active_subs_r = await db.execute(
        select(func.count()).where(Subscription.active_flag == True)  # noqa: E712
    )
    active_subs = active_subs_r.scalar_one()

    top_events_r = await db.execute(
        select(EventLog.event_code, func.count().label("cnt"))
        .where(EventLog.created_at >= t24h)
        .group_by(EventLog.event_code)
        .order_by(desc("cnt"))
        .limit(10)
    )
    top_events = [{"event_code": r[0], "count": r[1]} for r in top_events_r.all()]

    recent_failures_r = await db.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]))
        .order_by(desc(DeliveryAttempt.created_at))
        .limit(5)
    )
    recent_failures = [
        {"id": str(r.id), "subscription_id": str(r.subscription_id),
         "status": r.status.value, "error": r.error_message}
        for r in recent_failures_r.scalars().all()
    ]

    return {
        "total_events_24h": events_24h,
        "total_events_7d": events_7d,
        "total_deliveries_24h": deliveries_24h,
        "delivery_success_rate_24h": round(success_rate, 2),
        "pending_deliveries": pending,
        "dead_letter_count": dead,
        "active_subscriptions": active_subs,
        "top_events": top_events,
        "recent_failures": recent_failures,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_report(db: AsyncSession, days: int = 7) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_r = await db.execute(
        select(func.count()).where(DeliveryAttempt.created_at >= since)
    )
    total = total_r.scalar_one()

    sent_r = await db.execute(
        select(func.count()).where(
            and_(DeliveryAttempt.status == DeliveryStatus.SENT, DeliveryAttempt.created_at >= since)
        )
    )
    sent = sent_r.scalar_one()

    failed_r = await db.execute(
        select(func.count()).where(
            and_(DeliveryAttempt.status == DeliveryStatus.FAILED, DeliveryAttempt.created_at >= since)
        )
    )
    failed = failed_r.scalar_one()

    dead_r = await db.execute(
        select(func.count()).where(
            and_(DeliveryAttempt.status == DeliveryStatus.DEAD_LETTER, DeliveryAttempt.created_at >= since)
        )
    )
    dead = dead_r.scalar_one()

    avg_retry_r = await db.execute(
        select(func.avg(DeliveryAttempt.attempt_no)).where(DeliveryAttempt.created_at >= since)
    )
    avg_retry = float(avg_retry_r.scalar_one() or 1.0)

    top_producers_r = await db.execute(
        select(EventLog.module, func.count().label("cnt"))
        .where(EventLog.created_at >= since)
        .group_by(EventLog.module)
        .order_by(desc("cnt"))
        .limit(10)
    )
    top_producers = [{"module": r[0], "count": r[1]} for r in top_producers_r.all()]

    # Latency per subscription
    latency_r = await db.execute(
        select(DeliveryAttempt.subscription_id, func.avg(DeliveryAttempt.duration_ms).label("avg_ms"))
        .where(
            and_(
                DeliveryAttempt.created_at >= since,
                DeliveryAttempt.duration_ms.isnot(None),
            )
        )
        .group_by(DeliveryAttempt.subscription_id)
        .limit(20)
    )
    latency = [{"subscription_id": str(r[0]), "avg_latency_ms": round(float(r[1] or 0), 1)} for r in latency_r.all()]

    # Failure reasons
    errors_r = await db.execute(
        select(DeliveryAttempt.response_status, func.count().label("cnt"))
        .where(
            and_(
                DeliveryAttempt.created_at >= since,
                DeliveryAttempt.response_status.isnot(None),
                DeliveryAttempt.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
            )
        )
        .group_by(DeliveryAttempt.response_status)
        .order_by(desc("cnt"))
        .limit(10)
    )
    failure_reasons = [{"http_status": r[0], "count": r[1]} for r in errors_r.all()]

    return {
        "delivery_success_rate": round((sent / total * 100) if total > 0 else 100.0, 2),
        "total_delivered": sent,
        "total_failed": failed,
        "total_dead_letter": dead,
        "avg_retry_count": round(avg_retry, 2),
        "top_event_producers": top_producers,
        "failure_reasons": failure_reasons,
        "subscription_latency": latency,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def ai_health_monitor(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 1: Detect failing endpoints, latency spikes, high retry patterns."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # Subscriptions with high failure rate
    subs_r = await db.execute(
        select(Subscription).where(Subscription.active_flag == True)  # noqa: E712
    )
    subs = list(subs_r.scalars().all())

    failing = []
    for sub in subs:
        total_r = await db.execute(
            select(func.count()).where(
                and_(DeliveryAttempt.subscription_id == sub.id, DeliveryAttempt.created_at >= since)
            )
        )
        total = total_r.scalar_one()
        if total == 0:
            continue
        failed_r = await db.execute(
            select(func.count()).where(
                and_(
                    DeliveryAttempt.subscription_id == sub.id,
                    DeliveryAttempt.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
                    DeliveryAttempt.created_at >= since,
                )
            )
        )
        failed = failed_r.scalar_one()
        failure_rate = failed / total * 100 if total > 0 else 0

        avg_lat_r = await db.execute(
            select(func.avg(DeliveryAttempt.duration_ms)).where(
                and_(
                    DeliveryAttempt.subscription_id == sub.id,
                    DeliveryAttempt.status == DeliveryStatus.SENT,
                    DeliveryAttempt.created_at >= since,
                )
            )
        )
        avg_lat = float(avg_lat_r.scalar_one() or 0)

        if failure_rate > 30 or avg_lat > 5000:
            failing.append({
                "subscription_id": str(sub.id),
                "name": sub.name,
                "endpoint_url": sub.endpoint_url,
                "failure_rate_pct": round(failure_rate, 1),
                "avg_latency_ms": round(avg_lat, 0),
                "recommendation": (
                    "Endpoint consistently failing — verify URL, auth, and server health."
                    if failure_rate > 30 else "High latency detected — consider increasing timeout."
                ),
            })

    dead_total_r = await db.execute(
        select(func.count()).where(
            and_(DeliveryAttempt.status == DeliveryStatus.DEAD_LETTER, DeliveryAttempt.created_at >= since)
        )
    )
    dead_total = dead_total_r.scalar_one()

    return {
        "agent": "Integration Health Monitor",
        "window_hours": 24,
        "failing_subscriptions": failing,
        "dead_letter_count_24h": dead_total,
        "summary": f"{len(failing)} subscription(s) need attention. {dead_total} events in dead-letter queue.",
    }


async def ai_payload_advisor(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 2: Suggest payload field improvements per event type."""
    # Find most published event codes
    result = await db.execute(
        select(EventLog.event_code, func.count().label("cnt"))
        .group_by(EventLog.event_code)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_events = result.all()

    recommendations = []
    for event_code, cnt in top_events:
        # Sample 1 event payload
        sample_r = await db.execute(
            select(EventLog).where(EventLog.event_code == event_code).limit(1)
        )
        sample = sample_r.scalar_one_or_none()
        if not sample:
            continue
        envelope = _canonical_event_payload(sample)
        data = envelope.get("data", {})
        keys = list(data.keys()) if isinstance(data, dict) else []
        missing = []
        if not envelope.get("reference", {}).get("id"):
            missing.append("reference.id in event envelope")
        if len(keys) < 3:
            missing.append("more context fields (timestamps, changed_fields)")
        recommendations.append({
            "event_code": event_code,
            "publish_count": cnt,
            "current_fields": [k for k in keys if not k.startswith("_")],
            "suggestions": missing or ["Payload looks complete"],
        })

    return {
        "agent": "Payload Advisor",
        "recommendations": recommendations,
        "tip": "Include actor_id, changed_fields, and before/after values in update events for better consumer experience.",
    }


async def ai_anomaly_detector(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 3: Detect unusual event volumes and error bursts."""
    now = datetime.now(timezone.utc)
    t1h = now - timedelta(hours=1)
    t24h = now - timedelta(hours=24)

    # Compare last hour vs 24h average
    last_hour_r = await db.execute(select(func.count()).where(EventLog.created_at >= t1h))
    last_hour = last_hour_r.scalar_one()

    total_24h_r = await db.execute(select(func.count()).where(EventLog.created_at >= t24h))
    total_24h = total_24h_r.scalar_one()
    hourly_avg = total_24h / 24 if total_24h else 0

    volume_anomaly = last_hour > hourly_avg * 3 if hourly_avg > 0 else False

    # Error burst: failures in last 1h
    errors_1h_r = await db.execute(
        select(func.count()).where(
            and_(
                DeliveryAttempt.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
                DeliveryAttempt.created_at >= t1h,
            )
        )
    )
    errors_1h = errors_1h_r.scalar_one()

    errors_24h_r = await db.execute(
        select(func.count()).where(
            and_(
                DeliveryAttempt.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
                DeliveryAttempt.created_at >= t24h,
            )
        )
    )
    errors_24h = errors_24h_r.scalar_one()
    error_avg = errors_24h / 24 if errors_24h else 0
    error_burst = errors_1h > error_avg * 3 if error_avg > 0 else (errors_1h > 20)

    anomalies = []
    if volume_anomaly:
        anomalies.append({
            "type": "HIGH_EVENT_VOLUME",
            "message": f"Last hour had {last_hour} events vs hourly avg of {hourly_avg:.1f}",
            "severity": "WARNING",
        })
    if error_burst:
        anomalies.append({
            "type": "ERROR_BURST",
            "message": f"Last hour had {errors_1h} delivery errors vs hourly avg of {error_avg:.1f}",
            "severity": "HIGH",
        })

    return {
        "agent": "Anomaly Detector",
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "last_hour_events": last_hour,
        "hourly_avg_events": round(hourly_avg, 1),
        "last_hour_errors": errors_1h,
        "note": "Anomalies are reported only — no automatic action taken.",
    }
