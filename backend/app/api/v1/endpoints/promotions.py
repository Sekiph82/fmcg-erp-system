"""Promotional Schemes Auto-Apply API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.promotions import (
    PromoSchemeCreate, PromoSchemeRead, PromoSchemeListItem,
    EvaluateOrderRequest, EvaluateOrderResult,
    SalesOrderPromoRead,
    OverrideRequestCreate, OverrideRequestRead, ApproveOverrideRequest,
    PromoAIRecRead, AckPromoAIRec,
    PromoDashboard, PromoUsageRow,
)
from app.models.promotions import SchemeStatus, OverrideStatus, PromoAIRecStatus
import app.services.promotions_service as svc
import uuid

router = APIRouter()


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=PromoDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.dashboard_summary(db)


# ── Scheme CRUD ────────────────────────────────────────────────────────────────

@router.get("/schemes", response_model=List[PromoSchemeListItem])
async def list_schemes(
    status: Optional[SchemeStatus] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_schemes(db, status, active_only)


@router.post("/schemes", response_model=PromoSchemeRead, status_code=201)
async def create_scheme(data: PromoSchemeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_scheme(db, data)


@router.get("/schemes/{scheme_id}", response_model=PromoSchemeRead)
async def get_scheme(scheme_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.get_scheme(db, scheme_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/schemes/{scheme_id}/activate", response_model=PromoSchemeRead)
async def activate_scheme(scheme_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.activate_scheme(db, scheme_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/schemes/{scheme_id}/status")
async def update_scheme_status(
    scheme_id: uuid.UUID,
    status: SchemeStatus,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.update_scheme_status(db, scheme_id, status)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Order Evaluation ───────────────────────────────────────────────────────────

@router.post("/evaluate-order", response_model=EvaluateOrderResult)
async def evaluate_order(data: EvaluateOrderRequest, db: AsyncSession = Depends(get_db)):
    return await svc.evaluate_order(
        db,
        data.sales_order_id,
        str(data.customer_id) if data.customer_id else None,
        data.channel,
        data.region,
        str(data.price_list_id) if data.price_list_id else None,
        data.order_lines,
    )


@router.post("/evaluate-order/{sales_order_id}/save", response_model=List[SalesOrderPromoRead])
async def save_promos(
    sales_order_id: uuid.UUID,
    data: EvaluateOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    eval_result = await svc.evaluate_order(
        db,
        sales_order_id,
        str(data.customer_id) if data.customer_id else None,
        data.channel,
        data.region,
        str(data.price_list_id) if data.price_list_id else None,
        data.order_lines,
    )
    await svc.save_order_promos(db, sales_order_id, eval_result)
    return await svc.get_order_promos(db, sales_order_id)


# ── Sales Order Promos ─────────────────────────────────────────────────────────

@router.get("/sales-orders/{sales_order_id}/promotions", response_model=List[SalesOrderPromoRead])
async def get_order_promos(sales_order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_order_promos(db, sales_order_id)


@router.post("/sales-orders/{sales_order_id}/promotions/recalculate", response_model=EvaluateOrderResult)
async def recalculate(
    sales_order_id: uuid.UUID,
    data: EvaluateOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    return await svc.evaluate_order(
        db,
        sales_order_id,
        str(data.customer_id) if data.customer_id else None,
        data.channel,
        data.region,
        str(data.price_list_id) if data.price_list_id else None,
        data.order_lines,
    )


# ── Override Requests ──────────────────────────────────────────────────────────

@router.get("/override-requests", response_model=List[OverrideRequestRead])
async def list_overrides(
    status: Optional[OverrideStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_override_requests(db, status)


@router.post("/override-requests", response_model=OverrideRequestRead, status_code=201)
async def create_override(data: OverrideRequestCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_override_request(db, data)


@router.post("/override-requests/{req_id}/approve", response_model=OverrideRequestRead)
async def approve_override(
    req_id: uuid.UUID,
    data: ApproveOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.approve_override(db, req_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/usage")
async def usage_report(db: AsyncSession = Depends(get_db)):
    rows = await svc.usage_report(db)
    return [
        {
            "scheme_id": str(r.id),
            "scheme_code": r.scheme_code,
            "scheme_name": r.scheme_name,
            "scheme_type": r.scheme_type,
            "order_count": r.order_count,
            "total_discount": float(r.total_discount),
            "total_free_value": float(r.total_free_value),
            "total_cost": float(r.total_cost),
        }
        for r in rows
    ]


# ── AI Agents ──────────────────────────────────────────────────────────────────

@router.post("/ai/run-agents")
async def run_agents(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_ai_agents(db)
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[PromoAIRecRead])
async def list_ai_recs(
    status: Optional[PromoAIRecStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=PromoAIRecRead)
async def ack_ai_rec(
    rec_id: uuid.UUID,
    data: AckPromoAIRec,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.ack_ai_rec(db, rec_id, data.status)
    except ValueError as e:
        raise HTTPException(404, str(e))
