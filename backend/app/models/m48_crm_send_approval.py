"""M48.S01.T023 (M36 audit F4): second-editor approval for direct marketing sends that have no campaign record —
ABM group campaigns and single sends of an e-mail design. One row approves one exact payload (SHA-256 of the
canonical JSON) for one target, and is used once."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CRMSendApproval(Base):
    __tablename__ = "crm_send_approvals"
    __table_args__ = (Index("ix_crm_send_approvals_kind_target", "kind", "target_id"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind         = Column(String(20), nullable=False)          # ABM_GROUP | DESIGN_SEND
    target_id    = Column(UUID(as_uuid=True), nullable=False)  # account group id / e-mail design id
    company_id   = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    payload      = Column(JSON, nullable=False)                # what the approver saw
    content_hash = Column(String(64), nullable=False)
    status       = Column(String(10), nullable=False, default="PENDING")   # PENDING|APPROVED|REJECTED|USED
    requested_by = Column(String(100), nullable=False)
    decided_by   = Column(String(100), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False)
    decided_at   = Column(DateTime(timezone=True), nullable=True)
    used_at      = Column(DateTime(timezone=True), nullable=True)
