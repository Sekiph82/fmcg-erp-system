"""
External e-commerce store integration (Shopify, WooCommerce, ...).

No store connector is implemented yet. The earlier placeholder created hard-coded
``ORD-SIM-*`` orders and marked products SYNCED with invented external IDs without
contacting any store; that fabricated integration data and was removed. Import and
inventory sync refuse until a real connector exists.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import EcommerceOrderMapping


async def list_order_mappings(db: AsyncSession, limit: int = 100) -> List[EcommerceOrderMapping]:
    result = await db.execute(
        select(EcommerceOrderMapping)
        .order_by(EcommerceOrderMapping.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
