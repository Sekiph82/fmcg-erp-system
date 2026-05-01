from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl

from app.models.webhook import AuthType, DeliveryStatus, HttpMethod


# ── Event Definitions ─────────────────────────────────────────────────────────

class EventDefinitionCreate(BaseModel):
    event_code: str
    event_name: str
    module: str
    description: Optional[str] = None
    payload_schema: Optional[Dict[str, Any]] = None
    active_flag: bool = True


class EventDefinitionOut(BaseModel):
    id: UUID
    event_code: str
    event_name: str
    module: str
    description: Optional[str] = None
    payload_schema: Optional[Dict[str, Any]] = None
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Event Logs ────────────────────────────────────────────────────────────────

class EventLogOut(BaseModel):
    id: UUID
    event_code: str
    module: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    payload: Dict[str, Any]
    actor_id: Optional[str] = None
    partition_key: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishEventRequest(BaseModel):
    event_code: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    payload: Dict[str, Any] = {}
    actor_id: Optional[str] = None
    partition_key: Optional[str] = None


class ReplayRequest(BaseModel):
    event_ids: Optional[List[UUID]] = None          # replay specific events
    event_code: Optional[str] = None                # replay all events of a type
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    subscription_ids: Optional[List[UUID]] = None   # replay to specific subs only


# ── Subscriptions ─────────────────────────────────────────────────────────────

class FilterRule(BaseModel):
    field: str      # JSON path like "payload.status"
    op: str         # eq / ne / gt / lt / contains / in
    value: Any


class SubscriptionCreate(BaseModel):
    name: str
    endpoint_url: str
    http_method: HttpMethod = HttpMethod.POST
    headers: Optional[Dict[str, str]] = None
    auth_type: AuthType = AuthType.NONE
    secret_key: Optional[str] = None
    auth_user: Optional[str] = None
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: int = 5
    timeout_seconds: int = 30
    active_flag: bool = True


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    endpoint_url: Optional[str] = None
    http_method: Optional[HttpMethod] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[AuthType] = None
    secret_key: Optional[str] = None
    auth_user: Optional[str] = None
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    active_flag: Optional[bool] = None


class SubscriptionOut(BaseModel):
    id: UUID
    name: str
    endpoint_url: str
    http_method: HttpMethod
    headers: Optional[Dict[str, Any]] = None
    auth_type: AuthType
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: int
    timeout_seconds: int
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Delivery Attempts ─────────────────────────────────────────────────────────

class DeliveryAttemptOut(BaseModel):
    id: UUID
    event_log_id: UUID
    subscription_id: UUID
    attempt_no: int
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempted_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    status: DeliveryStatus
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RetryRequest(BaseModel):
    delivery_ids: Optional[List[UUID]] = None
    subscription_id: Optional[UUID] = None


# ── Inbound Endpoints ─────────────────────────────────────────────────────────

class InboundEndpointCreate(BaseModel):
    name: str
    endpoint_path: str
    method: HttpMethod = HttpMethod.POST
    auth_type: AuthType = AuthType.NONE
    secret_key: Optional[str] = None
    handler_module: Optional[str] = None
    description: Optional[str] = None
    active_flag: bool = True


class InboundEndpointOut(BaseModel):
    id: UUID
    name: str
    endpoint_path: str
    method: HttpMethod
    auth_type: AuthType
    handler_module: Optional[str] = None
    description: Optional[str] = None
    active_flag: bool
    last_received_at: Optional[datetime] = None
    receive_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class WebhookDashboard(BaseModel):
    total_events_24h: int
    total_events_7d: int
    total_deliveries_24h: int
    delivery_success_rate_24h: float
    pending_deliveries: int
    dead_letter_count: int
    active_subscriptions: int
    top_events: List[Dict[str, Any]]
    recent_failures: List[Dict[str, Any]]


# ── Reports ───────────────────────────────────────────────────────────────────

class WebhookReport(BaseModel):
    delivery_success_rate: float
    total_delivered: int
    total_failed: int
    total_dead_letter: int
    avg_retry_count: float
    top_event_producers: List[Dict[str, Any]]
    failure_reasons: List[Dict[str, Any]]
    subscription_latency: List[Dict[str, Any]]
