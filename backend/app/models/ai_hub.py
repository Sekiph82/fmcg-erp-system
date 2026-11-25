"""M45 access tokens for add-ins and AI clients (T012/T022), MCP write requests (T022), agents (T008/T009),
prospecting (T001) and research/enrichment (T002/T003)."""
import uuid

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PersonalAccessToken(Base):
    """A user's token for the Outlook/Gmail add-in or an MCP client. Acts with the user's own permissions, narrowed
    further by scopes. Only the SHA-256 is stored; the token is shown once."""
    __tablename__ = "personal_access_tokens"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name               = Column(String(100), nullable=False)
    token_hash         = Column(String(64), nullable=False, unique=True)
    prefix             = Column(String(12), nullable=False)
    scopes             = Column(JSON, nullable=False)          # e.g. ["crm.addin"], ["mcp.read", "mcp.write"]
    rate_limit_per_min = Column(Integer, nullable=False, default=60)
    expires_at         = Column(DateTime(timezone=True), nullable=False)
    revoked_at         = Column(DateTime(timezone=True), nullable=True)
    last_used_at       = Column(DateTime(timezone=True), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIActionRequest(Base):
    """A write proposed by an AI client or agent; nothing happens until a person approves it."""
    __tablename__ = "ai_action_requests"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source       = Column(String(10), nullable=False)          # MCP | AGENT | PROSPECT
    source_ref   = Column(String(100), nullable=True)          # token id / agent run id / suggestion id
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action       = Column(String(40), nullable=False)          # create_task | send_email | update_field
    arguments    = Column(JSON, nullable=False)
    summary      = Column(String(500), nullable=False)
    status       = Column(String(10), nullable=False, default="PENDING")   # PENDING | APPROVED | REJECTED | DONE | FAILED
    decided_by   = Column(String(100), nullable=True)
    decided_at   = Column(DateTime(timezone=True), nullable=True)
    result       = Column(JSON, nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
