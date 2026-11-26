"""Van Sales / Mobile POS API endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as _BM, Field as _F

from app.core.deps import get_current_user
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


VAN_MANAGERS = ("field.supervise", "logistics.edit")  # supervisors / logistics officers act for any van


async def _van_actor_or_403(db: AsyncSession, user, van) -> None:
    """Van actions (check-in, photo, POS sale/payment, sync): the van's driver, the rep assigned to the van's route,
    or a supervisor / logistics manager. Everyone else gets 403 (M48.S01.T024)."""
    from app.core.access_control import has_any_permission
    from app.models.field_sales import SalesRep, SalesRoute

    if van.driver_id == user.id or has_any_permission(user, VAN_MANAGERS):
        return
    if van.route_id is not None:
        rep_user = (await db.execute(select(SalesRep.user_id).join(SalesRoute, SalesRoute.assigned_rep_id == SalesRep.id)
                                     .where(SalesRoute.id == van.route_id))).scalars().first()
        if rep_user == user.id:
            return
    raise HTTPException(status_code=403, detail="Only this van's driver or rep, or a supervisor, can do this")


async def _visit_for_actor(db: AsyncSession, user, visit_id: UUID):
    from app.models.van_sales import Van, VanVisit
    visit = await db.get(VanVisit, visit_id)
    if not visit:
        raise _404("Visit")
    await _van_actor_or_403(db, user, await db.get(Van, visit.van_id))
    return visit


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
async def check_in(visit_id: UUID, payload: VisitCheckIn, db: AsyncSession = Depends(get_db),
                   user=Depends(get_current_user)):
    visit = await _visit_for_actor(db, user, visit_id)
    try:
        return await svc.check_in_visit(db, visit, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/visits/{visit_id}/check-out", response_model=VisitOut)
async def check_out(visit_id: UUID, notes: Optional[str] = None, db: AsyncSession = Depends(get_db),
                    user=Depends(get_current_user)):
    visit = await _visit_for_actor(db, user, visit_id)
    return await svc.check_out_visit(db, visit, notes)


@router.post("/visits/{visit_id}/missed", response_model=VisitOut)
async def missed(visit_id: UUID, reason: Optional[str] = None, db: AsyncSession = Depends(get_db),
                 user=Depends(get_current_user)):
    visit = await _visit_for_actor(db, user, visit_id)
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
    van_id: UUID, payload: TxnCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    await _van_actor_or_403(db, user, v)
    try:
        txn = await svc.create_transaction(db, v, payload, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await svc.get_transaction(db, txn.id)  # lines/payments loaded (TxnOut cannot lazy-load in async)


@router.get("/transactions/{txn_id}", response_model=TxnOut)
async def get_transaction(txn_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_transaction(db, txn_id)
    if not t:
        raise _404("Transaction")
    return t


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/transactions/{txn_id}/payments", response_model=PaymentOut, status_code=201)
async def add_payment(
    txn_id: UUID, payload: PaymentCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    t = await svc.get_transaction(db, txn_id)
    if not t:
        raise _404("Transaction")
    await _van_actor_or_403(db, user, await svc.get_van(db, t.van_id))
    try:
        return await svc.add_payment(db, t, payload, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


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
async def sync(van_id: UUID, payload: SyncPayload, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    v = await svc.get_van(db, van_id)
    if not v:
        raise _404("Van")
    await _van_actor_or_403(db, user, v)
    return await svc.process_sync(db, v, payload, user_id=user.id)


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


# ── Outlet Photo Capture ──────────────────────────────────────────────────────

class PhotoIn(_BM):
    photo_url: str = _F(max_length=2000, pattern=r"^https://\S+$")


@router.post("/visits/{visit_id}/photo")
async def set_visit_photo(
    visit_id: UUID,
    payload: PhotoIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Record an outlet photo URL against a visit."""
    visit = await _visit_for_actor(db, user, visit_id)
    visit.outlet_photo_url = payload.photo_url
    await db.commit()
    return {"visit_id": str(visit_id), "outlet_photo_url": payload.photo_url}


@router.post("/visits/{visit_id}/photo-upload")
async def upload_visit_photo(visit_id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                             user=Depends(get_current_user)):
    """Outlet photo from the device camera: stored (and malware-scanned) like the field app's photos; the visit keeps
    the storage key, not a public URL. Only a visit that was checked in can carry a photo."""
    from app.api.v1.endpoints.field_app import _forget, _store
    from app.models.van_sales import VisitStatus
    visit = await _visit_for_actor(db, user, visit_id)
    if visit.status not in (VisitStatus.CHECKED_IN.value, VisitStatus.COMPLETED.value):
        raise HTTPException(status_code=409, detail="Check in before adding the outlet photo")
    old = visit.outlet_photo_url
    visit.outlet_photo_url = "doc:" + await _store(file)
    await db.commit()
    if old and old.startswith("doc:"):
        _forget([old[4:]])
    return {"visit_id": str(visit_id), "has_photo": True}


# ── Field Rep Daily GPS Log ───────────────────────────────────────────────────

