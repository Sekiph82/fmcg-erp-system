from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.deps import get_current_user, get_db
from app.models.sales import (
    Customer, SalesOrder, SOLine, Shipment, ShipmentLine,
    Invoice, InvoiceLine, Payment,
    SOStatus, ShipmentStatus, InvoiceStatus,
)
from app.schemas.sales import (
    CustomerCreate, CustomerUpdate, CustomerRead,
    SOCreate, SOUpdate, SORead, SODetailRead, SOLineRead,
    ShipmentCreate, ShipmentRead, ShipmentDetailRead, ShipmentLineRead,
    InvoiceRead, InvoiceDetailRead, PaymentCreate, PaymentRead,
    AllocateSORequest, DispatchShipmentRequest, InvoiceFromShipmentRequest,
    OutstandingInvoiceRow, SalesSummary,
    MpesaPaymentRequest, MpesaCallbackPayload, MpesaTransactionRead,
)
from app.crud import sales as crud
from app.services import sales_service as svc
from app.services import mpesa_service as mpesa_svc

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_so_read(so: SalesOrder) -> SORead:
    d = SORead.model_validate(so)
    if so.customer:
        d.customer_name = so.customer.name
    if so.warehouse:
        d.warehouse_name = so.warehouse.name
    if so.lines:
        d.line_count = len(so.lines)
        total = sum(
            (l.ordered_quantity * l.unit_price * (1 - l.discount_pct) * (1 + l.tax_rate))
            for l in so.lines
        )
        d.total_value = total.quantize(Decimal("0.01"))
    today = date.today()
    delta = (so.requested_delivery_date - today).days
    d.days_until_delivery = delta
    return d


def _build_so_detail(so: SalesOrder) -> SODetailRead:
    d = SODetailRead.model_validate(so)
    if so.customer:
        d.customer_name = so.customer.name
    if so.warehouse:
        d.warehouse_name = so.warehouse.name
    if so.lines:
        d.line_count = len(so.lines)
        total = sum(
            (l.ordered_quantity * l.unit_price * (1 - l.discount_pct) * (1 + l.tax_rate))
            for l in so.lines
        )
        d.total_value = total.quantize(Decimal("0.01"))
        lines_out = []
        for l in so.lines:
            lr = SOLineRead.model_validate(l)
            if l.product:
                lr.product_name = l.product.name
                lr.product_sku = l.product.sku
            lines_out.append(lr)
        d.lines = lines_out
    today = date.today()
    delta = (so.requested_delivery_date - today).days
    d.days_until_delivery = delta
    return d


def _build_shipment_read(s: Shipment) -> ShipmentRead:
    d = ShipmentRead.model_validate(s)
    if s.so:
        d.so_no = s.so.order_no
        if s.so.customer:
            d.customer_name = s.so.customer.name
    if s.warehouse:
        d.warehouse_name = s.warehouse.name
    if s.lines:
        d.line_count = len(s.lines)
        d.picked_count = sum(1 for l in s.lines if l.is_picked)
    return d


def _build_shipment_detail(s: Shipment) -> ShipmentDetailRead:
    d = ShipmentDetailRead.model_validate(s)
    if s.so:
        d.so_no = s.so.order_no
        if s.so.customer:
            d.customer_name = s.so.customer.name
    if s.warehouse:
        d.warehouse_name = s.warehouse.name
    if s.lines:
        d.line_count = len(s.lines)
        d.picked_count = sum(1 for l in s.lines if l.is_picked)
        lines_out = []
        for l in s.lines:
            lr = ShipmentLineRead.model_validate(l)
            if l.product:
                lr.product_name = l.product.name
                lr.product_sku = l.product.sku
            if l.lot:
                lr.lot_number = l.lot.lot_number
            lines_out.append(lr)
        d.lines = lines_out
    return d


def _build_invoice_read(inv: Invoice) -> InvoiceRead:
    d = InvoiceRead.model_validate(inv)
    if inv.customer:
        d.customer_name = inv.customer.name
    if inv.so:
        d.so_no = inv.so.order_no
    return d


