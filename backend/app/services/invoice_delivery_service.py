"""When an invoice is cut and where it goes (owner 2026-11-20).

* Shops / distributors (orders from the office, field reps, the portal): the invoice is created when the goods are
  delivered (driver's proof of delivery), not when the order is entered, and e-mailed to the shop's address.
* Online marketplace orders (source ECOMMERCE: Shopify today; n11 / Hepsiburada / Trendyol connectors when their
  credentials arrive): the invoice is created when the payment is received, e-mailed to the buyer's address on the
  marketplace, and a paper copy goes into the parcel (the pick/pack screen shows "print invoice for the parcel").

Nothing here blocks the delivery or the payment: if the invoice cannot be created (e.g. no sales posting rule), the
reason is logged and the office invoices by hand as before.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

log = logging.getLogger(__name__)
PARCEL_NOTE = "PRINT FOR PARCEL: put a paper copy of this invoice in the parcel."


def invoice_email(invoice, customer_name: str, lines, promotions: tuple = ()) -> tuple[str, str]:
    from app.core.config import settings

    rows = "\n".join(
        f"  {(l.description or '')[:40]:<40} {Decimal(l.quantity):>8} x {Decimal(l.unit_price):>10.2f}"
        + (f"  -{Decimal(l.discount_pct) * 100:.1f}%" if l.discount_pct else "")
        + f"  = {Decimal(l.line_total):>10.2f}" for l in lines)
    promo = ("\nPromotions applied:\n"
             + "\n".join(f"  - {p}" for p in promotions) + "\n") if promotions else ""
    subject = f"Invoice {invoice.invoice_no} from {settings.PROJECT_NAME}"
    body = (f"Dear {customer_name},\n\nYour invoice {invoice.invoice_no} dated {invoice.invoice_date}:\n\n{rows}\n{promo}\n"
            f"Subtotal: {invoice.currency} {Decimal(invoice.subtotal):.2f}\nTax: {invoice.currency} {Decimal(invoice.tax_amount):.2f}\n"
            f"Total: {invoice.currency} {Decimal(invoice.total_amount):.2f}\nDue date: {invoice.due_date}\n\nThank you for your order.")
    return subject, body


async def queue_invoice_email(db, invoice, to_email: Optional[str], customer_name: str) -> bool:
    from app.models.sales import InvoiceLine
    from app.services.crm_outbound_service import queue

    if not to_email or "@" not in to_email:
        log.info("invoice %s: no e-mail address on file, not sent", invoice.invoice_no)
        return False
    from app.services.shop_promotions import order_promotion_names

    lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id))).scalars().all()
    subject, body = invoice_email(invoice, customer_name, lines, tuple(await order_promotion_names(db, invoice.so_id)))
    await queue(db, to_email=to_email, subject=subject, body=body, purpose="INVOICE",
                dedupe_key=f"invoice:{invoice.id}", customer_id=invoice.customer_id, created_by="invoicing")
    return True


async def invoice_on_delivery(db, shipment_id: uuid.UUID, user_id) -> Optional[object]:
    """Called by the driver's proof of delivery while the shipment is still DISPATCHED. Savepoint: never fails the POD."""
    from app.models.sales import Customer, Invoice, OrderSource, SalesOrder, Shipment
    from app.services.sales_service import invoice_from_shipment

    shipment = (await db.execute(select(Shipment).options(selectinload(Shipment.invoice))
                                 .where(Shipment.id == shipment_id))).scalar_one_or_none()
    if shipment is None or shipment.invoice is not None:
        return None
    so = await db.get(SalesOrder, shipment.so_id)
    if so is None or so.source == OrderSource.ECOMMERCE:      # marketplace orders are invoiced on payment
        return None
    if (await db.execute(select(Invoice.id).where(Invoice.so_id == so.id, Invoice.shipment_id.is_(None)).limit(1))).first():
        return None                                          # invoiced on the whole order already
    customer = await db.get(Customer, so.customer_id)
    from app.services.shop_promotions import order_promotion_names

    promos = await order_promotion_names(db, so.id)
    today = date.today()
    try:
        async with db.begin_nested():
            invoice = await invoice_from_shipment(
                db, shipment, invoice_no=f"INV-{shipment.shipment_no}"[:50], invoice_date=today,
                due_date=today + timedelta(days=int(customer.payment_terms_days or 0)), user_id=user_id,
                notes="\n".join(["Invoiced automatically on delivery"] + [f"Promotion: {p}" for p in promos]))
    except Exception as exc:  # e.g. sales posting rule missing: the office invoices by hand
        log.warning("shipment %s delivered but not invoiced automatically: %s", shipment.shipment_no, exc)
        return None
    await _mail_quietly(db, invoice, customer.email, customer.name)
    return invoice


