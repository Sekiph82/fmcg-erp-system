"""Pydantic schemas for Bank API / Open Banking."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.bank_api import (
    BankApiType, BankConnectionStatus, BankSyncStatus,
    BankTxnClassification, BankTxnDirection,
)


class BankConnectionCreate(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    bank_code: Optional[str] = None
    currency: str = "KES"
    api_type: BankApiType = BankApiType.MOCK
    credentials_ref: Optional[str] = None


class BankConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connection_no: str
    bank_name: str
    account_name: str
    account_number: str
    bank_code: Optional[str]
    currency: str
    status: BankConnectionStatus
    last_synced_at: Optional[datetime]
    api_type: BankApiType
    credentials_ref: Optional[str]
    created_at: datetime


class BankTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connection_id: UUID
    txn_date: date
    value_date: Optional[date]
    description: str
    amount: float
    direction: BankTxnDirection
    reference: str
    balance_after: Optional[float]
    classification: BankTxnClassification
    is_reconciled: bool
    matched_record_id: Optional[UUID]
    matched_record_type: Optional[str]
    created_at: datetime


class BankSyncLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connection_id: UUID
    synced_at: datetime
    transactions_fetched: int
    status: BankSyncStatus
    message: Optional[str]
    created_at: datetime


class ReconcileBankTransaction(BaseModel):
    matched_record_type: str
    matched_record_id: Optional[UUID] = None


class ClassifyBankTransaction(BaseModel):
    classification: BankTxnClassification


class BankApiDashboard(BaseModel):
    total_connections: int
    active_connections: int
    total_balance: float
    unreconciled_count: int
    unreconciled_amount: float
    last_sync_at: Optional[datetime]
    recent_sync_logs: List[BankSyncLogRead] = []


class BankSyncResult(BaseModel):
    connection: BankConnectionRead
    log: BankSyncLogRead
    transactions: List[BankTransactionRead]
