from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import secondary_sales as crud
from app.services import secondary_sales_service as svc
from app.models.secondary_sales import SecondarySalesStatus
from app.schemas.secondary_sales import (
    RetailerCreate, RetailerRead,
    SecondarySalesUpload, SecondarySalesRead, SecondarySalesDetail,
    SecondarySalesLineRead,
    InventorySnapshotCreate, InventorySnapshotRead,
    SellThroughRow, DistributorPerformanceRow, ProductSellThroughRow,
    AIInsightResult,
)

router = APIRouter()


def _retailer_read(r) -> RetailerRead:
    out = RetailerRead.model_validate(r)
    if r.distributor:
        out.distributor_name = r.distributor.name
    return out


def _header_read(h) -> SecondarySalesRead:
    out = SecondarySalesRead.model_validate(h)
    if h.distributor:
        out.distributor_name = h.distributor.name
    return out


def _header_detail(h) -> SecondarySalesDetail:
    out = SecondarySalesDetail.model_validate(h)
    if h.distributor:
        out.distributor_name = h.distributor.name
    lines = []
    for line in h.lines:
        lr = SecondarySalesLineRead.model_validate(line)
        if line.product:
            lr.product_name = line.product.name
            if not lr.product_sku:
                lr.product_sku = line.product.sku
        if line.retailer and not lr.retailer_name:
            lr.retailer_name = line.retailer.name
        lines.append(lr)
    out.lines = lines
    return out


def _snap_read(s) -> InventorySnapshotRead:
    out = InventorySnapshotRead.model_validate(s)
    if s.distributor:
        out.distributor_name = s.distributor.name
    if s.product:
        out.product_name = s.product.name
        out.product_sku = s.product.sku
    return out


# ── Retailers ─────────────────────────────────────────────────────────────────

