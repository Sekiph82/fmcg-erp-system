"""Field app (M38.S02/S03): one mobile screen per field role, scoped to the signed-in employee.

* Sales rep / pre-seller / moto rider (a SalesRep linked to the user): today's route stops, visits with GPS and outlet
  photo, order capture with server prices (DRAFT sales order, source FIELD_SALES), open invoices, collections
  (cash / M-Pesa code / cheque, PENDING until finance confirms) and M-Pesa STK requests.
* Delivery driver (DeliveryTrip.driver_user_id): my trips, start/finish, proof of delivery with signature, photo and
  GPS, failed delivery with reason.
* Field controller (permission field.audit): outlet audits with a fixed checklist, score, photos, GPS.
* Supervisor (permission field.supervise): compliance per rep (coverage, orders, collections, audit scores).

Every action that the device may retry carries a client_ref, so a resend never creates a second record.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.core.deps import get_current_user
from app.db.session import get_db

router = APIRouter()

CHECKLIST = (  # outlet audit items (v1); score = % OK
    ("stock_available", "Our core products are in stock"),
    ("shelf_share", "Products are on the agreed shelf / planogram"),
    ("price_tags", "Correct price tags are displayed"),
    ("posm", "Posters / branded material in place"),
    ("fridge", "Branded fridge is clean, ours only, switched on"),
    ("freshness", "No expired or damaged stock on shelf"),
    ("rep_visit", "Outlet confirms our rep visits on schedule"),
)
OPEN_INVOICE = ("ISSUED", "PARTIALLY_PAID", "OVERDUE")


# ── schemas ───────────────────────────────────────────────────────────────────

class GPS(BaseModel):
    lat: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    lng: Optional[Decimal] = Field(default=None, ge=-180, le=180)


class VisitIn(GPS):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    customer_id: uuid.UUID
    outcome: str = Field(pattern=r"^(ORDERED|NO_ORDER|CUSTOMER_CLOSED|CREDIT_HOLD|NOT_FOUND)$")
    notes: Optional[str] = Field(default=None, max_length=1000)


class LineIn(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"))


class OrderIn(BaseModel):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    customer_id: uuid.UUID
    requested_delivery_date: date
    payment_method: str = Field(default="cash", pattern=r"^(cash|mpesa|credit|bank_transfer)$")
    visit_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    lines: List[LineIn] = Field(min_length=1, max_length=200)


class CollectionIn(GPS):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    customer_id: uuid.UUID
    invoice_id: uuid.UUID          # v1: every collection settles an invoice (on-account credit is not booked yet)
    method: str = Field(pattern=r"^(CASH|MPESA|CHEQUE|BANK_TRANSFER)$")
    amount: Decimal = Field(gt=0, le=Decimal("100000000"), decimal_places=2)
    mpesa_code: Optional[str] = Field(default=None, pattern=r"^[A-Z0-9]{8,12}$")
    mpesa_phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{9,15}$")
    reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


class StkIn(BaseModel):
    phone: str = Field(pattern=r"^(\+?254|0)[17][0-9]{8}$")
    amount: Decimal = Field(gt=0, le=Decimal("250000"), decimal_places=2)


class FailIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AnswerIn(BaseModel):
    key: str
    ok: bool
    note: Optional[str] = Field(default=None, max_length=500)


class AuditIn(GPS):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    customer_id: uuid.UUID
    answers: List[AnswerIn]
    notes: Optional[str] = Field(default=None, max_length=2000)


# ── helpers ───────────────────────────────────────────────────────────────────

async def _my_rep(db: AsyncSession, user):
    from app.models.field_sales import SalesRep

    return (await db.execute(select(SalesRep).where(SalesRep.user_id == user.id, SalesRep.is_active.is_(True))
                             .limit(1))).scalar_one_or_none()


async def _rep_or_403(db: AsyncSession, user):
    rep = await _my_rep(db, user)
    if rep is None:
        raise HTTPException(403, "You are not set up as a field sales rep. Ask your sales manager to link your login.")
    return rep


async def _route_stops(db: AsyncSession, rep):
    from app.models.field_sales import RouteStop, SalesRoute

    return (await db.execute(select(RouteStop, SalesRoute).join(SalesRoute, SalesRoute.id == RouteStop.route_id)
                             .where(SalesRoute.assigned_rep_id == rep.id, SalesRoute.is_active.is_(True))
                             .order_by(SalesRoute.code, RouteStop.stop_sequence))).all()


async def _my_customer(db: AsyncSession, rep, customer_id: uuid.UUID):
    """The customer if it is on one of the rep's routes (else 403); returns (customer, route_id)."""
    from app.models.sales import Customer

    for stop, route in await _route_stops(db, rep):
        if stop.customer_id == customer_id:
            customer = await db.get(Customer, customer_id)
            if customer is None or not customer.is_active:
                break
            return customer, route.id
    raise HTTPException(403, "This customer is not on your route.")