def _build_invoice_detail(inv: Invoice) -> InvoiceDetailRead:
    d = InvoiceDetailRead.model_validate(inv)
    if inv.customer:
        d.customer_name = inv.customer.name
    if inv.so:
        d.so_no = inv.so.order_no
    if inv.lines:
        lines_out = []
        for l in inv.lines:
            from app.schemas.sales import InvoiceLineRead
            lr = InvoiceLineRead.model_validate(l)
            if l.product:
                lr.product_name = l.product.name
                lr.product_sku = l.product.sku
            lines_out.append(lr)
        d.lines = lines_out
    return d


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers/", response_model=List[CustomerRead])
async def list_customers(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await crud.list_customers(db, active_only=active_only)


@router.post("/customers/", response_model=CustomerRead, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await crud.create_customer(db, body.model_dump())
    await db.commit()
    await db.refresh(c)
    return c


@router.get("/customers/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await crud.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return c


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await crud.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c


# ── Sales Orders ──────────────────────────────────────────────────────────────

@router.get("/orders/", response_model=List[SORead])
async def list_orders(
    status: Optional[SOStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    # Marketing filters — campaign/promotion attribution visibility
    campaign_id: Optional[uuid.UUID] = Query(None, description="Filter by linked campaign"),
    promotion_id: Optional[uuid.UUID] = Query(None, description="Filter by linked promotion"),
    crm_segment_id: Optional[uuid.UUID] = Query(None, description="Filter by CRM segment"),
    source: Optional[str] = Query(None, description="Filter by order source (MANUAL/FIELD_SALES/ECOMMERCE/...)"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sos = await crud.list_sos(db, status=status, customer_id=customer_id)
    # Apply marketing filters in-memory (avoids altering crud layer)
    if campaign_id:
        sos = [s for s in sos if str(getattr(s, "campaign_id", None)) == str(campaign_id)]
    if promotion_id:
        sos = [s for s in sos if str(getattr(s, "promotion_id", None)) == str(promotion_id)]
    if crm_segment_id:
        sos = [s for s in sos if str(getattr(s, "crm_segment_id", None)) == str(crm_segment_id)]
    if source:
        sos = [s for s in sos if str(getattr(s, "source", "")).upper() == source.upper()]
    return [_build_so_read(so) for so in sos]


@router.post("/orders/", response_model=SODetailRead, status_code=201)
async def create_order(
    body: SOCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = body.model_dump()
    data["lines"] = [l.model_dump() for l in body.lines]
    so = await crud.create_so(db, data, created_by_id=current_user.id)
    await db.commit()
    so = await crud.get_so(db, so.id)
    return _build_so_detail(so)


@router.get("/orders/{so_id}", response_model=SODetailRead)
async def get_order(
    so_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    return _build_so_detail(so)


@router.patch("/orders/{so_id}", response_model=SODetailRead)
async def update_order(
    so_id: uuid.UUID,
    body: SOUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    if so.status not in (SOStatus.DRAFT,):
        raise HTTPException(422, "Only DRAFT orders can be updated")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(so, k, v)
    await db.commit()
    so = await crud.get_so(db, so_id)
    return _build_so_detail(so)


@router.post("/orders/{so_id}/confirm", response_model=SODetailRead)
async def confirm_order(
    so_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    so = await svc.confirm_so(db, so, current_user.id)
    await db.commit()
    so = await crud.get_so(db, so_id)
    return _build_so_detail(so)


@router.post("/orders/{so_id}/allocate", response_model=SODetailRead)
async def allocate_order(
    so_id: uuid.UUID,
    body: AllocateSORequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    so = await svc.allocate_so(db, so, body.warehouse_id, current_user.id)
    await db.commit()
    so = await crud.get_so(db, so_id)
    return _build_so_detail(so)


@router.post("/orders/{so_id}/cancel", response_model=SODetailRead)
async def cancel_order(
    so_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    so = await svc.cancel_so(db, so)
    await db.commit()
    so = await crud.get_so(db, so_id)
    return _build_so_detail(so)


# ── Shipments ─────────────────────────────────────────────────────────────────

@router.get("/shipments/", response_model=List[ShipmentRead])
async def list_shipments(
    status: Optional[ShipmentStatus] = None,
    so_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ships = await crud.list_shipments(db, status=status, so_id=so_id)
    return [_build_shipment_read(s) for s in ships]


@router.post("/shipments/", response_model=ShipmentDetailRead, status_code=201)
async def create_shipment(
    body: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Validate SO is in a shippable state
    so = await crud.get_so(db, body.so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    if so.status not in (SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING):
        raise HTTPException(422, f"SO must be CONFIRMED/ALLOCATED/PICKING, is {so.status.value}")
    data = body.model_dump()
    data["lines"] = [l.model_dump() for l in body.lines]
    s = await crud.create_shipment(db, data, created_by_id=current_user.id)
    await db.commit()
    s = await crud.get_shipment(db, s.id)
    return _build_shipment_detail(s)


@router.get("/shipments/{shipment_id}", response_model=ShipmentDetailRead)
async def get_shipment(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = await crud.get_shipment(db, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    return _build_shipment_detail(s)


@router.post("/shipments/{shipment_id}/start-picking", response_model=ShipmentDetailRead)
async def start_picking(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = await crud.get_shipment(db, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    s = await svc.start_picking(db, s)
    await db.commit()
    s = await crud.get_shipment(db, shipment_id)
    return _build_shipment_detail(s)


@router.post("/shipments/{shipment_id}/lines/{line_id}/pick", response_model=ShipmentLineRead)
async def pick_line(
    shipment_id: uuid.UUID,
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    line = await crud.get_shipment_line(db, line_id)
    if not line or line.shipment_id != shipment_id:
        raise HTTPException(404, "Shipment line not found")
    line = await svc.pick_line(db, line, current_user.id)
    await db.commit()
    line = await crud.get_shipment_line(db, line_id)
    lr = ShipmentLineRead.model_validate(line)
    if line.product:
        lr.product_name = line.product.name
        lr.product_sku = line.product.sku
    if line.lot:
        lr.lot_number = line.lot.lot_number
    return lr


@router.post("/shipments/{shipment_id}/dispatch", response_model=ShipmentDetailRead)
async def dispatch_shipment(
    shipment_id: uuid.UUID,
    body: DispatchShipmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = await crud.get_shipment(db, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")

    # Payment guard: block dispatch for prepaid customers with outstanding payment
    so = await crud.get_so(db, s.so_id)
    if so and so.customer:
        mpesa_svc.assert_payment_cleared_for_dispatch(so, so.customer.is_prepaid)

    s = await svc.dispatch_shipment(db, s, body.dispatched_date, current_user.id)
    await db.commit()
    s = await crud.get_shipment(db, shipment_id)
    return _build_shipment_detail(s)


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices/", response_model=List[InvoiceRead])
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invs = await crud.list_invoices(db, status=status, customer_id=customer_id)
    return [_build_invoice_read(inv) for inv in invs]


@router.post("/shipments/{shipment_id}/invoice", response_model=InvoiceDetailRead, status_code=201)
async def create_invoice_from_shipment(
    shipment_id: uuid.UUID,
    body: InvoiceFromShipmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = await crud.get_shipment(db, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    inv = await svc.invoice_from_shipment(
        db, s,
        invoice_no=body.invoice_no,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        user_id=current_user.id,
        notes=body.notes,
    )
    await db.commit()
    inv = await crud.get_invoice(db, inv.id)
    return _build_invoice_detail(inv)


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetailRead)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inv = await crud.get_invoice(db, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _build_invoice_detail(inv)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentRead, status_code=201)
async def record_payment(
    invoice_id: uuid.UUID,
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inv = await crud.get_invoice(db, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    payment = await svc.record_payment(
        db, inv,
        amount=body.amount,
        payment_date=body.payment_date,
        reference=body.reference,
        notes=body.notes,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(payment)
    return payment


# ── M-Pesa ────────────────────────────────────────────────────────────────────

@router.post("/orders/{so_id}/mpesa/initiate", response_model=MpesaTransactionRead, status_code=201)
async def initiate_mpesa_payment(
    so_id: uuid.UUID,
    body: MpesaPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    tx = await mpesa_svc.initiate_payment(db, so, body.phone_number, body.amount, current_user.id)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.post("/mpesa/callback", response_model=dict)
async def mpesa_callback(
    body: MpesaCallbackPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives payment confirmation from Safaricom Daraja.
    This endpoint must be publicly reachable (no auth header required by Safaricom).
    """
    tx = await mpesa_svc.handle_callback(
        db,
        checkout_request_id=body.checkout_request_id,
        result_code=body.result_code,
        result_description=body.result_description,
        mpesa_receipt_number=body.mpesa_receipt_number,
        amount=body.amount,
    )

    # If payment succeeded, recalculate full/partial status using SO total
    if tx.status.value == "completed":
        so = await crud.get_so(db, tx.so_id)
        if so and so.lines:
            so_total = sum(
                l.ordered_quantity * l.unit_price * (1 - l.discount_pct) * (1 + l.tax_rate)
                for l in so.lines
            )
            from decimal import Decimal as D
            await mpesa_svc.recalculate_payment_status(db, so, D(str(so_total)))

    await db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/orders/{so_id}/mpesa/transactions", response_model=List[MpesaTransactionRead])
async def list_mpesa_transactions(
    so_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    so = await crud.get_so(db, so_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    txns = await crud.get_mpesa_transactions(db, so_id)
    return txns


# ── Reports & Dashboard ───────────────────────────────────────────────────────

@router.post("/invoices/sync-overdue", response_model=dict)
async def sync_overdue(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await svc.sync_overdue_invoices(db)
    await db.commit()
    return {"updated": count}


@router.get("/reports/outstanding", response_model=List[OutstandingInvoiceRow])
async def outstanding_invoices(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invs = await crud.list_invoices(
        db,
        status=None,
        customer_id=None,
    )
    rows = []
    from datetime import date as date_cls
    today = date_cls.today()
    for inv in invs:
        if inv.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            continue
        outstanding = max(inv.total_amount - inv.paid_amount, Decimal("0"))
        delta = (today - inv.due_date).days
        days_overdue = delta if delta > 0 else None
        rows.append(OutstandingInvoiceRow(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            customer_name=inv.customer.name if inv.customer else "",
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            total_amount=inv.total_amount,
            paid_amount=inv.paid_amount,
            outstanding_balance=outstanding,
            days_overdue=days_overdue,
            status=inv.status,
        ))
    rows.sort(key=lambda r: (r.days_overdue is None, -(r.days_overdue or 0)))
    return rows


@router.get("/reports/summary", response_model=SalesSummary)
async def sales_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sos = await crud.list_sos(db)
    invs = await crud.list_invoices(db)

    total_orders = len(sos)
    confirmed_orders = sum(
        1 for so in sos
        if so.status not in (SOStatus.DRAFT, SOStatus.CANCELLED)
    )
    total_order_value = sum(
        sum(
            l.ordered_quantity * l.unit_price * (1 - l.discount_pct) * (1 + l.tax_rate)
            for l in so.lines
        )
        for so in sos
        if so.status not in (SOStatus.CANCELLED,)
    ) or Decimal("0")

    active_invs = [i for i in invs if i.status != InvoiceStatus.CANCELLED]
    total_invoiced = sum(i.total_amount for i in active_invs) or Decimal("0")
    total_collected = sum(i.paid_amount for i in active_invs) or Decimal("0")
    outstanding = max(total_invoiced - total_collected, Decimal("0"))
    overdue_count = sum(1 for i in active_invs if i.status == InvoiceStatus.OVERDUE)

    return SalesSummary(
        total_orders=total_orders,
        confirmed_orders=confirmed_orders,
        total_order_value=Decimal(str(total_order_value)).quantize(Decimal("0.01")),
        total_invoiced=Decimal(str(total_invoiced)).quantize(Decimal("0.01")),
        total_collected=Decimal(str(total_collected)).quantize(Decimal("0.01")),
        outstanding_balance=Decimal(str(outstanding)).quantize(Decimal("0.01")),
        overdue_invoices=overdue_count,
    )


# ── Marketing-aware sales analytics ───────────────────────────────────────────

from typing import Dict, Any
from sqlalchemy import func as sqlfunc


@router.get("/analytics/by-source", response_model=list)
async def sales_by_source(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Order count and value by OrderSource — surfaces ecommerce vs field-sales vs manual.
    Attribution-ready: shows which channel drives most revenue.
    """
    rows = await db.execute(
        select(
            SalesOrder.source,
            sqlfunc.count(SalesOrder.id).label("order_count"),
        )
        .group_by(SalesOrder.source)
        .order_by(sqlfunc.count(SalesOrder.id).desc())
    )
    return [
        {
            "source": r.source.value if hasattr(r.source, "value") else str(r.source),
            "order_count": r.order_count,
        }
        for r in rows.all()
    ]


@router.get("/analytics/by-segment", response_model=list)
async def sales_by_segment(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Order count grouped by customer segment tag — supports CRM segment performance tracking.
    """
    from app.models.sales import Customer
    rows = await db.execute(
        select(
            Customer.segment,
            Customer.channel,
            sqlfunc.count(SalesOrder.id).label("order_count"),
        )
        .join(Customer, SalesOrder.customer_id == Customer.id)
        .where(Customer.segment.isnot(None))
        .group_by(Customer.segment, Customer.channel)
        .order_by(sqlfunc.count(SalesOrder.id).desc())
    )
    return [
        {
            "segment": r.segment,
            "channel": r.channel.value if hasattr(r.channel, "value") else str(r.channel),
            "order_count": r.order_count,
        }
        for r in rows.all()
    ]


@router.get("/analytics/by-campaign", response_model=list)
async def sales_by_campaign(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Order count and campaign attribution visibility.
    Links SalesOrder.campaign_id back to campaign names from the marketing module.
    """
    from app.models.marketing import Campaign
    rows = await db.execute(
        select(
            SalesOrder.campaign_id,
            Campaign.campaign_name,
            Campaign.campaign_type,
            sqlfunc.count(SalesOrder.id).label("order_count"),
        )
        .join(Campaign, SalesOrder.campaign_id == Campaign.id, isouter=True)
        .where(SalesOrder.campaign_id.isnot(None))
        .group_by(SalesOrder.campaign_id, Campaign.campaign_name, Campaign.campaign_type)
        .order_by(sqlfunc.count(SalesOrder.id).desc())
    )
    return [
        {
            "campaign_id": str(r.campaign_id),
            "campaign_name": r.campaign_name,
            "campaign_type": r.campaign_type.value if hasattr(r.campaign_type, "value") else str(r.campaign_type),
            "order_count": r.order_count,
        }
        for r in rows.all()
    ]
