from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as _BM
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.tpm import (
    TPMPlanCreate, TPMPlanRead,
    TPMPromotionCreate, TPMPromotionRead,
    TPMBudgetLineCreate, TPMBudgetLineRead,
    TPMExpectedPerfCreate, TPMExpectedPerfRead,
    TPMActualPerfCreate, TPMActualPerfRead,
    TPMClaimCreate, TPMClaimRead, TPMClaimReviewRequest, TPMClaimSettleRequest,
    TPMAIRecRead, TPMAIRecAckRequest,
    TPMDashboard,
)
from app.models.tpm import TPMPlanStatus, TPMPromotionStatus
import app.services.tpm_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[TPMPlanRead])
async def list_plans(
    status: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_plans(db, status=status, fiscal_year=fiscal_year)


@router.post("/plans", response_model=TPMPlanRead)
async def create_plan(data: TPMPlanCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_plan(db, data)


@router.get("/plans/{plan_id}", response_model=TPMPlanRead)
async def get_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    plan = await svc.get_plan(db, str(plan_id))
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


@router.post("/plans/{plan_id}/approve", response_model=TPMPlanRead)
async def approve_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.approve_plan(db, str(plan_id))


@router.patch("/plans/{plan_id}/status", response_model=TPMPlanRead)
async def update_plan_status(
    plan_id: UUID,
    status: TPMPlanStatus = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_plan_status(db, str(plan_id), status)


# ── Promotions ────────────────────────────────────────────────────────────────

@router.get("/promotions", response_model=List[TPMPromotionRead])
async def list_promotions(
    status: Optional[str] = None,
    plan_id: Optional[UUID] = None,
    promotion_type: Optional[str] = None,
    channel_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_promotions(
        db,
        status=status,
        plan_id=str(plan_id) if plan_id else None,
        promotion_type=promotion_type,
        channel_id=channel_id,
        brand_id=brand_id,
    )


@router.post("/promotions", response_model=TPMPromotionRead)
async def create_promotion(data: TPMPromotionCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_promotion(db, data)


@router.get("/promotions/{promo_id}", response_model=TPMPromotionRead)
async def get_promotion(promo_id: UUID, db: AsyncSession = Depends(get_db)):
    promo = await svc.get_promotion(db, str(promo_id))
    if not promo:
        raise HTTPException(404, "Promotion not found")
    return promo


@router.post("/promotions/{promo_id}/approve", response_model=TPMPromotionRead)
async def approve_promotion(promo_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.approve_promotion(db, str(promo_id))


@router.patch("/promotions/{promo_id}/status", response_model=TPMPromotionRead)
async def update_promotion_status(
    promo_id: UUID,
    status: TPMPromotionStatus = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_promotion_status(db, str(promo_id), status)


@router.post("/promotions/{promo_id}/link-scheme", response_model=TPMPromotionRead)
async def link_scheme(promo_id: UUID, scheme_id: UUID = Query(...), db: AsyncSession = Depends(get_db)):
    return await svc.link_scheme(db, str(promo_id), str(scheme_id))


# ── Budget Lines ──────────────────────────────────────────────────────────────

@router.post("/promotions/{promo_id}/budget-lines", response_model=TPMBudgetLineRead)
async def add_budget_line(promo_id: UUID, data: TPMBudgetLineCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_budget_line(db, str(promo_id), data)


# ── Performance ───────────────────────────────────────────────────────────────

@router.put("/promotions/{promo_id}/expected-perf", response_model=TPMExpectedPerfRead)
async def set_expected_perf(promo_id: UUID, data: TPMExpectedPerfCreate, db: AsyncSession = Depends(get_db)):
    return await svc.set_expected_perf(db, str(promo_id), data)


@router.put("/promotions/{promo_id}/actual-perf", response_model=TPMActualPerfRead)
async def set_actual_perf(promo_id: UUID, data: TPMActualPerfCreate, db: AsyncSession = Depends(get_db)):
    return await svc.set_actual_perf(db, str(promo_id), data)


@router.get("/promotions/{promo_id}/performance")
async def get_performance(promo_id: UUID, db: AsyncSession = Depends(get_db)):
    promo = await svc.get_promotion(db, str(promo_id))
    if not promo:
        raise HTTPException(404, "Promotion not found")
    return {
        "expected": promo.expected_perf,
        "actual":   promo.actual_perf,
    }


# ── Claims ────────────────────────────────────────────────────────────────────

@router.get("/claims", response_model=List[TPMClaimRead])
async def list_claims(
    status: Optional[str] = None,
    promotion_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_claims(db, status=status, promotion_id=str(promotion_id) if promotion_id else None)


@router.post("/claims", response_model=TPMClaimRead)
async def create_claim(data: TPMClaimCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_claim(db, data)


@router.get("/claims/{claim_id}", response_model=TPMClaimRead)
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    claim = await svc.get_claim(db, str(claim_id))
    if not claim:
        raise HTTPException(404, "Claim not found")
    return claim


@router.post("/claims/{claim_id}/review", response_model=TPMClaimRead)
async def review_claim(claim_id: UUID, req: TPMClaimReviewRequest, db: AsyncSession = Depends(get_db)):
    return await svc.review_claim(db, str(claim_id), req)


@router.post("/claims/{claim_id}/settle", response_model=TPMClaimRead)
async def settle_claim(claim_id: UUID, req: TPMClaimSettleRequest, db: AsyncSession = Depends(get_db)):
    return await svc.settle_claim(db, str(claim_id), req)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/budget-vs-actual")
async def report_budget_vs_actual(
    fiscal_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.report_budget_vs_actual(db, fiscal_year=fiscal_year)


@router.get("/reports/roi")
async def report_roi(db: AsyncSession = Depends(get_db)):
    return await svc.report_roi(db)


@router.get("/reports/claim-aging")
async def report_claim_aging(db: AsyncSession = Depends(get_db)):
    return await svc.report_claim_aging(db)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-agents")
async def run_agents(db: AsyncSession = Depends(get_db)):
    return await svc.run_agents(db)


@router.get("/ai/recommendations", response_model=List[TPMAIRecRead])
async def get_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_ai_recs(db, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=TPMAIRecRead)
async def ack_ai_rec(rec_id: UUID, req: TPMAIRecAckRequest, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, str(rec_id), req)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec


# ── Distributor Rebate Accruals ───────────────────────────────────────────────

class AccrualIn(_BM):
    distributor_id: str
    distributor_name: Optional[str] = None
    promotion_id: Optional[str] = None
    period_month: str         # YYYY-MM
    rebate_rate_pct: Optional[float] = None
    rebate_amount_flat: Optional[float] = None
    total_sales_value: float = 0.0
    total_units_sold: float = 0.0
    notes: Optional[str] = None


class AccrualAddIn(_BM):
    sales_value: float
    units_sold: float = 0.0


@router.post("/rebate-accruals", status_code=201)
async def create_rebate_accrual(payload: AccrualIn, db: AsyncSession = Depends(get_db)):
    from app.models.tpm import DistributorRebateAccrual
    # Compute accrued amount
    accrued = 0.0
    if payload.rebate_rate_pct:
        accrued = payload.total_sales_value * payload.rebate_rate_pct / 100
    elif payload.rebate_amount_flat:
        accrued = payload.total_units_sold * payload.rebate_amount_flat

    acc = DistributorRebateAccrual(
        promotion_id=_uuid.UUID(payload.promotion_id) if payload.promotion_id else None,
        distributor_id=payload.distributor_id,
        distributor_name=payload.distributor_name,
        period_month=payload.period_month,
        rebate_rate_pct=payload.rebate_rate_pct,
        rebate_amount_flat=payload.rebate_amount_flat,
        total_sales_value=payload.total_sales_value,
        total_units_sold=payload.total_units_sold,
        accrued_amount=accrued,
        outstanding_amount=accrued,
        notes=payload.notes,
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return {"id": str(acc.id), "distributor_id": acc.distributor_id,
            "period_month": acc.period_month, "accrued_amount": float(acc.accrued_amount),
            "status": acc.status}


@router.get("/rebate-accruals")
async def list_rebate_accruals(
    distributor_id: Optional[str] = None,
    status: Optional[str] = None,
    period_month: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.tpm import DistributorRebateAccrual
    q = select(DistributorRebateAccrual)
    if distributor_id:
        q = q.where(DistributorRebateAccrual.distributor_id == distributor_id)
    if status:
        q = q.where(DistributorRebateAccrual.status == status)
    if period_month:
        q = q.where(DistributorRebateAccrual.period_month == period_month)
    q = q.order_by(desc(DistributorRebateAccrual.period_month)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "distributor_name": r.distributor_name,
         "period_month": r.period_month, "accrued_amount": float(r.accrued_amount),
         "settled_amount": float(r.settled_amount), "outstanding_amount": float(r.outstanding_amount),
         "status": r.status, "claim_ref": r.claim_ref,
         "total_sales_value": float(r.total_sales_value)}
        for r in rows
    ]


@router.post("/rebate-accruals/{accrual_id}/settle")
async def settle_accrual(
    accrual_id: str,
    claim_ref: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Mark rebate accrual as settled — links to a claim reference."""
    from app.models.tpm import DistributorRebateAccrual, RebateAccrualStatus
    r = await db.execute(select(DistributorRebateAccrual).where(DistributorRebateAccrual.id == _uuid.UUID(accrual_id)))
    acc = r.scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "Accrual not found")
    acc.settled_amount = acc.accrued_amount
    acc.outstanding_amount = 0
    acc.status = RebateAccrualStatus.SETTLED
    acc.settled_at = datetime.utcnow()
    acc.claim_ref = claim_ref
    await db.commit()
    return {"id": accrual_id, "status": "SETTLED", "settled_amount": float(acc.settled_amount), "claim_ref": claim_ref}
