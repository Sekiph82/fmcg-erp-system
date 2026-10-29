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
from app.models.finance import (
    AccountingPostingRule,
    AccountType,
    ChartOfAccount,
    JournalEntry,
    JournalLine,
    JournalStatus,
)


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_so(so: SalesOrder, *statuses: SOStatus) -> None:
    if so.status not in statuses:
        raise HTTPException(422, f"SO is {so.status}; requires: {[s.value for s in statuses]}")


def _assert_ship(s: Shipment, *statuses: ShipmentStatus) -> None:
    if s.status not in statuses:
        raise HTTPException(422, f"Shipment is {s.status}; requires: {[s.value for s in statuses]}")


async def _lock_sales_order_for_update(db: AsyncSession, so: SalesOrder) -> SalesOrder:
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_so = result.scalar_one_or_none()
    if locked_so is None:
        raise HTTPException(404, "Sales order not found")
    return locked_so


async def _active_posting_rule(
    db: AsyncSession, source_event: str
) -> AccountingPostingRule:
    result = await db.execute(
        select(AccountingPostingRule)
        .where(
            AccountingPostingRule.source_module == "sales",
            AccountingPostingRule.source_event == source_event,
            AccountingPostingRule.is_active.is_(True),
        )
        .order_by(AccountingPostingRule.priority, AccountingPostingRule.created_at, AccountingPostingRule.id)
        .limit(1)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            422,
            f"No active accounting posting rule is configured for sales/{source_event}",
        )
    return rule


async def _require_sales_account_types(
    db: AsyncSession, expected: list[tuple[Optional[uuid.UUID], AccountType, str]]
) -> None:
    required = [(account_id, account_type, label) for account_id, account_type, label in expected if account_id]
    ids = {account_id for account_id, _, _ in required}
    accounts = {
        account.id: account
        for account in (await db.execute(select(ChartOfAccount).where(ChartOfAccount.id.in_(ids)))).scalars().all()
    } if ids else {}
    for account_id, account_type, label in required:
        account = accounts.get(account_id)
        if account is None or account.account_type != account_type:
            raise HTTPException(422, f"Configured {label} account must exist and have type {account_type.value}")


async def _post_sales_journal(
    db: AsyncSession,
    *,
    source_event: str,
    source_id: uuid.UUID,
    source_ref: str,
    entry_date: date,
    description: str,
    amount: Decimal,
    currency: str,
    debit_lines: list[tuple[uuid.UUID, Decimal, str]],
    credit_lines: list[tuple[uuid.UUID, Decimal, str]],
    user_id: uuid.UUID,
) -> JournalEntry:
    """Post one configured, balanced sales journal in the source transaction."""
    from app.services.finance_service import (
        assert_journal_lines_postable,
        assert_posting_period_open,
        get_or_create_operational_posting_event,
        mark_journal_posted,
        mark_operational_posting_posted,
        validate_journal_lines_balance,
    )
    from app.models.finance import OperationalPostingStatus

    event, batch, _ = await get_or_create_operational_posting_event(
        db,
        source_module="sales",
        source_event=source_event,
        source_id=source_id,
        event_date=entry_date,
        source_ref=source_ref,
        amount=amount,
        currency=currency,
        created_by_id=user_id,
    )
    if event.status == OperationalPostingStatus.POSTED and event.journal_entry_id:
        existing = await db.get(JournalEntry, event.journal_entry_id)
        if existing is not None:
            return existing
    if event.status != OperationalPostingStatus.PENDING:
        raise HTTPException(409, f"Sales posting event {source_event}/{source_id} already exists but is not posted")

    lines_data = [
        {"account_id": account_id, "description": line_description, "debit": debit, "credit": Decimal("0"), "currency": currency}
        for account_id, debit, line_description in debit_lines if debit > 0
    ] + [
        {"account_id": account_id, "description": line_description, "debit": Decimal("0"), "credit": credit, "currency": currency}
        for account_id, credit, line_description in credit_lines if credit > 0
    ]
    validate_journal_lines_balance(lines_data)
    await assert_journal_lines_postable(db, lines_data)
    await assert_posting_period_open(db, entry_date)

    entry = JournalEntry(
        entry_no=f"AUTO-SLS-{source_id.hex}",
        entry_date=entry_date,
        description=description[:255],
        source_module="sales",
        source_event=source_event,
        source_id=source_id,
        source_ref=source_ref[:100],
        status=JournalStatus.DRAFT,
        is_posted=False,
        posting_batch_id=batch.id,
        created_by_id=user_id,
    )
    entry.lines = [JournalLine(**line_data) for line_data in lines_data]
    db.add(entry)
    await db.flush()
    await mark_journal_posted(db, entry, user_id)
    await mark_operational_posting_posted(
        db, event, batch, journal_entry_id=entry.id, posted_by_id=user_id
    )
    return entry


