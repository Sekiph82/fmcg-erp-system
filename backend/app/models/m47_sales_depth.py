"""M47.S01.T009 sales depth: task calendar links, 1-to-1 video messages, meeting recaps, sales AI budget usage.

The trained deal-win model reuses ci_models (kind DEAL_WIN); imported contracts reuse contracts / cpq_renewals / documents.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CRMTaskCalendarLink(Base):
    """An open CRM task (crm_activities row) pushed to its assignee's Google / Outlook calendar.
    activity_id has no FK on purpose: a deleted task leaves the link so the provider event can still be removed."""
    __tablename__ = "crm_task_calendar_links"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    connection_id     = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    external_event_id = Column(String(1024), nullable=True)
    pushed_hash       = Column(String(64), nullable=True)      # digest of the subject/due last written
    updated_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SalesVideoMessage(Base):
    """A short video for ONE contact, served only through an expiring, revocable token link (SHA-256 digest stored)."""
    __tablename__ = "sales_video_messages"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id      = Column(UUID(as_uuid=True), ForeignKey("cms_media.id", ondelete="CASCADE"), nullable=False)
    title         = Column(String(200), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_name  = Column(String(200), nullable=True)
    customer_id   = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    crm_record_id = Column(UUID(as_uuid=True), nullable=True)
    token_hash    = Column(String(64), nullable=False, unique=True)
    expires_at    = Column(DateTime(timezone=True), nullable=False)
    revoked_at    = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SalesVideoView(Base):
    """One view of a video message (30-minute de-dupe per keyed viewer hash; no IP stored)."""
    __tablename__ = "sales_video_views"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id    = Column(UUID(as_uuid=True), ForeignKey("sales_video_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_hash = Column(String(64), nullable=False)
    seconds     = Column(Integer, nullable=False, default=0)
    at          = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class MeetingRecap(Base):
    """Transcript of a meeting and its recap (decisions / action items, each quoting the transcript)."""
    __tablename__ = "meeting_recaps"

    meeting_id  = Column(UUID(as_uuid=True), ForeignKey("meeting_records.id", ondelete="CASCADE"), primary_key=True)
    transcript  = Column(Text, nullable=False)
    source      = Column(String(20), nullable=False)            # TEXT_UPLOAD | TRANSCRIPTION
    recap       = Column(JSON, nullable=False, default=dict)    # {decisions: [...], action_items: [...]}
    engine      = Column(String(20), nullable=False, default="rules")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(100), nullable=True)
    task_ids    = Column(JSON, nullable=False, default=list)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SalesAiUsage(Base):
    """Monthly spend of optional sales AI (recaps, quote drafts) against the configured budget (atomic reservation)."""
    __tablename__ = "sales_ai_usage"

    month = Column(String(7), primary_key=True)                 # YYYY-MM
    spent = Column(Numeric(12, 4), nullable=False, default=0)
    calls = Column(Integer, nullable=False, default=0)
