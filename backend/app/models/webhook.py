from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class HttpMethod(str, PyEnum):
    POST = "POST"
    PUT = "PUT"


class AuthType(str, PyEnum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    HMAC = "hmac"


class DeliveryStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class EventDefinition(Base, TimestampMixin):
    """Catalog of all event types in the system."""
    __tablename__ = "webhook_event_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_code = Column(String(100), unique=True, nullable=False, index=True)
    event_name = Column(String(255), nullable=False)
    module = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    payload_schema = Column(JSONB, nullable=True)        # JSON Schema for docs
    active_flag = Column(Boolean, default=True, nullable=False)

    logs = relationship("EventLog", back_populates="definition")


class EventLog(Base, TimestampMixin):
    """Immutable log of every published event."""
    __tablename__ = "webhook_event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_def_id = Column(UUID(as_uuid=True), ForeignKey("webhook_event_definitions.id", ondelete="SET NULL"), nullable=True, index=True)
    event_code = Column(String(100), nullable=False, index=True)    # denormalized for fast filter
    module = Column(String(100), nullable=False, index=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String(100), nullable=True, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    actor_id = Column(String(100), nullable=True)                   # user who triggered
    partition_key = Column(String(100), nullable=True, index=True)  # for ordering guarantees
    sequence_no = Column(Integer, nullable=True)

    definition = relationship("EventDefinition", back_populates="logs")
    deliveries = relationship("DeliveryAttempt", back_populates="event_log", cascade="all, delete-orphan")


class Subscription(Base, TimestampMixin):
    """Outbound webhook subscription."""
    __tablename__ = "webhook_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    endpoint_url = Column(String(2048), nullable=False)
    http_method = Column(Enum(HttpMethod), default=HttpMethod.POST, nullable=False)
    headers = Column(JSONB, nullable=True, default=dict)             # custom headers
    auth_type = Column(Enum(AuthType), default=AuthType.NONE, nullable=False)
    secret_key = Column(String(512), nullable=True)                 # bearer token / hmac secret / basic pass
    auth_user = Column(String(255), nullable=True)                  # basic auth username
    filter_expression = Column(JSONB, nullable=True)                # [{field, op, value}]
    event_codes = Column(JSONB, nullable=True)                      # list of event codes; null = all
    transform_template = Column(JSONB, nullable=True)               # field mapping {target: source}
    max_retries = Column(Integer, default=5, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    active_flag = Column(Boolean, default=True, nullable=False)

    deliveries = relationship("DeliveryAttempt", back_populates="subscription", cascade="all, delete-orphan")


class DeliveryAttempt(Base, TimestampMixin):
    """Per-event per-subscription delivery record."""
    __tablename__ = "webhook_delivery_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_log_id = Column(UUID(as_uuid=True), ForeignKey("webhook_event_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_no = Column(Integer, default=1, nullable=False)
    request_payload = Column(JSONB, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    attempted_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)

    event_log = relationship("EventLog", back_populates="deliveries")
    subscription = relationship("Subscription", back_populates="deliveries")


class InboundEndpoint(Base, TimestampMixin):
    """Registered inbound webhook receiver."""
    __tablename__ = "webhook_inbound_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    endpoint_path = Column(String(255), unique=True, nullable=False, index=True)  # slug for /webhooks/inbound/{path}
    method = Column(Enum(HttpMethod), default=HttpMethod.POST, nullable=False)
    auth_type = Column(Enum(AuthType), default=AuthType.NONE, nullable=False)
    secret_key = Column(String(512), nullable=True)
    handler_module = Column(String(100), nullable=True)             # internal handler tag (e.g. "payment_confirmation")
    description = Column(Text, nullable=True)
    active_flag = Column(Boolean, default=True, nullable=False)
    last_received_at = Column(DateTime(timezone=True), nullable=True)
    receive_count = Column(Integer, default=0, nullable=False)