async def _post_invoice_to_gl(db: AsyncSession, invoice: Invoice, user_id: uuid.UUID) -> JournalEntry:
    rule = await _active_posting_rule(db, "SALES_INVOICE_ISSUED")
    if not rule.debit_account_id or not rule.credit_account_id:
        raise HTTPException(422, "Invoice posting rule must configure the receivables debit and revenue credit accounts")
    if invoice.subtotal < 0 or invoice.tax_amount < 0 or invoice.total_amount <= 0:
        raise HTTPException(422, "Invoice totals must be positive and non-negative by component before posting")
    if invoice.total_amount != invoice.subtotal + invoice.tax_amount:
        raise HTTPException(422, "Invoice total does not equal subtotal plus tax; refusing to post")
    if invoice.tax_amount > 0 and not rule.tax_account_id:
        raise HTTPException(422, "Invoice posting rule must configure a tax liability account when invoice tax is non-zero")
    if invoice.tax_amount == 0 and rule.tax_account_id is None:
        tax_lines: list[tuple[uuid.UUID, Decimal, str]] = []
    else:
        tax_lines = [(rule.tax_account_id, invoice.tax_amount, f"Tax on invoice {invoice.invoice_no}")]
    await _require_sales_account_types(
        db,
        [
            (rule.debit_account_id, AccountType.ASSET, "receivables debit"),
            (rule.credit_account_id, AccountType.REVENUE, "revenue credit"),
            (rule.tax_account_id if invoice.tax_amount > 0 else None, AccountType.LIABILITY, "tax liability"),
        ],
    )
    return await _post_sales_journal(
        db,
        source_event="SALES_INVOICE_ISSUED",
        source_id=invoice.id,
        source_ref=invoice.invoice_no,
        entry_date=invoice.invoice_date,
        description=f"Sales invoice {invoice.invoice_no}",
        amount=invoice.total_amount,
        currency=invoice.currency,
        debit_lines=[(rule.debit_account_id, invoice.total_amount, f"Receivable for invoice {invoice.invoice_no}")],
        credit_lines=[
            (rule.credit_account_id, invoice.subtotal, f"Revenue for invoice {invoice.invoice_no}"),
            *tax_lines,
        ],
        user_id=user_id,
    )


async def _post_customer_payment_to_gl(
    db: AsyncSession, payment: Payment, invoice: Invoice, user_id: uuid.UUID
) -> JournalEntry:
    from app.models.finance import OperationalPostingEvent, OperationalPostingStatus

    method = (payment.method or "cash").strip().lower()
    if method not in {"cash", "bank", "mpesa"}:
        raise HTTPException(422, "Customer payment method must be cash, bank, or mpesa")
    source_event = f"CUSTOMER_PAYMENT_RECEIVED_{method.upper()}"
    rule = await _active_posting_rule(db, source_event)
    if not rule.clearing_account_id or not rule.credit_account_id:
        raise HTTPException(422, "Payment posting rule must configure a clearing debit and receivables credit account")
    invoice_event = (await db.execute(
        select(OperationalPostingEvent).where(
            OperationalPostingEvent.source_module == "sales",
            OperationalPostingEvent.source_event == "SALES_INVOICE_ISSUED",
            OperationalPostingEvent.source_id == str(invoice.id),
        )
    )).scalar_one_or_none()
    if (
        invoice_event is None
        or invoice_event.status != OperationalPostingStatus.POSTED
        or invoice_event.journal_entry_id is None
    ):
        raise HTTPException(409, "Invoice has no posted receivables journal to settle")
    invoice_journal = (await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == invoice_event.journal_entry_id)
    )).scalar_one_or_none()
    invoice_receivables_accounts = {
        line.account_id for line in (invoice_journal.lines if invoice_journal else []) if line.debit > 0
    }
    if (
        invoice_journal is None
        or not invoice_journal.is_posted
        or invoice_journal.status != JournalStatus.POSTED
        or len(invoice_receivables_accounts) != 1
        or rule.credit_account_id not in invoice_receivables_accounts
    ):
        raise HTTPException(422, "Payment posting rule must credit the same receivables account debited by the invoice")
    await _require_sales_account_types(
        db,
        [
            (rule.clearing_account_id, AccountType.ASSET, "payment clearing debit"),
            (rule.credit_account_id, AccountType.ASSET, "receivables credit"),
        ],
    )
    return await _post_sales_journal(
        db,
        source_event=source_event,
        source_id=payment.id,
        source_ref=payment.reference or str(payment.id),
        entry_date=payment.payment_date,
        description=f"Customer payment for invoice {invoice.invoice_no}",
        amount=payment.amount,
        currency=invoice.currency,
        debit_lines=[(rule.clearing_account_id, payment.amount, f"{method.upper()} receipt {payment.reference or payment.id}")],
        credit_lines=[(rule.credit_account_id, payment.amount, f"Receivable settlement for invoice {invoice.invoice_no}")],
        user_id=user_id,
    )


