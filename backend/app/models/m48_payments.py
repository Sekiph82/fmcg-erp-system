"""M48.S01.T010 card payments through a hosted-checkout provider (Pesapal API 3.0) on customer payment links.

We never see a card number or CVV: the customer pays on the provider's hosted page; we keep only the provider's order
tracking id, its confirmation code and the status it reports when we ask it (GetTransactionStatus).
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CardProviderConfig(Base):
    """One row per provider. The consumer secret is sealed at rest (enc: envelope, same key as webhook secrets).
    Money is real only when environment=LIVE and live_active (two finance people + the runtime flag)."""
    __tablename__ = "card_provider_configs"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider               = Column(String(20), nullable=False, unique=True)            # PESAPAL
    environment            = Column(String(10), nullable=False, default="SANDBOX")      # SANDBOX | LIVE
    base_url               = Column(String(200), nullable=False)
    consumer_key           = Column(String(200), nullable=False)
    consumer_secret_stored = Column(Text, nullable=False)                               # enc:… envelope
    ipn_id                 = Column(String(64), nullable=True)
    ipn_url                = Column(String(300), nullable=True)
    live_requested_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    live_approved_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    live_active            = Column(Boolean, nullable=False, default=False)
    updated_by_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at             = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CardPayment(Base):
    """One hosted-checkout order for (part of) a payment link's invoice.
    status: what the provider says (PENDING until it reports a final state; EXPIRED = our reservation lapsed).
    settlement: what we did with the money, exactly once (row lock + unique collection_id):
      NONE | TEST_SETTLED (sandbox money, never booked) | COLLECTION (pending collection, finance confirms → ledger)
      | NEEDS_REVIEW (paid more than the open balance or amount/currency differ: finance decides) | REFUNDED."""
    __tablename__ = "card_payments"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id            = Column(UUID(as_uuid=True), ForeignKey("pay_links.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id         = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    provider           = Column(String(20), nullable=False, default="PESAPAL")
    simulated          = Column(Boolean, nullable=False, default=True)
    merchant_reference = Column(String(50), nullable=False, unique=True)
    order_tracking_id  = Column(String(64), nullable=True, unique=True)
    redirect_url       = Column(Text, nullable=True)
    amount             = Column(Numeric(16, 2), nullable=False)
    currency           = Column(String(10), nullable=False)
    status             = Column(String(12), nullable=False, default="PENDING")  # PENDING|COMPLETED|FAILED|INVALID|REVERSED|EXPIRED
    status_description = Column(String(200), nullable=True)
    confirmation_code  = Column(String(64), nullable=True)
    payment_method     = Column(String(40), nullable=True)
    settlement         = Column(String(14), nullable=False, default="NONE")
    collection_id      = Column(UUID(as_uuid=True), ForeignKey("cash_collections.id", ondelete="SET NULL"), nullable=True, unique=True)
    notifications      = Column(Integer, nullable=False, default=0)                 # IPN / return hits (replays included)
    last_checked_at    = Column(DateTime(timezone=True), nullable=True)
    created_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at       = Column(DateTime(timezone=True), nullable=True)


class CardRefund(Base):
    """Pesapal allows one refund per payment (unique card_payment_id). Requested by one person, approved by another;
    the provider's 200 only means "received" — the refund is COMPLETED when the status query reports REVERSED."""
    __tablename__ = "card_refunds"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_payment_id  = Column(UUID(as_uuid=True), ForeignKey("card_payments.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount           = Column(Numeric(16, 2), nullable=False)
    reason           = Column(String(255), nullable=False)
    status           = Column(String(10), nullable=False, default="REQUESTED")  # REQUESTED|SUBMITTED|UNKNOWN|COMPLETED|REJECTED|FAILED
    provider_message = Column(String(255), nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    requested_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at       = Column(DateTime(timezone=True), nullable=True)
