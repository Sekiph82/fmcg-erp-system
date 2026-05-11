import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.core.access_control import (
    can_modify_scope,
    can_view_scope,
    forbidden_detail,
    has_any_permission,
    require_any_permission,
)
from app.crud import inventory as crud
from app.services import inventory_service as svc
from app.models.inventory import MovementType, Stock, StockMovement
from app.schemas.inventory import (
    LotCreate, LotUpdate, LotRead,
    StockRead, StockSummaryRead,
    StockMovementCreate, StockMovementRead, MovementDetailRead,
    StockMovementUpdate,
    StockEntryRequest, StockIssueRequest, StockTransferRequest,
    StockAdjustRequest,
    ValuationSummary, AgingRow,
)

logger = logging.getLogger(__name__)

router = APIRouter()

INVENTORY_VIEW_PERMISSIONS = ("inventory.view", "inventory.view_all", "inventory.view_own_scope")


def _inventory_forbidden(message: str = "You can view this record but cannot modify it in this scope.") -> HTTPException:
    return HTTPException(status_code=403, detail=forbidden_detail(message))


def _has_broad_inventory_view(user) -> bool:
    return has_any_permission(user, ("inventory.view", "inventory.view_all"))


def _can_view_warehouse(user, warehouse_id: uuid.UUID) -> bool:
    return _has_broad_inventory_view(user) or can_view_scope(user, "inventory", "warehouse", warehouse_id)


def _require_warehouse_action(user, action: str, warehouse_id: uuid.UUID) -> None:
    if not can_modify_scope(user, "inventory", action, "warehouse", warehouse_id):
        raise _inventory_forbidden()


def _require_transfer_scope(user, from_warehouse_id: uuid.UUID, to_warehouse_id: uuid.UUID) -> None:
    transfer_allowed = (
        can_modify_scope(user, "inventory", "transfer", "warehouse", from_warehouse_id)
        and can_modify_scope(user, "inventory", "transfer", "warehouse", to_warehouse_id)
    )
    dispatch_receive_allowed = (
        can_modify_scope(user, "inventory", "dispatch", "warehouse", from_warehouse_id)
        and can_modify_scope(user, "inventory", "receive", "warehouse", to_warehouse_id)
    )
    if not (transfer_allowed or dispatch_receive_allowed):
        raise _inventory_forbidden("You can view these warehouses but cannot transfer stock between these scopes.")


async def _get_stock_or_404(db: AsyncSession, stock_id: uuid.UUID) -> Stock:
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")
    return stock


def _require_movement_scope(user, movement: StockMovement, action: str = "edit") -> None:
    if movement.movement_type in (MovementType.RECEIPT, MovementType.RETURN):
        if movement.destination_warehouse_id:
            _require_warehouse_action(user, "receive", movement.destination_warehouse_id)
        return
    if movement.movement_type in (MovementType.ISSUE, MovementType.WRITE_OFF):
        if movement.source_warehouse_id:
            _require_warehouse_action(user, "dispatch", movement.source_warehouse_id)
        return
    if movement.movement_type == MovementType.TRANSFER:
        if movement.source_warehouse_id and movement.destination_warehouse_id:
            _require_transfer_scope(user, movement.source_warehouse_id, movement.destination_warehouse_id)
        return
    if movement.movement_type == MovementType.ADJUSTMENT:
        warehouse_id = movement.destination_warehouse_id or movement.source_warehouse_id
        if warehouse_id:
            _require_warehouse_action(user, "adjust", warehouse_id)
        return
    raise _inventory_forbidden()


# ── Lots ───────────────────────────────────────────────────────────────────────

