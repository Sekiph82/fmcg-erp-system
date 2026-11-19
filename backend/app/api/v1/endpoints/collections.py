"""Customer collections (M38.S02.T004): money received by reps/collectors or entered by the office.

The office Collections screen (`/dashboard/sales/collections`) and the field app share these records. A collection is
PENDING until finance confirms it; confirming an invoice-linked collection posts a payment to that invoice (the
normal invoice payment rules apply). Only PENDING collections can be cancelled or marked bounced (cheques).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.field_ops import CashCollection

router = APIRouter()
VIEW = ("sales.view", "finance.view")
FINANCE = ("finance.edit", "finance.approve")
APPROVE = ("finance.approve",)  # confirming money posts it to the ledger
METHOD_TO_PAYMENT = {"CASH": "cash", "MPESA": "mpesa", "BANK_TRANSFER": "bank", "CHEQUE": "bank"}


class CollectionCreate(BaseModel):
    collection_no: Optional[str] = Field(default=None, max_length=40)
    customer_id: uuid.UUID
    sales_order_id: Optional[uuid.UUID] = None
    invoice_id: uuid.UUID          # v1: every collection settles an invoice
    rep_id: Optional[uuid.UUID] = None
    collection_date: date
    method: str = Field(pattern=r"^(CASH|MPESA|BANK_TRANSFER|CHEQUE)$")
    amount: Decimal = Field(gt=0, le=Decimal("100000000"), decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=10)
    reference: Optional[str] = Field(default=None, max_length=100)
    mpesa_code: Optional[str] = Field(default=None, pattern=r"^[A-Z0-9]{8,12}$")
    mpesa_phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{9,15}$")
    notes: Optional[str] = Field(default=None, max_length=1000)


async def _out(db: AsyncSession, rows) -> list:
    from app.models.field_sales import SalesRep
    from app.models.sales import Customer, Invoice, SalesOrder

    async def names(model, ids, attr):
        ids = {i for i in ids if i}
        return {r.id: getattr(r, attr) for r in (await db.execute(select(model).where(model.id.in_(ids)))).scalars()} if ids else {}

    cust = await names(Customer, [c.customer_id for c in rows], "name")
    inv = await names(Invoice, [c.invoice_id for c in rows], "invoice_no")
    so = await names(SalesOrder, [c.sales_order_id for c in rows], "order_no")
    rep = await names(SalesRep, [c.rep_id for c in rows], "name")
    return [{"id": str(c.id), "collection_no": c.collection_no, "customer_id": str(c.customer_id),
             "customer_name": cust.get(c.customer_id), "sales_order_id": str(c.sales_order_id) if c.sales_order_id else None,
             "order_no": so.get(c.sales_order_id), "invoice_id": str(c.invoice_id) if c.invoice_id else None,
             "invoice_no": inv.get(c.invoice_id), "rep_id": str(c.rep_id) if c.rep_id else None, "rep_name": rep.get(c.rep_id),
             "collection_date": str(c.collection_date), "method": c.method, "amount": float(c.amount), "currency": c.currency,
             "reference": c.reference, "mpesa_code": c.mpesa_code, "mpesa_phone": c.mpesa_phone, "status": c.status,
             "notes": c.notes, "gps": [float(c.gps_lat), float(c.gps_lng)] if c.gps_lat is not None and c.gps_lng is not None else None,
             "reconciled_at": c.reconciled_at.isoformat() if c.reconciled_at else None,
             "created_at": c.created_at.isoformat() if c.created_at else None} for c in rows]


async def _locked(db: AsyncSession, collection_id: uuid.UUID) -> CashCollection:
    c = (await db.execute(select(CashCollection).where(CashCollection.id == collection_id).with_for_update())).scalar_one_or_none()
    if c is None:
        raise HTTPException(404, "Collection not found")
    return c


@router.get("/", dependencies=[Depends(require_any_permission(VIEW))])
async def list_collections(customer_id: Optional[uuid.UUID] = None, status: Optional[str] = Query(None, max_length=20),
                           method: Optional[str] = Query(None, max_length=20), from_date: Optional[date] = None,
                           to_date: Optional[date] = None, db: AsyncSession = Depends(get_db)):
    q = select(CashCollection)
    if customer_id:
        q = q.where(CashCollection.customer_id == customer_id)
    if status:
        q = q.where(CashCollection.status == status)
    if method:
        q = q.where(CashCollection.method == method)
    if from_date:
        q = q.where(CashCollection.collection_date >= from_date)
    if to_date:
        q = q.where(CashCollection.collection_date <= to_date)
    rows = (await db.execute(q.order_by(CashCollection.collection_date.desc(), CashCollection.created_at.desc()).limit(500))).scalars().all()
    return await _out(db, rows)


@router.get("/{collection_id}", dependencies=[Depends(require_any_permission(VIEW))])
async def get_collection(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(CashCollection, collection_id)
    if c is None:
        raise HTTPException(404, "Collection not found")
    return (await _out(db, [c]))[0]


@router.post("/", status_code=201, dependencies=[Depends(require_any_permission(("sales.create", "finance.create")))])
async def create_collection(body: CollectionCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.sales import Customer, Invoice

    customer = await db.get(Customer, body.customer_id)
    if customer is None:
        raise HTTPException(422, "Customer not found")
    if body.method == "MPESA" and not body.mpesa_code:
        raise HTTPException(422, "An M-Pesa collection needs the M-Pesa confirmation code.")
    from app.api.v1.endpoints.field_app import open_to_collect

    inv = (await db.execute(select(Invoice).where(Invoice.id == body.invoice_id).with_for_update())).scalar_one_or_none()
    if inv is None or inv.customer_id != customer.id:
        raise HTTPException(422, "The invoice does not belong to this customer.")
    if body.currency and body.currency != inv.currency:
        raise HTTPException(422, f"The invoice is in {inv.currency}; record the collection in that currency.")
    if body.amount > await open_to_collect(db, inv):
        raise HTTPException(422, "The amount is more than the invoice's open balance (including collections awaiting confirmation).")
    so_id = body.sales_order_id or inv.so_id
    c = CashCollection(collection_no=body.collection_no or f"COL-{date.today():%y%m%d}-{secrets.token_hex(4).upper()}",
                       customer_id=customer.id, invoice_id=body.invoice_id, sales_order_id=so_id, rep_id=body.rep_id,
                       collected_by_id=user.id, collection_date=body.collection_date, method=body.method, amount=body.amount,
                       currency=inv.currency, reference=body.reference, mpesa_code=body.mpesa_code,
                       mpesa_phone=body.mpesa_phone, status="PENDING", notes=body.notes)
    db.add(c)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "This collection number or M-Pesa code is already recorded.")
    return (await _out(db, [c]))[0]


@router.post("/{collection_id}/confirm", dependencies=[Depends(require_any_permission(APPROVE))])
async def confirm(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Finance confirms the money arrived (a cheque: after it cleared) and it becomes a payment on the invoice.
    The person who recorded the collection cannot confirm it."""
    from app.models.sales import Invoice
    from app.services import sales_service

    c = await _locked(db, collection_id)
    # a cheque is posted only once it has cleared: PENDING → DEPOSITED → confirm (or bounce); never posted then reversed
    if c.method == "CHEQUE" and c.status != "DEPOSITED":
        raise HTTPException(409, "Record the cheque as deposited first; confirm it only after the bank has cleared it.")
    if c.status not in ("PENDING", "DEPOSITED"):
        raise HTTPException(409, f"Collection is {c.status}.")
    if c.collected_by_id == user.id:
        raise HTTPException(403, "You recorded this collection; another finance user must confirm it.")
    if c.invoice_id is None:
        raise HTTPException(409, "This collection is not linked to an invoice; link it or cancel it.")
    if c.invoice_id:
        inv = await db.get(Invoice, c.invoice_id)
        if inv.currency != c.currency:
            raise HTTPException(409, f"Currency mismatch: collection {c.currency}, invoice {inv.currency}.")
        payment = await sales_service.record_payment(
            db, inv, amount=Decimal(c.amount), payment_date=c.collection_date,
            reference=c.mpesa_code or c.reference or c.collection_no, notes=f"Collection {c.collection_no}",
            user_id=user.id, method=METHOD_TO_PAYMENT[c.method])
        c.payment_id = payment.id
    c.status, c.confirmed_by_id, c.confirmed_at = "CONFIRMED", user.id, datetime.now(timezone.utc)
    await db.commit()
    return (await _out(db, [c]))[0]


