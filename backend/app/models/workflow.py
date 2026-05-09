import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ApprovalModule(str, enum.Enum):
    PURCHASE_ORDER       = "PURCHASE_ORDER"
    PURCHASE_REQUISITION = "PURCHASE_REQUISITION"
    BUDGET               = "BUDGET"
    PRODUCTION_ORDER     = "PRODUCTION_ORDER"
    SALES_INVOICE        = "SALES_INVOICE"
    EXPENSE              = "EXPENSE"
    CONTRACT             = "CONTRACT"
    PRICE_LIST           = "PRICE_LIST"
    CREDIT_NOTE          = "CREDIT_NOTE"
    OTHER                = "OTHER"


class ApprovalStatus(str, enum.Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class ApprovalRule(Base, TimestampMixin):
    """
    Defines who must approve what, at which level, and within which SLA.
    Rules are evaluated by (module, amount) — the first matching rule per level wins.
    """
    __tablename__ = "approval_rules"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module        = Column(Enum(ApprovalModule), nullable=False, index=True)
    level         = Column(Integer, nullable=False, default=1)   # 1 = first approver
    required_role = Column(String(100), nullable=False)          # role name e.g. "finance_manager"
    amount_min    = Column(Numeric(18, 2), nullable=False, default=0)
    amount_max    = Column(Numeric(18, 2), nullable=True)        # null = no upper cap
    sla_hours     = Column(Integer, nullable=False, default=24)
    is_active     = Column(Boolean, default=True, nullable=False)
    description   = Column(String(255), nullable=True)


class ApprovalRequest(Base, TimestampMixin):
    """
    A single approval chain instance for any ERP object.
    Progresses through levels until all levels are APPROVED or one is REJECTED.
    """
    __tablename__ = "approval_requests"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module        = Column(Enum(ApprovalModule), nullable=False, index=True)
    object_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    object_ref    = Column(String(100), nullable=False)           # e.g. "PO-0042"
    amount        = Column(Numeric(18, 2), nullable=True)
    currency      = Column(String(10), nullable=False, default="KES")
    status        = Column(Enum(ApprovalStatus, name="workflow_approvalstatus"), nullable=False, default=ApprovalStatus.PENDING)
    current_level = Column(Integer, nullable=False, default=1)
    max_level     = Column(Integer, nullable=False, default=1)
    description   = Column(Text, nullable=True)

    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    final_action_at = Column(DateTime(timezone=True), nullable=True)
    final_action_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    requested_by   = relationship("User", foreign_keys=[requested_by_id])
    final_actor    = relationship("User", foreign_keys=[final_action_by_id])
    steps          = relationship("ApprovalStep", back_populates="request",
                                  cascade="all, delete-orphan",
                                  order_by="ApprovalStep.level")


class ApprovalStep(Base, TimestampMixin):
    """
    One level in an approval chain. Created when the previous level is approved.
    """
    __tablename__ = "approval_steps"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id    = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    level         = Column(Integer, nullable=False)
    required_role = Column(String(100), nullable=False)
    status        = Column(Enum(ApprovalStatus, name="workflow_approvalstatus"), nullable=False, default=ApprovalStatus.PENDING)
    sla_deadline  = Column(DateTime(timezone=True), nullable=True)
    action_at     = Column(DateTime(timezone=True), nullable=True)
    action_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    request   = relationship("ApprovalRequest", back_populates="steps")
    action_by = relationship("User", foreign_keys=[action_by_id])