class RepDayLogIn(_BM):
    rep_user_id: Optional[UUID] = None
    rep_name: Optional[str] = None
    log_date: date
    start_time: Optional[str] = None
    start_gps_lat: Optional[float] = _F(default=None, ge=-90, le=90)
    start_gps_lng: Optional[float] = _F(default=None, ge=-180, le=180)
    start_photo_url: Optional[str] = None
    end_time: Optional[str] = None
    end_gps_lat: Optional[float] = _F(default=None, ge=-90, le=90)
    end_gps_lng: Optional[float] = _F(default=None, ge=-180, le=180)
    end_photo_url: Optional[str] = None
    total_visits: Optional[int] = _F(default=None, ge=0, le=10000)
    total_km_est: Optional[float] = _F(default=None, ge=0, le=100000)
    total_sales: Optional[float] = _F(default=None, ge=0)
    notes: Optional[str] = _F(default=None, max_length=2000)


def _day_log_writer_or_403(user, rep_user_id: UUID) -> None:
    """A rep writes only their own day log; a supervisor (field.supervise) may write for another rep."""
    from app.core.access_control import has_permission
    if rep_user_id != user.id and not has_permission(user, "field.supervise"):
        raise HTTPException(status_code=403, detail="You can only write your own day log")


@router.post("/rep-day-log", status_code=201)
async def create_rep_day_log(
    payload: RepDayLogIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create or upsert a field rep daily GPS log entry (defaults to the signed-in user's own log)."""
    from app.models.van_sales import VanRepDayLog
    from datetime import datetime as _dt, timezone as _tz

    if not payload.rep_user_id:
        payload.rep_user_id = user.id
        payload.rep_name = payload.rep_name or user.full_name or user.username
    _day_log_writer_or_403(user, payload.rep_user_id)

    existing_r = await db.execute(
        select(VanRepDayLog).where(
            VanRepDayLog.rep_user_id == (payload.rep_user_id if payload.rep_user_id else None),
            VanRepDayLog.log_date == payload.log_date,
        )
    ) if payload.rep_user_id else None

    existing = existing_r.scalar_one_or_none() if existing_r else None

    def _parse_dt(s: Optional[str]):
        if not s:
            return None
        try:
            v = _dt.fromisoformat(s)
        except Exception:
            return None
        # the column is naive UTC; a browser sends ISO with "Z"
        return v.astimezone(_tz.utc).replace(tzinfo=None) if v.tzinfo else v

    if existing:
        for attr, val in [
            ("end_time", _parse_dt(payload.end_time)),
            ("end_gps_lat", payload.end_gps_lat),
            ("end_gps_lng", payload.end_gps_lng),
            ("end_photo_url", payload.end_photo_url),
            ("total_visits", payload.total_visits),
            ("total_km_est", payload.total_km_est),
            ("total_sales", payload.total_sales),
            ("notes", payload.notes),
        ]:
            if val is not None:
                setattr(existing, attr, val)
        await db.commit()
        return {"id": str(existing.id), "action": "updated"}

    log = VanRepDayLog(
        rep_user_id=payload.rep_user_id,
        rep_name=payload.rep_name,
        log_date=payload.log_date,
        start_time=_parse_dt(payload.start_time),
        start_gps_lat=payload.start_gps_lat,
        start_gps_lng=payload.start_gps_lng,
        start_photo_url=payload.start_photo_url,
        end_time=_parse_dt(payload.end_time),
        end_gps_lat=payload.end_gps_lat,
        end_gps_lng=payload.end_gps_lng,
        end_photo_url=payload.end_photo_url,
        total_visits=payload.total_visits,
        total_km_est=payload.total_km_est,
        total_sales=payload.total_sales,
        notes=payload.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {"id": str(log.id), "action": "created"}


@router.get("/rep-day-log")
async def list_rep_day_logs(
    rep_user_id: Optional[str] = None,
    log_date: Optional[date] = None,
    mine: bool = False,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List field rep daily logs (``mine=true``: only the signed-in user's)."""
    from app.models.van_sales import VanRepDayLog
    if mine:
        rep_user_id = str(user.id)
    q = select(VanRepDayLog)
    if rep_user_id:
        q = q.where(VanRepDayLog.rep_user_id == rep_user_id)
    if log_date:
        q = q.where(VanRepDayLog.log_date == log_date)
    q = q.order_by(desc(VanRepDayLog.log_date)).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        {
            "id": str(lg.id),
            "rep_name": lg.rep_name,
            "rep_user_id": str(lg.rep_user_id) if lg.rep_user_id else None,
            "log_date": str(lg.log_date),
            "start_time": lg.start_time.isoformat() if lg.start_time else None,
            "start_gps_lat": float(lg.start_gps_lat) if lg.start_gps_lat else None,
            "start_gps_lng": float(lg.start_gps_lng) if lg.start_gps_lng else None,
            "end_time": lg.end_time.isoformat() if lg.end_time else None,
            "end_gps_lat": float(lg.end_gps_lat) if lg.end_gps_lat else None,
            "end_gps_lng": float(lg.end_gps_lng) if lg.end_gps_lng else None,
            "total_visits": lg.total_visits,
            "total_km_est": float(lg.total_km_est) if lg.total_km_est else None,
            "total_sales": float(lg.total_sales) if lg.total_sales else None,
            "start_photo_url": lg.start_photo_url,
            "end_photo_url": lg.end_photo_url,
            "notes": lg.notes,
            "created_at": lg.created_at.isoformat() if lg.created_at else "",
        }
        for lg in logs
    ]
