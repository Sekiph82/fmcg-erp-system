from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import inventory as crud
from app.services import inventory_service as svc
from app.schemas.inventory import (
    LotCreate, LotUpdate, LotRead,
    StockRead, StockSummaryRead,
    StockMovementCreate, StockMovementRead, MovementDetailRead,
    StockEntryRequest, StockIssueRequest, StockTransferRequest,
)

router = APIRouter()


# ── Lots ───────────────────────────────────────────────────────────────────────

@router.get("/lots", response_model=List[LotRead],
            dependencies=[Depends(require_permission("inventory", "view"))])
async def list_lots(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await crud.list_lots(db, skip=skip, limit=limit)


@router.post("/lots", response_model=LotRead, status_code=201,
             dependencies=[Depends(require_permission("inventory", "create"))])
async def create_lot(data: LotCreate, db: AsyncSession = Depends(get_db)):
    obj = await crud.create_lot(db, data)
    await db.commit()
    return obj


@router.get("/lots/{lot_id}", response_model=LotRead,
            dependencies=[Depends(require_permission("inventory", "view"))])
async def get_lot(lot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_lot(db, lot_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lot not found")
    return obj


@router.patch("/lots/{lot_id}", response_model=LotRead,
              dependencies=[Depends(require_permission("inventory", "edit"))])
async def update_lot(lot_id: uuid.UUID, data: LotUpdate, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_lot(db, lot_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lot not found")
    obj = await crud.update_lot(db, obj, data)
    await db.commit()
    return obj


# ── Stock ──────────────────────────────────────────────────────────────────────

@router.get("/stock", response_model=List[StockRead],
            dependencies=[Depends(require_permission("inventory", "view"))])
async def list_stocks(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_stocks(db, warehouse_id=warehouse_id, product_id=product_id,
                                  material_id=material_id, skip=skip, limit=limit)


# ── Movements ──────────────────────────────────────────────────────────────────

@router.get("/movements", response_model=List[StockMovementRead],
            dependencies=[Depends(require_permission("inventory", "view"))])
async def list_movements(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_movements(db, warehouse_id=warehouse_id, product_id=product_id,
                                     skip=skip, limit=limit)


@router.post("/movements", response_model=StockMovementRead, status_code=201)
async def create_movement(
    data: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "edit")),
):
    obj = await crud.create_movement(db, data, current_user.id)
    await db.commit()
    return obj


# ── Business operation endpoints ───────────────────────────────────────────────

@router.post("/stock/entry", response_model=StockMovementRead, status_code=201,
             summary="Receive stock into warehouse (IN)")
async def stock_entry(
    req: StockEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "create")),
):
    """
    Receive goods into a warehouse. Creates a RECEIPT movement and increases
    on-hand stock. Optionally tracks by lot_number and expiry_date.
    """
    movement = await svc.stock_entry(db, req, current_user.id)
    await db.commit()
    return movement


@router.post("/stock/issue", response_model=StockMovementRead, status_code=201,
             summary="Issue stock from warehouse (OUT)")
async def stock_issue(
    req: StockIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "edit")),
):
    """
    Issue goods out of a warehouse. Validates that sufficient stock is available
    before creating an ISSUE movement. Returns 422 with details if stock is
    insufficient.
    """
    movement = await svc.stock_issue(db, req, current_user.id)
    await db.commit()
    return movement


@router.post("/stock/transfer", response_model=StockMovementRead, status_code=201,
             summary="Transfer stock between warehouses")
async def stock_transfer(
    req: StockTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "edit")),
):
    """
    Move goods from one warehouse to another. Validates source availability.
    Atomically debits source and credits destination within a single transaction.
    """
    movement = await svc.stock_transfer(db, req, current_user.id)
    await db.commit()
    return movement


@router.get("/stock/summary", response_model=List[StockSummaryRead],
            summary="Current stock levels with product and warehouse names",
            dependencies=[Depends(require_permission("inventory", "view"))])
async def stock_summary(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns enriched stock records including product SKU/name, warehouse name,
    lot number, expiry date, and a flag when quantity falls below reorder point.
    """
    return await svc.get_stock_summary(db, warehouse_id=warehouse_id, product_id=product_id,
                                       skip=skip, limit=limit)


@router.get("/movements/detail", response_model=List[MovementDetailRead],
            summary="Movement ledger enriched with names",
            dependencies=[Depends(require_permission("inventory", "view"))])
async def movements_detail(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Full movement history with product, warehouse and user names resolved."""
    return await svc.get_movement_detail(db, warehouse_id=warehouse_id, product_id=product_id,
                                         skip=skip, limit=limit)


# ── Channel stock awareness ────────────────────────────────────────────────────

@router.get("/channel-stock-summary",
            dependencies=[Depends(require_permission("inventory", "view"))])
async def channel_stock_summary(
    product_id: Optional[uuid.UUID] = None,
    store_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-module channel stock summary: joins warehouse stock with marketing
    channel allocations. Useful for visibility between e-commerce and WMS.
    """
    from sqlalchemy import select as sqsel, func as sqfunc, text
    from app.models.marketing import ChannelStock, Store

    q = sqsel(
        ChannelStock.product_id,
        ChannelStock.store_id,
        Store.store_name,
        Store.platform,
        ChannelStock.allocated_stock,
        ChannelStock.reserved_stock,
        ChannelStock.available_stock,
    ).join(Store, Store.id == ChannelStock.store_id)

    if product_id:
        q = q.where(ChannelStock.product_id == product_id)
    if store_id:
        q = q.where(ChannelStock.store_id == store_id)

    rows = (await db.execute(q)).all()
    return [
        {
            "product_id": str(r.product_id),
            "store_id": str(r.store_id),
            "store_name": r.store_name,
            "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
            "allocated_stock": float(r.allocated_stock or 0),
            "reserved_stock": float(r.reserved_stock or 0),
            "available_stock": float(r.available_stock or 0),
        }
        for r in rows
    ]
