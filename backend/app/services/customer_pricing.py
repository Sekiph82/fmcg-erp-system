"""Server-side selling price for one customer (distributor portal and field order capture use the same rule).

Price lists for the customer/distributor in the customer's currency win; otherwise the product's selling price.
No usable price → None (the product cannot be ordered). Clients never send prices.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


async def convert(db: AsyncSession, amount: Decimal, from_currency: str, to_currency: str) -> Optional[Decimal]:
    """Amount in another currency via the KES rates in exchange_rates (rate_to_kes); None when a rate is missing."""
    from app.services.finance_service import get_rate

    async def to_kes_rate(cur: str) -> Optional[Decimal]:
        if cur.upper() == "KES":
            return Decimal("1")
        r = await get_rate(db, cur, None)
        return Decimal(str(r.rate_to_kes)) if r and r.rate_to_kes else None

    src, dst = await to_kes_rate(from_currency), await to_kes_rate(to_currency)
    if not src or not dst:
        return None
    return (amount * src / dst).quantize(Decimal("0.01"))


async def unit_price(db: AsyncSession, product, customer, distributor_id, quantity: Decimal) -> Optional[Decimal]:
    from app.schemas.price_list import PriceResolveRequest
    from app.services.price_list_service import resolve_price

    res = await resolve_price(db, PriceResolveRequest(product_id=product.id, quantity=quantity, uom=product.uom.value,
                                                      customer_id=customer.id, distributor_id=distributor_id,
                                                      currency=customer.currency))
    price = Decimal(str(res.get("effective_price") or res.get("unit_price") or 0))
    if price > 0 and res.get("source_price_list"):
        list_currency = res.get("currency") or customer.currency
        if list_currency == customer.currency:
            return price
        # e.g. a USD list for a KES shop: convert at finance's latest exchange rate; no rate → not orderable
        return await convert(db, price, list_currency, customer.currency)
    # ponytail: selling_price is assumed to be in the customer's currency; add a product price currency if multi-currency selling starts
    if product.selling_price and product.selling_price > 0:
        return Decimal(str(product.selling_price))
    return None