# ── SO Lifecycle ──────────────────────────────────────────────────────────────

async def confirm_so(db: AsyncSession, so: SalesOrder, user_id: uuid.UUID) -> SalesOrder:
    _assert_so(so, SOStatus.DRAFT)
    if not so.lines:
        raise HTTPException(422, "Sales order must have at least one line")
    # Credit limit check
    if so.customer and so.customer.credit_limit is not None:
        order_value = sum(
            l.ordered_quantity * l.unit_price * (1 - l.discount_pct) * (1 + l.tax_rate)
            for l in so.lines
        )
        outstanding = await _get_customer_outstanding(db, so.customer_id)
        if outstanding + order_value > so.customer.credit_limit:
            available = max(so.customer.credit_limit - outstanding, Decimal("0"))
            raise HTTPException(
                422,
                f"Credit limit exceeded. Limit: {so.customer.credit_limit}, "
                f"Outstanding: {outstanding:.2f}, Order: {order_value:.2f}, "
                f"Available: {available:.2f}"
            )
    so.status = SOStatus.CONFIRMED
    so.confirmed_by_id = user_id
    so.confirmed_at = datetime.now(timezone.utc)
    await db.flush()
    return so


async def _get_customer_outstanding(db: AsyncSession, customer_id: uuid.UUID) -> Decimal:
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            )
        )
    )
    invs = result.scalars().all()
    return sum(max(i.total_amount - i.paid_amount, Decimal("0")) for i in invs)