async def _mail_quietly(db, invoice, to_email, name) -> bool:
    """Queue the invoice e-mail in a savepoint; a mail problem never undoes the delivery or the invoice."""
    try:
        async with db.begin_nested():
            return await queue_invoice_email(db, invoice, to_email, name)
    except Exception as exc:
        log.warning("invoice %s created but its e-mail could not be queued: %s", invoice.invoice_no, exc)
        return False


async def invoice_paid_marketplace_order(db, so_id: uuid.UUID, buyer_email: Optional[str], buyer_name: str, user_id):
    """Marketplace order paid: invoice the whole order now, mail it to the buyer, flag a paper copy for the parcel."""
    from app.models.sales import Invoice, InvoiceLine, InvoiceStatus, SalesOrder, SOLine, SOStatus
    from app.services.sales_service import _post_invoice_to_gl, record_payment

    so = (await db.execute(select(SalesOrder).options(selectinload(SalesOrder.lines).selectinload(SOLine.product))
                           .where(SalesOrder.id == so_id))).scalar_one()
    if so.status == SOStatus.CANCELLED:  # imported marketplace orders may still be DRAFT: they are paid already
        raise ValueError(f"order {so.order_no} is cancelled")
    existing = (await db.execute(select(Invoice).where(Invoice.so_id == so.id).limit(1))).scalar_one_or_none()
    if existing is not None:
        return existing
    subtotal = tax_total = Decimal("0")
    lines = []
    for l in so.lines:
        net = (Decimal(l.ordered_quantity) * Decimal(l.unit_price) * (1 - Decimal(l.discount_pct or 0))).quantize(Decimal("0.01"))
        tax = (net * Decimal(l.tax_rate or 0)).quantize(Decimal("0.01"))
        subtotal, tax_total = subtotal + net, tax_total + tax
        lines.append(InvoiceLine(product_id=l.product_id, description=l.product.name if l.product else None,
                                 so_line_id=l.id, quantity=l.ordered_quantity, unit=l.unit, unit_price=l.unit_price,
                                 discount_pct=l.discount_pct, tax_rate=l.tax_rate, line_total=net + tax))
    today = date.today()
    try:
        async with db.begin_nested():
            invoice = Invoice(invoice_no=f"INV-{so.order_no}"[:50], so_id=so.id, customer_id=so.customer_id,
                              invoice_date=today, due_date=today, status=InvoiceStatus.ISSUED, currency=so.currency,
                              subtotal=subtotal, tax_amount=tax_total, total_amount=subtotal + tax_total,
                              paid_amount=Decimal("0"), notes=PARCEL_NOTE, created_by_id=user_id)
            db.add(invoice)
            await db.flush()
            for il in lines:
                il.invoice_id = invoice.id
                db.add(il)
            await _post_invoice_to_gl(db, invoice, user_id)
    except Exception as exc:
        log.warning("marketplace order %s paid but not invoiced automatically: %s", so.order_no, exc)
        return None
    # the money is already in (marketplace payout to the bank): close the receivable the invoice just opened
    try:
        async with db.begin_nested():
            await record_payment(db, invoice, Decimal(invoice.total_amount), today, f"marketplace {so.order_no}",
                                 "Paid on the marketplace", user_id, method="bank")
    except Exception as exc:  # e.g. no bank receipt posting rule: finance records the receipt by hand
        log.warning("marketplace invoice %s left open, payment not recorded: %s", invoice.invoice_no, exc)
    await _mail_quietly(db, invoice, buyer_email, buyer_name)
    return invoice
