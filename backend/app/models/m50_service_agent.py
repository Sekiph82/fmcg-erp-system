"""M50.S01.T005/T006 service-agent evidence: answered turns (with review and CSAT/CES), customer-confirmed ticket
actions, and knowledge-gap proposals that become approved KB articles."""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ServiceAgentTurn(Base):
    __tablename__ = "sa_turns"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id       = Column(UUID(as_uuid=True), ForeignKey("crm_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    question         = Column(Text, nullable=False)                 # e-mail addresses and phone numbers are redacted
    answer           = Column(Text, nullable=True)
    lang             = Column(String(2), nullable=False)            # en | sw | tr
    outcome          = Column(String(12), nullable=False, index=True)  # ANSWERED|ABSTAINED|HANDOFF|REFUSED|ORDER|TICKET|PROPOSAL|SAFETY|INJECTION
    mode             = Column(String(10), nullable=False)           # LLM | FALLBACK | RULES
    topic            = Column(String(20), nullable=False, default="other")
    citations        = Column(JSON, nullable=False, default=list)   # [{"slug","version"}]
    complaint_class  = Column(String(16), nullable=True)            # SAFETY | QUALITY | PACKAGING | LABEL_ISSUE | FOREIGN_OBJECT
    complaint_id     = Column(UUID(as_uuid=True), ForeignKey("consumer_complaints.id", ondelete="SET NULL"), nullable=True)
    lot_number       = Column(String(100), nullable=True)
    review_verdict   = Column(String(20), nullable=True)            # CORRECT | WRONG_CITATION | INACCURATE | UNSUPPORTED
    reviewed_by      = Column(String(100), nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    review_note      = Column(Text, nullable=True)
    csat             = Column(Integer, nullable=True)               # 1-5
    ces              = Column(Integer, nullable=True)               # 1-7 (7 = very easy)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class ServiceAgentAction(Base):
    """A write the agent proposed for a signed-in customer. Nothing is written until that customer confirms."""
    __tablename__ = "sa_actions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("crm_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    kind         = Column(String(20), nullable=False)               # TICKET_CREATE | TICKET_COMMENT
    payload      = Column(JSON, nullable=False)
    status       = Column(String(10), nullable=False, default="PROPOSED")   # PROPOSED | EXECUTED | CANCELLED | EXPIRED
    ticket_id    = Column(UUID(as_uuid=True), ForeignKey("helpdesk_tickets.id", ondelete="SET NULL"), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at   = Column(DateTime(timezone=True), nullable=True)


class KBGapProposal(Base):
    __tablename__ = "kb_gap_proposals"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_key        = Column(String(120), nullable=False, index=True)
    topic              = Column(String(20), nullable=False, default="other")
    sample_questions   = Column(JSON, nullable=False, default=list)
    question_count     = Column(Integer, nullable=False, default=0)
    languages          = Column(JSON, nullable=False, default=dict)
    status             = Column(String(10), nullable=False, default="PROPOSED", index=True)   # PROPOSED | APPROVED | REJECTED
    proposed_title     = Column(String(300), nullable=False)
    proposed_summary   = Column(Text, nullable=True)
    proposed_content_md = Column(Text, nullable=False, default="")
    target_article_id  = Column(UUID(as_uuid=True), ForeignKey("kb_articles.id", ondelete="SET NULL"), nullable=True)   # update this article
    article_id         = Column(UUID(as_uuid=True), ForeignKey("kb_articles.id", ondelete="SET NULL"), nullable=True)    # result
    created_by         = Column(String(100), nullable=False)
    decided_by         = Column(String(100), nullable=True)
    decision_note      = Column(Text, nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at         = Column(DateTime(timezone=True), nullable=True)
