from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import wms as crud
from app.services import wms_service as svc
from app.models.wms import StockCountStatus
from app.schemas.wms import (
    WarehouseZoneCreate, WarehouseZoneRead,
    StorageLocationCreate, StorageLocationUpdate, StorageLocationRead, ScanLocationResult,
    StockCountCreate, StockCountRead, StockCountDetailRead, StockCountLineRead,
    RecordCountRequest,
    PutawayRequest, QuarantineRequest, ReleaseQuarantineRequest,
    FEFOSuggestion,
    NearExpiryRow, LowStockRow, StockAgingRow, LotTraceResult,
)

router = APIRouter()


def _zone_read(zone) -> WarehouseZoneRead:
    r = WarehouseZoneRead.model_validate(zone)
    if zone.warehouse:
        r.warehouse_name = zone.warehouse.name
    r.location_count = len(zone.locations)
    return r


def _location_read(loc) -> StorageLocationRead:
    r = StorageLocationRead.model_validate(loc)
    if loc.zone:
        r.zone_code = loc.zone.code
        r.zone_name = loc.zone.name
        r.zone_type = loc.zone.zone_type
        if loc.zone.warehouse:
            r.warehouse_id = loc.zone.warehouse.id
            r.warehouse_name = loc.zone.warehouse.name
    return r


def _count_read(c) -> StockCountRead:
    r = StockCountRead.model_validate(c)
    if c.warehouse:
        r.warehouse_name = c.warehouse.name
    if c.zone:
        r.zone_name = c.zone.name
    r.total_lines = len(c.lines)
    r.counted_lines = sum(1 for l in c.lines if l.is_counted)
    return r


def _count_detail(c) -> StockCountDetailRead:
    r = StockCountDetailRead.model_validate(c)
    if c.warehouse:
        r.warehouse_name = c.warehouse.name
    if c.zone:
        r.zone_name = c.zone.name
    r.total_lines = len(c.lines)
    r.counted_lines = sum(1 for l in c.lines if l.is_counted)
    lines = []
    for line in c.lines:
        lr = StockCountLineRead.model_validate(line)
        if line.product:
            lr.product_name = line.product.name
            lr.product_sku = line.product.sku
        if line.material:
            lr.material_name = line.material.name
            lr.material_code = line.material.code
        if line.lot:
            lr.lot_number = line.lot.lot_number
        if line.location:
            lr.location_code = line.location.code
        lines.append(lr)
    r.lines = lines
    return r


# ── Zones ─────────────────────────────────────────────────────────────────────

