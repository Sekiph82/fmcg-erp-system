"""M49.S01.T007-T010 organic social: post metrics read back from the networks, author opt-outs, webhook replay ledger,
provider quota counters. Side tables; synthetic/simulated rows are marked by the post's publish_mode."""
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SocialPostMetric(Base):
    """One metric exactly as the provider returned it (never estimated). Latest fetch per (post, metric) wins."""
    __tablename__ = "m49_social_post_metrics"
    __table_args__ = (UniqueConstraint("post_id", "metric", name="uq_m49_social_post_metric"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id    = Column(UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    network    = Column(String(12), nullable=False)
    metric     = Column(String(80), nullable=False)
    value      = Column(Numeric(20, 2), nullable=False)
    source     = Column(String(160), nullable=False)       # the provider endpoint that returned it
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SocialOptOut(Base):
    """An author who asked not to be stored: items from this author are dropped and existing ones erased."""
    __tablename__ = "m49_social_optouts"
    __table_args__ = (UniqueConstraint("network", "author_hash", name="uq_m49_social_optout"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    network     = Column(String(12), nullable=False)
    author_hash = Column(String(64), nullable=False)       # sha256 of the lower-cased handle (the handle itself is not kept)
    reason      = Column(String(200), nullable=True)
    created_by  = Column(String(100), nullable=False)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SocialWebhookEvent(Base):
    """Replay ledger: a webhook delivery (same body) is processed once."""
    __tablename__ = "m49_social_webhook_events"
    __table_args__ = (UniqueConstraint("source", "event_hash", name="uq_m49_social_webhook_event"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source      = Column(String(12), nullable=False)
    event_hash  = Column(String(64), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SocialQuotaUse(Base):
    """Our own count of quota-bearing provider calls (YouTube videos.insert bucket, X posts) per UTC day."""
    __tablename__ = "m49_social_quota_use"
    __table_args__ = (UniqueConstraint("network", "bucket", "day", name="uq_m49_social_quota"),)

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    network = Column(String(12), nullable=False)
    bucket  = Column(String(30), nullable=False)
    day     = Column(Date, nullable=False)
    used    = Column(Integer, nullable=False, default=0)
