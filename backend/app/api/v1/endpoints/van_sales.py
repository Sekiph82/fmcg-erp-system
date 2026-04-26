"""Van Sales / Mobile POS API endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.van_sales import (
    VanCreate, VanUpdate, VanOut,
    VanStockOut, StockLoadRequest,
    VisitCreate, VisitCheckIn, VisitOut,
    TxnCreate, TxnOut,
    PaymentCreate, PaymentOut,
    ReconciliationCreate, ReconciliationOut,
    SyncPayload, SyncResult,
    VSAIRecOut, VSAIRecAck,
)
from app.services import van_sales_service as svc

router = APIRouter()


def _404(label: str = "Record"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


# ── Vans ─────────────────────────────────────────────────────────────────────

@router.get("/vans", response_model=List[VanOut])
async def list_vans(
    status: Optional[str] = None, skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_vans(db, status=status, skip=skip, limit=limit)


@router.post("/vans", response_model=VanOut, status_code=201)
async def create_van(payload: VanCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_van(db, payload)


@router.get("/vans/{van_id}", response_model=VanOut)
async def get_van(van_id: UUID, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return v


@router.patch("/vans/{van_id}", response_model=VanOut)
async def update_van(van_id: UUID, payload: VanUpdate, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.update_van(db, v, payload)


# ── Van Stock ─────────────────────────────────────────────────────────────────

@router.get("/vans/{van_id}/stock", response_model=List[VanStockOut])
async def get_stock(van_id: UUID, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.get_van_stock(db, van_id)


@router.post("/vans/{van_id}/stock/load", response_model=List[VanStockOut], status_code=201)
async def load_stock(van_id: UUID, payload: StockLoadRequest, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.load_stock(db, v, payload, user_id=None)


# ── Visits ────────────────────────────────────────────────────────────────────

@router.get("/vans/{van_id}/visits", response_model=List[VisitOut])
async def list_visits(
    van_id: UUID,
    route_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.list_visits(db, van_id, route_date=route_date)


@router.post("/vans/{van_id}/visits", response_model=VisitOut, status_code=201)
async def create_visit(van_id: UUID, payload: VisitCreate, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    try:
        return await svc.create_visit(db, v, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/visits/{visit_id}/check-in", response_model=VisitOut)
async def check_in(visit_id: UUID, payload: VisitCheckIn, db: AsyncSession = Depends(get_db)):
    from app.models.van_sales import VanVisit
    visit = await db.get(VanVisit, visit_id)
    if not visit:
        raise _404("Visit")
    return await svc.check_in_visit(db, visit, payload)


@router.post("/visits/{visit_id}/check-out", response_model=VisitOut)
async def check_out(visit_id: UUID, notes: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from app.models.van_sales import VanVisit
    visit = await db.get(VanVisit, visit_id)
    if not visit:
        raise _404("Visit")
    return await svc.check_out_visit(db, visit, notes)


@router.post("/visits/{visit_id}/missed", response_model=VisitOut)
async def missed(visit_id: UUID, reason: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from app.models.van_sales import VanVisit
    visit = await db.get(VanVisit, visit_id)
    if not visit:
        raise _404("Visit")
    return await svc.mark_missed_visit(db, visit, reason)


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/vans/{van_id}/transactions", response_model=List[TxnOut])
async def list_transactions(
    van_id: UUID,
    route_date: Optional[date] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.list_transactions(db, van_id, route_date=route_date, skip=skip, limit=limit)


@router.post("/vans/{van_id}/transactions", response_model=TxnOut, status_code=201)
async def create_transaction(
    van_id: UUID, payload: TxnCreate, db: AsyncSession = Depends(get_db)
):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    try:
        return await svc.create_transaction(db, v, payload, user_id=None)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/transactions/{txn_id}", response_model=TxnOut)
async def get_transaction(txn_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_transaction(db, txn_id)
    if not t:
        raise _404("Transaction")
    return t


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/transactions/{txn_id}/payments", response_model=PaymentOut, status_code=201)
async def add_payment(
    txn_id: UUID, payload: PaymentCreate, db: AsyncSession = Depends(get_db)
):
    t = await svc.get_transaction(db, txn_id)
    if not t:
        raise _404("Transaction")
    return await svc.add_payment(db, t, payload, user_id=None)


# ── Reconciliation ────────────────────────────────────────────────────────────

@router.get("/vans/{van_id}/reconciliations", response_model=List[ReconciliationOut])
async def list_reconciliations(
    van_id: UUID, skip: int = 0, limit: int = 30, db: AsyncSession = Depends(get_db)
):
    return await svc.list_reconciliations(db, van_id, skip=skip, limit=limit)


@router.post("/vans/{van_id}/reconciliations", response_model=ReconciliationOut, status_code=201)
async def create_reconciliation(
    van_id: UUID, payload: ReconciliationCreate, db: AsyncSession = Depends(get_db)
):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.create_reconciliation(db, v, payload, user_id=None)


@router.post("/reconciliations/{recon_id}/approve", response_model=ReconciliationOut)
async def approve_reconciliation(recon_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models.van_sales import VanReconciliation
    recon = await db.get(VanReconciliation, recon_id)
    if not recon:
        raise _404("Reconciliation")
    return await svc.approve_reconciliation(db, recon, user_id=None)


# ── Offline Sync ──────────────────────────────────────────────────────────────

@router.post("/vans/{van_id}/sync", response_model=SyncResult, status_code=201)
async def sync(van_id: UUID, payload: SyncPayload, db: AsyncSession = Depends(get_db)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    return await svc.process_sync(db, v, payload, user_id=None)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/van/{van_id}/summary", response_model=Dict[str, Any])
async def report_van_summary(van_id: UUID, days: int = 30, db: AsyncSession = Depends(get_db)):
    return await svc.report_van_summary(db, van_id, days=days)


@router.get("/reports/route-performance", response_model=List[Dict])
async def report_route_performance(days: int = 30, db: AsyncSession = Depends(get_db)):
    return await svc.report_route_performance(db, days=days)


@router.get("/reports/driver-performance", response_model=List[Dict])
async def report_driver_performance(days: int = 30, db: AsyncSession = Depends(get_db)):
    return await svc.report_driver_performance(db, days=days)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[VSAIRecOut], status_code=201)
async def run_ai(db: AsyncSession = Depends(get_db)):
    return await svc.run_ai_agents(db)


@router.get("/ai/recommendations", response_model=List[VSAIRecOut])
async def ai_recs(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=VSAIRecOut)
async def ack_rec(rec_id: UUID, payload: VSAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise _404("Recommendation")
    return rec
