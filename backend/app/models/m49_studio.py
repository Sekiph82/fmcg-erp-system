"""M49.S01.T012 Integrated Marketing Studio: a brief per campaign, links from the campaign to the records other
modules already own (assets, designs, posts, ad trees, audiences), and budget requests against the finance cap."""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class StudioCampaign(Base):
    """The brief of one campaign. Versioned: each change keeps the previous brief in brief_history (last 20)."""
    __tablename__ = "m49_studio_campaigns"

    campaign_id   = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="CASCADE"), primary_key=True)
    brief         = Column(JSON, nullable=False, default=dict)
    brief_version = Column(Integer, nullable=False, default=1)
    brief_history = Column(JSON, nullable=False, default=list)
    updated_by    = Column(String(100), nullable=False)
    updated_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StudioLink(Base):
    """kind: DAM_ASSET | BRAND_ASSET | EMAIL_DESIGN | SOCIAL_POST | AD_TREE | AUDIENCE_SYNC | AUDIENCE.
    linked_version = the asset / design version that was approved when it was linked."""
    __tablename__ = "m49_studio_links"
    __table_args__ = (UniqueConstraint("campaign_id", "kind", "ref_id", name="uq_m49_studio_link"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id    = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    kind           = Column(String(16), nullable=False)
    ref_id         = Column(UUID(as_uuid=True), nullable=False)
    linked_version = Column(Integer, nullable=True)
    label          = Column(String(300), nullable=False)
    created_by     = Column(String(100), nullable=False)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StudioBudgetRequest(Base):
    """status: APPLIED (within the cap, applied at once) | PENDING (over the cap, needs a finance approver who is
    not the requester) | APPROVED | REJECTED. cap = the cap in force when it was asked."""
    __tablename__ = "m49_studio_budget_requests"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id  = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    amount       = Column(Numeric(16, 2), nullable=False)
    cap          = Column(Numeric(16, 2), nullable=False)
    status       = Column(String(10), nullable=False)
    note         = Column(String(300), nullable=True)
    requested_by = Column(String(100), nullable=False)
    decided_by   = Column(String(100), nullable=True)
    decided_at   = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
