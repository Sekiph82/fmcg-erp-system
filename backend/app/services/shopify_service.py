"""Shopify connector: import web orders as draft sales orders and push stock levels.

Uses the Shopify Admin REST API with a custom-app access token (settings, never stored in the
database). Shopify buyers become native ERP customers (channel ONLINE, with a CRM profile) linked
by Shopify customer id; guest checkouts go to the configured web-store customer. Orders become
DRAFT sales orders in the configured warehouse once every line's SKU matches an ERP product; otherwise the order is recorded as
FAILED with the reason and no sales order is created. Each Shopify order is imported once
(unique per platform + external id). Inventory sync sets the Shopify location's available
quantity to the ERP warehouse's unblocked available stock for every SKU-matched variant.
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

import httpx
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import sales as sales_crud
from app.models.integrations import CrmCustomerMapping, EcommerceOrderMapping, EcommerceProductMapping, SyncStatus
from app.models.inventory import Lot, Stock, StockType
from app.models.master import Product
from app.models.marketing import AcquisitionSource, CRMProfile
from app.models.sales import Customer, CustomerChannel, OrderSource, PaymentMethod

PLATFORM = "SHOPIFY"
_SHOP_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}\.myshopify\.com$")
_NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
MAX_PAGES = 40
PAGE_SIZE = 250
_PAID = {"paid", "partially_paid", "partially_refunded", "refunded"}


class ShopifyError(RuntimeError):
    pass


def shopify_configured() -> bool:
    return bool(settings.SHOPIFY_SHOP_DOMAIN and settings.SHOPIFY_ACCESS_TOKEN)


class ShopifyClient:
    def __init__(self, shop_domain: str, access_token: str, api_version: str,
                 transport: Optional[httpx.AsyncBaseTransport] = None):
        domain = (shop_domain or "").strip().lower()
        if not _SHOP_DOMAIN.fullmatch(domain):
            raise ShopifyError("SHOPIFY_SHOP_DOMAIN must be the store's <name>.myshopify.com domain.")
        if not re.fullmatch(r"\d{4}-\d{2}", api_version or ""):
            raise ShopifyError("SHOPIFY_API_VERSION must look like 2024-10.")
        self._base = f"https://{domain}/admin/api/{api_version}"
        self._client = httpx.AsyncClient(
            headers={"X-Shopify-Access-Token": access_token, "Accept": "application/json"},
            timeout=httpx.Timeout(20.0), transport=transport, follow_redirects=False,
        )

    @classmethod
    def from_settings(cls, transport: Optional[httpx.AsyncBaseTransport] = None) -> "ShopifyClient":
        if not shopify_configured():
            raise ShopifyError("Shopify is not configured (SHOPIFY_SHOP_DOMAIN and SHOPIFY_ACCESS_TOKEN).")
        return cls(settings.SHOPIFY_SHOP_DOMAIN, settings.SHOPIFY_ACCESS_TOKEN, settings.SHOPIFY_API_VERSION, transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        for attempt in range(3):
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                raise ShopifyError(f"Shopify request failed: {exc.__class__.__name__}") from exc
            if response.status_code == 429 and attempt < 2:  # REST bucket throttling
                try:
                    wait = float(response.headers.get("Retry-After") or 2)
                except ValueError:
                    wait = 2.0
                await asyncio.sleep(min(max(wait, 0.0), 10.0))
                continue
            if response.status_code >= 400:
                detail = response.text[:300]
                raise ShopifyError(f"Shopify {method} {url.split('/admin/')[-1]} returned {response.status_code}: {detail}")
            return response
        raise ShopifyError("Shopify kept throttling the request.")

    async def _paged(self, path: str, key: str, params: dict[str, Any]) -> list[dict]:
        url: Optional[str] = f"{self._base}/{path}"
        query: Optional[dict[str, Any]] = {**params, "limit": PAGE_SIZE}
        items: list[dict] = []
        for _ in range(MAX_PAGES):
            response = await self._request("GET", url, params=query)
            try:
                items.extend(response.json().get(key, []))
            except (ValueError, AttributeError) as exc:
                raise ShopifyError(f"Shopify returned a non-JSON {key} page.") from exc
            match = _NEXT_LINK.search(response.headers.get("Link", ""))
            if not match:
                return items
            url, query = match.group(1), None  # page_info URL already carries the cursor
            if not url.startswith(self._base):
                raise ShopifyError("Unexpected pagination host from Shopify.")
        raise ShopifyError(f"More than {MAX_PAGES * PAGE_SIZE} {key}; narrow the date range.")

    async def orders(self, created_at_min: Optional[datetime]) -> list[dict]:
        params: dict[str, Any] = {"status": "any"}
        if created_at_min is not None:
            params["created_at_min"] = created_at_min.astimezone(timezone.utc).isoformat()
        return await self._paged("orders.json", "orders", params)

    async def variants(self) -> list[dict]:
        products = await self._paged("products.json", "products", {"fields": "id,variants"})
        return [v for p in products for v in p.get("variants", [])]

    async def set_available(self, location_id: str, inventory_item_id: int, available: int) -> None:
        await self._request("POST", f"{self._base}/inventory_levels/set.json", json={
            "location_id": int(location_id), "inventory_item_id": int(inventory_item_id), "available": int(available)})


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _money(value: Any) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _line_quantity(li: dict) -> Decimal:
    # current_quantity excludes refunded/removed units; older API versions only send quantity
    return Decimal(str(li.get("current_quantity", li.get("quantity")) or 0))


def _order_lines(order: dict, products: dict, skus: list[str], lines: list[dict]) -> list[dict]:
    taxes_included = bool(order.get("taxes_included"))
    so_lines = []
    for sku, li in zip(skus, lines):
        qty = _line_quantity(li)
        if qty <= 0:
            continue  # fully refunded or removed line
        rate = sum((Decimal(str(t.get("rate") or 0)) for t in li.get("tax_lines") or []), Decimal("0"))
        # total_discount covers the whole ordered line; keep 4 dp so qty x price stays within a cent
        ordered = Decimal(str(li.get("quantity") or qty))
        unit = Decimal(str(li.get("price") or "0")) - Decimal(str(li.get("total_discount") or "0")) / ordered
        if taxes_included and rate:
            unit = unit / (1 + rate)  # shop prices include tax: store net, the SO adds tax_rate
        product = products[sku]
        so_lines.append({"line_no": len(so_lines) + 1, "product_id": product.id, "ordered_quantity": qty,
                         "unit": getattr(product.uom, "value", str(product.uom)),
                         "unit_price": max(unit, Decimal("0")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                         "tax_rate": (rate * 100).quantize(Decimal("0.01")), "discount_pct": Decimal("0"),
                         "notes": f"Shopify line {li.get('id')}"})
    return so_lines


def _text(value: Any, size: int) -> Optional[str]:
    value = str(value or "").strip()
    return value[:size] or None


async def _resolve_customer(db: AsyncSession, order: dict, fallback: Customer, order_date: date) -> Customer:
    """The ERP customer for a Shopify buyer: linked by Shopify customer id, created on first order.

    Guest checkouts (no Shopify customer) stay on the configured web-store customer. Buyers are never
    matched by e-mail: Shopify checkout e-mails are unverified, so matching could attach a stranger's
    order to an existing trade account. To use an existing ERP account, point its SHOPIFY mapping at it.
    """
    buyer = order.get("customer") or {}
    buyer_id = _text(buyer.get("id"), 200)
    if buyer_id is None:
        return fallback
    mapping = (await db.execute(select(CrmCustomerMapping).where(
        CrmCustomerMapping.crm_provider == PLATFORM,
        CrmCustomerMapping.external_crm_id == buyer_id))).scalar_one_or_none()
    if mapping is not None:
        customer = await db.get(Customer, mapping.customer_id)
        if customer is None or not customer.is_active:
            raise ShopifyError(f"ERP customer linked to Shopify customer {buyer_id} is inactive.")
        mapping.last_sync_at = datetime.now(timezone.utc)
        profile = (await db.execute(select(CRMProfile).where(CRMProfile.customer_id == customer.id))).scalar_one_or_none()
        if profile is not None:
            profile.last_touch_source = "shopify"
            profile.last_contact_date = max(profile.last_contact_date or order_date, order_date)
        return customer
    address = buyer.get("default_address") or order.get("billing_address") or {}
    name = " ".join(filter(None, [_text(buyer.get("first_name"), 100), _text(buyer.get("last_name"), 100)]))
    name = name or _text(buyer.get("email"), 255) or f"Shopify customer {buyer_id}"
    customer = Customer(
        code=f"SHOP-C-{buyer_id}"[:50], name=name[:255], contact_person=name[:255],
        email=_text(buyer.get("email"), 255), phone=_text(buyer.get("phone") or address.get("phone"), 50),
        address=_text(", ".join(filter(None, [address.get("address1"), address.get("address2")])), 2000),
        city=_text(address.get("city"), 100), country=_text(address.get("country"), 100),
        channel=CustomerChannel.ONLINE, currency=(order.get("currency") or fallback.currency or "KES")[:10],
        payment_terms_days=0, is_prepaid=True,  # consumer web buyers pay up front, no credit line
        # same commercial scope as the web-store account, so scoped access rules apply unchanged
        company_id=fallback.company_id, branch_id=fallback.branch_id, sales_region_id=fallback.sales_region_id,
        sales_team_id=fallback.sales_team_id, customer_group_id=fallback.customer_group_id,
        notes=f"Created from Shopify customer {buyer_id}",
    )
    db.add(customer)
    await db.flush()
    db.add_all([
        CrmCustomerMapping(customer_id=customer.id, crm_provider=PLATFORM, external_crm_id=buyer_id,
                           sync_status=SyncStatus.SYNCED, sync_direction="PULL",
                           last_sync_at=datetime.now(timezone.utc)),
        CRMProfile(customer_id=customer.id, acquisition_source=AcquisitionSource.DIRECT,
                   acquisition_channel="SHOPIFY", first_touch_source="shopify", last_touch_source="shopify",
                   last_contact_date=order_date, preferred_contact_method="email" if customer.email else None),
    ])
    await db.flush()
    return customer


async def _import_one(db: AsyncSession, order: dict, mapping: EcommerceOrderMapping, name: str, customer: Customer,
                      warehouse_id: str, actor_id: uuid.UUID) -> Optional[str]:
    """Create the draft sales order and fill the mapping; return an error message when the order can't map."""
    mapping.external_order_no = name[:200]
    mapping.raw_payload = json.dumps(order)[:20000]
    mapping.last_sync_at = datetime.now(timezone.utc)
    lines = order.get("line_items") or []
    skus = [(li.get("sku") or "").strip() for li in lines]
    products = {p.sku: p for p in (await db.execute(
        select(Product).where(Product.sku.in_([s for s in skus if s])))).scalars()}
    missing = sorted({s or f"<no SKU: {li.get('title')}>" for s, li in zip(skus, lines)
                      if _line_quantity(li) > 0 and (not s or s not in products)})
    so_lines = [] if missing else _order_lines(order, products, skus, lines)
    if missing or not so_lines:
        error = f"Unknown SKU(s): {', '.join(missing)[:900]}" if missing else "Order has no open line items."
        mapping.sync_status = SyncStatus.FAILED
        mapping.error_message = error
        db.add(mapping)
        await db.flush()
        return error
    created = datetime.fromisoformat(str(order["created_at"]).replace("Z", "+00:00")).date()
    customer = await _resolve_customer(db, order, customer, created)
    paid = (order.get("financial_status") or "").lower() in _PAID
    so = await sales_crud.create_so(db, {
        "order_no": f"SHOP-{name.lstrip('#')}"[:50], "customer_id": customer.id, "order_date": created,
        "requested_delivery_date": created, "warehouse_id": uuid.UUID(warehouse_id),
        "currency": (order.get("currency") or customer.currency or "KES")[:3],
        "source": OrderSource.ECOMMERCE,
        # paid online (card/wallet payouts settle to the bank); otherwise collected later on account
        "payment_method": PaymentMethod.BANK_TRANSFER if paid else PaymentMethod.CREDIT,
        "company_id": customer.company_id, "branch_id": customer.branch_id,
        "notes": f"Imported from Shopify order {name} ({order.get('financial_status') or 'unknown'} payment); "
                 "shipping and order-level charges are not included",
        "lines": so_lines,
    }, created_by_id=actor_id)
    mapping.so_id = so.id
    mapping.sync_status = SyncStatus.SYNCED
    mapping.error_message = None
    db.add(mapping)
    await db.flush()
    return None