@router.get("/zones/", response_model=List[WarehouseZoneRead])
async def list_zones(
    warehouse_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    zones = await crud.list_zones(db, warehouse_id=warehouse_id, skip=skip, limit=limit)
    return [_zone_read(z) for z in zones]


@router.post("/zones/", response_model=WarehouseZoneRead, status_code=201)
async def create_zone(
    data: WarehouseZoneCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_zone(db, data)
    await db.commit()
    zone = await crud.get_zone(db, obj.id)
    return _zone_read(zone)


@router.get("/zones/{zone_id}", response_model=WarehouseZoneRead)
async def get_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    zone = await crud.get_zone(db, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")
    return _zone_read(zone)


# ── Locations ─────────────────────────────────────────────────────────────────

@router.get("/locations/", response_model=List[StorageLocationRead])
async def list_locations(
    zone_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    locs = await crud.list_locations(db, zone_id=zone_id, warehouse_id=warehouse_id, skip=skip, limit=limit)
    return [_location_read(l) for l in locs]


@router.post("/locations/", response_model=StorageLocationRead, status_code=201)
async def create_location(
    data: StorageLocationCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = await crud.create_location(db, data)
    await db.commit()
    loc = await crud.get_location(db, obj.id)
    return _location_read(loc)


@router.patch("/locations/{location_id}", response_model=StorageLocationRead)
async def update_location(
    location_id: uuid.UUID,
    data: StorageLocationUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    loc = await crud.get_location(db, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    loc = await crud.update_location(db, loc, data)
    await db.commit()
    loc = await crud.get_location(db, location_id)
    return _location_read(loc)


# ── Scan endpoints ─────────────────────────────────────────────────────────────

@router.get("/scan/location/{barcode}", response_model=ScanLocationResult,
            summary="Scan a storage location barcode")
async def scan_location(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    loc = await crud.get_location_by_barcode(db, barcode)
    if not loc:
        raise HTTPException(404, f"No location found with barcode '{barcode}'")

    from sqlalchemy import select as sel
    from app.models.inventory import Stock
    stocks = await db.execute(
        sel(Stock).where(Stock.location_id == loc.id, Stock.quantity_on_hand > 0)
    )
    stock_lines = [
        {
            "stock_type": s.stock_type.value,
            "product_id": str(s.product_id) if s.product_id else None,
            "material_id": str(s.material_id) if s.material_id else None,
            "lot_id": str(s.lot_id) if s.lot_id else None,
            "quantity_on_hand": float(s.quantity_on_hand),
            "quantity_available": float(s.quantity_available),
            "is_blocked": s.is_blocked,
        }
        for s in stocks.scalars()
    ]
    return ScanLocationResult(location=_location_read(loc), stock_lines=stock_lines)


@router.get("/scan/lot/{lot_number}", summary="Look up a lot by number/barcode")
async def scan_lot(
    lot_number: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from sqlalchemy import select as sel
    from app.models.inventory import Lot, Stock
    r = await db.execute(sel(Lot).where(Lot.lot_number == lot_number))
    lot = r.scalar_one_or_none()
    if not lot:
        raise HTTPException(404, f"Lot '{lot_number}' not found")

    stocks = await db.execute(
        sel(Stock).where(Stock.lot_id == lot.id, Stock.quantity_on_hand > 0)
    )
    return {
        "lot_number": lot.lot_number,
        "batch_number": lot.batch_number,
        "expiry_date": str(lot.expiry_date) if lot.expiry_date else None,
        "manufacture_date": str(lot.manufacture_date) if lot.manufacture_date else None,
        "is_quarantine": lot.is_quarantine,
        "stock_positions": [
            {
                "warehouse_id": str(s.warehouse_id),
                "quantity_on_hand": float(s.quantity_on_hand),
                "quantity_available": float(s.quantity_available),
                "is_blocked": s.is_blocked,
                "location_id": str(s.location_id) if s.location_id else None,
            }
            for s in stocks.scalars()
        ],
    }


@router.get("/scan/product/{barcode}", summary="Look up a product by barcode")
async def scan_product(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    from sqlalchemy import select as sel
    from app.models.master import Product
    from app.models.inventory import Stock
    r = await db.execute(sel(Product).where(Product.barcode == barcode))
    product = r.scalar_one_or_none()
    if not product:
        raise HTTPException(404, f"No product with barcode '{barcode}'")
    stocks = await db.execute(sel(Stock).where(Stock.product_id == product.id, Stock.quantity_on_hand > 0))
    return {
        "product_id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "barcode": product.barcode,
        "uom": product.uom.value,
        "reorder_point": float(product.reorder_point),
        "stock_positions": [
            {
                "warehouse_id": str(s.warehouse_id),
                "lot_id": str(s.lot_id) if s.lot_id else None,
                "quantity_available": float(s.quantity_available),
                "is_blocked": s.is_blocked,
                "location_id": str(s.location_id) if s.location_id else None,
            }
            for s in stocks.scalars()
        ],
    }


# ── WMS Operations ────────────────────────────────────────────────────────────

@router.post("/putaway", summary="Assign stock to a storage location")
async def putaway(
    req: PutawayRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stock = await svc.putaway(db, req, current_user.id)
    await db.commit()
    return {"message": "Stock assigned to location", "location_id": str(stock.location_id)}


@router.post("/quarantine", summary="Block stock (quarantine)")
async def quarantine(
    req: QuarantineRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await svc.quarantine_stock(db, req, current_user.id)
    await db.commit()
    return {"message": f"{len(rows)} stock row(s) quarantined", "blocked_rows": len(rows)}


@router.post("/release", summary="Release quarantined stock")
async def release(
    req: ReleaseQuarantineRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await svc.release_quarantine(db, req, current_user.id)
    await db.commit()
    return {"message": f"{len(rows)} stock row(s) released", "released_rows": len(rows)}


@router.get("/fefo", response_model=List[FEFOSuggestion],
            summary="FEFO/FIFO lot suggestions for picking")
async def fefo_suggestions(
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: float = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_fefo_suggestions(db, product_id, warehouse_id, Decimal(str(quantity)))


# ── Stock Counts ──────────────────────────────────────────────────────────────

@router.get("/counts/", response_model=List[StockCountRead])
async def list_counts(
    warehouse_id: Optional[uuid.UUID] = None,
    status: Optional[StockCountStatus] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    counts = await crud.list_counts(db, warehouse_id=warehouse_id, status=status, skip=skip, limit=limit)
    return [_count_read(c) for c in counts]


@router.post("/counts/", response_model=StockCountRead, status_code=201)
async def create_count(
    data: StockCountCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = await crud.create_count(db, data, current_user.id)
    await db.commit()
    c = await crud.get_count(db, obj.id)
    return _count_read(c)


@router.get("/counts/{count_id}", response_model=StockCountDetailRead)
async def get_count(
    count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Stock count not found")
    return _count_detail(c)


@router.post("/counts/{count_id}/start", response_model=StockCountRead)
async def start_count(
    count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Count not found")
    c = await svc.start_count(db, c)
    await db.commit()
    c = await crud.get_count(db, count_id)
    return _count_read(c)


@router.post("/counts/{count_id}/lines/{line_id}/record", response_model=StockCountLineRead)
async def record_count_line(
    count_id: uuid.UUID, line_id: uuid.UUID,
    req: RecordCountRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Count not found")
    if c.status != StockCountStatus.IN_PROGRESS:
        raise HTTPException(422, "Count is not IN_PROGRESS")
    line = await crud.get_count_line(db, line_id)
    if not line or line.count_id != count_id:
        raise HTTPException(404, "Line not found")
    line = await svc.record_count_line(db, line, req)
    await db.commit()
    return StockCountLineRead.model_validate(line)


@router.post("/counts/{count_id}/submit", response_model=StockCountRead)
async def submit_count(
    count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Count not found")
    c = await svc.submit_count(db, c)
    await db.commit()
    c = await crud.get_count(db, count_id)
    return _count_read(c)


@router.post("/counts/{count_id}/approve", response_model=StockCountRead)
async def approve_count(
    count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Count not found")
    c = await svc.approve_count(db, c, current_user.id)
    await db.commit()
    c = await crud.get_count(db, count_id)
    return _count_read(c)


@router.post("/counts/{count_id}/cancel", response_model=StockCountRead)
async def cancel_count(
    count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    c = await crud.get_count(db, count_id)
    if not c:
        raise HTTPException(404, "Count not found")
    c = await svc.cancel_count(db, c)
    await db.commit()
    c = await crud.get_count(db, count_id)
    return _count_read(c)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/near-expiry", response_model=List[NearExpiryRow])
async def near_expiry_report(
    days_ahead: int = Query(30, ge=1, le=365),
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_near_expiry_report(db, days_ahead=days_ahead, warehouse_id=warehouse_id)


@router.get("/reports/low-stock", response_model=List[LowStockRow])
async def low_stock_report(
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_low_stock_report(db, warehouse_id=warehouse_id)


@router.get("/reports/aging", response_model=List[StockAgingRow])
async def stock_aging_report(
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_stock_aging_report(db, warehouse_id=warehouse_id)


@router.get("/reports/lot-trace/{lot_number}", response_model=LotTraceResult)
async def lot_trace_report(
    lot_number: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_lot_trace(db, lot_number)


@router.get("/reports/movement-ledger")
async def movement_ledger(
    warehouse_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    movement_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.get_movement_ledger(
        db, warehouse_id=warehouse_id,
        date_from=date_from, date_to=date_to,
        movement_type=movement_type,
        skip=skip, limit=limit,
    )


# Fix missing import
from decimal import Decimal  # noqa: E402
