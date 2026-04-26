"""Moto Sales extension — M-Pesa, Fraud, Rider Performance endpoints."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import moto_sales_service as svc

router = APIRouter()


def _404(label: str = "Record"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


# ── Pydantic schemas (inline, small surface) ──────────────────────────────────

class StkPushRequest(BaseModel):
    txn_id: UUID
    phone_number: str
    amount: Decimal


class StkCallbackRequest(BaseModel):
    checkout_request_id: str
    result_code: str
    result_desc: str
    mpesa_receipt_no: Optional[str] = None
    raw: dict = {}


class FraudReviewRequest(BaseModel):
    status: str
    resolution: Optional[str] = None


class PerformanceComputeRequest(BaseModel):
    driver_id: UUID
    perf_date: date


# ── M-Pesa ────────────────────────────────────────────────────────────────────

@router.post("/mpesa/stk-push", status_code=201)
async def stk_push(payload: StkPushRequest, db: AsyncSession = Depends(get_db)):
    return await svc.initiate_stk_push(db, payload.txn_id, payload.phone_number, payload.amount)


@router.post("/mpesa/callback")
async def stk_callback(payload: StkCallbackRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.handle_stk_callback(
        db,
        checkout_request_id=payload.checkout_request_id,
        result_code=payload.result_code,
        result_desc=payload.result_desc,
        mpesa_receipt_no=payload.mpesa_receipt_no,
        raw=payload.raw,
    )
    if not result:
        raise _404("M-Pesa payment record")
    return result


@router.get("/mpesa/payments")
async def list_mpesa(
    txn_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_mpesa_payments(db, txn_id=txn_id, status=status)


# ── Fraud ─────────────────────────────────────────────────────────────────────

@router.post("/fraud/scan", status_code=201)
async def run_fraud_scan(days: int = 7, db: AsyncSession = Depends(get_db)):
    return await svc.run_fraud_scan(db, cutoff_days=days)


@router.get("/fraud/alerts")
async def list_fraud_alerts(
    van_id: Optional[UUID] = None,
    driver_id: Optional[UUID] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_fraud_alerts(
        db, van_id=van_id, driver_id=driver_id, status=status, severity=severity, skip=skip, limit=limit
    )


@router.patch("/fraud/alerts/{alert_id}")
async def review_alert(
    alert_id: UUID,
    payload: FraudReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await svc.review_fraud_alert(db, alert_id, payload.status, payload.resolution, reviewer_id=None)
    if not result:
        raise _404("Alert")
    return result


# ── Rider Performance ─────────────────────────────────────────────────────────

@router.post("/performance/compute", status_code=201)
async def compute_performance(payload: PerformanceComputeRequest, db: AsyncSession = Depends(get_db)):
    return await svc.compute_rider_performance(db, payload.driver_id, payload.perf_date)


@router.get("/performance")
async def list_performance(
    driver_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_rider_performance(db, driver_id=driver_id, from_date=from_date, to_date=to_date, skip=skip, limit=limit)


@router.get("/performance/leaderboard")
async def get_leaderboard(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.leaderboard(db, from_date=from_date, to_date=to_date)
