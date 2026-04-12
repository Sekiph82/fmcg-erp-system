"""
E-commerce Integration Service — scalable placeholder.

Architecture ready for Shopify, WooCommerce, and other marketplace integrations.
To activate a platform:
  1. Add IntegrationConfig with provider=SHOPIFY or WOOCOMMERCE, with settings_json
     containing {"shop_url": "...", "api_key": "...", "api_secret": "..."}
  2. Implement _fetch_orders_from_platform() / _push_inventory_to_platform().
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import (
    EcommerceOrderMapping, EcommerceProductMapping, SyncStatus,
    IntegrationProvider, IntegrationLogStatus,
)
from app.models.inventory import Stock
from app.models.master import Product
from app.services import integration_service as log_svc

logger = logging.getLogger(__name__)


async def import_orders(
    db: AsyncSession,
    platform: str,
    since_date: Optional[str] = None,
    limit: int = 50,
) -> Tuple[int, int, List[str]]:
    """
    Import orders from an external platform.
    PLACEHOLDER: simulates import, creates EcommerceOrderMapping records.
    Returns (imported, mapped, errors).
    """
    # PLACEHOLDER: would call platform API here
    simulated_orders = [
        {"external_order_id": f"ORD-SIM-{i:04d}", "external_order_no": f"#{1000+i}"}
        for i in range(min(limit, 3))  # simulate 3 orders max in placeholder mode
    ]

    imported = 0
    mapped = 0
    errors: List[str] = []

    for order in simulated_orders:
        try:
            existing = await db.execute(
                select(EcommerceOrderMapping).where(
                    EcommerceOrderMapping.source_platform == platform.upper(),
                    EcommerceOrderMapping.external_order_id == order["external_order_id"],
                )
            )
            if existing.scalar_one_or_none():
                continue  # already imported

            mapping = EcommerceOrderMapping(
                source_platform=platform.upper(),
                external_order_id=order["external_order_id"],
                external_order_no=order["external_order_no"],
                sync_status=SyncStatus.PENDING,
                raw_payload=json.dumps(order),
                last_sync_at=datetime.now(timezone.utc),
            )
            db.add(mapping)
            await db.flush()
            imported += 1
        except Exception as exc:
            errors.append(f"{order['external_order_id']}: {exc}")

    await log_svc.log_call(
        db,
        provider=IntegrationProvider.SHOPIFY if "shopify" in platform.lower() else IntegrationProvider.GENERIC,
        integration_type="ORDER_IMPORT",
        endpoint=f"{platform}/orders",
        request_payload={"since_date": since_date, "limit": limit},
        response_payload={"imported": imported, "errors": len(errors)},
        status=IntegrationLogStatus.SUCCESS if not errors else IntegrationLogStatus.FAILED,
        error_message="; ".join(errors[:3]) if errors else None,
    )

    await db.flush()
    return imported, mapped, errors


async def sync_inventory(
    db: AsyncSession,
    platform: str,
) -> Tuple[int, int, List[str]]:
    """
    Push current stock levels to external platform.
    PLACEHOLDER: queries internal stock, simulates push.
    """
    products_result = await db.execute(
        select(Product.id, Product.sku, Product.name).where(Product.is_active == True).limit(100)
    )
    products = list(products_result.all())

    synced = 0
    errors: List[str] = []

    for product in products:
        # PLACEHOLDER: would call platform inventory API
        # e.g. PUT /products/{external_id}/inventory_levels.json
        try:
            # Upsert product mapping
            existing = await db.execute(
                select(EcommerceProductMapping).where(
                    EcommerceProductMapping.source_platform == platform.upper(),
                    EcommerceProductMapping.product_id == product.id,
                )
            )
            mapping = existing.scalar_one_or_none()
            if not mapping:
                mapping = EcommerceProductMapping(
                    source_platform=platform.upper(),
                    external_product_id=f"EXT-{str(product.id)[:8].upper()}",
                    external_sku=product.sku,
                    product_id=product.id,
                    sync_status=SyncStatus.SYNCED,
                    last_sync_at=datetime.now(timezone.utc),
                )
                db.add(mapping)
            else:
                mapping.sync_status = SyncStatus.SYNCED
                mapping.last_sync_at = datetime.now(timezone.utc)
            await db.flush()
            synced += 1
        except Exception as exc:
            errors.append(f"{product.sku}: {exc}")

    await log_svc.log_call(
        db,
        provider=IntegrationProvider.SHOPIFY if "shopify" in platform.lower() else IntegrationProvider.GENERIC,
        integration_type="INVENTORY_SYNC",
        endpoint=f"{platform}/inventory",
        request_payload={"product_count": len(products)},
        response_payload={"synced": synced, "errors": len(errors)},
        status=IntegrationLogStatus.SUCCESS if not errors else IntegrationLogStatus.FAILED,
    )

    await db.flush()
    return len(products), synced, errors


async def list_order_mappings(db: AsyncSession, limit: int = 100) -> List[EcommerceOrderMapping]:
    result = await db.execute(
        select(EcommerceOrderMapping)
        .order_by(EcommerceOrderMapping.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
