"""Bank API / Open Banking service with mock Kenyan bank sync."""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bank_api import (
    BankApiType, BankConnection, BankConnectionStatus, BankSyncLog, BankSyncStatus,
    BankTransaction, BankTxnClassification, BankTxnDirection,
)
from app.schemas.bank_api import (
    BankConnectionCreate, BankApiDashboard, BankSyncResult,
)


MOCK_DESCRIPTIONS = [
    ("M-PESA PAYBILL RECEIPT SAFARICOM PLC", BankTxnDirection.CREDIT, Decimal("18500.00")),
    ("CUSTOMER EFT PAYMENT NAIVAS LTD", BankTxnDirection.CREDIT, Decimal("124800.00")),
    ("RTGS RECEIPT QUICKMART SUPERMARKET", BankTxnDirection.CREDIT, Decimal("96750.00")),
    ("SUPPLIER PAYMENT BIDCO AFRICA", BankTxnDirection.DEBIT, Decimal("78500.00")),
    ("SALARY PAYROLL MAY STAFF", BankTxnDirection.DEBIT, Decimal("215000.00")),
    ("KRA VAT PAYMENT ITAX", BankTxnDirection.DEBIT, Decimal("64200.00")),
    ("KENYA POWER BILL PAYMENT", BankTxnDirection.DEBIT, Decimal("43800.00")),
    ("WATER SERVICES BILL PAYMENT", BankTxnDirection.DEBIT, Decimal("12300.00")),
    ("BANK CHARGES MONTHLY LEDGER FEE", BankTxnDirection.DEBIT, Decimal("850.00")),
    ("RENT PAYMENT INDUSTRIAL AREA GODOWN", BankTxnDirection.DEBIT, Decimal("95000.00")),
    ("INTERNAL TRANSFER TO USD ACCOUNT", BankTxnDirection.DEBIT, Decimal("50000.00")),
    ("LOAN INTEREST CHARGE", BankTxnDirection.DEBIT, Decimal("18500.00")),
    ("DISTRIBUTOR PAYMENT EASTLANDS WHOLESALE", BankTxnDirection.CREDIT, Decimal("74200.00")),
    ("CARD SETTLEMENT RETAIL OUTLET", BankTxnDirection.CREDIT, Decimal("22600.00")),
]


def classify_description(description: str) -> BankTxnClassification:
    text = description.upper()
    if "M-PESA" in text or "MPESA" in text or "PAYBILL" in text or "CARD SETTLEMENT" in text:
        return BankTxnClassification.PAYMENT
    if "SALARY" in text or "PAYROLL" in text:
        return BankTxnClassification.PAYROLL
    if "SUPPLIER" in text or "BIDCO" in text:
        return BankTxnClassification.SUPPLIER_PAYMENT
    if "BANK CHARGE" in text or "LEDGER FEE" in text or "INTEREST CHARGE" in text:
        return BankTxnClassification.BANK_CHARGE
    if "KRA" in text or "ITAX" in text or "VAT" in text:
        return BankTxnClassification.TAX
    if "POWER" in text or "WATER" in text or "UTILITY" in text:
        return BankTxnClassification.UTILITIES
    if "RENT" in text or "GODOWN" in text:
        return BankTxnClassification.RENT
    if "TRANSFER" in text:
        return BankTxnClassification.TRANSFER
    if "CUSTOMER" in text or "DISTRIBUTOR" in text or "RECEIPT" in text or "RTGS" in text:
        return BankTxnClassification.SALES_RECEIPT
    return BankTxnClassification.OTHER


async def _next_connection_no(db: AsyncSession) -> str:
    count = (await db.execute(select(func.count()).select_from(BankConnection))).scalar() or 0
    return f"BANK-CONN-{count + 1:05d}"


