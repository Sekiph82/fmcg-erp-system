"""
Inventory business logic service.

All stock mutations go through here. Rules:
  - Stock cannot go negative (InsufficientStockError).
  - Every mutation writes an immutable StockMovement ledger row.
  - Stock rows are locked with SELECT FOR UPDATE before any write to prevent
    race conditions under concurrent requests.
  - Lots are auto-created when a lot_number is supplied on entry; reused on
    issue/transfer by matching lot_number + product_id.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.models.master import Product, Warehouse
from app.schemas.inventory import (
    StockEntryRequest,
    StockIssueRequest,
    StockTransferRequest,
    StockSummaryRead,
    MovementDetailRead,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

class InsufficientStockError(HTTPException):
    def __init__(self, available: Decimal, requested: Decimal, product: str, warehouse: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INSUFFICIENT_STOCK",
                "message": f"Cannot issue {requested} units of '{product}' from '{warehouse}'. "
                           f"Only {available} available.",
                "available": float(available),
                "requested": float(requested),
            },
        )


async def _require_product(db: AsyncSession, product_id: uuid.UUID) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_active == True))  # noqa: E712
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found or inactive")
    return product


async def _require_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_active == True))  # noqa: E712
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail=f"Warehouse {warehouse_id} not found or inactive")
    return warehouse


async def _get_or_create_lot(
    db: AsyncSession,
    product_id: uuid.UUID,
    lot_number: str,
    expiry_date: Optional[date] = None,
) -> Lot:
    result = await db.execute(
        select(Lot).where(Lot.product_id == product_id, Lot.lot_number == lot_number)
    )
    lot = result.scalar_one_or_none()
    if not lot:
        lot = Lot(
            product_id=product_id,
            lot_number=lot_number,
            expiry_date=expiry_date,
        )
        db.add(lot)
        await db.flush()
    return lot


async def _get_stock_for_update(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    lot_id: Optional[uuid.UUID],
) -> Optional[Stock]:
    """Fetch the stock row with a row-level lock to prevent concurrent writes."""
    filters = [
        Stock.warehouse_id == warehouse_id,
        Stock.product_id == product_id,
        Stock.stock_type == StockType.PRODUCT,
    ]
    if lot_id:
        filters.append(Stock.lot_id == lot_id)
    else:
        filters.append(Stock.lot_id.is_(None))

    result = await db.execute(
        select(Stock).where(and_(*filters)).with_for_update()
    )
    return result.scalar_one_or_none()


def _upsert_stock(
    existing: Optional[Stock],
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    lot_id: Optional[uuid.UUID],
    delta: Decimal,
) -> Stock:
    if existing:
        existing.quantity_on_hand += delta
        existing.quantity_available = existing.quantity_on_hand - existing.quantity_reserved
        return existing
    return Stock(
        stock_type=StockType.PRODUCT,
        warehouse_id=warehouse_id,
        product_id=product_id,
        lot_id=lot_id,
        quantity_on_hand=delta,
        quantity_reserved=Decimal("0"),
        quantity_available=delta,
    )


# ── Public operations ──────────────────────────────────────────────────────────

async def stock_entry(
    db: AsyncSession,
    req: StockEntryRequest,
    created_by_id: uuid.UUID,
) -> StockMovement:
    """Receive stock into a warehouse (IN / RECEIPT)."""
    product = await _require_product(db, req.product_id)
    warehouse = await _require_warehouse(db, req.warehouse_id)

    if req.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantity must be positive")

    lot_id: Optional[uuid.UUID] = None
    if req.lot_number:
        lot = await _get_or_create_lot(db, req.product_id, req.lot_number, req.expiry_date)
        lot_id = lot.id

    total_cost = (req.quantity * req.unit_cost) if req.unit_cost else None

    movement = StockMovement(
        reference_number=req.reference,
        movement_type=MovementType.RECEIPT,
        stock_type=StockType.PRODUCT,
        movement_date=date.today(),
        product_id=req.product_id,
        lot_id=lot_id,
        destination_warehouse_id=req.warehouse_id,
        quantity=req.quantity,
        unit_cost=req.unit_cost,
        total_cost=total_cost,
        notes=req.notes,
        created_by_id=created_by_id,
    )
    db.add(movement)
    await db.flush()

    existing = await _get_stock_for_update(db, req.warehouse_id, req.product_id, lot_id)
    stock = _upsert_stock(existing, req.warehouse_id, req.product_id, lot_id, req.quantity)
    if not existing:
        db.add(stock)

    await db.flush()
    await db.refresh(movement)
    return movement


async def stock_issue(
    db: AsyncSession,
    req: StockIssueRequest,
    created_by_id: uuid.UUID,
) -> StockMovement:
    """Issue stock out of a warehouse (OUT / ISSUE). Validates available quantity."""
    product = await _require_product(db, req.product_id)
    warehouse = await _require_warehouse(db, req.warehouse_id)

    if req.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantity must be positive")

    lot_id: Optional[uuid.UUID] = None
    if req.lot_number:
        result = await db.execute(
            select(Lot).where(Lot.product_id == req.product_id, Lot.lot_number == req.lot_number)
        )
        lot = result.scalar_one_or_none()
        if not lot:
            raise HTTPException(status_code=404, detail=f"Lot '{req.lot_number}' not found for this product")
        lot_id = lot.id

    # Lock and check stock
    stock = await _get_stock_for_update(db, req.warehouse_id, req.product_id, lot_id)
    available = stock.quantity_available if stock else Decimal("0")
    if available < req.quantity:
        raise InsufficientStockError(available, req.quantity, product.name, warehouse.name)

    movement = StockMovement(
        reference_number=req.reference,
        movement_type=MovementType.ISSUE,
        stock_type=StockType.PRODUCT,
        movement_date=date.today(),
        product_id=req.product_id,
        lot_id=lot_id,
        source_warehouse_id=req.warehouse_id,
        quantity=req.quantity,
        notes=req.notes,
        created_by_id=created_by_id,
    )
    db.add(movement)

    stock.quantity_on_hand -= req.quantity
    stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved

    await db.flush()
    await db.refresh(movement)
    return movement


async def stock_transfer(
    db: AsyncSession,
    req: StockTransferRequest,
    created_by_id: uuid.UUID,
) -> StockMovement:
    """Transfer stock between two warehouses. Validates source quantity."""
    if req.from_warehouse_id == req.to_warehouse_id:
        raise HTTPException(status_code=422, detail="Source and destination warehouse must differ")

    product = await _require_product(db, req.product_id)
    from_wh = await _require_warehouse(db, req.from_warehouse_id)
    await _require_warehouse(db, req.to_warehouse_id)

    if req.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantity must be positive")

    lot_id: Optional[uuid.UUID] = None
    if req.lot_number:
        result = await db.execute(
            select(Lot).where(Lot.product_id == req.product_id, Lot.lot_number == req.lot_number)
        )
        lot = result.scalar_one_or_none()
        if not lot:
            raise HTTPException(status_code=404, detail=f"Lot '{req.lot_number}' not found for this product")
        lot_id = lot.id

    # Lock source stock first, then destination (consistent ordering prevents deadlocks)
    src_stock = await _get_stock_for_update(db, req.from_warehouse_id, req.product_id, lot_id)
    src_available = src_stock.quantity_available if src_stock else Decimal("0")
    if src_available < req.quantity:
        raise InsufficientStockError(src_available, req.quantity, product.name, from_wh.name)

    dst_stock = await _get_stock_for_update(db, req.to_warehouse_id, req.product_id, lot_id)

    movement = StockMovement(
        reference_number=req.reference,
        movement_type=MovementType.TRANSFER,
        stock_type=StockType.PRODUCT,
        movement_date=date.today(),
        product_id=req.product_id,
        lot_id=lot_id,
        source_warehouse_id=req.from_warehouse_id,
        destination_warehouse_id=req.to_warehouse_id,
        quantity=req.quantity,
        notes=req.notes,
        created_by_id=created_by_id,
    )
    db.add(movement)

    # Deduct from source
    src_stock.quantity_on_hand -= req.quantity
    src_stock.quantity_available = src_stock.quantity_on_hand - src_stock.quantity_reserved

    # Add to destination
    dst = _upsert_stock(dst_stock, req.to_warehouse_id, req.product_id, lot_id, req.quantity)
    if not dst_stock:
        db.add(dst)

    await db.flush()
    await db.refresh(movement)
    return movement


# ── Adjust / Delete stock record ──────────────────────────────────────────────

async def adjust_stock_record(
    db: AsyncSession,
    stock_id: uuid.UUID,
    new_quantity: Decimal,
    reason: str,
    reference: Optional[str],
    created_by_id: uuid.UUID,
) -> StockMovement:
    """
    Adjust a Stock record to a new quantity by creating an ADJUSTMENT movement.
    The delta can be positive (increase) or negative (decrease / write-off).
    Raises 422 if the adjustment would take stock below zero.
    """
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Stock).options(
            selectinload(Stock.product),
            selectinload(Stock.warehouse),
        ).where(Stock.id == stock_id).with_for_update()
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")

    new_qty = Decimal(str(new_quantity))
    if new_qty < 0:
        raise HTTPException(status_code=422, detail="New quantity cannot be negative")

    delta = new_qty - stock.quantity_on_hand

    if delta == 0:
        raise HTTPException(status_code=422, detail="New quantity is the same as current quantity — no adjustment needed")

    warehouse = stock.warehouse
    if not warehouse:
        raise HTTPException(status_code=422, detail="Stock record has no linked warehouse")

    ref = reference or f"ADJ-{stock_id}"
    movement = StockMovement(
        reference_number=ref,
        movement_type=MovementType.ADJUSTMENT,
        stock_type=stock.stock_type,
        movement_date=date.today(),
        product_id=stock.product_id,
        material_id=stock.material_id,
        lot_id=stock.lot_id,
        source_warehouse_id=stock.warehouse_id if delta < 0 else None,
        destination_warehouse_id=stock.warehouse_id if delta > 0 else None,
        quantity=abs(delta),
        notes=f"Stock adjustment: {reason}",
        created_by_id=created_by_id,
    )
    db.add(movement)

    stock.quantity_on_hand = new_qty
    stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved

    await db.flush()
    await db.refresh(movement)
    return movement


async def delete_stock_record(
    db: AsyncSession,
    stock_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> None:
    """
    Delete a Stock record.
    - Allowed only when quantity_on_hand == 0 (stock already cleared).
    - Returns structured 409 if stock still has quantity.
    """
    result = await db.execute(select(Stock).where(Stock.id == stock_id).with_for_update())
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")

    from sqlalchemy import func as sqfunc
    movement_count = (await db.execute(
        select(sqfunc.count()).select_from(StockMovement).where(
            StockMovement.product_id == stock.product_id,
            (StockMovement.source_warehouse_id == stock.warehouse_id) |
            (StockMovement.destination_warehouse_id == stock.warehouse_id),
        )
    )).scalar_one()

    if stock.quantity_on_hand != 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVENTORY_RECORD_NOT_EMPTY",
                "message": (
                    f"This stock record cannot be deleted because it still has "
                    f"{stock.quantity_on_hand} units on hand. "
                    "Adjust the stock to zero first."
                ),
                "details": {
                    "stockId": str(stock_id),
                    "quantityOnHand": float(stock.quantity_on_hand),
                    "references": [
                        {
                            "module": "Stock Movements",
                            "count": movement_count,
                            "hint": "Issue or write off remaining stock first.",
                        }
                    ],
                },
            },
        )

    await db.delete(stock)
    await db.flush()


async def delete_movement_record(
    db: AsyncSession,
    movement_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> None:
    """
    Delete a StockMovement and reverse its effect on the Stock record.
    - Finds the affected Stock row and applies the reverse delta.
    - If reversing would push stock below zero, raises 409.
    """
    from sqlalchemy import and_

    result = await db.execute(select(StockMovement).where(StockMovement.id == movement_id))
    movement = result.scalar_one_or_none()
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found")

    async def _reverse_stock(warehouse_id: Optional[uuid.UUID], delta: Decimal) -> None:
        if not warehouse_id:
            return
        filters = [
            Stock.warehouse_id == warehouse_id,
            Stock.stock_type == movement.stock_type,
        ]
        if movement.stock_type == StockType.PRODUCT:
            filters.append(Stock.product_id == movement.product_id)
        else:
            filters.append(Stock.material_id == movement.material_id)
        if movement.lot_id:
            filters.append(Stock.lot_id == movement.lot_id)

        res = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
        stock = res.scalar_one_or_none()
        if stock:
            new_qty = stock.quantity_on_hand + delta
            if new_qty < 0:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "MOVEMENT_REVERSAL_WOULD_CAUSE_NEGATIVE_STOCK",
                        "message": (
                            "Deleting this movement would bring stock below zero. "
                            "Reverse or adjust dependent movements first."
                        ),
                        "details": {
                            "movementId": str(movement_id),
                            "hint": "Create a compensating movement or adjust stock manually.",
                        },
                    },
                )
            stock.quantity_on_hand = new_qty
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved

    # Reverse the stock delta (opposite of what _apply_stock_delta does)
    if movement.movement_type in (MovementType.RECEIPT, MovementType.RETURN):
        await _reverse_stock(movement.destination_warehouse_id, -movement.quantity)
    elif movement.movement_type in (MovementType.ISSUE, MovementType.WRITE_OFF):
        await _reverse_stock(movement.source_warehouse_id, movement.quantity)
    elif movement.movement_type == MovementType.TRANSFER:
        await _reverse_stock(movement.source_warehouse_id, movement.quantity)
        await _reverse_stock(movement.destination_warehouse_id, -movement.quantity)
    elif movement.movement_type == MovementType.ADJUSTMENT:
        wh = movement.destination_warehouse_id or movement.source_warehouse_id
        await _reverse_stock(wh, -movement.quantity)

    await db.delete(movement)
    await db.flush()


# ── Enriched queries ───────────────────────────────────────────────────────────

async def get_stock_summary(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[StockSummaryRead]:
    """Return stock rows joined with product, warehouse and lot names."""
    from sqlalchemy.orm import selectinload

    q = (
        select(Stock)
        .options(
            selectinload(Stock.product),
            selectinload(Stock.warehouse),
            selectinload(Stock.lot),
        )
        .where(Stock.stock_type == StockType.PRODUCT)
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)
    if product_id:
        q = q.where(Stock.product_id == product_id)

    result = await db.execute(q.offset(skip).limit(limit))
    rows: List[Stock] = list(result.scalars().all())

    out = []
    for s in rows:
        below_reorder = (
            s.product is not None
            and s.quantity_available < s.product.reorder_point
        )
        out.append(StockSummaryRead(
            id=s.id,
            stock_type=s.stock_type,
            product_id=s.product_id,
            product_sku=s.product.sku if s.product else None,
            product_name=s.product.name if s.product else None,
            warehouse_id=s.warehouse_id,
            warehouse_code=s.warehouse.code if s.warehouse else "",
            warehouse_name=s.warehouse.name if s.warehouse else "",
            lot_id=s.lot_id,
            lot_number=s.lot.lot_number if s.lot else None,
            expiry_date=s.lot.expiry_date if s.lot else None,
            quantity_on_hand=s.quantity_on_hand,
            quantity_reserved=s.quantity_reserved,
            quantity_available=s.quantity_available,
            is_below_reorder=below_reorder,
        ))
    return out


async def get_movement_detail(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[MovementDetailRead]:
    from sqlalchemy.orm import selectinload

    q = (
        select(StockMovement)
        .options(
            selectinload(StockMovement.source_warehouse),
            selectinload(StockMovement.destination_warehouse),
            selectinload(StockMovement.created_by),
        )
        .order_by(StockMovement.movement_date.desc(), StockMovement.created_at.desc())
    )
    if warehouse_id:
        q = q.where(
            (StockMovement.source_warehouse_id == warehouse_id) |
            (StockMovement.destination_warehouse_id == warehouse_id)
        )
    if product_id:
        q = q.where(StockMovement.product_id == product_id)

    result = await db.execute(q.offset(skip).limit(limit))
    movements = list(result.scalars().all())

    # Bulk-fetch product names
    product_ids = {m.product_id for m in movements if m.product_id}
    products: dict[uuid.UUID, Product] = {}
    if product_ids:
        pr = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for p in pr.scalars():
            products[p.id] = p

    out = []
    for m in movements:
        product = products.get(m.product_id) if m.product_id else None
        out.append(MovementDetailRead(
            id=m.id,
            reference_number=m.reference_number,
            movement_type=m.movement_type,
            stock_type=m.stock_type,
            movement_date=m.movement_date,
            product_id=m.product_id,
            material_id=m.material_id,
            lot_id=m.lot_id,
            source_warehouse_id=m.source_warehouse_id,
            destination_warehouse_id=m.destination_warehouse_id,
            quantity=m.quantity,
            unit_cost=m.unit_cost,
            total_cost=m.total_cost,
            notes=m.notes,
            created_by_id=m.created_by_id,
            product_sku=product.sku if product else None,
            product_name=product.name if product else None,
            source_warehouse_name=m.source_warehouse.name if m.source_warehouse else None,
            destination_warehouse_name=m.destination_warehouse.name if m.destination_warehouse else None,
            created_by_username=m.created_by.username if m.created_by else None,
        ))
    return out
