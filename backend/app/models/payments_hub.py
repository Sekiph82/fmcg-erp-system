"""M45.S01.T021 customer payment links."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PaymentLink(Base):
    __tablename__ = "pay_links"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash     = Column(String(64), nullable=False, unique=True)
    invoice_id     = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    currency       = Column(String(10), nullable=False)
    allow_partial  = Column(Boolean, nullable=False, default=True)
    status         = Column(String(10), nullable=False, default="ACTIVE")   # ACTIVE | PAID | TEST_PAID | REVOKED
    settled_amount = Column(Numeric(16, 2), nullable=False, default=0)
    expires_at     = Column(DateTime(timezone=True), nullable=False)
    revoked_at     = Column(DateTime(timezone=True), nullable=True)
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PaymentLinkAttempt(Base):
    """One payment attempt from the customer page; settled once, from the provider's callback."""
    __tablename__ = "pay_link_attempts"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id       = Column(UUID(as_uuid=True), ForeignKey("pay_links.id", ondelete="CASCADE"), nullable=False, index=True)
    provider      = Column(String(10), nullable=False, default="MPESA")    # MPESA | CARD
    mpesa_tx_id   = Column(UUID(as_uuid=True), ForeignKey("integration_mpesa_transactions.id", ondelete="SET NULL"), nullable=True, unique=True)
    amount        = Column(Numeric(16, 2), nullable=False)
    simulated     = Column(Boolean, nullable=False, default=False)
    status        = Column(String(12), nullable=False, default="PENDING")  # PENDING | SETTLED | TEST_SETTLED | FAILED
    receipt       = Column(String(40), nullable=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("cash_collections.id", ondelete="SET NULL"), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    settled_at    = Column(DateTime(timezone=True), nullable=True)
