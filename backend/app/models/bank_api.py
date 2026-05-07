"""Bank API / Open Banking integration models."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class BankConnectionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISCONNECTED = "DISCONNECTED"


class BankApiType(str, enum.Enum):
    DIRECT = "DIRECT"
    MOCK = "MOCK"


class BankTxnDirection(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class BankTxnClassification(str, enum.Enum):
    SALES_RECEIPT = "SALES_RECEIPT"
    PAYMENT = "PAYMENT"
    SUPPLIER_PAYMENT = "SUPPLIER_PAYMENT"
    PAYROLL = "PAYROLL"
    BANK_CHARGE = "BANK_CHARGE"
    TAX = "TAX"
    UTILITIES = "UTILITIES"
    RENT = "RENT"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class BankSyncStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class BankConnection(Base, TimestampMixin):
    __tablename__ = "bank_api_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_no = Column(String(50), unique=True, nullable=False, index=True)
    bank_name = Column(String(120), nullable=False)
    account_name = Column(String(255), nullable=False)
    account_number = Column(String(100), nullable=False)
    bank_code = Column(String(40), nullable=True)
    currency = Column(String(10), nullable=False, default="KES")
    status = Column(
        SAEnum(BankConnectionStatus, native_enum=False),
        nullable=False,
        default=BankConnectionStatus.ACTIVE,
        index=True,
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    api_type = Column(SAEnum(BankApiType, native_enum=False), nullable=False, default=BankApiType.MOCK)
    credentials_ref = Column(String(255), nullable=True)

    transactions = relationship(
        "BankTransaction",
        back_populates="connection",
        cascade="all, delete-orphan",
        order_by="BankTransaction.txn_date.desc()",
    )
    sync_logs = relationship(
        "BankSyncLog",
        back_populates="connection",
        cascade="all, delete-orphan",
        order_by="BankSyncLog.synced_at.desc()",
    )


class BankTransaction(Base, TimestampMixin):
    __tablename__ = "bank_api_transactions"
    __table_args__ = (
        UniqueConstraint("connection_id", "reference", name="uq_bank_api_txn_connection_ref"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("bank_api_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    txn_date = Column(Date, nullable=False, index=True)
    value_date = Column(Date, nullable=True)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    direction = Column(SAEnum(BankTxnDirection, native_enum=False), nullable=False, index=True)
    reference = Column(String(100), nullable=False, index=True)
    balance_after = Column(Numeric(18, 4), nullable=True)
    classification = Column(
        SAEnum(BankTxnClassification, native_enum=False),
        nullable=False,
        default=BankTxnClassification.OTHER,
        index=True,
    )
    is_reconciled = Column(Boolean, nullable=False, default=False, index=True)
    matched_record_id = Column(UUID(as_uuid=True), nullable=True)
    matched_record_type = Column(String(100), nullable=True)

    connection = relationship("BankConnection", back_populates="transactions")


class BankSyncLog(Base, TimestampMixin):
    __tablename__ = "bank_api_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("bank_api_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    synced_at = Column(DateTime(timezone=True), nullable=False)
    transactions_fetched = Column(Integer, nullable=False, default=0)
    status = Column(SAEnum(BankSyncStatus, native_enum=False), nullable=False, default=BankSyncStatus.SUCCESS)
    message = Column(Text, nullable=True)

    connection = relationship("BankConnection", back_populates="sync_logs")
