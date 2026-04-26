"""Moto Sales extension — M-Pesa STK, Fraud Detection, Rider Performance."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.van_sales import (
    VanMpesaPayment, MpesaStkStatus,
    VanFraudAlert, FraudType, FraudSeverity, FraudAlertStatus,
    VanRiderPerformance,
    VanSalesTxn, VanSalesTxnLine, VanPayment, VanVisit,
    TxnType, TxnStatus, VisitStatus, PaymentStatus,
)


def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


# ── M-Pesa STK Push ───────────────────────────────────────────────────────────

async def initiate_stk_push(
    db: AsyncSession,
    txn_id: uuid.UUID,
    phone: str,
    amount: Decimal,
) -> VanMpesaPayment:
    """
    In production, call Safaricom Daraja API here.
    Here we create the record and return PENDING status.
    The callback endpoint updates it when Safaricom responds.
    """
    import random, string
    merchant_req_id = "MS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
    checkout_req_id = "ws_CO_" + datetime.utcnow().strftime("%d%m%Y%H%M%S") + str(random.randint(100000, 999999))

    mpesa = VanMpesaPayment(
        txn_id=txn_id,
        phone_number=phone,
        amount=amount,
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        status=MpesaStkStatus.PENDING.value,
        request_time=datetime.utcnow(),
    )
    db.add(mpesa)
    await db.commit()
    await db.refresh(mpesa)
    return mpesa


async def handle_stk_callback(
    db: AsyncSession,
    checkout_request_id: str,
    result_code: str,
    result_desc: str,
    mpesa_receipt_no: Optional[str],
    raw: dict,
) -> Optional[VanMpesaPayment]:
    result = await db.execute(
        select(VanMpesaPayment).where(VanMpesaPayment.checkout_request_id == checkout_request_id)
    )
    mpesa = result.scalars().first()
    if not mpesa:
        return None

    mpesa.result_code = result_code
    mpesa.result_desc = result_desc
    mpesa.callback_time = datetime.utcnow()
    mpesa.raw_callback = raw

    if result_code == "0":
        mpesa.status = MpesaStkStatus.SUCCESS.value
        mpesa.mpesa_receipt_no = mpesa_receipt_no
        # Link to van_payment
        pay = VanPayment(
            txn_id=mpesa.txn_id,
            method="MPESA",
            amount=mpesa.amount,
            reference_no=mpesa_receipt_no,
            collected_at=datetime.utcnow(),
            receipt_no=mpesa_receipt_no,
        )
        db.add(pay)
        await db.flush()
        mpesa.van_payment_id = pay.id
        # Update txn payment status
        txn = await db.get(VanSalesTxn, mpesa.txn_id)
        if txn:
            txn.paid_amount = (txn.paid_amount or Decimal("0")) + mpesa.amount
            txn.balance_due = max(Decimal("0"), (txn.total_amount or Decimal("0")) - txn.paid_amount)
            txn.payment_status = PaymentStatus.PAID.value if txn.balance_due == 0 else PaymentStatus.PARTIAL.value
    else:
        mpesa.status = MpesaStkStatus.FAILED.value

    await db.commit()
    await db.refresh(mpesa)
    return mpesa


async def list_mpesa_payments(
    db: AsyncSession, txn_id: Optional[uuid.UUID] = None, status: Optional[str] = None
) -> List[VanMpesaPayment]:
    q = select(VanMpesaPayment)
    if txn_id:
        q = q.where(VanMpesaPayment.txn_id == txn_id)
    if status:
        q = q.where(VanMpesaPayment.status == status)
    result = await db.execute(q.order_by(VanMpesaPayment.created_at.desc()).limit(200))
    return result.scalars().all()


# ── Fraud Detection ───────────────────────────────────────────────────────────

def _severity_from_score(score: Decimal) -> str:
    if score >= 85:
        return FraudSeverity.CRITICAL.value
    if score >= 65:
        return FraudSeverity.HIGH.value
    if score >= 40:
        return FraudSeverity.MEDIUM.value
    return FraudSeverity.LOW.value


async def run_fraud_scan(db: AsyncSession, cutoff_days: int = 7) -> List[VanFraudAlert]:
    alerts: list[VanFraudAlert] = []
    cutoff = datetime.utcnow() - timedelta(days=cutoff_days)

    # 1 — Abnormal discounts (avg > 20%)
    disc_q = await db.execute(
        select(
            VanSalesTxnLine.txn_id,
            func.avg(VanSalesTxnLine.discount_pct).label("avg_disc"),
        )
        .join(VanSalesTxn, VanSalesTxn.id == VanSalesTxnLine.txn_id)
        .where(VanSalesTxn.created_at >= cutoff)
        .group_by(VanSalesTxnLine.txn_id)
        .having(func.avg(VanSalesTxnLine.discount_pct) > 20)
    )
    for row in disc_q.all():
        txn = await db.get(VanSalesTxn, row.txn_id)
        score = Decimal(min(100, 30 + float(row.avg_disc or 0) * 2))
        a = VanFraudAlert(
            txn_id=row.txn_id,
            van_id=txn.van_id if txn else None,
            driver_id=txn.driver_id if txn else None,
            fraud_type=FraudType.ABNORMAL_DISCOUNT.value,
            risk_score=score,
            severity=_severity_from_score(score),
            description=f"Transaction avg discount {float(row.avg_disc or 0):.1f}% exceeds 20% threshold",
            data={"avg_discount_pct": float(row.avg_disc or 0)},
        )
        db.add(a)
        alerts.append(a)

    # 2 — Repeated returns: same customer, >3 returns in 7 days
    ret_q = await db.execute(
        select(
            VanSalesTxn.customer_id,
            VanSalesTxn.driver_id,
            func.count().label("return_count"),
        )
        .where(
            VanSalesTxn.txn_type == TxnType.RETURN.value,
            VanSalesTxn.created_at >= cutoff,
        )
        .group_by(VanSalesTxn.customer_id, VanSalesTxn.driver_id)
        .having(func.count() > 3)
    )
    for row in ret_q.all():
        score = Decimal(min(100, 40 + row.return_count * 8))
        a = VanFraudAlert(
            driver_id=row.driver_id,
            fraud_type=FraudType.REPEATED_RETURN.value,
            risk_score=score,
            severity=_severity_from_score(score),
            description=f"Customer received {row.return_count} returns in {cutoff_days} days from same driver",
            data={"return_count": row.return_count, "customer_id": str(row.customer_id)},
        )
        db.add(a)
        alerts.append(a)

    # 3 — Payment mismatch: transactions with paid > total (overpayment) or unpaid invoiced > 72h
    mismatch_q = await db.execute(
        select(VanSalesTxn).where(
            VanSalesTxn.status == TxnStatus.CONFIRMED.value,
            VanSalesTxn.payment_status == PaymentStatus.UNPAID.value,
            VanSalesTxn.created_at <= datetime.utcnow() - timedelta(hours=72),
        ).limit(50)
    )
    for txn in mismatch_q.scalars().all():
        a = VanFraudAlert(
            txn_id=txn.id,
            van_id=txn.van_id,
            driver_id=txn.driver_id,
            fraud_type=FraudType.PAYMENT_MISMATCH.value,
            risk_score=Decimal("55"),
            severity=FraudSeverity.MEDIUM.value,
            description=f"Transaction {txn.txn_no} unpaid after 72 hours",
            data={"txn_no": txn.txn_no, "total": float(txn.total_amount or 0)},
        )
        db.add(a)
        alerts.append(a)

    if alerts:
        await db.commit()
    return alerts


async def list_fraud_alerts(
    db: AsyncSession,
    van_id: Optional[uuid.UUID] = None,
    driver_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0, limit: int = 100,
) -> List[VanFraudAlert]:
    q = select(VanFraudAlert)
    if van_id:
        q = q.where(VanFraudAlert.van_id == van_id)
    if driver_id:
        q = q.where(VanFraudAlert.driver_id == driver_id)
    if status:
        q = q.where(VanFraudAlert.status == status)
    if severity:
        q = q.where(VanFraudAlert.severity == severity)
    result = await db.execute(q.order_by(VanFraudAlert.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def review_fraud_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    new_status: str,
    resolution: Optional[str],
    reviewer_id: Optional[uuid.UUID],
) -> Optional[VanFraudAlert]:
    alert = await db.get(VanFraudAlert, alert_id)
    if alert:
        alert.status = new_status
        alert.resolution = resolution
        alert.reviewed_by = reviewer_id
        alert.reviewed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(alert)
    return alert


# ── Rider Performance ─────────────────────────────────────────────────────────

def _calc_score(
    route_completion: float,
    collection_rate: float,
    cash_variance_abs: float,
    total_sales: float,
    fraud_flags: int,
) -> Decimal:
    """Composite 0–100 score."""
    score = 0.0
    score += route_completion * 0.30           # 30% weight
    score += collection_rate * 0.25            # 25% weight
    score += max(0, 100 - min(cash_variance_abs / 1000 * 10, 100)) * 0.15  # 15% cash accuracy
    score += min(total_sales / 50000 * 100, 100) * 0.20   # 20% sales volume (benchmark 50k)
    score += max(0, 100 - fraud_flags * 15) * 0.10        # 10% clean record
    return Decimal(str(round(min(100, max(0, score)), 2)))


async def compute_rider_performance(
    db: AsyncSession, driver_id: uuid.UUID, perf_date: date
) -> VanRiderPerformance:
    # Visits
    visit_q = await db.execute(
        select(VanVisit).where(
            VanVisit.route_date == perf_date,
        ).where(
            func.cast(VanVisit.van_id, type_=None).in_(
                select(func.cast(VanSalesTxn.van_id, type_=None))
                .where(VanSalesTxn.driver_id == driver_id)
                .limit(1)
            ) if False else True  # simplified: query visits where driver matches via txns
        )
    )

    # Simpler approach: get van_id from txns
    txn_q = await db.execute(
        select(VanSalesTxn).where(
            VanSalesTxn.driver_id == driver_id,
            func.date(VanSalesTxn.txn_datetime) == perf_date,
            VanSalesTxn.txn_type == TxnType.SALE.value,
            VanSalesTxn.status != TxnStatus.CANCELLED.value,
        )
    )
    txns = txn_q.scalars().all()
    total_sales = sum(_D(t.total_amount) for t in txns)
    total_paid = sum(_D(t.paid_amount) for t in txns)
    total_orders = len(txns)

    van_id = txns[0].van_id if txns else None

    # Visits for this van/date
    visits_all = []
    if van_id:
        vq = await db.execute(
            select(VanVisit).where(VanVisit.van_id == van_id, VanVisit.route_date == perf_date)
        )
        visits_all = vq.scalars().all()

    total_visits = len(visits_all)
    completed = sum(1 for v in visits_all if v.status == VisitStatus.COMPLETED.value)
    missed = sum(1 for v in visits_all if v.status == VisitStatus.MISSED.value)

    route_comp = (completed / total_visits * 100) if total_visits else 0
    coll_rate = (float(total_paid) / float(total_sales) * 100) if total_sales > 0 else 0

    # Fraud flags today
    fraud_q = await db.execute(
        select(func.count()).select_from(VanFraudAlert).where(
            VanFraudAlert.driver_id == driver_id,
            func.date(VanFraudAlert.created_at) == perf_date,
        )
    )
    fraud_count = fraud_q.scalar_one()

    score = _calc_score(route_comp, coll_rate, 0, float(total_sales), fraud_count)

    # Upsert
    existing = await db.execute(
        select(VanRiderPerformance).where(
            VanRiderPerformance.driver_id == driver_id,
            VanRiderPerformance.perf_date == perf_date,
        )
    )
    perf = existing.scalars().first()

    if perf:
        perf.total_sales = total_sales
        perf.total_orders = total_orders
        perf.total_visits = total_visits
        perf.completed_visits = completed
        perf.missed_visits = missed
        perf.route_completion_pct = Decimal(str(round(route_comp, 2)))
        perf.collection_rate_pct = Decimal(str(round(coll_rate, 2)))
        perf.expected_cash = total_sales
        perf.fraud_flag_count = fraud_count
        perf.performance_score = score
        perf.van_id = van_id
    else:
        perf = VanRiderPerformance(
            driver_id=driver_id,
            van_id=van_id,
            perf_date=perf_date,
            total_sales=total_sales,
            total_orders=total_orders,
            total_visits=total_visits,
            completed_visits=completed,
            missed_visits=missed,
            route_completion_pct=Decimal(str(round(route_comp, 2))),
            collection_rate_pct=Decimal(str(round(coll_rate, 2))),
            expected_cash=total_sales,
            fraud_flag_count=fraud_count,
            performance_score=score,
        )
        db.add(perf)

    await db.commit()
    await db.refresh(perf)
    return perf


async def list_rider_performance(
    db: AsyncSession,
    driver_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = 0, limit: int = 50,
) -> List[VanRiderPerformance]:
    q = select(VanRiderPerformance)
    if driver_id:
        q = q.where(VanRiderPerformance.driver_id == driver_id)
    if from_date:
        q = q.where(VanRiderPerformance.perf_date >= from_date)
    if to_date:
        q = q.where(VanRiderPerformance.perf_date <= to_date)
    result = await db.execute(q.order_by(VanRiderPerformance.perf_date.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def leaderboard(
    db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    if not from_date:
        from_date = date.today() - timedelta(days=7)
    if not to_date:
        to_date = date.today()

    q = await db.execute(
        select(
            VanRiderPerformance.driver_id,
            func.avg(VanRiderPerformance.performance_score).label("avg_score"),
            func.sum(VanRiderPerformance.total_sales).label("total_sales"),
            func.sum(VanRiderPerformance.total_orders).label("total_orders"),
            func.avg(VanRiderPerformance.route_completion_pct).label("avg_route_completion"),
            func.avg(VanRiderPerformance.collection_rate_pct).label("avg_collection_rate"),
            func.sum(VanRiderPerformance.fraud_flag_count).label("total_fraud_flags"),
        )
        .where(
            VanRiderPerformance.perf_date >= from_date,
            VanRiderPerformance.perf_date <= to_date,
        )
        .group_by(VanRiderPerformance.driver_id)
        .order_by(func.avg(VanRiderPerformance.performance_score).desc())
    )
    rows = q.all()
    return [
        {
            "rank": i + 1,
            "driver_id": str(r.driver_id),
            "avg_score": round(float(r.avg_score or 0), 1),
            "total_sales": float(r.total_sales or 0),
            "total_orders": int(r.total_orders or 0),
            "avg_route_completion": round(float(r.avg_route_completion or 0), 1),
            "avg_collection_rate": round(float(r.avg_collection_rate or 0), 1),
            "total_fraud_flags": int(r.total_fraud_flags or 0),
        }
        for i, r in enumerate(rows)
    ]