@router.get("/lots", response_model=List[LotRead],
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
async def list_lots(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await crud.list_lots(db, skip=skip, limit=limit)


@router.post("/lots", response_model=LotRead, status_code=201,
             dependencies=[Depends(require_permission("inventory", "create"))])
async def create_lot(data: LotCreate, db: AsyncSession = Depends(get_db)):
    obj = await crud.create_lot(db, data)
    await db.commit()
    return obj


@router.get("/lots/{lot_id}", response_model=LotRead,
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
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


@router.delete("/lots/{lot_id}", status_code=204,
               dependencies=[Depends(require_permission("inventory", "edit"))])
async def delete_lot(lot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select as sqsel
    from app.models.inventory import Stock
    obj = await crud.get_lot(db, lot_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lot not found")
    # Remove any stock records linked to this lot
    stocks = (await db.execute(sqsel(Stock).where(Stock.lot_id == lot_id))).scalars().all()
    for s in stocks:
        await db.delete(s)
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


# ── Stock ──────────────────────────────────────────────────────────────────────

@router.get("/stock", response_model=List[StockRead])
async def list_stocks(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS)),
):
    if warehouse_id and not _can_view_warehouse(current_user, warehouse_id):
        raise _inventory_forbidden("You do not have view access to this warehouse scope.")
    stocks = await crud.list_stocks(db, warehouse_id=warehouse_id, product_id=product_id,
                                    material_id=material_id, skip=skip, limit=limit)
    if _has_broad_inventory_view(current_user):
        return stocks
    return [stock for stock in stocks if _can_view_warehouse(current_user, stock.warehouse_id)]


@router.post("/stock/{stock_id}/adjust", response_model=StockMovementRead, status_code=201,
             summary="Adjust stock to a new quantity via ADJUSTMENT movement")
async def adjust_stock(
    stock_id: uuid.UUID,
    req: StockAdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Adjust a stock record to a new on-hand quantity.
    Creates an ADJUSTMENT movement recording the delta and reason.
    The adjustment can increase or decrease stock but never below zero.
    """
    stock = await _get_stock_or_404(db, stock_id)
    _require_warehouse_action(current_user, "adjust", stock.warehouse_id)
    movement = await svc.adjust_stock_record(
        db, stock_id, req.new_quantity, req.reason, req.reference, current_user.id
    )
    await db.commit()
    logger.info("Stock %s adjusted to %s by user %s", stock_id, req.new_quantity, current_user.id)
    return movement


@router.delete("/stock/{stock_id}", status_code=204,
               summary="Delete a stock record (only if quantity is zero)")
async def delete_stock(
    stock_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a stock record. Blocked if quantity_on_hand != 0.
    Use the adjust endpoint to zero out stock first.
    """
    stock = await _get_stock_or_404(db, stock_id)
    _require_warehouse_action(current_user, "delete", stock.warehouse_id)
    await svc.delete_stock_record(db, stock_id, current_user.id)
    await db.commit()
    logger.info("Stock record %s deleted by user %s", stock_id, current_user.id)
    return Response(status_code=204)


# ── Movements ──────────────────────────────────────────────────────────────────

@router.get("/movements", response_model=List[StockMovementRead])
async def list_movements(
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS)),
):
    if warehouse_id and not _can_view_warehouse(current_user, warehouse_id):
        raise _inventory_forbidden("You do not have view access to this warehouse scope.")
    movements = await crud.list_movements(db, warehouse_id=warehouse_id, product_id=product_id,
                                          skip=skip, limit=limit)
    if _has_broad_inventory_view(current_user):
        return movements
    return [
        movement for movement in movements
        if (
            movement.source_warehouse_id and _can_view_warehouse(current_user, movement.source_warehouse_id)
        ) or (
            movement.destination_warehouse_id and _can_view_warehouse(current_user, movement.destination_warehouse_id)
        )
    ]


@router.post("/movements", response_model=StockMovementRead, status_code=201)
async def create_movement(
    data: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    preview = StockMovement(**data.model_dump(), created_by_id=current_user.id)
    _require_movement_scope(current_user, preview)
    obj = await crud.create_movement(db, data, current_user.id)
    await db.commit()
    return obj


@router.patch("/movements/{movement_id}", response_model=StockMovementRead,
              summary="Edit movement notes or reference number")
async def update_movement(
    movement_id: uuid.UUID,
    data: StockMovementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update non-financial fields of a stock movement (notes and reference number only).
    Quantity, type, and warehouse cannot be changed — use delete + recreate for that.
    """
    from sqlalchemy import select as sqsel
    from app.models.inventory import StockMovement
    result = await db.execute(sqsel(StockMovement).where(StockMovement.id == movement_id))
    movement = result.scalar_one_or_none()
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found")
    _require_movement_scope(current_user, movement)

    if data.reference_number is not None:
        movement.reference_number = data.reference_number
    if data.notes is not None:
        movement.notes = data.notes

    await db.flush()
    await db.refresh(movement)
    await db.commit()
    logger.info("Movement %s updated by user %s", movement_id, current_user.id)
    return movement


@router.delete("/movements/{movement_id}", status_code=204,
               summary="Delete a movement and reverse its stock impact")
async def delete_movement(
    movement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a stock movement and reverse its effect on the Stock record.
    Blocked if reversal would cause negative stock.
    """
    result = await db.execute(select(StockMovement).where(StockMovement.id == movement_id))
    movement = result.scalar_one_or_none()
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found")
    _require_movement_scope(current_user, movement)
    await svc.delete_movement_record(db, movement_id, current_user.id)
    await db.commit()
    logger.info("Movement %s deleted by user %s", movement_id, current_user.id)
    return Response(status_code=204)


# ── Business operation endpoints ───────────────────────────────────────────────

@router.post("/stock/entry", response_model=StockMovementRead, status_code=201,
             summary="Receive stock into warehouse (IN)")
async def stock_entry(
    req: StockEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Receive goods into a warehouse. Creates a RECEIPT movement and increases
    on-hand stock. Optionally tracks by lot_number and expiry_date.
    """
    _require_warehouse_action(current_user, "receive", req.warehouse_id)
    movement = await svc.stock_entry(db, req, current_user.id)
    await db.commit()
    return movement


@router.post("/stock/issue", response_model=StockMovementRead, status_code=201,
             summary="Issue stock from warehouse (OUT)")
async def stock_issue(
    req: StockIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Issue goods out of a warehouse. Validates that sufficient stock is available
    before creating an ISSUE movement. Returns 422 with details if stock is
    insufficient.
    """
    _require_warehouse_action(current_user, "dispatch", req.warehouse_id)
    movement = await svc.stock_issue(db, req, current_user.id)
    await db.commit()
    return movement


@router.post("/stock/transfer", response_model=StockMovementRead, status_code=201,
             summary="Transfer stock between warehouses")
async def stock_transfer(
    req: StockTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Move goods from one warehouse to another. Validates source availability.
    Atomically debits source and credits destination within a single transaction.
    """
    _require_transfer_scope(current_user, req.from_warehouse_id, req.to_warehouse_id)
    movement = await svc.stock_transfer(db, req, current_user.id)
    await db.commit()
    return movement


@router.get("/stock/summary", response_model=List[StockSummaryRead],
            summary="Current stock levels with product and warehouse names",
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
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
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
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
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
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


# ── Inventory Valuation ────────────────────────────────────────────────────────

@router.get("/valuation", response_model=ValuationSummary,
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
async def inventory_valuation(
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """FIFO / WAC / Standard cost valuation for all active stocks."""
    return await svc.inventory_valuation_report(db, warehouse_id=warehouse_id)


@router.get("/aging", response_model=List[AgingRow],
            dependencies=[Depends(require_any_permission(INVENTORY_VIEW_PERMISSIONS))])
async def inventory_aging(
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Inventory aging: days held per cost layer, grouped into buckets."""
    return await svc.inventory_aging_report(db, warehouse_id=warehouse_id)