def _gps(body):
    return getattr(body, "lat", None), getattr(body, "lng", None)


async def open_to_collect(db: AsyncSession, inv) -> Decimal:
    """Invoice balance minus collections already recorded and awaiting finance confirmation."""
    from app.models.field_ops import CashCollection

    pending = (await db.execute(select(func.coalesce(func.sum(CashCollection.amount), 0)).where(
        CashCollection.invoice_id == inv.id, CashCollection.status.in_(("PENDING", "DEPOSITED"))))).scalar_one()
    return Decimal(inv.total_amount) - Decimal(inv.paid_amount) - Decimal(pending)


def _no(prefix: str) -> str:
    return f"{prefix}-{date.today():%y%m%d}-{secrets.token_hex(4).upper()}"


async def _store(file: UploadFile) -> str:
    """Store an image through the document storage service; returns the opaque key. Infected files are refused."""
    from app.services.document_storage_service import get_document_storage, scan_document

    if not (file.filename or "").lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(415, "Photos and signatures must be JPG or PNG images.")
    storage = get_document_storage()
    stored = await storage.store_upload(file, max_bytes=8 * 1024 * 1024)
    from app.core.config import settings

    scan = (await scan_document(storage.path_for(stored.storage_key))).status
    if scan == "INFECTED" or (scan == "SCAN_ERROR" and settings.DOCUMENT_CLAMAV_HOST.strip()):
        storage.delete(stored.storage_key)
        raise HTTPException(422, "The file was rejected by the malware scanner (or the scanner is unavailable); try again.")
    return stored.storage_key


def _perm(user, code: str):
    if not has_permission(user, code):
        raise HTTPException(403, f"Missing permission {code}")


async def _existing(db: AsyncSession, model, client_ref: str):
    return (await db.execute(select(model).where(model.client_ref == client_ref))).scalar_one_or_none()


async def _replay(db: AsyncSession, model, client_ref: str, owner_attr: str, owner_id):
    """After an IntegrityError: the earlier record for this client_ref if it is the caller's own, else 409."""
    existing = await _existing(db, model, client_ref)
    if existing is None or getattr(existing, owner_attr) != owner_id:
        raise HTTPException(409, "This was already recorded, or conflicts with an existing record.")
    return existing


# ── who am I ──────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.delivery import DeliveryTrip
    from app.models.van_sales import Van

    rep = await _my_rep(db, user)
    van = (await db.execute(select(Van).where(Van.driver_id == user.id).limit(1))).scalar_one_or_none()
    driver = (await db.execute(select(func.count()).select_from(DeliveryTrip).where(
        DeliveryTrip.driver_user_id == user.id, DeliveryTrip.trip_date >= date.today() - timedelta(days=1)))).scalar_one()
    return {
        "full_name": user.full_name or user.username,
        "rep": {"id": str(rep.id), "code": rep.code, "name": rep.name, "vehicle_type": rep.vehicle_type.value,
                "region": rep.region} if rep else None,
        "van": {"id": str(van.id), "van_code": van.van_code} if van else None,
        "is_driver": driver > 0,
        "can_audit": has_permission(user, "field.audit"),
        "can_supervise": has_permission(user, "field.supervise"),
    }


# ── rep: my day ───────────────────────────────────────────────────────────────

