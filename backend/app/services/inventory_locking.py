"""Shared transaction-scoped locks for inventory logical keys."""
from __future__ import annotations

from hashlib import sha256
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def lot_identity(
    *,
    lot_number: str,
    product_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
) -> str:
    item_type = "product" if product_id is not None else "material"
    item_id = product_id if product_id is not None else material_id
    return f"inventory-lot:{item_type}:{item_id}:{lot_number}"


def stock_identity(
    *,
    stock_type,
    warehouse_id: UUID,
    product_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    lot_id: Optional[UUID] = None,
) -> str:
    item_type = "product" if product_id is not None else "material"
    item_id = product_id if product_id is not None else material_id
    stock_type_value = getattr(stock_type, "value", stock_type)
    return f"inventory-stock:{stock_type_value}:{warehouse_id}:{item_type}:{item_id}:{lot_id or ''}"


async def lock_inventory_identity(db: AsyncSession, identity: str) -> None:
    """Protect select-then-insert upserts where a row-level lock cannot exist yet."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    lock_id = int.from_bytes(sha256(identity.encode("utf-8")).digest()[:8], "big", signed=True)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))