async def create_connection(db: AsyncSession, data: BankConnectionCreate) -> BankConnection:
    obj = BankConnection(
        connection_no=await _next_connection_no(db),
        **data.model_dump(),
        status=BankConnectionStatus.ACTIVE,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_connections(db: AsyncSession) -> List[BankConnection]:
    result = await db.execute(select(BankConnection).order_by(BankConnection.created_at.desc()))
    return list(result.scalars().all())


async def get_connection(db: AsyncSession, connection_id: uuid.UUID) -> BankConnection:
    result = await db.execute(
        select(BankConnection)
        .options(selectinload(BankConnection.sync_logs))
        .where(BankConnection.id == connection_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError("Bank connection not found")
    return obj


async def sync_connection(db: AsyncSession, connection_id: uuid.UUID) -> BankSyncResult:
    conn = await get_connection(db, connection_id)
    now = datetime.now(timezone.utc)

    if conn.status != BankConnectionStatus.ACTIVE:
        log = BankSyncLog(
            connection_id=conn.id,
            synced_at=now,
            transactions_fetched=0,
            status=BankSyncStatus.FAILED,
            message="Connection is disconnected.",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        raise ValueError("Connection is disconnected")

    if conn.api_type == BankApiType.DIRECT:
        log = BankSyncLog(
            connection_id=conn.id,
            synced_at=now,
            transactions_fetched=0,
            status=BankSyncStatus.FAILED,
            message="Direct bank API sync requires bank-specific credentials and adapter configuration.",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        raise ValueError("Direct bank API adapter is not configured")

    latest_balance = (await db.execute(
        select(BankTransaction.balance_after)
        .where(BankTransaction.connection_id == conn.id)
        .order_by(BankTransaction.txn_date.desc(), BankTransaction.created_at.desc())
        .limit(1)
    )).scalar()
    balance = Decimal(str(latest_balance or "850000.00"))

    count = random.randint(10, 20)
    txns: List[BankTransaction] = []
    for i in range(count):
        desc, direction, base_amount = random.choice(MOCK_DESCRIPTIONS)
        variation = Decimal(str(random.randint(85, 125))) / Decimal("100")
        amount = (base_amount * variation).quantize(Decimal("0.01"))
        txn_date = date.today() - timedelta(days=random.randint(0, 6))
        balance = balance + amount if direction == BankTxnDirection.CREDIT else balance - amount
        reference = f"MOCK-{now.strftime('%Y%m%d%H%M%S')}-{i + 1:03d}"
        txn = BankTransaction(
            connection_id=conn.id,
            txn_date=txn_date,
            value_date=txn_date,
            description=desc,
            amount=amount,
            direction=direction,
            reference=reference,
            balance_after=balance,
            classification=classify_description(desc),
        )
        db.add(txn)
        txns.append(txn)

    conn.last_synced_at = now
    log = BankSyncLog(
        connection_id=conn.id,
        synced_at=now,
        transactions_fetched=count,
        status=BankSyncStatus.SUCCESS,
        message=f"Mock sync fetched {count} Kenyan bank transactions.",
    )
    db.add(log)
    await db.commit()
    await db.refresh(conn)
    await db.refresh(log)
    for txn in txns:
        await db.refresh(txn)
    return BankSyncResult(connection=conn, log=log, transactions=txns)


async def list_transactions(
    db: AsyncSession,
    connection_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    reconciled: Optional[bool] = None,
    limit: int = 100,
) -> List[BankTransaction]:
    q = select(BankTransaction)
    if connection_id:
        q = q.where(BankTransaction.connection_id == connection_id)
    if start_date:
        q = q.where(BankTransaction.txn_date >= start_date)
    if end_date:
        q = q.where(BankTransaction.txn_date <= end_date)
    if reconciled is not None:
        q = q.where(BankTransaction.is_reconciled == reconciled)
    q = q.order_by(BankTransaction.txn_date.desc(), BankTransaction.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_transaction(db: AsyncSession, transaction_id: uuid.UUID) -> BankTransaction:
    result = await db.execute(select(BankTransaction).where(BankTransaction.id == transaction_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError("Bank transaction not found")
    return obj


async def reconcile_transaction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    matched_record_type: str,
    matched_record_id: Optional[uuid.UUID],
) -> BankTransaction:
    txn = await get_transaction(db, transaction_id)
    txn.is_reconciled = True
    txn.matched_record_type = matched_record_type
    txn.matched_record_id = matched_record_id
    await db.commit()
    await db.refresh(txn)
    return txn


async def classify_transaction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    classification: BankTxnClassification,
) -> BankTransaction:
    txn = await get_transaction(db, transaction_id)
    txn.classification = classification
    await db.commit()
    await db.refresh(txn)
    return txn


async def get_dashboard(db: AsyncSession) -> BankApiDashboard:
    total_connections = (await db.execute(select(func.count()).select_from(BankConnection))).scalar() or 0
    active_connections = (await db.execute(
        select(func.count()).select_from(BankConnection).where(BankConnection.status == BankConnectionStatus.ACTIVE)
    )).scalar() or 0
    unreconciled_count = (await db.execute(
        select(func.count()).select_from(BankTransaction).where(BankTransaction.is_reconciled == False)
    )).scalar() or 0
    unreconciled_amount = (await db.execute(
        select(func.coalesce(func.sum(BankTransaction.amount), 0)).where(BankTransaction.is_reconciled == False)
    )).scalar() or 0
    last_sync_at = (await db.execute(select(func.max(BankConnection.last_synced_at)))).scalar()

    latest_by_connection = await db.execute(
        select(BankTransaction.connection_id, func.max(BankTransaction.created_at).label("created_at"))
        .group_by(BankTransaction.connection_id)
    )
    total_balance = Decimal("0")
    for connection_id, created_at in latest_by_connection.fetchall():
        bal = (await db.execute(
            select(BankTransaction.balance_after).where(
                and_(BankTransaction.connection_id == connection_id, BankTransaction.created_at == created_at)
            ).limit(1)
        )).scalar()
        total_balance += Decimal(str(bal or 0))

    logs = list((await db.execute(
        select(BankSyncLog).order_by(BankSyncLog.synced_at.desc()).limit(5)
    )).scalars().all())

    return BankApiDashboard(
        total_connections=total_connections,
        active_connections=active_connections,
        total_balance=float(total_balance),
        unreconciled_count=unreconciled_count,
        unreconciled_amount=float(unreconciled_amount or 0),
        last_sync_at=last_sync_at,
        recent_sync_logs=logs,
    )