@router.get("/today")
async def today(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_sales import DailyTarget, VisitLog
    from app.models.sales import Customer, Invoice, InvoiceStatus, OrderSource, SalesOrder, SOLine, SOStatus

    rep = await _rep_or_403(db, user)
    stops = await _route_stops(db, rep)
    ids = [s.customer_id for s, _ in stops]
    customers = {c.id: c for c in (await db.execute(select(Customer).where(Customer.id.in_(ids)))).scalars()} if ids else {}
    visits = {v.customer_id: v for v in (await db.execute(select(VisitLog).where(
        VisitLog.rep_id == rep.id, VisitLog.visit_date == date.today()).order_by(VisitLog.visited_at))).scalars()}
    balances = dict((await db.execute(select(Invoice.customer_id, func.sum(Invoice.total_amount - Invoice.paid_amount)).where(
        Invoice.customer_id.in_(ids), Invoice.status.in_([InvoiceStatus[s] for s in OPEN_INVOICE]))
        .group_by(Invoice.customer_id))).all()) if ids else {}
    sold = (await db.execute(select(func.coalesce(func.sum(SOLine.ordered_quantity * SOLine.unit_price), 0)).join(
        SalesOrder, SalesOrder.id == SOLine.so_id).where(SalesOrder.sales_rep_id == rep.id, SalesOrder.order_date == date.today(),
                                                         SalesOrder.source == OrderSource.FIELD_SALES,
                                                         SalesOrder.status != SOStatus.CANCELLED))).scalar_one()
    target = (await db.execute(select(DailyTarget).where(DailyTarget.rep_id == rep.id, DailyTarget.target_date == date.today())
                               .limit(1))).scalar_one_or_none()
    out = []
    for stop, route in stops:
        c = customers.get(stop.customer_id)
        if c is None or not c.is_active:
            continue
        v = visits.get(c.id)
        out.append({"customer_id": str(c.id), "name": c.name, "contact": c.contact_person, "phone": c.phone,
                    "address": c.delivery_address or c.address, "route": route.name, "sequence": stop.stop_sequence,
                    "lat": float(stop.lat_override or c.gps_lat) if (stop.lat_override or c.gps_lat) is not None else None,
                    "lng": float(stop.lng_override or c.gps_lng) if (stop.lng_override or c.gps_lng) is not None else None,
                    "visit": {"id": str(v.id), "outcome": v.outcome.value, "order_id": str(v.order_id) if v.order_id else None}
                    if v else None,
                    "open_balance": float(balances.get(c.id) or 0), "currency": c.currency})
    return {"date": date.today().isoformat(), "stops": out, "visited": sum(1 for s in out if s["visit"]),
            "sold_today": float(sold), "target_amount": float(target.target_amount) if target else None}


@router.post("/visits", status_code=201)
async def log_visit(body: VisitIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_sales import VisitLog, VisitOutcome

    rep = await _rep_or_403(db, user)
    if (existing := await _existing(db, VisitLog, body.client_ref)) is not None:
        if existing.rep_id != rep.id:
            raise HTTPException(409, "Duplicate reference.")
        return {"id": str(existing.id), "duplicate": True}
    _, route_id = await _my_customer(db, rep, body.customer_id)
    lat, lng = _gps(body)
    v = VisitLog(rep_id=rep.id, customer_id=body.customer_id, route_id=route_id, visit_date=date.today(),
                 visited_at=datetime.now(timezone.utc), outcome=VisitOutcome(body.outcome), gps_lat=lat, gps_lng=lng,
                 notes=body.notes, client_ref=body.client_ref)
    db.add(v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"id": str((await _replay(db, VisitLog, body.client_ref, "rep_id", rep.id)).id), "duplicate": True}
    return {"id": str(v.id), "duplicate": False}


@router.post("/visits/{visit_id}/photo")
async def visit_photo(visit_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                      user=Depends(get_current_user)):
    from app.models.field_sales import VisitLog

    rep = await _rep_or_403(db, user)
    v = await db.get(VisitLog, visit_id)
    if v is None or v.rep_id != rep.id:
        raise HTTPException(404, "Visit not found")
    v.photo_key = await _store(file)
    await db.commit()
    return {"ok": True}


@router.get("/catalog")
async def catalog(customer_id: uuid.UUID, search: Optional[str] = Query(None, max_length=100),
                  db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.master import Product
    from app.services.customer_pricing import unit_price

    rep = await _rep_or_403(db, user)
    customer, _ = await _my_customer(db, rep, customer_id)
    q = select(Product).where(Product.is_active.is_(True))
    if search:
        q = q.where(or_(Product.name.ilike(f"%{search.strip()}%"), Product.sku.ilike(f"%{search.strip()}%")))
    items = []
    for p in (await db.execute(q.order_by(Product.name).limit(60))).scalars():
        price = await unit_price(db, p, customer, None, Decimal("1"))
        if price is not None:
            items.append({"product_id": str(p.id), "sku": p.sku, "name": p.name, "uom": p.uom.value, "unit_price": float(price)})
    return {"currency": customer.currency, "items": items}


@router.post("/orders", status_code=201)
async def place_order(body: OrderIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_sales import VisitLog, VisitOutcome
    from app.models.master import Product
    from app.models.sales import OrderSource, PaymentMethod, SalesOrder, SOLine, SOStatus
    from app.services.commercial_access_service import inherit_commercial_scope
    from app.services.customer_pricing import unit_price

    rep = await _rep_or_403(db, user)
    offline_id = f"field:{body.client_ref}"
    existing = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == offline_id))).scalar_one_or_none()
    if existing is not None:
        if existing.sales_rep_id != rep.id:
            raise HTTPException(409, "Duplicate reference.")
        return {"id": str(existing.id), "order_no": existing.order_no, "duplicate": True}
    customer, route_id = await _my_customer(db, rep, body.customer_id)
    if body.requested_delivery_date < date.today():
        raise HTTPException(422, "The delivery date cannot be in the past.")
    if len({l.product_id for l in body.lines}) != len(body.lines):
        raise HTTPException(422, "Each product may appear only once.")
    priced = []
    for line in body.lines:
        product = await db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise HTTPException(422, "A product in the order is not available.")
        price = await unit_price(db, product, customer, None, line.quantity)
        if price is None:
            raise HTTPException(422, f"{product.name} has no price for this customer.")
        priced.append((product, line.quantity, price))
    so = SalesOrder(order_no=_no("FS"), customer_id=customer.id, order_date=date.today(),
                    requested_delivery_date=body.requested_delivery_date, status=SOStatus.DRAFT, currency=customer.currency,
                    payment_method=PaymentMethod(body.payment_method), source=OrderSource.FIELD_SALES, sales_rep_id=rep.id,
                    route_id=route_id, offline_id=offline_id, offline_synced_at=datetime.now(timezone.utc),
                    created_by_id=user.id, notes=body.notes)
    inherit_commercial_scope(so, customer)
    db.add(so)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == offline_id))).scalar_one_or_none()
        if existing is None or existing.sales_rep_id != rep.id:
            raise HTTPException(409, "The order could not be saved; please send it again.")
        return {"id": str(existing.id), "order_no": existing.order_no, "duplicate": True}
    so_lines = [SOLine(so_id=so.id, line_no=n, product_id=product.id, ordered_quantity=qty, unit=product.uom.value,
                       unit_price=price, cost_price=product.standard_cost, discount_pct=Decimal("0"))
                for n, (product, qty, price) in enumerate(priced, start=1)]
    db.add_all(so_lines)
    await db.flush()
    from app.services.shop_promotions import apply_to_order  # same list price for all; the shop's promotions on top

    promotions = await apply_to_order(db, so, customer)
    order_total = sum((l.ordered_quantity * l.unit_price * (1 - l.discount_pct) for l in so_lines), Decimal("0"))  # before commit expires the lines
    if body.visit_id:
        v = await db.get(VisitLog, body.visit_id)
        if v is not None and v.rep_id == rep.id and v.customer_id == customer.id:
            v.order_id, v.outcome = so.id, VisitOutcome.ORDERED
    await db.commit()
    from app.services.notifications_service import notify_new_order
    await notify_new_order(db, so, customer.name, "field")
    return {"id": str(so.id), "order_no": so.order_no, "currency": so.currency,
            "total": float(order_total), "promotions": promotions, "duplicate": False}


