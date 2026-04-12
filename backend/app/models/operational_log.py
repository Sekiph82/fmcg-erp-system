import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class OperationalLog(Base):
    """Operational audit trail for business-domain events (inventory, production, sales, finance)."""

    __tablename__ = "operational_logs"
    __table_args__ = (
        Index("ix_op_log_module", "module_name"),
        Index("ix_op_log_entity", "entity_type", "entity_id"),
        Index("ix_op_log_created_by", "created_by_id"),
        Index("ix_op_log_status", "status"),
        Index("ix_op_log_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Domain classification
    module_name = Column(String(50), nullable=False)    # inventory | production | sales | finance | mpesa | procurement
    entity_type = Column(String(100), nullable=False)   # stock_movement | production_order | invoice | payment …
    entity_id = Column(String(100), nullable=True)      # UUID string of the affected entity
    action_type = Column(String(50), nullable=False)    # CREATED | UPDATED | APPROVED | REJECTED | ISSUED | RECEIVED …

    # Outcome
    status = Column(String(20), nullable=False, default="SUCCESS")  # SUCCESS | FAILED | PENDING
    error_message = Column(Text, nullable=True)

    # Payloads (for debugging / reconciliation)
    request_payload = Column(JSONB, nullable=True)
    response_payload = Column(JSONB, nullable=True)

    # Who triggered it
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_email = Column(String(255), nullable=True)  # denormalised

    # When
    created_at = Column(
        __import__("sqlalchemy").DateTime(timezone=True),
        nullable=False,
        server_default=__import__("sqlalchemy").text("now()"),
        index=True,
    )

    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")


class MpesaStatusHistory(Base):
    """Tracks every status transition on an IntegrationMpesaTransaction."""

    __tablename__ = "mpesa_status_history"
    __table_args__ = (
        Index("ix_mpesa_history_tx", "transaction_id"),
        Index("ix_mpesa_history_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("integration_mpesa_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_status = Column(String(20), nullable=True)   # null on initial creation
    new_status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)

    created_at = Column(
        __import__("sqlalchemy").DateTime(timezone=True),
        nullable=False,
        server_default=__import__("sqlalchemy").text("now()"),
    )

    transaction = relationship("IntegrationMpesaTransaction", foreign_keys=[transaction_id], lazy="noload")