@router.post("/{collection_id}/reconcile", dependencies=[Depends(require_any_permission(FINANCE))])
async def reconcile(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await _locked(db, collection_id)
    if c.status != "CONFIRMED":
        raise HTTPException(409, "Only confirmed collections can be reconciled.")
    c.status, c.reconciled_at = "RECONCILED", datetime.now(timezone.utc)
    await db.commit()
    return (await _out(db, [c]))[0]


@router.post("/{collection_id}/deposit", dependencies=[Depends(require_any_permission(FINANCE))])
async def deposit(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """A cheque handed in to the bank; it is confirmed (posted) only when the bank clears it."""
    c = await _locked(db, collection_id)
    if c.status != "PENDING" or c.method != "CHEQUE":
        raise HTTPException(409, "Only pending cheques can be deposited.")
    c.status = "DEPOSITED"
    await db.commit()
    return (await _out(db, [c]))[0]


@router.post("/{collection_id}/bounce", dependencies=[Depends(require_any_permission(FINANCE))])
async def bounce(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await _locked(db, collection_id)
    if c.status not in ("PENDING", "DEPOSITED") or c.method != "CHEQUE":
        raise HTTPException(409, "Only cheques that are not yet confirmed can be marked bounced.")
    c.status = "BOUNCED"
    await db.commit()
    return (await _out(db, [c]))[0]


@router.post("/{collection_id}/cancel", dependencies=[Depends(require_any_permission(FINANCE))])
async def cancel(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await _locked(db, collection_id)
    if c.status not in ("PENDING", "DEPOSITED"):
        raise HTTPException(409, "Only collections that are not yet confirmed can be cancelled.")
    c.status = "CANCELLED"
    await db.commit()
    return (await _out(db, [c]))[0]
