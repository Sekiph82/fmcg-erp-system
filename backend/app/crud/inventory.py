from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
import uuid

from app.models.inventory import Stock, Lot, StockMovement, StockType
from app.schemas.inventory import LotCreate, LotUpdate, StockMovementCreate


# ── Lot ────────────────────────────────────────────────────────────────────────

async def get_lot(db: AsyncSession, lot_id: uuid.UUID) -> Optional[Lot]:
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    return result.scalar_one_or_none()


async def list_lots(db: AsyncSession, skip=0, limit=50) -> List[Lot]:
    result = await db.execute(select(Lot).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_lot(db: AsyncSession, data: LotCreate) -> Lot:
    obj = Lot(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_lot(db: AsyncSession, obj: Lot, data: LotUpdate) -> Lot:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Stock ──────────────────────────────────────────────────────────────────────

async def list_stocks(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    skip=0,
    limit=50,
) -> List[Stock]:
    q = select(Stock)
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)
    if product_id:
        q = q.where(Stock.product_id == product_id)
    if material_id:
        q = q.where(Stock.material_id == material_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def _apply_stock_delta(
    db: AsyncSession,
    movement: StockMovement,
) -> None:
    """Update or create Stock records based on a movement."""

    async def _upsert(warehouse_id, delta):
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

        result = await db.execute(select(Stock).where(and_(*filters)))
        stock = result.scalar_one_or_none()

        if stock:
            stock.quantity_on_hand += delta
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
        else:
            stock = Stock(
                stock_type=movement.stock_type,
                warehouse_id=warehouse_id,
                product_id=movement.product_id,
                material_id=movement.material_id,
                lot_id=movement.lot_id,
                quantity_on_hand=delta,
                quantity_reserved=0,
                quantity_available=delta,
            )
            db.add(stock)

    from app.models.inventory import MovementType
    if movement.movement_type in (MovementType.RECEIPT, MovementType.RETURN):
        await _upsert(movement.destination_warehouse_id, movement.quantity)
    elif movement.movement_type in (MovementType.ISSUE, MovementType.WRITE_OFF):
        await _upsert(movement.source_warehouse_id, -movement.quantity)
    elif movement.movement_type == MovementType.TRANSFER:
        await _upsert(movement.source_warehouse_id, -movement.quantity)
        await _upsert(movement.destination_warehouse_id, movement.quantity)
    elif movement.movement_type == MovementType.ADJUSTMENT:
        await _upsert(movement.destination_warehouse_id or movement.source_warehouse_id, movement.quantity)


# ── Stock Movement ─────────────────────────────────────────────────────────────

async def list_movements(
    db: AsyncSession,
    warehouse_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    skip=0,
    limit=50,
) -> List[StockMovement]:
    q = select(StockMovement)
    if warehouse_id:
        q = q.where(
            (StockMovement.source_warehouse_id == warehouse_id) |
            (StockMovement.destination_warehouse_id == warehouse_id)
        )
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    result = await db.execute(q.order_by(StockMovement.movement_date.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_movement(
    db: AsyncSession, data: StockMovementCreate, created_by_id: uuid.UUID
) -> StockMovement:
    obj = StockMovement(**data.model_dump(), created_by_id=created_by_id)
    db.add(obj)
    await db.flush()
    await _apply_stock_delta(db, obj)
    await db.refresh(obj)
    return obj
