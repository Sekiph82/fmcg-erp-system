"""M47.S01.T008 automation and data depth: inbound workflow webhooks and custom web-event definitions."""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CRMWorkflowHook(Base):
    """Inbound webhook of one workflow. The token is shown once; only its SHA-256 digest is stored."""
    __tablename__ = "crm_workflow_hooks"

    workflow_id  = Column(UUID(as_uuid=True), ForeignKey("crm_workflows.id", ondelete="CASCADE"), primary_key=True)
    token_digest = Column(String(64), nullable=False)
    token_hint   = Column(String(8), nullable=False)          # last characters, to tell tokens apart
    created_by   = Column(String(100), nullable=True)
    rotated_at   = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class WebEventDefinition(Base):
    """A named custom website event and the properties it may carry (name -> string | number | boolean)."""
    __tablename__ = "web_event_definitions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    properties  = Column(JSON, nullable=False, default=dict)
    active      = Column(Boolean, nullable=False, default=True)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), nullable=True)


class WebEventProperty(Base):
    """Validated properties of one collected custom event; deleted with the event (forget / retention)."""
    __tablename__ = "web_event_properties"

    event_id   = Column(UUID(as_uuid=True), ForeignKey("web_events.id", ondelete="CASCADE"), primary_key=True)
    properties = Column(JSON, nullable=False)
