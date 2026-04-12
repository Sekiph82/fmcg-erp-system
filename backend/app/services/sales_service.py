"""
Sales & Distribution business logic service.

Workflow:
  DRAFT → CONFIRMED → ALLOCATED → PICKING → SHIPPED → INVOICED

  confirm_so:          DRAFT → CONFIRMED
  allocate_so:         CONFIRMED → ALLOCATED  (reserves stock)
  create_shipment:     creates Shipment from SO (caller must have CONFIRMED/ALLOCATED)
  start_picking:       PICKING status on shipment
  pick_line:           marks line is_picked = True
  dispatch_shipment:   issues stock (ISSUE movement), updates SO status to SHIPPED/INVOICED
  invoice_from_ship:   creates Invoice from dispatched shipment quantities
  record_payment:      updates paid_amount, sets PAID/PARTIALLY_PAID/OVERDUE
  update_overdue:      sweeps invoices past due date → OVERDUE
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sales import (
    SalesOrder, SOLine, Shipment, ShipmentLine,
    Invoice, InvoiceLine, Payment,
    SOStatus, ShipmentStatus, InvoiceStatus,
)
from app.models.inventory import Stock, StockMovement, MovementType, StockType


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_so(so: SalesOrder, *statuses: SOStatus) -> None:
    if so.status not in statuses:
        raise HTTPException(422, f"SO is {so.status}; requires: {[s.value for s in statuses]}")


def _assert_ship(s: Shipment, *statuses: ShipmentStatus) -> None:
    if s.status not in statuses:
        raise HTTPException(422, f"Shipment is {s.status}; requires: {[s.value for s in statuses]}")


# ── SO Lifecycle ──────────────────────────────────────────────────────────────

async def confirm_so(db: AsyncSession, so: SalesOrder, user_id: uuid.UUID) -> SalesOrder:
    _assert_so(so, SOStatus.DRAFT)
    if not so.lines:
        raise HTTPException(422, "Sales order must have at least one line")
    so.status = SOStatus.CONFIRMED
    so.confirmed_by_id = user_id
    so.confirmed_at = datetime.now(timezone.utc)
    await db.flush()
    return so


async def allocate_so(
    db: AsyncSession,
    so: SalesOrder,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SalesOrder:
    _assert_so(so, SOStatus.CONFIRMED)

    # Re-load with product info
    lines_result = await db.execute(
        select(SOLine).where(SOLine.so_id == so.id)
    )
    lines = list(lines_result.scalars().all())

    for line in lines:
        qty_needed = line.ordered_quantity - line.allocated_quantity
        if qty_needed <= 0:
            continue

        filters = [
            Stock.warehouse_id == warehouse_id,
            Stock.product_id == line.product_id,
            Stock.stock_type == StockType.PRODUCT,
            Stock.is_blocked == False,  # noqa: E712
        ]
        result = await db.execute(
            select(Stock).where(and_(*filters)).with_for_update()
        )
        stocks = list(result.scalars().all())
        available = sum(s.quantity_available for s in stocks)

        if available < qty_needed:
            raise HTTPException(
                422,
                detail={
                    "error": "INSUFFICIENT_STOCK",
                    "message": f"Insufficient stock for line {line.line_no}. "
                               f"Need {qty_needed}, available {available}.",
                    "available": float(available),
                    "required": float(qty_needed),
                }
            )

        remaining = qty_needed
        for stock in stocks:
            if remaining <= 0:
                break
            alloc = min(stock.quantity_available, remaining)
            stock.quantity_reserved += alloc
            stock.quantity_available -= alloc
            remaining -= alloc

        line.allocated_quantity = line.ordered_quantity

    so.status = SOStatus.ALLOCATED
    so.warehouse_id = warehouse_id
    await db.flush()
    return so


async def cancel_so(db: AsyncSession, so: SalesOrder) -> SalesOrder:
    _assert_so(so, SOStatus.DRAFT, SOStatus.CONFIRMED, SOStatus.ALLOCATED)
    # If allocated, release reservations
    if so.status == SOStatus.ALLOCATED and so.warehouse_id:
        await _release_so_allocation(db, so)
    so.status = SOStatus.CANCELLED
    await db.flush()
    return so


async def _release_so_allocation(db: AsyncSession, so: SalesOrder) -> None:
    lines_result = await db.execute(select(SOLine).where(SOLine.so_id == so.id))
    lines = list(lines_result.scalars().all())
    for line in lines:
        if line.allocated_quantity <= 0:
            continue
        result = await db.execute(
            select(Stock).where(
                and_(
                    Stock.warehouse_id == so.warehouse_id,
                    Stock.product_id == line.product_id,
                    Stock.stock_type == StockType.PRODUCT,
                )
            ).with_for_update()
        )
        stocks = list(result.scalars().all())
        remaining = line.allocated_quantity
        for stock in stocks:
            release = min(stock.quantity_reserved, remaining)
            stock.quantity_reserved -= release
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
            remaining -= release
            if remaining <= 0:
                break
        line.allocated_quantity = Decimal("0")
    await db.flush()


# ── Shipment Lifecycle ────────────────────────────────────────────────────────

async def start_picking(db: AsyncSession, shipment: Shipment) -> Shipment:
    _assert_ship(shipment, ShipmentStatus.PENDING)
    shipment.status = ShipmentStatus.PICKING
    await db.flush()
    return shipment


async def pick_line(
    db: AsyncSession,
    line: ShipmentLine,
    user_id: uuid.UUID,
) -> ShipmentLine:
    line.is_picked = True
    line.picked_by_id = user_id
    line.picked_at = datetime.now(timezone.utc)
    await db.flush()
    # Check if all lines are picked → auto-advance to PACKED
    result = await db.execute(
        select(ShipmentLine).where(ShipmentLine.shipment_id == line.shipment_id)
    )
    all_lines = list(result.scalars().all())
    if all_lines and all(l.is_picked for l in all_lines):
        ship_result = await db.execute(
            select(Shipment).where(Shipment.id == line.shipment_id)
        )
        ship = ship_result.scalar_one_or_none()
        if ship and ship.status == ShipmentStatus.PICKING:
            ship.status = ShipmentStatus.PACKED
    await db.flush()
    return line


async def dispatch_shipment(
    db: AsyncSession,
    shipment: Shipment,
    dispatched_date: Optional[date],
    user_id: uuid.UUID,
) -> Shipment:
    _assert_ship(shipment, ShipmentStatus.PENDING, ShipmentStatus.PICKING, ShipmentStatus.PACKED)

    today = date.today()
    dispatch_date = dispatched_date or today

    # Load full shipment with lines and SO
    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.lines),
            selectinload(Shipment.so).selectinload(SalesOrder.lines),
        )
        .where(Shipment.id == shipment.id)
    )
    shipment = result.scalar_one()

    for line in shipment.lines:
        # ISSUE stock movement
        filters = [
            Stock.warehouse_id == shipment.warehouse_id,
            Stock.product_id == line.product_id,
            Stock.stock_type == StockType.PRODUCT,
            Stock.is_blocked == False,  # noqa: E712
        ]
        if line.lot_id:
            filters.append(Stock.lot_id == line.lot_id)

        stock_result = await db.execute(
            select(Stock).where(and_(*filters)).with_for_update()
        )
        stocks = list(stock_result.scalars().all())
        available = sum(
            s.quantity_on_hand - (s.quantity_reserved - min(s.quantity_reserved, line.quantity))
            for s in stocks
        )
        # Simpler: just check quantity_on_hand total
        total_on_hand = sum(s.quantity_on_hand for s in stocks)
        if total_on_hand < line.quantity:
            raise HTTPException(
                422,
                f"Insufficient on-hand stock for shipment line (product {line.product_id}). "
                f"On hand: {total_on_hand}, required: {line.quantity}"
            )

        remaining = line.quantity
        for stock in stocks:
            if remaining <= 0:
                break
            deduct = min(stock.quantity_on_hand, remaining)
            stock.quantity_on_hand -= deduct
            stock.quantity_reserved = max(stock.quantity_reserved - deduct, Decimal("0"))
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
            remaining -= deduct

        movement = StockMovement(
            reference_number=shipment.shipment_no,
            movement_type=MovementType.ISSUE,
            stock_type=StockType.PRODUCT,
            movement_date=dispatch_date,
            product_id=line.product_id,
            lot_id=line.lot_id,
            source_warehouse_id=shipment.warehouse_id,
            quantity=line.quantity,
            notes=f"Shipment {shipment.shipment_no} dispatch",
            created_by_id=user_id,
        )
        db.add(movement)
        await db.flush()
        line.stock_movement_id = movement.id

        # Update SO line shipped_quantity
        if line.so_line_id:
            so_line_result = await db.execute(
                select(SOLine).where(SOLine.id == line.so_line_id).with_for_update()
            )
            so_line = so_line_result.scalar_one_or_none()
            if so_line:
                so_line.shipped_quantity += line.quantity

    shipment.status = ShipmentStatus.DISPATCHED
    shipment.dispatched_date = dispatch_date
    shipment.dispatched_by_id = user_id

    # Update SO status
    so_lines_result = await db.execute(
        select(SOLine).where(SOLine.so_id == shipment.so_id)
    )
    so_lines = list(so_lines_result.scalars().all())
    all_shipped = all(l.shipped_quantity >= l.ordered_quantity for l in so_lines)
    so_result = await db.execute(select(SalesOrder).where(SalesOrder.id == shipment.so_id).with_for_update())
    so = so_result.scalar_one()
    if all_shipped:
        so.status = SOStatus.SHIPPED
    else:
        so.status = SOStatus.PICKING  # Partial shipment

    await db.flush()
    return shipment


# ── Invoice lifecycle ─────────────────────────────────────────────────────────

async def invoice_from_shipment(
    db: AsyncSession,
    shipment: Shipment,
    invoice_no: str,
    invoice_date: date,
    due_date: date,
    user_id: uuid.UUID,
    notes: Optional[str] = None,
) -> Invoice:
    _assert_ship(shipment, ShipmentStatus.DISPATCHED)
    if shipment.invoice:
        raise HTTPException(422, "Shipment already has an invoice")

    # Load SO for customer and pricing
    so_result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines).selectinload(SOLine.product))
        .where(SalesOrder.id == shipment.so_id)
    )
    so = so_result.scalar_one()

    lines_data = []
    subtotal = Decimal("0")
    tax_total = Decimal("0")

    # Load shipment lines with product
    ship_lines_result = await db.execute(
        select(ShipmentLine)
        .options(selectinload(ShipmentLine.product))
        .where(ShipmentLine.shipment_id == shipment.id)
    )
    ship_lines = list(ship_lines_result.scalars().all())

    for sl in ship_lines:
        # Find matching SO line for pricing
        so_line = next((l for l in so.lines if l.id == sl.so_line_id), None)
        unit_price = so_line.unit_price if so_line else Decimal("0")
        discount_pct = so_line.discount_pct if so_line else Decimal("0")
        tax_rate = so_line.tax_rate if so_line else Decimal("0")
        net_price = unit_price * (1 - discount_pct)
        line_total = (sl.quantity * net_price * (1 + tax_rate)).quantize(Decimal("0.01"))
        subtotal += sl.quantity * net_price
        tax_total += sl.quantity * net_price * tax_rate

        lines_data.append(InvoiceLine(
            product_id=sl.product_id,
            description=sl.product.name if sl.product else None,
            so_line_id=sl.so_line_id,
            quantity=sl.quantity,
            unit=sl.unit,
            unit_price=unit_price,
            discount_pct=discount_pct,
            tax_rate=tax_rate,
            line_total=line_total,
        ))

    total_amount = (subtotal + tax_total).quantize(Decimal("0.01"))

    invoice = Invoice(
        invoice_no=invoice_no,
        so_id=shipment.so_id,
        shipment_id=shipment.id,
        customer_id=so.customer_id,
        invoice_date=invoice_date,
        due_date=due_date,
        status=InvoiceStatus.ISSUED,
        currency=so.currency,
        subtotal=subtotal.quantize(Decimal("0.01")),
        tax_amount=tax_total.quantize(Decimal("0.01")),
        total_amount=total_amount,
        paid_amount=Decimal("0"),
        notes=notes,
        created_by_id=user_id,
    )
    db.add(invoice)
    await db.flush()

    for il in lines_data:
        il.invoice_id = invoice.id
        db.add(il)

    # Mark SO as INVOICED if fully shipped
    so_result2 = await db.execute(select(SalesOrder).where(SalesOrder.id == so.id).with_for_update())
    so2 = so_result2.scalar_one()
    if so2.status == SOStatus.SHIPPED:
        so2.status = SOStatus.INVOICED

    await db.flush()
    await db.refresh(invoice)
    return invoice


async def record_payment(
    db: AsyncSession,
    invoice: Invoice,
    amount: Decimal,
    payment_date: date,
    reference: Optional[str],
    notes: Optional[str],
    user_id: uuid.UUID,
) -> Payment:
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(422, "Invoice already fully paid")
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(422, "Invoice is cancelled")

    payment = Payment(
        invoice_id=invoice.id,
        payment_date=payment_date,
        amount=amount,
        reference=reference,
        notes=notes,
        created_by_id=user_id,
    )
    db.add(payment)
    await db.flush()

    invoice.paid_amount += amount
    outstanding = invoice.total_amount - invoice.paid_amount
    if outstanding <= Decimal("0.005"):
        invoice.status = InvoiceStatus.PAID
    elif invoice.paid_amount > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    await db.flush()
    return payment


async def sync_overdue_invoices(db: AsyncSession) -> int:
    """Mark past-due ISSUED/PARTIALLY_PAID invoices as OVERDUE."""
    from sqlalchemy import update
    today = date.today()
    result = await db.execute(
        select(Invoice).where(
            Invoice.due_date < today,
            Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
        )
    )
    invoices = list(result.scalars().all())
    for inv in invoices:
        inv.status = InvoiceStatus.OVERDUE
    await db.flush()
    return len(invoices)