async def allocate_so(
    db: AsyncSession,
    so: SalesOrder,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SalesOrder:
    # Serialize allocation attempts for the same order before reading its lines.
    # Stock-row locks alone protect competing orders but do not prevent two stale
    # requests for this same order from reserving the same line twice.
    so = await _lock_sales_order_for_update(db, so)
    _assert_so(so, SOStatus.CONFIRMED)

    # Re-load with product info
    lines_result = await db.execute(
        select(SOLine)
        .where(SOLine.so_id == so.id)
        .with_for_update()
        .execution_options(populate_existing=True)
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
            select(Stock)
            .where(and_(*filters))
            .with_for_update()
            .execution_options(populate_existing=True)
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
    so = await _lock_sales_order_for_update(db, so)
    _assert_so(so, SOStatus.DRAFT, SOStatus.CONFIRMED, SOStatus.ALLOCATED)
    # If allocated, release reservations
    if so.status == SOStatus.ALLOCATED and so.warehouse_id:
        await _release_so_allocation(db, so)
    so.status = SOStatus.CANCELLED
    await db.flush()
    return so


async def _release_so_allocation(db: AsyncSession, so: SalesOrder) -> None:
    lines_result = await db.execute(
        select(SOLine)
        .where(SOLine.so_id == so.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    lines = list(lines_result.scalars().all())
    for line in lines:
        if line.allocated_quantity <= 0:
            continue
        result = await db.execute(
            select(Stock)
            .where(
                and_(
                    Stock.warehouse_id == so.warehouse_id,
                    Stock.product_id == line.product_id,
                    Stock.stock_type == StockType.PRODUCT,
                )
            )
            .with_for_update()
            .execution_options(populate_existing=True)
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
    today = date.today()
    dispatch_date = dispatched_date or today

    # Lock and refresh the shipment before validating its transition so a retry
    # cannot dispatch a stale PENDING object twice. Keep the global mutation order
    # shipment -> sales order -> stock to serialize with cancellation/allocation.
    result = await db.execute(
        select(Shipment)
        .options(selectinload(Shipment.lines))
        .where(Shipment.id == shipment.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(404, "Shipment not found")
    _assert_ship(shipment, ShipmentStatus.PENDING, ShipmentStatus.PICKING, ShipmentStatus.PACKED)

    so_result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == shipment.so_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    so = so_result.scalar_one_or_none()
    if so is None:
        raise HTTPException(404, "Sales order not found")

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
            select(Stock)
            .where(and_(*filters))
            .with_for_update()
            .execution_options(populate_existing=True)
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
                select(SOLine)
                .where(SOLine.id == line.so_line_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            so_line = so_line_result.scalar_one_or_none()
            if so_line:
                so_line.shipped_quantity += line.quantity

    shipment.status = ShipmentStatus.DISPATCHED
    shipment.dispatched_date = dispatch_date
    shipment.dispatched_by_id = user_id

    # Persist the increments in this transaction before refreshing cached lines;
    # this session disables autoflush, so populate_existing would otherwise erase
    # the just-computed shipped_quantity values from the identity map.
    await db.flush()

    # Update SO status
    so_lines_result = await db.execute(
        select(SOLine)
        .where(SOLine.so_id == shipment.so_id)
        .execution_options(populate_existing=True)
    )
    so_lines = list(so_lines_result.scalars().all())
    all_shipped = all(l.shipped_quantity >= l.ordered_quantity for l in so_lines)
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
        line_subtotal = (sl.quantity * net_price).quantize(Decimal("0.01"))
        line_tax = (line_subtotal * tax_rate).quantize(Decimal("0.01"))
        line_total = line_subtotal + line_tax
        subtotal += line_subtotal
        tax_total += line_tax

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

    subtotal = subtotal.quantize(Decimal("0.01"))
    tax_total = tax_total.quantize(Decimal("0.01"))
    total_amount = subtotal + tax_total

    invoice = Invoice(
        invoice_no=invoice_no,
        so_id=shipment.so_id,
        shipment_id=shipment.id,
        customer_id=so.customer_id,
        invoice_date=invoice_date,
        due_date=due_date,
        status=InvoiceStatus.ISSUED,
        currency=so.currency,
        subtotal=subtotal,
        tax_amount=tax_total,
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

    await _post_invoice_to_gl(db, invoice, user_id)

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
    method: str = "cash",
) -> Payment:
    locked_result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    invoice = locked_result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(422, "Invoice already fully paid")
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(422, "Invoice is cancelled")
    if amount <= 0:
        raise HTTPException(422, "Customer payment amount must be greater than zero")
    outstanding_before_payment = invoice.total_amount - invoice.paid_amount
    if amount > outstanding_before_payment:
        raise HTTPException(422, "Customer payment cannot exceed the invoice outstanding balance")
    normalized_method = (method or "cash").strip().lower()
    if normalized_method not in {"cash", "bank", "mpesa"}:
        raise HTTPException(422, "Customer payment method must be cash, bank, or mpesa")

    payment = Payment(
        invoice_id=invoice.id,
        payment_date=payment_date,
        amount=amount,
        method=normalized_method,
        reference=reference,
        notes=notes,
        created_by_id=user_id,
    )
    db.add(payment)
    await db.flush()

    await _post_customer_payment_to_gl(db, payment, invoice, user_id)

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


# ── Customer Statement ─────────────────────────────────────────────────────────

def _age_bucket(days_overdue: Optional[int]) -> str:
    if days_overdue is None or days_overdue <= 0:
        return "CURRENT"
    if days_overdue <= 30:
        return "1-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


async def get_customer_statement(db: AsyncSession, customer_id: uuid.UUID) -> dict:
    from app.models.sales import Customer, SalesOrder
    from app.schemas.sales import (
        StatementInvoiceRow, AgedBalanceSummary, CustomerStatement,
    )

    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        return None

    inv_result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.so))
        .where(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.status != InvoiceStatus.CANCELLED,
            )
        )
        .order_by(Invoice.due_date)
    )
    invoices = inv_result.scalars().all()

    today = date.today()
    rows = []
    aged = AgedBalanceSummary()

    for inv in invoices:
        if inv.status == InvoiceStatus.PAID:
            continue
        outstanding = max(inv.total_amount - inv.paid_amount, Decimal("0"))
        delta = (today - inv.due_date).days
        days_overdue = delta if delta > 0 else None
        bucket = _age_bucket(days_overdue)

        rows.append(StatementInvoiceRow(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            so_no=inv.so.order_no if inv.so else None,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            total_amount=inv.total_amount,
            paid_amount=inv.paid_amount,
            outstanding_balance=outstanding,
            status=inv.status,
            days_overdue=days_overdue,
            age_bucket=bucket,
        ))

        if bucket == "CURRENT":
            aged.current += outstanding
        elif bucket == "1-30":
            aged.days_1_30 += outstanding
        elif bucket == "31-60":
            aged.days_31_60 += outstanding
        elif bucket == "61-90":
            aged.days_61_90 += outstanding
        else:
            aged.days_90_plus += outstanding

    aged.total_outstanding = aged.current + aged.days_1_30 + aged.days_31_60 + aged.days_61_90 + aged.days_90_plus

    credit_used = aged.total_outstanding
    credit_available = (customer.credit_limit - credit_used) if customer.credit_limit else None

    return CustomerStatement(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_code=customer.code,
        credit_limit=customer.credit_limit,
        credit_used=credit_used,
        credit_available=credit_available,
        as_of_date=today,
        invoices=rows,
        aged_balance=aged,
    )


async def get_credit_check(
    db: AsyncSession, customer_id: uuid.UUID, order_value: Decimal
) -> dict:
    from app.models.sales import Customer
    from app.schemas.sales import CreditCheckResult

    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        return None

    outstanding = await _get_customer_outstanding(db, customer_id)
    credit_limit = customer.credit_limit
    if credit_limit is None:
        return CreditCheckResult(
            customer_id=customer.id,
            customer_name=customer.name,
            credit_limit=None,
            credit_used=outstanding,
            credit_available=None,
            order_value=order_value,
            would_exceed=False,
            can_confirm=True,
            message="No credit limit set for this customer",
        )

    would_exceed = outstanding + order_value > credit_limit
    credit_available = max(credit_limit - outstanding, Decimal("0"))
    return CreditCheckResult(
        customer_id=customer.id,
        customer_name=customer.name,
        credit_limit=credit_limit,
        credit_used=outstanding,
        credit_available=credit_available,
        order_value=order_value,
        would_exceed=would_exceed,
        can_confirm=not would_exceed,
        message=(
            f"Credit available: {credit_available:.2f}. Order would exceed limit by "
            f"{(outstanding + order_value - credit_limit):.2f}"
            if would_exceed
            else f"Within limit. Credit available after order: "
                 f"{max(credit_available - order_value, Decimal('0')):.2f}"
        ),
    )


# ── Order Margin ──────────────────────────────────────────────────────────────

async def get_order_margin(db: AsyncSession, so_id: uuid.UUID) -> dict:
    from app.schemas.sales import OrderMarginLineRow, OrderMarginSummary

    result = await db.execute(
        select(SalesOrder)
        .options(
            selectinload(SalesOrder.lines).selectinload(SOLine.product),
            selectinload(SalesOrder.customer),
        )
        .where(SalesOrder.id == so_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        return None

    lines_out = []
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    lines_with_cost = 0
    lines_without_cost = 0

    for l in (so.lines or []):
        net_price = l.unit_price * (1 - l.discount_pct)
        line_revenue = l.ordered_quantity * net_price * (1 + l.tax_rate)
        total_revenue += line_revenue

        if l.cost_price is not None:
            line_cost = l.ordered_quantity * l.cost_price
            total_cost += line_cost
            gross_margin_pct = ((net_price - l.cost_price) / net_price * 100) if net_price else None
            lines_with_cost += 1
        else:
            line_cost = None
            gross_margin_pct = None
            lines_without_cost += 1

        lines_out.append(OrderMarginLineRow(
            line_no=l.line_no,
            product_id=l.product_id,
            product_name=l.product.name if l.product else None,
            ordered_quantity=l.ordered_quantity,
            unit=l.unit,
            unit_price=l.unit_price,
            discount_pct=l.discount_pct,
            net_price=net_price.quantize(Decimal("0.0001")),
            cost_price=l.cost_price,
            line_revenue=line_revenue.quantize(Decimal("0.01")),
            line_cost=line_cost.quantize(Decimal("0.01")) if line_cost is not None else None,
            gross_margin_pct=gross_margin_pct.quantize(Decimal("0.01")) if gross_margin_pct is not None else None,
        ))

    gross_profit = (total_revenue - total_cost) if lines_with_cost > 0 else None
    gross_margin_pct = (gross_profit / total_revenue * 100).quantize(Decimal("0.01")) if (gross_profit is not None and total_revenue > 0) else None

    return OrderMarginSummary(
        so_id=so.id,
        order_no=so.order_no,
        customer_name=so.customer.name if so.customer else None,
        total_revenue=total_revenue.quantize(Decimal("0.01")),
        total_cost=total_cost.quantize(Decimal("0.01")) if lines_with_cost > 0 else None,
        gross_profit=gross_profit.quantize(Decimal("0.01")) if gross_profit is not None else None,
        gross_margin_pct=gross_margin_pct,
        lines_with_cost=lines_with_cost,
        lines_without_cost=lines_without_cost,
        lines=lines_out,
    )