def _created(order: dict) -> datetime:
    try:
        value = datetime.fromisoformat(str(order.get("created_at")).replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


async def _record_failure(db: AsyncSession, external_id: str, name: str, error: str) -> None:
    async with db.begin_nested():
        mapping = (await db.execute(select(EcommerceOrderMapping).where(
            EcommerceOrderMapping.source_platform == PLATFORM,
            EcommerceOrderMapping.external_order_id == external_id))).scalar_one_or_none()
        if mapping is None:
            mapping = EcommerceOrderMapping(source_platform=PLATFORM, external_order_id=external_id)
            db.add(mapping)
        elif mapping.sync_status == SyncStatus.SYNCED:
            return  # a concurrent run imported it; never downgrade a synced order
        mapping.external_order_no = name[:200]
        mapping.sync_status = SyncStatus.FAILED
        mapping.error_message = error
        mapping.so_id = None
        mapping.last_sync_at = datetime.now(timezone.utc)


async def import_orders(db: AsyncSession, client: ShopifyClient, since: Optional[datetime], actor_id: uuid.UUID,
                        limit: int = 250) -> ImportResult:
    customer_id = settings.SHOPIFY_CUSTOMER_ID
    warehouse_id = settings.SHOPIFY_WAREHOUSE_ID
    if not customer_id or not warehouse_id:
        raise ShopifyError("Set SHOPIFY_CUSTOMER_ID (web-store customer) and SHOPIFY_WAREHOUSE_ID before importing.")
    try:
        customer_uuid, _ = uuid.UUID(customer_id), uuid.UUID(warehouse_id)
    except ValueError as exc:
        raise ShopifyError("SHOPIFY_CUSTOMER_ID and SHOPIFY_WAREHOUSE_ID must be UUIDs.") from exc
    customer = await db.get(Customer, customer_uuid)
    if customer is None:
        raise ShopifyError("SHOPIFY_CUSTOMER_ID does not match an ERP customer.")
    result = ImportResult()
    orders = sorted(await client.orders(since), key=lambda o: (_created(o), str(o.get("id"))))
    existing = {m.external_order_id: m for m in (await db.execute(select(EcommerceOrderMapping).where(
        EcommerceOrderMapping.source_platform == PLATFORM,
        EcommerceOrderMapping.external_order_id.in_([str(o.get("id")) for o in orders])))).scalars()}
    # oldest first so a backlog drains over runs; new orders and FAILED retries have separate budgets
    # so orders that keep failing can't starve newer ones
    new_budget = retry_budget = max(1, min(limit, 1000))
    for order in orders:
        external_id = str(order.get("id"))
        name = str(order.get("name") or order.get("order_number") or external_id)
        mapping = existing.get(external_id)
        if (mapping is not None and mapping.sync_status == SyncStatus.SYNCED) or order.get("cancelled_at"):
            result.skipped += 1
            continue
        if mapping is None:
            if new_budget == 0:
                continue
            new_budget -= 1
        else:
            if retry_budget == 0:
                continue
            retry_budget -= 1
        # FAILED mappings are retried in place, e.g. once the missing SKU exists in the ERP
        target = mapping or EcommerceOrderMapping(source_platform=PLATFORM, external_order_id=external_id)
        try:
            async with db.begin_nested():  # sales order + mapping commit or roll back together
                outcome = await _import_one(db, order, target, name, customer, warehouse_id, actor_id)
        except IntegrityError:
            outcome = f"Already imported, or order number SHOP-{name.lstrip('#')} is in use"
            await _record_failure(db, external_id, name, outcome)
        except Exception as exc:  # one malformed order must not discard the rest of the batch
            outcome = f"Could not import: {exc.__class__.__name__}: {exc}"[:500]
            await _record_failure(db, external_id, name, outcome)
        if outcome is None:
            result.imported += 1
        else:
            result.failed += 1
            result.errors.append(f"{name}: {outcome}")
    return result


@dataclass
class InventoryResult:
    synced: int = 0
    unmatched: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def sync_inventory(db: AsyncSession, client: ShopifyClient) -> InventoryResult:
    location_id = settings.SHOPIFY_LOCATION_ID
    warehouse_id = settings.SHOPIFY_WAREHOUSE_ID
    if not location_id or not warehouse_id:
        raise ShopifyError("Set SHOPIFY_LOCATION_ID and SHOPIFY_WAREHOUSE_ID before syncing inventory.")
    if not location_id.isdigit():
        raise ShopifyError("SHOPIFY_LOCATION_ID must be the numeric Shopify location id.")
    try:
        warehouse = uuid.UUID(warehouse_id)
    except ValueError as exc:
        raise ShopifyError("SHOPIFY_WAREHOUSE_ID must be a UUID.") from exc
    result = InventoryResult()
    variants = [v for v in await client.variants() if (v.get("sku") or "").strip()]
    by_sku = {p.sku: p for p in (await db.execute(select(Product).where(
        Product.sku.in_([v["sku"].strip() for v in variants])))).scalars()}
    sellable = case((Stock.quantity_available > 0, Stock.quantity_available), else_=0)
    available = dict((await db.execute(
        select(Stock.product_id, func.coalesce(func.sum(sellable), 0))
        .outerjoin(Lot, Lot.id == Stock.lot_id)
        .where(Stock.warehouse_id == warehouse, Stock.stock_type == StockType.PRODUCT,
               Stock.is_blocked.is_(False),
               # quarantined or expired lots are not offered for sale
               or_(Lot.id.is_(None), Lot.is_quarantine.is_(False)),
               or_(Lot.expiry_date.is_(None), Lot.expiry_date >= date.today()))
        .group_by(Stock.product_id))).all())
    existing = {m.external_product_id: m for m in (await db.execute(select(EcommerceProductMapping).where(
        EcommerceProductMapping.source_platform == PLATFORM))).scalars()}
    for variant in variants:
        sku = variant["sku"].strip()
        product = by_sku.get(sku)
        if product is None:
            result.unmatched += 1
            continue
        qty = int(Decimal(str(available.get(product.id, 0))))  # whole units for sale (rows clamped at 0)
        mapping = existing.get(str(variant["id"])) or EcommerceProductMapping(
            source_platform=PLATFORM, external_product_id=str(variant["id"]))
        mapping.external_sku, mapping.product_id = sku, product.id
        mapping.last_sync_at = datetime.now(timezone.utc)
        try:
            await client.set_available(location_id, variant["inventory_item_id"], qty)
            mapping.sync_status = SyncStatus.SYNCED
            result.synced += 1
        except ShopifyError as exc:
            mapping.sync_status = SyncStatus.FAILED
            result.failed += 1
            result.errors.append(f"{sku}: {exc}"[:300])
        db.add(mapping)
    await db.flush()
    return result