@router.get("/customers/{customer_id}/invoices")
async def open_invoices(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.sales import Invoice, InvoiceStatus

    rep = await _rep_or_403(db, user)
    await _my_customer(db, rep, customer_id)
    rows = (await db.execute(select(Invoice).where(Invoice.customer_id == customer_id,
                                                  Invoice.status.in_([InvoiceStatus[s] for s in OPEN_INVOICE]))
                             .order_by(Invoice.due_date))).scalars().all()
    return [{"id": str(i.id), "invoice_no": i.invoice_no, "due_date": str(i.due_date), "currency": i.currency,
             "total": float(i.total_amount), "outstanding": float(i.total_amount - i.paid_amount),
             "overdue": i.due_date < date.today()} for i in rows]


@router.post("/collections", status_code=201)
async def record_collection(body: CollectionIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_ops import CashCollection
    from app.models.sales import Invoice, InvoiceStatus

    rep = await _rep_or_403(db, user)
    if (existing := await _existing(db, CashCollection, body.client_ref)) is not None:
        if existing.collected_by_id != user.id:
            raise HTTPException(409, "Duplicate reference.")
        return {"id": str(existing.id), "collection_no": existing.collection_no, "duplicate": True}
    customer, _ = await _my_customer(db, rep, body.customer_id)
    if body.method == "MPESA" and not body.mpesa_code:
        raise HTTPException(422, "Enter the M-Pesa confirmation code from the customer's message.")
    inv = (await db.execute(select(Invoice).where(Invoice.id == body.invoice_id).with_for_update())).scalar_one_or_none()
    if inv is None or inv.customer_id != customer.id or inv.status.value not in OPEN_INVOICE:
        raise HTTPException(422, "The invoice is not an open invoice of this customer.")
    if body.amount > await open_to_collect(db, inv):
        raise HTTPException(422, "The amount is more than the invoice's open balance (including collections awaiting confirmation).")
    so_id = inv.so_id
    lat, lng = _gps(body)
    c = CashCollection(collection_no=_no("COL"), customer_id=customer.id, invoice_id=body.invoice_id, sales_order_id=so_id,
                       rep_id=rep.id, collected_by_id=user.id, collection_date=date.today(), method=body.method,
                       amount=body.amount, currency=inv.currency, reference=body.reference, mpesa_code=body.mpesa_code,
                       mpesa_phone=body.mpesa_phone, gps_lat=lat, gps_lng=lng, status="PENDING", client_ref=body.client_ref,
                       notes=body.notes)
    db.add(c)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _existing(db, CashCollection, body.client_ref)
        if existing is not None and existing.collected_by_id == user.id:
            return {"id": str(existing.id), "collection_no": existing.collection_no, "duplicate": True}
        raise HTTPException(409, "This M-Pesa code was already recorded.")
    return {"id": str(c.id), "collection_no": c.collection_no, "status": c.status, "duplicate": False}


@router.get("/collections")
async def my_collections(day: Optional[date] = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_ops import CashCollection
    from app.models.sales import Customer

    rows = (await db.execute(select(CashCollection, Customer.name).join(Customer, Customer.id == CashCollection.customer_id)
                             .where(CashCollection.collected_by_id == user.id,
                                    CashCollection.collection_date == (day or date.today()))
                             .order_by(CashCollection.created_at.desc()))).all()
    return [{"id": str(c.id), "collection_no": c.collection_no, "customer": name, "method": c.method,
             "amount": float(c.amount), "currency": c.currency, "status": c.status, "mpesa_code": c.mpesa_code}
            for c, name in rows]


@router.post("/invoices/{invoice_id}/stk", status_code=201)
async def stk_push(invoice_id: uuid.UUID, body: StkIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Ask the customer's phone to pay an invoice by M-Pesa (STK push on the invoice's order)."""
    from app.models.sales import Invoice, SalesOrder
    from app.services import mpesa_service

    rep = await _rep_or_403(db, user)
    inv = await db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Invoice not found")
    customer, _ = await _my_customer(db, rep, inv.customer_id)
    if inv.status.value not in OPEN_INVOICE:
        raise HTTPException(422, "This invoice is not open.")
    if body.amount > inv.total_amount - inv.paid_amount:
        raise HTTPException(422, "The amount is more than the invoice's open balance.")
    digits = lambda x: (x or "")[-9:]  # compare the national number (07.. / 2547..)
    if not customer.phone or digits(customer.phone) != digits(body.phone):
        raise HTTPException(422, "M-Pesa requests go only to the customer's registered phone number.")
    so = (await db.execute(select(SalesOrder).where(SalesOrder.id == inv.so_id).with_for_update())).scalar_one()
    if so.payment_method.value != "mpesa":
        raise HTTPException(422, "This order is not set up for M-Pesa payment; record the M-Pesa code instead.")
    tx = await mpesa_service.initiate_payment(db, so, body.phone, body.amount, user.id)
    await db.commit()
    return {"id": str(tx.id), "status": getattr(tx.status, "value", tx.status), "checkout_request_id": tx.mpesa_request_id}


# ── driver: my trips ──────────────────────────────────────────────────────────

async def _my_trip(db: AsyncSession, user, trip_id: uuid.UUID):
    from app.models.delivery import DeliveryTrip

    trip = await db.get(DeliveryTrip, trip_id)
    if trip is None or trip.driver_user_id != user.id:
        raise HTTPException(404, "Trip not found")
    return trip


async def _my_stop(db: AsyncSession, user, trip_order_id: uuid.UUID):
    from app.models.delivery import TripOrder

    to = (await db.execute(select(TripOrder).where(TripOrder.id == trip_order_id).with_for_update())).scalar_one_or_none()
    if to is None:
        raise HTTPException(404, "Stop not found")
    trip = await _my_trip(db, user, to.trip_id)
    return to, trip


@router.get("/trips")
async def my_trips(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.delivery import DeliveryTrip, TripOrder
    from app.models.sales import Customer, SalesOrder, Shipment

    trips = (await db.execute(select(DeliveryTrip).where(DeliveryTrip.driver_user_id == user.id,
                                                         DeliveryTrip.trip_date >= date.today() - timedelta(days=1))
                              .order_by(DeliveryTrip.trip_date, DeliveryTrip.trip_no))).scalars().all()
    out = []
    for t in trips:
        rows = (await db.execute(select(TripOrder, Shipment, SalesOrder, Customer)
                                 .join(Shipment, Shipment.id == TripOrder.shipment_id)
                                 .join(SalesOrder, SalesOrder.id == Shipment.so_id)
                                 .join(Customer, Customer.id == SalesOrder.customer_id)
                                 .where(TripOrder.trip_id == t.id).order_by(TripOrder.delivery_sequence))).all()
        out.append({"id": str(t.id), "trip_no": t.trip_no, "trip_date": str(t.trip_date), "status": t.status.value,
                    "vehicle": t.vehicle_plate, "stops": [
                        {"id": str(o.id), "sequence": o.delivery_sequence, "status": o.status.value,
                         "failure_reason": o.failure_reason, "shipment_no": sh.shipment_no, "order_no": so.order_no,
                         "customer": c.name, "phone": c.phone, "address": c.delivery_address or c.address,
                         "lat": float(c.gps_lat) if c.gps_lat is not None else None,
                         "lng": float(c.gps_lng) if c.gps_lng is not None else None} for o, sh, so, c in rows]})
    return out


@router.post("/trips/{trip_id}/start")
async def start_trip(trip_id: uuid.UUID, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
                     user=Depends(get_current_user)):
    from app.models.delivery import TripStatus
    from app.services.customer_messaging import notify_trip_started

    trip = await _my_trip(db, user, trip_id)
    if trip.status not in (TripStatus.PLANNED, TripStatus.LOADING):
        raise HTTPException(409, f"Trip is {trip.status.value}.")
    trip.status, trip.departed_at = TripStatus.IN_TRANSIT, datetime.now(timezone.utc)
    await db.commit()
    background.add_task(notify_trip_started, trip.id)  # "on the way" to each shop (WhatsApp / SMS once set up)
    return {"status": trip.status.value}


@router.post("/trips/{trip_id}/finish")
async def finish_trip(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.delivery import TripOrder, TripOrderStatus, TripStatus

    trip = await _my_trip(db, user, trip_id)
    if trip.status != TripStatus.IN_TRANSIT:
        raise HTTPException(409, f"Trip is {trip.status.value}.")
    pending = (await db.execute(select(func.count()).select_from(TripOrder).where(
        TripOrder.trip_id == trip.id, TripOrder.status == TripOrderStatus.PENDING))).scalar_one()
    if pending:
        raise HTTPException(409, f"{pending} stop(s) still have no result.")
    trip.status, trip.returned_at = TripStatus.COMPLETED, datetime.now(timezone.utc)
    await db.commit()
    return {"status": trip.status.value}


@router.post("/trip-orders/{trip_order_id}/deliver", status_code=201)
async def deliver(trip_order_id: uuid.UUID, received_by: str = Form(..., min_length=2, max_length=255),
                  lat: Optional[Decimal] = Form(None, ge=-90, le=90), lng: Optional[Decimal] = Form(None, ge=-180, le=180),
                  notes: Optional[str] = Form(None, max_length=1000), signature: UploadFile = File(...),
                  photo: Optional[UploadFile] = File(None), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.delivery import ProofOfDelivery, TripOrderStatus, TripStatus
    from app.models.sales import Shipment, ShipmentStatus

    to, trip = await _my_stop(db, user, trip_order_id)
    if trip.status != TripStatus.IN_TRANSIT:
        raise HTTPException(409, "Start the trip first.")
    existing = (await db.execute(select(ProofOfDelivery).where(ProofOfDelivery.trip_order_id == to.id))).scalar_one_or_none()
    if existing is not None:  # a resend after a lost response
        return {"id": str(existing.id), "status": to.status.value, "duplicate": True}
    if to.status not in (TripOrderStatus.PENDING, TripOrderStatus.FAILED):  # FAILED: re-attempt later the same trip
        raise HTTPException(409, f"This stop is {to.status.value.lower()}.")
    sig_key = await _store(signature)
    photo_key = await _store(photo) if photo is not None and photo.filename else None
    pod = ProofOfDelivery(shipment_id=to.shipment_id, trip_order_id=to.id, received_by=received_by.strip(),
                          signature_key=sig_key, photo_url=photo_key, delivered_at=datetime.now(timezone.utc),
                          gps_lat=lat, gps_lng=lng, notes=notes, confirmed_by_id=user.id)
    db.add(pod)
    to.status = TripOrderStatus.DELIVERED
    shipment = await db.get(Shipment, to.shipment_id)
    if shipment is not None and shipment.status == ShipmentStatus.DISPATCHED:
        # the invoice is cut at delivery and e-mailed to the shop (never blocks the delivery)
        from app.services.invoice_delivery_service import invoice_on_delivery

        await invoice_on_delivery(db, shipment.id, user.id)
        shipment.status = ShipmentStatus.DELIVERED
    try:
        await db.commit()
    except IntegrityError:  # a parallel identical request won
        await db.rollback()
        existing = (await db.execute(select(ProofOfDelivery).where(ProofOfDelivery.trip_order_id == trip_order_id))).scalar_one()
        return {"id": str(existing.id), "status": "DELIVERED", "duplicate": True}
    return {"id": str(pod.id), "status": to.status.value, "duplicate": False}


@router.post("/trip-orders/{trip_order_id}/fail")
async def fail_delivery(trip_order_id: uuid.UUID, body: FailIn, db: AsyncSession = Depends(get_db),
                        user=Depends(get_current_user)):
    from app.models.delivery import TripOrderStatus, TripStatus

    to, trip = await _my_stop(db, user, trip_order_id)
    if trip.status != TripStatus.IN_TRANSIT or to.status != TripOrderStatus.PENDING:
        raise HTTPException(409, "This stop is not open.")
    to.status, to.failure_reason = TripOrderStatus.FAILED, body.reason
    await db.commit()
    return {"status": to.status.value}


# ── field controller: outlet audits ───────────────────────────────────────────

@router.get("/audit-checklist")
async def audit_checklist(user=Depends(get_current_user)):
    _perm(user, "field.audit")
    return [{"key": k, "label": label} for k, label in CHECKLIST]


@router.get("/audit-outlets")
async def audit_outlets(search: str = Query(..., min_length=2, max_length=100), db: AsyncSession = Depends(get_db),
                        user=Depends(get_current_user)):
    """Outlets on any active route, with the rep who serves them."""
    from app.models.field_sales import RouteStop, SalesRep, SalesRoute
    from app.models.sales import Customer

    _perm(user, "field.audit")
    rows = (await db.execute(select(Customer, SalesRoute, SalesRep).join(RouteStop, RouteStop.customer_id == Customer.id)
                             .join(SalesRoute, SalesRoute.id == RouteStop.route_id)
                             .outerjoin(SalesRep, SalesRep.id == SalesRoute.assigned_rep_id)
                             .where(SalesRoute.is_active.is_(True), Customer.is_active.is_(True),
                                    or_(Customer.name.ilike(f"%{search}%"), Customer.code.ilike(f"%{search}%")))
                             .order_by(Customer.name).limit(30))).all()
    return [{"customer_id": str(c.id), "name": c.name, "address": c.delivery_address or c.address, "route": r.name,
             "rep": rep.name if rep else None} for c, r, rep in rows]


@router.post("/audits", status_code=201)
async def create_audit(body: AuditIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_ops import FieldAudit
    from app.models.field_sales import RouteStop, SalesRoute
    from app.models.sales import Customer

    _perm(user, "field.audit")
    if (existing := await _existing(db, FieldAudit, body.client_ref)) is not None:
        if existing.auditor_id != user.id:
            raise HTTPException(409, "Duplicate reference.")
        return {"id": str(existing.id), "audit_no": existing.audit_no, "score": float(existing.score), "duplicate": True}
    keys = [k for k, _ in CHECKLIST]
    answers = {a.key: a for a in body.answers}
    if len(body.answers) != len(keys) or sorted(answers) != sorted(keys):
        raise HTTPException(422, "Answer every checklist item exactly once.")
    customer = await db.get(Customer, body.customer_id)
    if customer is None or not customer.is_active:
        raise HTTPException(404, "Outlet not found")
    route = (await db.execute(select(SalesRoute).join(RouteStop, RouteStop.route_id == SalesRoute.id).where(
        RouteStop.customer_id == customer.id, SalesRoute.is_active.is_(True)).order_by(SalesRoute.code).limit(1))).scalar_one_or_none()
    score = Decimal(sum(1 for a in answers.values() if a.ok) * 100) / Decimal(len(keys))
    lat, lng = _gps(body)
    audit = FieldAudit(audit_no=_no("AUD"), auditor_id=user.id, rep_id=route.assigned_rep_id if route else None,
                       customer_id=customer.id, route_id=route.id if route else None, audit_date=date.today(),
                       answers=[{"key": k, "ok": answers[k].ok, "note": answers[k].note} for k in keys],
                       score=score.quantize(Decimal("0.01")), photo_keys=[], gps_lat=lat, gps_lng=lng,
                       client_ref=body.client_ref, notes=body.notes)
    db.add(audit)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _replay(db, FieldAudit, body.client_ref, "auditor_id", user.id)
        return {"id": str(existing.id), "audit_no": existing.audit_no, "score": float(existing.score), "duplicate": True}
    return {"id": str(audit.id), "audit_no": audit.audit_no, "score": float(audit.score), "duplicate": False}


@router.post("/audits/{audit_id}/photo")
async def audit_photo(audit_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                      user=Depends(get_current_user)):
    from app.models.field_ops import FieldAudit

    _perm(user, "field.audit")
    audit = (await db.execute(select(FieldAudit).where(FieldAudit.id == audit_id).with_for_update())).scalar_one_or_none()
    if audit is None or audit.auditor_id != user.id:
        raise HTTPException(404, "Audit not found")
    if len(audit.photo_keys or []) >= 6:
        raise HTTPException(422, "At most 6 photos per audit.")
    audit.photo_keys = [*(audit.photo_keys or []), await _store(file)]
    await db.commit()
    return {"photos": len(audit.photo_keys)}


@router.get("/audits")
async def list_audits(days: int = Query(7, ge=1, le=92), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.models.field_ops import FieldAudit
    from app.models.field_sales import SalesRep
    from app.models.sales import Customer

    supervise = has_permission(user, "field.supervise")
    if not supervise:
        _perm(user, "field.audit")
    q = (select(FieldAudit, Customer.name, SalesRep.name).join(Customer, Customer.id == FieldAudit.customer_id)
         .outerjoin(SalesRep, SalesRep.id == FieldAudit.rep_id)
         .where(FieldAudit.audit_date >= date.today() - timedelta(days=days)))
    if not supervise:
        q = q.where(FieldAudit.auditor_id == user.id)
    rows = (await db.execute(q.order_by(FieldAudit.created_at.desc()).limit(200))).all()
    labels = dict(CHECKLIST)
    return [{"id": str(a.id), "audit_no": a.audit_no, "date": str(a.audit_date), "outlet": cname, "rep": rname,
             "score": float(a.score), "photos": len(a.photo_keys or []),
             "failed": [labels.get(x["key"], x["key"]) for x in a.answers if not x["ok"]]} for a, cname, rname in rows]


# ── supervisor ────────────────────────────────────────────────────────────────

@router.get("/compliance")
async def compliance(days: int = Query(7, ge=1, le=92), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Per active rep over the last N days: route coverage, orders, collections, audit scores."""
    from app.models.field_ops import CashCollection, FieldAudit
    from app.models.field_sales import RouteStop, SalesRep, SalesRoute, VisitLog
    from app.models.sales import OrderSource, SalesOrder, SOLine, SOStatus

    _perm(user, "field.supervise")
    since = date.today() - timedelta(days=days - 1)
    reps = (await db.execute(select(SalesRep).where(SalesRep.is_active.is_(True)).order_by(SalesRep.name))).scalars().all()

    def per_rep(rows):
        return {r[0]: r[1:] for r in rows}

    stops = per_rep((await db.execute(select(SalesRoute.assigned_rep_id, func.count(func.distinct(RouteStop.customer_id))).join(
        RouteStop, RouteStop.route_id == SalesRoute.id).where(SalesRoute.is_active.is_(True))
        .group_by(SalesRoute.assigned_rep_id))).all())
    visits = per_rep((await db.execute(select(VisitLog.rep_id, func.count(VisitLog.id), func.count(func.distinct(VisitLog.customer_id)),
                                              func.count(VisitLog.gps_lat), func.max(VisitLog.visited_at))
                                       .where(VisitLog.visit_date >= since).group_by(VisitLog.rep_id))).all())
    orders = per_rep((await db.execute(select(SalesOrder.sales_rep_id, func.count(func.distinct(SalesOrder.id)),
                                              func.coalesce(func.sum(SOLine.ordered_quantity * SOLine.unit_price), 0))
                                       .join(SOLine, SOLine.so_id == SalesOrder.id)
                                       .where(SalesOrder.source == OrderSource.FIELD_SALES, SalesOrder.order_date >= since,
                                              SalesOrder.status != SOStatus.CANCELLED)
                                       .group_by(SalesOrder.sales_rep_id))).all())
    cols = per_rep((await db.execute(select(CashCollection.rep_id, func.count(CashCollection.id), func.sum(CashCollection.amount))
                                     .where(CashCollection.collection_date >= since,
                                            CashCollection.status.in_(("PENDING", "DEPOSITED", "CONFIRMED", "RECONCILED")))
                                     .group_by(CashCollection.rep_id))).all())
    audits = per_rep((await db.execute(select(FieldAudit.rep_id, func.count(FieldAudit.id), func.avg(FieldAudit.score))
                                       .where(FieldAudit.audit_date >= since).group_by(FieldAudit.rep_id))).all())
    out = []
    for r in reps:
        n_stops = (stops.get(r.id) or (0,))[0]
        v = visits.get(r.id) or (0, 0, 0, None)
        o = orders.get(r.id) or (0, 0)
        c = cols.get(r.id) or (0, 0)
        a = audits.get(r.id) or (0, None)
        out.append({"rep_id": str(r.id), "rep": r.name, "code": r.code, "vehicle": r.vehicle_type.value,
                    "route_stops": n_stops, "visits": v[0], "outlets_visited": v[1],
                    "coverage_pct": min(100.0, round(100 * v[1] / n_stops, 1)) if n_stops else None,
                    "visits_with_gps_pct": round(100 * v[2] / v[0], 1) if v[0] else None,
                    "last_visit_at": v[3].isoformat() if v[3] else None,
                    "orders": o[0], "order_value": float(o[1] or 0), "collections": c[0], "collected": float(c[1] or 0),
                    "audits": a[0], "audit_score": round(float(a[1]), 1) if a[1] is not None else None})
    return {"days": days, "since": since.isoformat(), "reps": out}


@router.get("/moto")
async def moto_overview(days: int = Query(7, ge=1, le=92), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Moto/van riders for supervisors: open fraud alerts and the performance leaderboard, with rider names."""
    from app.models.user import User
    from app.services import moto_sales_service as moto

    _perm(user, "field.supervise")
    alerts = await moto.list_fraud_alerts(db, status="OPEN", limit=100)
    board = await moto.leaderboard(db, from_date=date.today() - timedelta(days=days - 1), to_date=date.today())
    ids = {a.driver_id for a in alerts if a.driver_id} | {uuid.UUID(b["driver_id"]) for b in board if b["driver_id"] not in (None, "None")}
    names = {u.id: (u.full_name or u.username) for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars()} if ids else {}
    return {
        "alerts": [{"id": str(a.id), "fraud_type": a.fraud_type, "severity": a.severity, "risk_score": float(a.risk_score or 0),
                    "rider": names.get(a.driver_id), "description": a.description,
                    "created_at": a.created_at.isoformat() if a.created_at else None} for a in alerts],
        "leaderboard": [{**b, "rider": names.get(uuid.UUID(b["driver_id"])) if b["driver_id"] not in (None, "None") else None}
                        for b in board],
    }