@router.get("/retailers", response_model=List[RetailerRead])
async def list_retailers(
    distributor_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    retailers = await crud.list_retailers(db, distributor_id=distributor_id, skip=skip, limit=limit)
    return [_retailer_read(r) for r in retailers]


@router.post("/retailers", response_model=RetailerRead, status_code=201)
async def create_retailer(
    data: RetailerCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_retailer(db, data)
    await db.commit()
    obj = await crud.get_retailer(db, obj.id)
    return _retailer_read(obj)


# ── Secondary Sales Upload ────────────────────────────────────────────────────

@router.post("/upload", response_model=SecondarySalesRead, status_code=201)
async def upload_secondary_sales(
    data: SecondarySalesUpload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    header = await svc.upload_secondary_sales(db, data, current_user.id)
    await db.commit()
    header = await crud.get_header(db, header.id)
    return _header_read(header)


@router.get("/", response_model=List[SecondarySalesRead])
async def list_secondary_sales(
    distributor_id: Optional[uuid.UUID] = None,
    status: Optional[SecondarySalesStatus] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    headers = await crud.list_headers(db, distributor_id=distributor_id, status=status, skip=skip, limit=limit)
    return [_header_read(h) for h in headers]


@router.get("/{header_id}", response_model=SecondarySalesDetail)
async def get_secondary_sales(
    header_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    h = await crud.get_header(db, header_id)
    if not h:
        raise HTTPException(404, "Secondary sales record not found")
    return _header_detail(h)


@router.post("/{header_id}/process", response_model=SecondarySalesRead)
async def process_secondary_sales(
    header_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    h = await crud.get_header(db, header_id)
    if not h:
        raise HTTPException(404, "Record not found")
    h = await svc.process_header(db, h)
    await db.commit()
    h = await crud.get_header(db, header_id)
    return _header_read(h)


@router.post("/{header_id}/reject", response_model=SecondarySalesRead)
async def reject_secondary_sales(
    header_id: uuid.UUID,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    h = await crud.get_header(db, header_id)
    if not h:
        raise HTTPException(404, "Record not found")
    h = await svc.reject_header(db, h, reason)
    await db.commit()
    h = await crud.get_header(db, header_id)
    return _header_read(h)


# ── Distributor Inventory ─────────────────────────────────────────────────────

@router.get("/inventory/snapshots", response_model=List[InventorySnapshotRead])
async def list_inventory_snapshots(
    distributor_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    snaps = await crud.list_snapshots(db, distributor_id=distributor_id, product_id=product_id, skip=skip, limit=limit)
    return [_snap_read(s) for s in snaps]


@router.post("/inventory/snapshots", response_model=InventorySnapshotRead, status_code=201)
async def create_inventory_snapshot(
    data: InventorySnapshotCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_snapshot(db, data)
    await db.commit()
    snaps = await crud.list_snapshots(db, distributor_id=data.distributor_id, product_id=data.product_id)
    snap = next((s for s in snaps if s.id == obj.id), obj)
    return _snap_read(snap)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/report/sell-through", response_model=List[SellThroughRow])
async def sell_through_report(
    distributor_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_sell_through_report(db, distributor_id=distributor_id, date_from=date_from, date_to=date_to)


@router.get("/report/distributor-performance", response_model=List[DistributorPerformanceRow])
async def distributor_performance_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_distributor_performance(db, date_from=date_from, date_to=date_to)


@router.get("/report/product-performance", response_model=List[ProductSellThroughRow])
async def product_performance_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_product_performance(db, date_from=date_from, date_to=date_to)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/ai/demand-signal", response_model=AIInsightResult)
async def ai_demand_signal(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_demand_signal(db, date_from=date_from, date_to=date_to)


@router.get("/ai/distributor-risk", response_model=AIInsightResult)
async def ai_distributor_risk(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_distributor_risk(db, date_from=date_from, date_to=date_to)


@router.get("/ai/promotion-impact", response_model=AIInsightResult)
async def ai_promotion_impact(
    promo_start: Optional[date] = None,
    promo_end: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_promotion_impact(db, promo_start=promo_start, promo_end=promo_end)


# ── Gap 59 Expansion: Distributor Aging + SKU Velocity ───────────────────────

from sqlalchemy import func, desc as _desc

@router.get("/analytics/distributor-aging",
            dependencies=[Depends(get_current_user)])
async def distributor_aging_analysis(db: AsyncSession = Depends(get_db)):
    """Days since last sell-through upload per distributor."""
    from app.models.secondary_sales import SecondarySalesHeader
    from datetime import datetime
    today = datetime.utcnow().date()
    from sqlalchemy import select
    r = await db.execute(
        select(
            SecondarySalesHeader.distributor_id,
            func.max(SecondarySalesHeader.upload_date).label("last_upload"),
            func.count().label("total_uploads"),
        ).group_by(SecondarySalesHeader.distributor_id)
    )
    rows = r.all()
    result = []
    for row in rows:
        last = row.last_upload.date() if row.last_upload else None
        days_since = (today - last).days if last else None
        bucket = "No Data" if days_since is None else ("0-30d" if days_since <= 30 else "31-60d" if days_since <= 60 else "61-90d" if days_since <= 90 else "91+d")
        result.append({
            "distributor_id": str(row.distributor_id) if row.distributor_id else None,
            "last_upload_date": str(last) if last else None,
            "days_since_upload": days_since,
            "aging_bucket": bucket,
            "total_uploads": row.total_uploads,
        })
    result.sort(key=lambda x: x["days_since_upload"] or 9999, reverse=True)
    return result


@router.get("/analytics/sku-velocity",
            dependencies=[Depends(get_current_user)])
async def sku_velocity(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top SKUs by sell-through velocity (units/day)."""
    from app.models.secondary_sales import SecondarySalesLine, SecondarySalesHeader
    from datetime import datetime, timedelta
    from sqlalchemy import select
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    r = await db.execute(
        select(
            SecondarySalesLine.product_sku,
            func.sum(SecondarySalesLine.quantity_sold).label("total_units"),
            func.sum(SecondarySalesLine.total_value).label("total_value"),
            func.count(SecondarySalesLine.id).label("txn_count"),
        )
        .join(SecondarySalesHeader, SecondarySalesLine.header_id == SecondarySalesHeader.id)
        .where(SecondarySalesHeader.period_from >= cutoff, SecondarySalesLine.product_sku.isnot(None))
        .group_by(SecondarySalesLine.product_sku)
        .order_by(_desc("total_units"))
        .limit(limit)
    )
    return [
        {"product_sku": row.product_sku, "total_units": float(row.total_units or 0),
         "units_per_day": round(float(row.total_units or 0) / days, 2),
         "total_value": float(row.total_value or 0), "txn_count": row.txn_count}
        for row in r.all()
    ]
