"""Server-side selling price for one customer (distributor portal and field order capture use the same rule).

Price lists for the customer/distributor in the customer's currency win; otherwise the product's selling price.
No usable price → None (the product cannot be ordered). Clients never send prices.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


async def unit_price(db: AsyncSession, product, customer, distributor_id, quantity: Decimal) -> Optional[Decimal]:
    from app.schemas.price_list import PriceResolveRequest
    from app.services.price_list_service import resolve_price

    res = await resolve_price(db, PriceResolveRequest(product_id=product.id, quantity=quantity, uom=product.uom.value,
                                                      customer_id=customer.id, distributor_id=distributor_id,
                                                      currency=customer.currency))
    price = Decimal(str(res.get("unit_price") or 0))
    if price > 0 and res.get("source_price_list") and (res.get("currency") or customer.currency) == customer.currency:
        return price
    # ponytail: selling_price is assumed to be in the customer's currency; add a product price currency if multi-currency selling starts
    if product.selling_price and product.selling_price > 0:
        return Decimal(str(product.selling_price))
    return None
