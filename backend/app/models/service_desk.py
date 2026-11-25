"""M45.S01.T019 service desk: agent skills/presence/capacity, SLA policies and timers, CSAT/CES/post-chat surveys,
macros, QA reviews and saved views."""
import uuid

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AgentProfile(Base):
    __tablename__ = "sd_agents"

    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skills           = Column(JSON, nullable=False, default=list)       # e.g. ["quality", "delivery", "swahili"]
    capacity         = Column(Integer, nullable=False, default=10)      # open tickets at most
    presence         = Column(String(10), nullable=False, default="OFFLINE")   # AVAILABLE | AWAY | OFFLINE
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)


class SLAPolicy(Base):
    __tablename__ = "sd_sla_policies"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                 = Column(String(100), nullable=False)
    priority             = Column(String(10), nullable=True)        # None = any
    channel              = Column(String(10), nullable=True)        # ticket source, None = any
    customer_tier        = Column(Integer, nullable=True)           # key-account tier (1 strategic), None = any
    first_response_hours = Column(Float, nullable=False)
    resolution_hours     = Column(Float, nullable=False)
    business_hours       = Column(Boolean, nullable=False, default=True)
    sort                 = Column(Integer, nullable=False, default=100)   # lower wins
    active               = Column(Boolean, nullable=False, default=True)


class TicketSLA(Base):
    __tablename__ = "sd_ticket_sla"

    ticket_id           = Column(UUID(as_uuid=True), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), primary_key=True)
    policy_id           = Column(UUID(as_uuid=True), ForeignKey("sd_sla_policies.id", ondelete="SET NULL"), nullable=True)
    first_response_due  = Column(DateTime(timezone=True), nullable=False)
    resolution_due      = Column(DateTime(timezone=True), nullable=False)
    paused_at           = Column(DateTime(timezone=True), nullable=True)   # waiting for the customer
    breached_first      = Column(Boolean, nullable=False, default=False)
    breached_resolution = Column(Boolean, nullable=False, default=False)


class Survey(Base):
    __tablename__ = "sd_surveys"
    __table_args__ = (UniqueConstraint("kind", "subject_id", name="uq_sd_survey_once"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind        = Column(String(10), nullable=False)          # CSAT | CES | POST_CHAT
    subject_id  = Column(UUID(as_uuid=True), nullable=False)  # ticket id or chat session id
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    agent_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    token_hash  = Column(String(64), nullable=False, unique=True)
    sent_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)
    score       = Column(Integer, nullable=True)              # CSAT 1–5, CES 1–7 (7 = very easy), post-chat 1–5
    comment     = Column(Text, nullable=True)


class Macro(Base):
    __tablename__ = "sd_macros"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(100), nullable=False, unique=True)
    body         = Column(Text, nullable=False)
    set_status   = Column(String(12), nullable=True)
    set_priority = Column(String(10), nullable=True)
    created_by   = Column(String(100), nullable=True)


class QAReview(Base):
    __tablename__ = "sd_qa_reviews"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id   = Column(UUID(as_uuid=True), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer    = Column(String(100), nullable=False)
    scores      = Column(JSON, nullable=False)                # {"accuracy": 1-5, "tone": 1-5, "resolution": 1-5}
    total       = Column(Float, nullable=False)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TicketView(Base):
    """A saved help-desk view (filters) for one agent or shared with the team ("help desk spaces")."""
    __tablename__ = "sd_views"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name     = Column(String(100), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filters  = Column(JSON, nullable=False)                   # {"status": [...], "priority": [...], "category": [...], "mine": bool}
    shared   = Column(Boolean, nullable=False, default=False)
