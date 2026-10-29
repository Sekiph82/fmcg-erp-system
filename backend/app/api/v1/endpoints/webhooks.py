"""Webhook / Event Engine endpoints."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_superuser
from app.models.webhook import DeliveryStatus
from app.schemas.webhook import (
    DeliveryAttemptOut, EventDefinitionCreate, EventDefinitionOut, EventDefinitionUpdate,
    EventDefinitionVersionOut,
    EventLogOut, InboundEndpointCreate, InboundEndpointOut,
    PublishEventRequest, ReplayRequest, RetryRequest,
    SubscriptionCreate, SubscriptionOut, SubscriptionUpdate,
    WebhookDashboard, WebhookReport,
)
import app.services.webhook_service as svc

router = APIRouter()


def _event_log_response(event_log):
    """Normalize historical payloads for the stable public event response."""
    return EventLogOut(
        id=event_log.id,
        event_code=event_log.event_code,
        module=event_log.module,
        reference_type=event_log.reference_type,
        reference_id=event_log.reference_id,
        payload=svc._canonical_event_payload(event_log),
        actor_id=event_log.actor_id,
        partition_key=event_log.partition_key,
        created_at=event_log.created_at,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=WebhookDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Event Definitions ─────────────────────────────────────────────────────────

@router.get("/event-definitions", response_model=List[EventDefinitionOut])
async def list_event_definitions(
    module: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_event_definitions(db, module=module, active_only=active_only, skip=skip, limit=limit)


@router.post("/event-definitions", response_model=EventDefinitionOut, status_code=201)
async def create_event_definition(
    data: EventDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    try:
        return await svc.create_event_definition(db, data, actor_id=str(current_user.id))
    except svc.EventSchemaGovernanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/event-definitions/{definition_id}", response_model=EventDefinitionOut)
async def update_event_definition(
    definition_id: UUID,
    data: EventDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    try:
        definition = await svc.update_event_definition(
            db, definition_id, data, actor_id=str(current_user.id)
        )
    except svc.EventSchemaGovernanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not definition:
        raise HTTPException(status_code=404, detail="Event definition not found")
    return definition


@router.get(
    "/event-definitions/{definition_id}/versions",
    response_model=List[EventDefinitionVersionOut],
)
async def list_event_definition_versions(
    definition_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    versions = await svc.list_event_definition_versions(db, definition_id)
    if versions is None:
        raise HTTPException(status_code=404, detail="Event definition not found")
    return versions


@router.post("/event-definitions/seed", status_code=200)
async def seed_event_definitions(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_superuser),
):
    await svc.seed_event_definitions(db)
    return {"detail": "Standard event definitions seeded"}


# ── Event Logs ────────────────────────────────────────────────────────────────

@router.get("/events", response_model=List[EventLogOut])
async def list_events(
    event_code: Optional[str] = None,
    module: Optional[str] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, desc, and_
    from app.models.webhook import EventLog
    q = select(EventLog).order_by(desc(EventLog.created_at))
    if event_code:
        q = q.where(EventLog.event_code == event_code)
    if module:
        q = q.where(EventLog.module == module)
    if reference_type:
        q = q.where(EventLog.reference_type == reference_type)
    if reference_id:
        q = q.where(EventLog.reference_id == reference_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return [_event_log_response(event) for event in result.scalars().all()]


@router.get("/events/{event_id}", response_model=EventLogOut)
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.webhook import EventLog
    result = await db.execute(select(EventLog).where(EventLog.id == event_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Event not found")
    return _event_log_response(obj)


@router.post("/events/publish", response_model=EventLogOut, status_code=201)
async def publish_event(
    data: PublishEventRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Publish an event manually (or from internal module calls)."""
    try:
        result = await svc.publish_event(
            db,
            data.event_code,
            data.payload,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            actor_id=data.actor_id,
            partition_key=data.partition_key,
            idempotency_key=data.idempotency_key,
            correlation_id=data.correlation_id,
            causation_id=data.causation_id,
        )
    except svc.EventPayloadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except svc.EventSchemaGovernanceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except svc.EventIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except svc.EventIdentifierValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if getattr(result, "_idempotency_replayed", False):
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotency-Replayed"] = "true"
    return result


@router.post("/events/replay")
async def replay_events(
    data: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_superuser),
):
    count = await svc.replay_events(db, data)
    return {"detail": f"Queued {count} delivery attempt(s)"}


# ── Subscriptions ─────────────────────────────────────────────────────────────

