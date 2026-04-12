from __future__ import annotations
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sales import (
    Customer, SalesOrder, SOLine, Shipment, ShipmentLine,
    Invoice, InvoiceLine, Payment, SOStatus, ShipmentStatus, InvoiceStatus,
    MpesaTransaction,
)


# ── Customers ─────────────────────────────────────────────────────────────────

async def list_customers(db: AsyncSession, active_only: bool = False) -> List[Customer]:
    q = select(Customer)
    if active_only:
        q = q.where(Customer.is_active == True)  # noqa: E712
    q = q.order_by(Customer.name)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_customer(db: AsyncSession, customer_id: uuid.UUID) -> Optional[Customer]:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def create_customer(db: AsyncSession, data: dict) -> Customer:
    c = Customer(**data)
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


# ── Sales Orders ──────────────────────────────────────────────────────────────

async def list_sos(
    db: AsyncSession,
    status: Optional[SOStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> List[SalesOrder]:
    q = select(SalesOrder).options(
        selectinload(SalesOrder.customer),
        selectinload(SalesOrder.warehouse),
        selectinload(SalesOrder.lines).selectinload(SOLine.product),
    )
    if status:
        q = q.where(SalesOrder.status == status)
    if customer_id:
        q = q.where(SalesOrder.customer_id == customer_id)
    q = q.order_by(SalesOrder.order_date.desc(), SalesOrder.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_so(db: AsyncSession, so_id: uuid.UUID) -> Optional[SalesOrder]:
    result = await db.execute(
        select(SalesOrder)
        .options(
            selectinload(SalesOrder.customer),
            selectinload(SalesOrder.warehouse),
            selectinload(SalesOrder.created_by),
            selectinload(SalesOrder.confirmed_by),
            selectinload(SalesOrder.lines).selectinload(SOLine.product),
            selectinload(SalesOrder.shipments).selectinload(Shipment.lines),
            selectinload(SalesOrder.invoices),
        )
        .where(SalesOrder.id == so_id)
    )
    return result.scalar_one_or_none()


async def create_so(db: AsyncSession, data: dict, created_by_id: uuid.UUID) -> SalesOrder:
    lines_data = data.pop("lines", [])
    so = SalesOrder(**data, created_by_id=created_by_id)
    db.add(so)
    await db.flush()
    for ld in lines_data:
        db.add(SOLine(so_id=so.id, **ld))
    await db.flush()
    await db.refresh(so)
    return so


async def get_so_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[SOLine]:
    result = await db.execute(select(SOLine).where(SOLine.id == line_id))
    return result.scalar_one_or_none()


# ── Shipments ─────────────────────────────────────────────────────────────────

async def list_shipments(
    db: AsyncSession,
    status: Optional[ShipmentStatus] = None,
    so_id: Optional[uuid.UUID] = None,
) -> List[Shipment]:
    q = select(Shipment).options(
        selectinload(Shipment.so).selectinload(SalesOrder.customer),
        selectinload(Shipment.warehouse),
        selectinload(Shipment.lines),
    )
    if status:
        q = q.where(Shipment.status == status)
    if so_id:
        q = q.where(Shipment.so_id == so_id)
    q = q.order_by(Shipment.scheduled_date, Shipment.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_shipment(db: AsyncSession, shipment_id: uuid.UUID) -> Optional[Shipment]:
    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.so).selectinload(SalesOrder.customer),
            selectinload(Shipment.warehouse),
            selectinload(Shipment.created_by),
            selectinload(Shipment.dispatched_by),
            selectinload(Shipment.lines).selectinload(ShipmentLine.product),
            selectinload(Shipment.lines).selectinload(ShipmentLine.lot),
            selectinload(Shipment.invoice),
        )
        .where(Shipment.id == shipment_id)
    )
    return result.scalar_one_or_none()


async def create_shipment(db: AsyncSession, data: dict, created_by_id: uuid.UUID) -> Shipment:
    lines_data = data.pop("lines", [])
    s = Shipment(**data, created_by_id=created_by_id)
    db.add(s)
    await db.flush()
    for ld in lines_data:
        db.add(ShipmentLine(shipment_id=s.id, **ld))
    await db.flush()
    await db.refresh(s)
    return s


async def get_shipment_line(db: AsyncSession, line_id: uuid.UUID) -> Optional[ShipmentLine]:
    result = await db.execute(
        select(ShipmentLine).options(
            selectinload(ShipmentLine.product),
            selectinload(ShipmentLine.lot),
        ).where(ShipmentLine.id == line_id)
    )
    return result.scalar_one_or_none()


# ── Invoices ──────────────────────────────────────────────────────────────────

async def list_invoices(
    db: AsyncSession,
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> List[Invoice]:
    q = select(Invoice).options(
        selectinload(Invoice.customer),
        selectinload(Invoice.so),
        selectinload(Invoice.payments),
    )
    if status:
        q = q.where(Invoice.status == status)
    if customer_id:
        q = q.where(Invoice.customer_id == customer_id)
    q = q.order_by(Invoice.due_date, Invoice.invoice_date.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_mpesa_transactions(db: AsyncSession, so_id: uuid.UUID) -> List[MpesaTransaction]:
    result = await db.execute(
        select(MpesaTransaction)
        .where(MpesaTransaction.so_id == so_id)
        .order_by(MpesaTransaction.created_at)
    )
    return list(result.scalars().all())


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Optional[Invoice]:
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.customer),
            selectinload(Invoice.so),
            selectinload(Invoice.shipment),
            selectinload(Invoice.created_by),
            selectinload(Invoice.lines).selectinload(InvoiceLine.product),
            selectinload(Invoice.payments),
        )
        .where(Invoice.id == invoice_id)
    )
    return result.scalar_one_or_none()
