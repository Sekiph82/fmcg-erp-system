"""
Global search endpoint — powers the Command Palette (Ctrl+K).
Returns records across products, materials, suppliers, customers,
sales orders, purchase orders, and invoices.
Navigation results are built client-side from NAV_CONFIG.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db

router = APIRouter()
log = logging.getLogger(__name__)


def _hit(type_: str, id_: Any, label: str, subtitle: str, href: str) -> dict:
    return {"type": type_, "id": str(id_), "label": label, "subtitle": subtitle, "href": href}


@router.get("/")
async def global_search(
    q: str = Query("", min_length=0, max_length=100),
    limit: int = Query(6, le=15),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Global search across ERP records.
    Returns up to `limit` results per category.
    Navigation items are filtered client-side.
    """
    q = q.strip()
    if not q:
        return {"records": []}

    pattern = f"%{q}%"
    results: list[dict] = []

    # ── Products ──────────────────────────────────────────────────────────────
    try:
        from app.models.master import Product
        rows = (await db.execute(
            select(Product.id, Product.name, Product.sku, Product.category)
            .where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
            .where(Product.is_active == True)  # noqa: E712
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("product", r.id, r.name,
                                f"Product · {r.sku or ''}", f"/dashboard/products"))
    except Exception as e:
        log.debug("Product search error: %s", e)

    # ── Materials ─────────────────────────────────────────────────────────────
    try:
        from app.models.master import Material
        rows = (await db.execute(
            select(Material.id, Material.name)
            .where(Material.name.ilike(pattern))
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("material", r.id, r.name,
                                "Material", "/dashboard/materials"))
    except Exception as e:
        log.debug("Material search error: %s", e)

    # ── Suppliers ─────────────────────────────────────────────────────────────
    try:
        from app.models.master import Supplier
        rows = (await db.execute(
            select(Supplier.id, Supplier.name)
            .where(Supplier.name.ilike(pattern))
            .where(Supplier.is_active == True)  # noqa: E712
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("supplier", r.id, r.name,
                                "Supplier", "/dashboard/suppliers"))
    except Exception as e:
        log.debug("Supplier search error: %s", e)

    # ── Customers ─────────────────────────────────────────────────────────────
    try:
        from app.models.sales import Customer
        rows = (await db.execute(
            select(Customer.id, Customer.name)
            .where(Customer.name.ilike(pattern))
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("customer", r.id, r.name,
                                "Customer", "/dashboard/sales/customers"))
    except Exception as e:
        log.debug("Customer search error: %s", e)

    # ── Sales Orders ──────────────────────────────────────────────────────────
    try:
        from app.models.sales import SalesOrder
        rows = (await db.execute(
            select(SalesOrder.id, SalesOrder.order_no)
            .where(SalesOrder.order_no.ilike(pattern))
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("sales_order", r.id, r.order_no,
                                "Sales Order", "/dashboard/sales/orders"))
    except Exception as e:
        log.debug("Sales order search error: %s", e)

    # ── Invoices ──────────────────────────────────────────────────────────────
    try:
        from app.models.sales import Invoice
        rows = (await db.execute(
            select(Invoice.id, Invoice.invoice_no)
            .where(Invoice.invoice_no.ilike(pattern))
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("invoice", r.id, r.invoice_no,
                                "Invoice", "/dashboard/sales/invoices"))
    except Exception as e:
        log.debug("Invoice search error: %s", e)

    # ── Purchase Orders ───────────────────────────────────────────────────────
    try:
        from app.models.procurement import PurchaseOrder
        rows = (await db.execute(
            select(PurchaseOrder.id, PurchaseOrder.po_no)
            .where(PurchaseOrder.po_no.ilike(pattern))
            .limit(limit)
        )).all()
        for r in rows:
            results.append(_hit("purchase_order", r.id, r.po_no,
                                "Purchase Order", "/dashboard/procurement/orders"))
    except Exception as e:
        log.debug("PO search error: %s", e)

    return {"records": results}
