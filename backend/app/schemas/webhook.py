from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator, model_validator

from app.core.config import settings
from app.models.webhook import AuthType, DeliveryStatus, HttpMethod


# ── Event Definitions ─────────────────────────────────────────────────────────

class EventDefinitionCreate(BaseModel):
    event_code: str
    event_name: str
    module: str
    description: Optional[str] = None
    payload_schema: Optional[Dict[str, Any]] = None
    active_flag: bool = True


class EventDefinitionUpdate(BaseModel):
    event_name: Optional[str] = None
    module: Optional[str] = None
    description: Optional[str] = None
    payload_schema: Optional[Dict[str, Any]] = None
    active_flag: Optional[bool] = None
    schema_change_summary: Optional[str] = None


class EventDefinitionOut(BaseModel):
    id: UUID
    event_code: str
    event_name: str
    module: str
    description: Optional[str] = None
    payload_schema: Optional[Dict[str, Any]] = None
    schema_version: int = 1
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EventDefinitionVersionOut(BaseModel):
    id: UUID
    event_def_id: UUID
    schema_version: int
    payload_schema: Optional[Dict[str, Any]] = None
    change_summary: Optional[str] = None
    created_by: Optional[str] = None
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


class DomainEventReference(BaseModel):
    """Business object associated with a domain event, when one exists."""
    type: Optional[str] = None
    id: Optional[str] = None


class DomainEventEnvelope(BaseModel):
    """Versioned event shape used by the webhook event engine."""
    id: UUID
    type: str
    module: str
    schema_version: int = 1
    occurred_at: datetime
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    reference: DomainEventReference
    data: Dict[str, Any]


class PublishEventRequest(BaseModel):
    event_code: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    actor_id: Optional[str] = None
    partition_key: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=255)
    correlation_id: Optional[str] = Field(default=None, max_length=200)
    causation_id: Optional[str] = Field(default=None, max_length=200)

    @field_validator("idempotency_key", "correlation_id", "causation_id")
    @classmethod
    def normalize_optional_event_identifier(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Event identifiers must not be blank.")
        return normalized


class ReplayRequest(BaseModel):
    event_ids: Optional[List[UUID]] = Field(default=None, max_length=200)  # replay specific events
    event_code: Optional[str] = None                # replay all events of a type
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    subscription_ids: Optional[List[UUID]] = Field(default=None, max_length=100)  # replay to specific subs only

    @field_validator("event_code")
    @classmethod
    def normalize_event_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("event_code must not be blank")
        return normalized

    @field_validator("from_dt", "to_dt")
    @classmethod
    def require_timezone_aware_replay_bounds(
        cls, value: Optional[datetime]
    ) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Replay date bounds must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_replay_scope(self) -> "ReplayRequest":
        if self.event_ids is not None and not self.event_ids:
            raise ValueError("event_ids must contain at least one ID when provided")
        if self.subscription_ids is not None and not self.subscription_ids:
            raise ValueError("subscription_ids must contain at least one ID when provided")
        if not (
            self.event_ids
            or self.event_code
            or self.from_dt
            or self.to_dt
        ):
            raise ValueError("Replay requires event IDs, an event code, or a date range")
        if self.from_dt and self.to_dt and self.from_dt > self.to_dt:
            raise ValueError("from_dt must be earlier than or equal to to_dt")
        return self


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
    secret_key: Optional[str] = Field(default=None, max_length=256)
    auth_user: Optional[str] = None
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: int = 5
    timeout_seconds: int = 30
    active_flag: bool = True

    @model_validator(mode="after")
    def validate_hmac_secret(self) -> "SubscriptionCreate":
        if self.auth_type != AuthType.NONE and not self.secret_key:
            raise ValueError("The selected webhook authentication type requires a secret")
        if self.auth_type == AuthType.BASIC and not self.auth_user:
            raise ValueError("Basic authentication requires a username")
        if self.auth_type == AuthType.HMAC and len(self.secret_key or "") < 32:
            raise ValueError("HMAC webhook secrets must contain at least 32 characters")
        return self


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    endpoint_url: Optional[str] = None
    http_method: Optional[HttpMethod] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[AuthType] = None
    secret_key: Optional[str] = Field(default=None, max_length=256)
    auth_user: Optional[str] = None
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    active_flag: Optional[bool] = None

    @model_validator(mode="after")
    def validate_hmac_secret(self) -> "SubscriptionUpdate":
        hmac_selected = self.auth_type == AuthType.HMAC
        secret_supplied = "secret_key" in self.model_fields_set
        if secret_supplied and self.secret_key is not None and hmac_selected and len(self.secret_key) < 32:
            raise ValueError("HMAC webhook secrets must contain at least 32 characters")
        return self


class SubscriptionOut(BaseModel):
    id: UUID
    name: str
    endpoint_url: str
    http_method: HttpMethod
    headers: Optional[Dict[str, Any]] = None
    auth_type: AuthType
    secret_version: int = 1
    previous_secret_expires_at: Optional[datetime] = None
    filter_expression: Optional[List[Dict[str, Any]]] = None
    event_codes: Optional[List[str]] = None
    transform_template: Optional[Dict[str, str]] = None
    max_retries: int
    timeout_seconds: int
    active_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("headers")
    def redact_custom_header_values(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        return {name: "[REDACTED]" for name in value}


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


class WebhookSecretRotationOut(BaseModel):
    secret_key: str
    secret_version: int
    previous_secret_expires_at: datetime


# ── Inbound Endpoints ─────────────────────────────────────────────────────────

class InboundEndpointCreate(BaseModel):
    name: str
    endpoint_path: str
    method: HttpMethod = HttpMethod.POST
    auth_type: AuthType = AuthType.NONE
    secret_key: Optional[str] = Field(default=None, max_length=256)
    handler_module: Optional[str] = None
    description: Optional[str] = None
    active_flag: bool = True

    @model_validator(mode="after")
    def validate_hmac_secret(self) -> "InboundEndpointCreate":
        if self.auth_type == AuthType.BASIC:
            raise ValueError("Inbound Basic authentication is not supported")
        if settings.ENVIRONMENT.lower() == "production" and self.auth_type == AuthType.NONE:
            raise ValueError("Inbound webhook endpoints require authentication in production")
        if self.auth_type != AuthType.NONE and not self.secret_key:
            raise ValueError("The selected webhook authentication type requires a secret")
        if self.auth_type == AuthType.HMAC and len(self.secret_key or "") < 32:
            raise ValueError("HMAC webhook secrets must contain at least 32 characters")
        return self


class InboundEndpointOut(BaseModel):
    id: UUID
    name: str
    endpoint_path: str
    method: HttpMethod
    auth_type: AuthType
    secret_version: int = 1
    previous_secret_expires_at: Optional[datetime] = None
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
