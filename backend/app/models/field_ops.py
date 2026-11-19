"""Field operations (M38.S02/S03): cash/M-Pesa collections recorded in the field and outlet audits by controllers."""
import uuid

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin


class CashCollection(Base, TimestampMixin):
    """Money a collector/rep received from a customer. PENDING until finance confirms it; confirming posts the
    payment to the invoice (when one is given)."""
    __tablename__ = "cash_collections"
    __table_args__ = (  # an M-Pesa code is used once, but a cancelled typo must not block the real one
        Index("uq_cash_collections_mpesa_code_live", "mpesa_code", unique=True,
              postgresql_where=text("mpesa_code IS NOT NULL AND status <> 'CANCELLED'")),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_no   = Column(String(40), unique=True, nullable=False, index=True)
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_id      = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=True, index=True)
    sales_order_id  = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    rep_id          = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), nullable=True)
    collected_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    collection_date = Column(Date, nullable=False)
    method          = Column(String(20), nullable=False)          # CASH | MPESA | BANK_TRANSFER | CHEQUE
    amount          = Column(Numeric(16, 2), nullable=False)
    currency        = Column(String(10), nullable=False)
    reference       = Column(String(100), nullable=True)
    mpesa_code      = Column(String(30), nullable=True)
    mpesa_phone     = Column(String(30), nullable=True)
    gps_lat         = Column(Numeric(10, 7), nullable=True)
    gps_lng         = Column(Numeric(10, 7), nullable=True)
    status          = Column(String(20), nullable=False, default="PENDING")  # PENDING|CONFIRMED|RECONCILED|BOUNCED|CANCELLED
    payment_id      = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    confirmed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at    = Column(DateTime(timezone=True), nullable=True)
    reconciled_at   = Column(DateTime(timezone=True), nullable=True)
    client_ref      = Column(String(64), unique=True, nullable=True)   # field app idempotency key
    notes           = Column(Text, nullable=True)


class FieldAudit(Base, TimestampMixin):
    """An outlet/route check by a field controller: fixed checklist, score, photos, GPS."""
    __tablename__ = "field_audits"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_no    = Column(String(40), unique=True, nullable=False, index=True)
    auditor_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    rep_id      = Column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    route_id    = Column(UUID(as_uuid=True), ForeignKey("sales_routes.id", ondelete="SET NULL"), nullable=True)
    audit_date  = Column(Date, nullable=False, index=True)
    answers     = Column(JSON, nullable=False)          # [{"key": ..., "ok": bool, "note": str|None}]
    score       = Column(Numeric(5, 2), nullable=False)  # % of checklist items OK
    photo_keys  = Column(JSON, nullable=True)            # document-storage keys
    gps_lat     = Column(Numeric(10, 7), nullable=True)
    gps_lng     = Column(Numeric(10, 7), nullable=True)
    client_ref  = Column(String(64), unique=True, nullable=True)
    notes       = Column(Text, nullable=True)