@router.get("/subscriptions", response_model=List[SubscriptionOut])
async def list_subscriptions(
    active_only: bool = False,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_subscriptions(db, active_only=active_only, skip=skip, limit=limit)


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
async def create_subscription(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_subscription(db, data)


@router.get("/subscriptions/{sub_id}", response_model=SubscriptionOut)
async def get_subscription(sub_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_subscription(db, sub_id)
    if not obj:
        raise HTTPException(404, "Subscription not found")
    return obj


@router.patch("/subscriptions/{sub_id}", response_model=SubscriptionOut)
async def update_subscription(sub_id: UUID, data: SubscriptionUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_subscription(db, sub_id, data)
    if not obj:
        raise HTTPException(404, "Subscription not found")
    return obj


@router.delete("/subscriptions/{sub_id}", status_code=204)
async def delete_subscription(sub_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_subscription(db, sub_id)
    if not ok:
        raise HTTPException(404, "Subscription not found")


@router.post("/subscriptions/{sub_id}/test")
async def test_subscription(sub_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.test_subscription(db, sub_id)


# ── Delivery Attempts ─────────────────────────────────────────────────────────

@router.get("/deliveries", response_model=List[DeliveryAttemptOut])
async def list_deliveries(
    subscription_id: Optional[UUID] = None,
    event_log_id: Optional[UUID] = None,
    delivery_status: Optional[DeliveryStatus] = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_deliveries(
        db,
        subscription_id=subscription_id,
        event_log_id=event_log_id,
        status=delivery_status,
        skip=skip,
        limit=limit,
    )


@router.get("/deliveries/dead-letter", response_model=List[DeliveryAttemptOut])
async def list_dead_letter(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_deliveries(db, status=DeliveryStatus.DEAD_LETTER, skip=skip, limit=limit)


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryAttemptOut)
async def retry_delivery(delivery_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.manual_retry_delivery(db, delivery_id)
    if not obj:
        raise HTTPException(404, "Delivery not found")
    return obj


@router.post("/deliveries/process-pending")
async def process_pending(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_superuser),
):
    """Trigger processing of pending delivery queue (background sweep)."""
    processed = await svc.process_pending_deliveries(db, limit=limit)
    retried = await svc.process_retry_deliveries(db, limit=limit)
    return {"processed": processed, "retried": retried}


# ── Inbound Endpoints ─────────────────────────────────────────────────────────

@router.get("/inbound-endpoints", response_model=List[InboundEndpointOut])
async def list_inbound_endpoints(db: AsyncSession = Depends(get_db)):
    return await svc.list_inbound_endpoints(db)


@router.post("/inbound-endpoints", response_model=InboundEndpointOut, status_code=201)
async def create_inbound_endpoint(
    data: InboundEndpointCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_superuser),
):
    return await svc.create_inbound_endpoint(db, data)


@router.api_route("/inbound/{endpoint_path:path}", methods=["POST", "PUT", "GET"])
async def receive_inbound_webhook(
    endpoint_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Dynamic inbound webhook receiver. Validates auth and logs event."""
    endpoint = await svc.get_inbound_endpoint_by_path(db, endpoint_path)
    if not endpoint:
        raise HTTPException(404, f"Inbound endpoint '{endpoint_path}' not found")

    body = await request.body()
    sig_header = request.headers.get("X-Webhook-Signature") or request.headers.get("Authorization")

    if not svc.verify_inbound_signature(endpoint, body, sig_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        payload = json.loads(body) if body else {}
    except Exception:
        payload = {"raw_body": body.decode(errors="replace")[:5000]}

    # Log as event
    try:
        await svc.stage_event(
            db,
            event_code=f"inbound.{endpoint.handler_module or endpoint_path}",
            payload=payload,
            reference_type="inbound_endpoint",
            reference_id=endpoint_path,
            module="inbound",
            idempotency_key=request.headers.get("Idempotency-Key"),
            correlation_id=request.headers.get("X-Correlation-ID"),
            causation_id=request.headers.get("X-Causation-ID"),
        )
    except svc.EventIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except svc.EventIdentifierValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Update receive counter
    endpoint.receive_count = (endpoint.receive_count or 0) + 1
    from datetime import datetime, timezone
    endpoint.last_received_at = datetime.now(timezone.utc)
    await db.commit()

    return {"received": True, "endpoint": endpoint_path}


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports", response_model=WebhookReport)
async def get_report(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_report(db, days=days)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/ai/health-monitor")
async def ai_health_monitor(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_health_monitor(db)


@router.get("/ai/payload-advisor")
async def ai_payload_advisor(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_payload_advisor(db)


@router.get("/ai/anomaly-detector")
async def ai_anomaly_detector(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_anomaly_detector(db)
