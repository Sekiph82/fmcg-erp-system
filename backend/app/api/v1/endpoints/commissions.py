"""Sales Commission Tracking API endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.commissions import (
    CommissionRuleCreate, CommissionRuleUpdate, CommissionRuleOut,
    TargetCreate, TargetOut,
    CommissionCalcRequest, CommissionTxnOut,
    AdjustmentCreate, AdjustmentOut,
    ApproveRequest, RejectRequest,
    PayoutCreate, PayoutOut,
    CMAIRecOut, CMAIRecAck,
)
from app.services import commissions_service as svc

router = APIRouter()


def _404(label: str = "Record"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=List[CommissionRuleOut])
async def list_rules(
    applies_to: Optional[str] = None, status: Optional[str] = None,
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
):
    return await svc.list_rules(db, applies_to=applies_to, status=status, skip=skip, limit=limit)


@router.post("/rules", response_model=CommissionRuleOut, status_code=201)
async def create_rule(payload: CommissionRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_rule(db, payload, user_id=None)


@router.get("/rules/{rule_id}", response_model=CommissionRuleOut)
async def get_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await svc.get_rule(db, rule_id)
    if not r:
        raise _404("Rule")
    return r


@router.patch("/rules/{rule_id}", response_model=CommissionRuleOut)
async def update_rule(rule_id: UUID, payload: CommissionRuleUpdate, db: AsyncSession = Depends(get_db)):
    r = await svc.get_rule(db, rule_id)
    if not r:
        raise _404("Rule")
    return await svc.update_rule(db, r, payload)


@router.post("/rules/{rule_id}/activate", response_model=CommissionRuleOut)
async def activate_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await svc.get_rule(db, rule_id)
    if not r:
        raise _404("Rule")
    return await svc.activate_rule(db, r)


# ── Targets ───────────────────────────────────────────────────────────────────

@router.get("/targets", response_model=List[TargetOut])
async def list_targets(
    entity_id: Optional[UUID] = None, period: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_targets(db, entity_id=entity_id, period=period)


@router.post("/targets", response_model=TargetOut, status_code=201)
async def upsert_target(payload: TargetCreate, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_target(db, payload)


# ── Calculate ─────────────────────────────────────────────────────────────────

@router.post("/calculate", response_model=CommissionTxnOut, status_code=201)
async def calculate(payload: CommissionCalcRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.calculate_commission(db, payload, user_id=None)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=List[CommissionTxnOut])
async def list_transactions(
    sales_rep_id: Optional[UUID] = None,
    distributor_id: Optional[UUID] = None,
    period: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_transactions(
        db, sales_rep_id=sales_rep_id, distributor_id=distributor_id,
        period=period, status=status, skip=skip, limit=limit,
    )


@router.get("/transactions/{txn_id}", response_model=CommissionTxnOut)
async def get_txn(txn_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_txn(db, txn_id)
    if not t:
        raise _404("Transaction")
    return t


@router.post("/transactions/{txn_id}/approve", response_model=CommissionTxnOut)
async def approve_txn(txn_id: UUID, payload: ApproveRequest, db: AsyncSession = Depends(get_db)):
    t = await svc.get_txn(db, txn_id)
    if not t:
        raise _404("Transaction")
    return await svc.approve_txn(db, t, user_id=None, comments=payload.comments)


@router.post("/transactions/{txn_id}/reject", response_model=CommissionTxnOut)
async def reject_txn(txn_id: UUID, payload: RejectRequest, db: AsyncSession = Depends(get_db)):
    t = await svc.get_txn(db, txn_id)
    if not t:
        raise _404("Transaction")
    return await svc.reject_txn(db, t, reason=payload.reason, user_id=None)


@router.post("/transactions/{txn_id}/adjustments", response_model=AdjustmentOut, status_code=201)
async def add_adjustment(txn_id: UUID, payload: AdjustmentCreate, db: AsyncSession = Depends(get_db)):
    t = await svc.get_txn(db, txn_id)
    if not t:
        raise _404("Transaction")
    return await svc.add_adjustment(db, t, payload, user_id=None)


# ── Payouts ───────────────────────────────────────────────────────────────────

@router.get("/payouts", response_model=List[PayoutOut])
async def list_payouts(
    entity_id: Optional[UUID] = None, period: Optional[str] = None,
    status: Optional[str] = None, db: AsyncSession = Depends(get_db),
):
    return await svc.list_payouts(db, entity_id=entity_id, period=period, status=status)


@router.post("/payouts", response_model=PayoutOut, status_code=201)
async def create_payout(payload: PayoutCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_payout(db, payload, user_id=None)


@router.post("/payouts/{payout_id}/approve", response_model=PayoutOut)
async def approve_payout(payout_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models.commissions import CommissionPayout
    p = await db.get(CommissionPayout, payout_id)
    if not p:
        raise _404("Payout")
    return await svc.approve_payout(db, p, user_id=None)


@router.post("/payouts/{payout_id}/mark-paid", response_model=PayoutOut)
async def mark_paid(payout_id: UUID, payment_date: date = Query(default_factory=date.today), db: AsyncSession = Depends(get_db)):
    from app.models.commissions import CommissionPayout
    p = await db.get(CommissionPayout, payout_id)
    if not p:
        raise _404("Payout")
    return await svc.mark_payout_paid(db, p, payment_date)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/summary", response_model=Dict[str, Any])
async def report_summary(db: AsyncSession = Depends(get_db)):
    return await svc.report_summary(db)


@router.get("/reports/by-period", response_model=List[Dict])
async def report_by_period(period: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_by_period(db, period=period)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[CMAIRecOut], status_code=201)
async def run_ai(db: AsyncSession = Depends(get_db)):
    return await svc.run_ai_agents(db)


@router.get("/ai/recommendations", response_model=List[CMAIRecOut])
async def ai_recs(
    agent_type: Optional[str] = None, status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=CMAIRecOut)
async def ack_rec(rec_id: UUID, payload: CMAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise _404("Recommendation")
    return rec
