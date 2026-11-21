"""Distributor / customer self-service portal (M38.S01.T002).

Signed in with the portal realm cookie (``app.core.external_auth``), never a staff session. Every query is scoped to
the signed-in user's own portal account and its linked customer. Prices are always resolved on the server (price
lists for the customer/distributor, else the product's selling price); a placed order becomes a DRAFT sales order
(source DISTRIBUTOR) that sales staff confirm — the credit-limit check runs at that confirmation.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import external_auth as ext
from app.db.session import get_db
from app.models.portal import PortalActivityType, PortalUser, PortalUserRole
from app.schemas.portal import PortalClaimCreate
from app.services import portal_service as svc

public = APIRouter()   # sign-in endpoints (no session yet)
router = APIRouter()   # everything else: signed-in portal user only

ORDERING_ROLES = {PortalUserRole.OWNER, PortalUserRole.BUYER}
CLAIM_ROLES = {PortalUserRole.OWNER, PortalUserRole.BUYER, PortalUserRole.LOGISTICS}


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class ActivateIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class OrderLineIn(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"))


class OrderIn(BaseModel):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")  # idempotency key from the browser
    requested_delivery_date: date
    notes: Optional[str] = Field(default=None, max_length=1000)
    lines: List[OrderLineIn] = Field(min_length=1, max_length=200)
    payment_method: Optional[str] = Field(default=None, pattern=r"^(cash|mpesa|credit)$")  # must be one the account allows


def payment_options(customer) -> dict:
    """How this customer may pay, from its commercial terms (no separate setting): prepaid accounts pay by M-Pesa
    before delivery; accounts without credit days pay on delivery (cash or M-Pesa); credit accounts may also buy on
    their terms. The first option is the default."""
    if customer.is_prepaid:
        allowed = ["mpesa"]
    elif not customer.payment_terms_days or (customer.credit_limit is not None and customer.credit_limit <= 0):
        allowed = ["cash", "mpesa"]
    else:
        allowed = ["credit", "mpesa", "cash"]
    return {"allowed": allowed, "default": allowed[0], "prepaid": bool(customer.is_prepaid),
            "terms_days": customer.payment_terms_days if "credit" in allowed else 0,
            "credit_limit": float(customer.credit_limit) if "credit" in allowed and customer.credit_limit is not None else None}


async def _customer(db: AsyncSession, user: PortalUser):
    from app.models.sales import Customer

    cid = user.account.linked_customer_id
    try:
        customer = await db.get(Customer, uuid.UUID(cid)) if cid else None
    except ValueError:
        customer = None
    if customer is None or not customer.is_active:
        raise HTTPException(409, "Your account is not linked to an active customer yet. Please contact your sales representative.")
    return customer


def _distributor_id(user: PortalUser):
    try:
        return uuid.UUID(user.account.linked_distributor_id) if user.account.linked_distributor_id else None
    except ValueError:
        return None


def _me(user: PortalUser, customer=None) -> dict:
    a = user.account
    return {"id": str(user.id), "full_name": user.full_name, "email": user.email, "role": user.role_type.value,
            "can_order": user.role_type in ORDERING_ROLES, "account_code": a.account_code,
            "account_type": a.account_type.value, "can_view_prices": bool(a.can_view_prices),
            "customer_name": customer.name if customer else None, "currency": customer.currency if customer else a.default_currency}


async def _price(db: AsyncSession, product, customer, distributor_id, quantity: Decimal):
    from app.services.customer_pricing import unit_price

    return await unit_price(db, product, customer, distributor_id, quantity)


# ── sign-in ───────────────────────────────────────────────────────────────────

@public.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    from app.models.portal import PortalAccountStatus

    key = await ext.login_guard("portal", body.email, request)
    user = (await db.execute(select(PortalUser).options(selectinload(PortalUser.account))
                             .where(func.lower(PortalUser.email) == body.email.strip().lower()))).scalar_one_or_none()
    usable = user is not None and user.is_active and user.account.portal_status == PortalAccountStatus.ACTIVE
    if not usable or not await ext.password_login(db, response, "portal", user, body.password, key):
        if not usable:
            ext.dummy_password_check(body.password)
            await ext.record_login_failure(key)
        raise HTTPException(401, "E-mail or password is incorrect, or the account is not active.")
    user.last_login_at = datetime.utcnow()
    await svc._log_activity(db, str(user.id), str(user.portal_account_id), PortalActivityType.LOGIN)
    await db.commit()
    return _me(user)


@public.post("/auth/activate")
async def activate(body: ActivateIn, db: AsyncSession = Depends(get_db)):
    user = await svc.activate_user_with_password(db, body.token, body.new_password)
    if not user:
        raise HTTPException(400, "This link is invalid or has expired. Ask your sales representative for a new one.")
    return {"detail": "Password set. You can sign in now.", "email": user.email}


class SignupIn(BaseModel):
    shop_name: str = Field(min_length=2, max_length=150)
    contact_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=9, max_length=20, pattern=r"^\+?[0-9 ]+$")
    email: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    address: str = Field(min_length=3, max_length=300)
    lat: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    lng: Optional[Decimal] = Field(default=None, ge=-180, le=180)


SIGNUP_PREFIX = "SIGNUP:"  # ponytail: the request rides in PortalAccount.notes as JSON; a column when requests need search


@public.post("/auth/signup-request", status_code=202)
async def signup_request(body: SignupIn, request: Request, db: AsyncSession = Depends(get_db)):
    """A shop asks for an ordering account from the app. Sales staff review it (Customer Portal → requests), create or
    link the customer and send the set-password link. Same answer whether or not the e-mail is known."""
    import json

    from app.core.login_limiter import check_login_allowed, record_login_failure
    from app.models.portal import PortalAccount, PortalAccountStatus, PortalAccountType

    key = f"portal-signup:{request.client.host if request.client else '-'}"
    await check_login_allowed(key)
    await record_login_failure(key)  # every request counts: at most a few per address per window
    email = body.email.strip().lower()
    known = (await db.execute(select(PortalUser.id).where(func.lower(PortalUser.email) == email))).first() or (
        await db.execute(select(PortalAccount.id).where(func.lower(PortalAccount.primary_contact_email) == email,
                                                        PortalAccount.portal_status == PortalAccountStatus.PENDING))).first()
    if not known:
        db.add(PortalAccount(
            account_code=f"REQ-{secrets.token_hex(4).upper()}", account_type=PortalAccountType.RETAILER,
            portal_status=PortalAccountStatus.PENDING, primary_contact_name=body.contact_name.strip(),
            primary_contact_email=email, primary_contact_phone=body.phone.strip(), can_view_prices=True,
            notes=SIGNUP_PREFIX + json.dumps({"shop_name": body.shop_name.strip(), "address": body.address.strip(),
                                              "lat": str(body.lat) if body.lat is not None else None,
                                              "lng": str(body.lng) if body.lng is not None else None})))
        await db.commit()
        from app.services.notifications_service import notify_permission_holders
        try:
            await notify_permission_holders(db, "partner_portal.manage_access", f"Shop sign-up: {body.shop_name.strip()}",
                                            f"{body.contact_name.strip()} asked for an ordering account (Customer Portal → requests).",
                                            module="sales")
        except Exception:  # the request is saved; staff also see it in the list
            pass
    return {"detail": "Thank you. Our sales team will check your request and send you a link to set your password."}


@public.post("/auth/logout")
async def logout(request: Request, response: Response):
    await ext.sign_out(request, response, "portal")
    return {"detail": "Signed out"}


# ── signed-in ─────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.sales import Customer

    cid = user.account.linked_customer_id
    try:
        customer = await db.get(Customer, uuid.UUID(cid)) if cid else None
    except ValueError:
        customer = None
    return {**_me(user, customer), "linked": customer is not None and customer.is_active}


@router.post("/password")
async def change_password(body: PasswordIn, response: Response, user: PortalUser = Depends(ext.get_portal_user),
                          db: AsyncSession = Depends(get_db)):
    from app.core.security import hash_password

    key = f"portal-pw:{user.id}"
    await ext.check_login_allowed(key)  # current-password guesses are rate-limited like sign-in
    if not ext.check_password(body.current_password, user.password_hash)[0]:
        await ext.record_login_failure(key)
        raise HTTPException(400, "Current password is incorrect.")
    if ext.check_password(body.new_password, user.password_hash)[0]:
        raise HTTPException(422, "Choose a password different from the current one.")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    ext.issue(response, "portal", user.id, user.password_hash)  # other sessions end; this one continues
    return {"detail": "Password changed"}


@router.get("/dashboard")
async def dashboard(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    await _customer(db, user)
    return await svc.get_portal_dashboard(db, user.account)


@router.get("/catalog")
async def catalog(search: Optional[str] = Query(None, max_length=100), page: int = Query(1, ge=1, le=500),
                  user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.master import Product

    customer = await _customer(db, user)
    q = select(Product).where(Product.is_active.is_(True))
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    rows = (await db.execute(q.order_by(Product.name).offset((page - 1) * 50).limit(50))).scalars().all()
    dist = _distributor_id(user)
    items = []
    for p in rows:
        price = await _price(db, p, customer, dist, Decimal("1"))
        if price is None:
            continue  # not orderable without a price
        items.append({"product_id": str(p.id), "sku": p.sku, "name": p.name, "uom": p.uom.value,
                      "units_per_carton": p.units_per_carton,
                      "unit_price": float(price) if user.account.can_view_prices else None})
    return {"currency": customer.currency, "page": page, "items": items, "has_more": len(rows) == 50}


@router.post("/orders", status_code=201)
async def place_order(body: OrderIn, user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.master import Product
    from app.models.sales import OrderSource, PaymentMethod, SalesOrder, SOLine, SOStatus
    from app.services.commercial_access_service import inherit_commercial_scope

    if user.role_type not in ORDERING_ROLES:
        raise HTTPException(403, "Your portal role cannot place orders.")
    customer = await _customer(db, user)
    if body.requested_delivery_date < date.today():
        raise HTTPException(422, "The delivery date cannot be in the past.")
    offline_id = f"portal:{user.account.id}:{body.client_ref}"
    existing = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == offline_id))).scalar_one_or_none()
    if existing is not None:  # same submission again (double click, retry): the first order, never a second
        return {"id": str(existing.id), "order_no": existing.order_no, "status": existing.status.value, "duplicate": True}
    if len({l.product_id for l in body.lines}) != len(body.lines):
        raise HTTPException(422, "Each product may appear only once in an order.")
    dist = _distributor_id(user)
    priced = []
    for line in body.lines:
        product = await db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise HTTPException(422, "A product in the order is not available.")
        price = await _price(db, product, customer, dist, line.quantity)
        if price is None:
            raise HTTPException(422, f"{product.name} has no price for your account.")
        priced.append((product, line.quantity, price))
    opts = payment_options(customer)
    method = body.payment_method or opts["default"]
    if method not in opts["allowed"]:
        raise HTTPException(422, "This payment method is not available for your account.")
    so = SalesOrder(order_no=f"WEB-{date.today():%y%m%d}-{secrets.token_hex(5).upper()}", customer_id=customer.id,
                    order_date=date.today(), requested_delivery_date=body.requested_delivery_date,
                    status=SOStatus.DRAFT, currency=customer.currency, payment_method=PaymentMethod(method),
                    source=OrderSource.DISTRIBUTOR, distributor_id=dist, offline_id=offline_id,
                    offline_synced_at=datetime.now(timezone.utc),
                    notes=f"Portal order by {user.full_name} ({user.email})" + (f": {body.notes}" if body.notes else ""))
    inherit_commercial_scope(so, customer)
    db.add(so)
    try:
        await db.flush()
    except IntegrityError:  # a concurrent identical submission won
        await db.rollback()
        existing = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == offline_id))).scalar_one_or_none()
        if existing is None:
            raise HTTPException(409, "The order could not be saved; please submit it again.")
        return {"id": str(existing.id), "order_no": existing.order_no, "status": existing.status.value, "duplicate": True}
    so_lines = [SOLine(so_id=so.id, line_no=n, product_id=product.id, ordered_quantity=qty, unit=product.uom.value,
                       unit_price=price, cost_price=product.standard_cost, discount_pct=Decimal("0"))
                for n, (product, qty, price) in enumerate(priced, start=1)]
    db.add_all(so_lines)
    await db.flush()
    from app.services.shop_promotions import apply_to_order  # same list price for all; the shop's promotions on top

    promotions = await apply_to_order(db, so, customer)
    order_total = sum((l.ordered_quantity * l.unit_price * (1 - l.discount_pct) for l in so_lines), Decimal("0"))  # before commit expires the lines
    await svc._log_activity(db, str(user.id), str(user.portal_account_id), PortalActivityType.SUBMIT_ORDER,
                            "sales_order", str(so.id))
    await db.commit()
    from app.services.notifications_service import notify_new_order
    await notify_new_order(db, so, customer.name, "portal")
    total = order_total
    return {"id": str(so.id), "order_no": so.order_no, "status": so.status.value, "currency": so.currency,
            "total": float(total) if user.account.can_view_prices else None,
            "promotions": promotions if user.account.can_view_prices else [], "duplicate": False}


@router.get("/promotions")
async def my_promotions(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    """The shop's own promotion table (prices stay the same list price for every shop)."""
    from app.services.shop_promotions import customer_promotions

    return await customer_promotions(db, await _customer(db, user))


@router.get("/payment-options")
async def get_payment_options(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    return payment_options(await _customer(db, user))


@router.post("/orders/{order_id}/pay-mpesa", status_code=201)
async def pay_mpesa(order_id: uuid.UUID, user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    """Send an M-Pesa payment request (STK push) for the order's open amount to the account's registered phone."""
    from app.models.sales import Invoice, InvoiceStatus, PaymentMethod, SalesOrder, SOLine
    from app.services import mpesa_service

    if user.role_type not in ORDERING_ROLES | {PortalUserRole.FINANCE}:
        raise HTTPException(403, "Your portal role cannot make payments.")
    customer = await _customer(db, user)
    so = (await db.execute(select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.customer_id == customer.id)
                           .with_for_update())).scalar_one_or_none()
    if so is None:
        raise HTTPException(404, "Order not found")
    if so.status.value == "CANCELLED":
        raise HTTPException(422, "This order was cancelled.")
    if not customer.phone:
        raise HTTPException(422, "No phone number is registered for your account; please contact your sales representative.")
    from datetime import timedelta

    from app.core.login_limiter import check_login_allowed, record_login_failure
    from app.models.sales import MpesaTransaction, MpesaTxStatus

    await check_login_allowed(f"portal-pay:{user.id}")   # a few payment requests per user per window
    await record_login_failure(f"portal-pay:{user.id}")
    recent = (await db.execute(select(MpesaTransaction.id).where(
        MpesaTransaction.so_id == so.id, MpesaTransaction.status == MpesaTxStatus.PENDING,
        MpesaTransaction.created_at > datetime.now(timezone.utc) - timedelta(minutes=2)))).first()
    if recent:
        raise HTTPException(409, "A payment request was just sent to your phone; check it or try again in two minutes.")
    inv = (await db.execute(select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
                            .where(Invoice.so_id == so.id,
                                   Invoice.status.notin_((InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT))))).one()
    if inv[0]:   # invoiced: what is still open on the invoices (0 when they are paid)
        due = Decimal(inv[1])
    else:        # not invoiced yet (pay before delivery): the order value less M-Pesa already received
        value = Decimal((await db.execute(select(func.coalesce(func.sum(
            SOLine.ordered_quantity * SOLine.unit_price * (1 - SOLine.discount_pct) * (1 + SOLine.tax_rate)), 0))
            .where(SOLine.so_id == so.id))).scalar())
        received = Decimal((await db.execute(select(func.coalesce(func.sum(MpesaTransaction.amount), 0)).where(
            MpesaTransaction.so_id == so.id, MpesaTransaction.status == MpesaTxStatus.COMPLETED))).scalar())
        due = value - received
    due = due.quantize(Decimal("1"))
    if due <= 0:
        raise HTTPException(422, "Nothing is due on this order.")
    if so.payment_method.value != "mpesa":
        if "mpesa" not in payment_options(customer)["allowed"]:
            raise HTTPException(422, "M-Pesa is not available for your account.")
        so.payment_method = PaymentMethod.MPESA  # the shop chose to pay this order by M-Pesa
    tx = await mpesa_service.initiate_payment(db, so, customer.phone, due, None)
    await svc._log_activity(db, str(user.id), str(user.portal_account_id), PortalActivityType.SUBMIT_ORDER,
                            "mpesa_payment", str(tx.id))
    await db.commit()
    return {"status": getattr(tx.status, "value", tx.status), "amount": float(due),
            "phone_hint": "…" + customer.phone[-3:]}


@router.get("/orders")
async def orders(status: Optional[str] = Query(None, max_length=20), page: int = Query(1, ge=1, le=500),
                 user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    await _customer(db, user)
    rows = await svc.get_portal_orders(db, user.account, status=status, skip=(page - 1) * 50, limit=50)
    if not user.account.can_view_prices:
        for r in rows:
            r["total"] = None
    return rows


@router.get("/orders/{order_id}")
async def order_detail(order_id: uuid.UUID, user: PortalUser = Depends(ext.get_portal_user),
                       db: AsyncSession = Depends(get_db)):
    from app.models.master import Product

    await _customer(db, user)
    order = await svc.get_portal_order_detail(db, user.account, str(order_id))
    if not order:
        raise HTTPException(404, "Order not found")
    from app.models.sales import SalesOrder
    from app.services.delivery_eta import order_tracking
    order["tracking"] = await order_tracking(db, await db.get(SalesOrder, order_id))  # scoped above: the caller's own order
    ids = [uuid.UUID(l["product_id"]) for l in order["lines"]]
    names = {str(p.id): (p.name, p.sku) for p in (await db.execute(select(Product).where(Product.id.in_(ids)))).scalars()} if ids else {}
    for l in order["lines"]:
        l["product_name"], l["sku"] = names.get(l["product_id"], ("?", "?"))
        if not user.account.can_view_prices:
            l["unit_price"] = None
    if not user.account.can_view_prices:
        order["total"] = None
        for i in order["invoices"]:
            i["total_amount"] = None
    return order


@router.get("/invoices")
async def invoices(page: int = Query(1, ge=1, le=500), user: PortalUser = Depends(ext.get_portal_user),
                   db: AsyncSession = Depends(get_db)):
    await _customer(db, user)
    return await svc.get_portal_invoices(db, user.account, skip=(page - 1) * 50, limit=50)


@router.get("/statement")
async def statement(from_date: Optional[date] = None, to_date: Optional[date] = None,
                    user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    await _customer(db, user)
    return await svc.get_portal_statement(db, user.account, from_date=from_date, to_date=to_date)


@router.get("/shipments")
async def shipments(page: int = Query(1, ge=1, le=500), user: PortalUser = Depends(ext.get_portal_user),
                    db: AsyncSession = Depends(get_db)):
    await _customer(db, user)
    return await svc.get_portal_shipments(db, user.account, skip=(page - 1) * 50, limit=50)


@router.get("/claims")
async def claims(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    rows = await svc.get_claims(db, str(user.portal_account_id))
    return [{"id": str(c.id), "claim_no": c.claim_no, "claim_type": c.claim_type.value, "status": c.status.value,
             "reason": c.reason, "linked_order_id": c.linked_order_id, "resolution_notes": c.resolution_notes,
             "created_at": c.created_at.isoformat() if c.created_at else None} for c in rows]


@router.post("/claims", status_code=201)
async def submit_claim(body: PortalClaimCreate, user: PortalUser = Depends(ext.get_portal_user),
                       db: AsyncSession = Depends(get_db)):
    if user.role_type not in CLAIM_ROLES:
        raise HTTPException(403, "Your portal role cannot submit claims.")
    if body.linked_order_id:  # only the account's own orders can be referenced
        try:
            ok = await svc.get_portal_order_detail(db, user.account, str(uuid.UUID(body.linked_order_id)))
        except ValueError:
            ok = None
        if not ok:
            raise HTTPException(422, "The order is not one of your orders.")
    c = await svc.create_claim(db, str(user.portal_account_id), str(user.id), body)
    return {"id": str(c.id), "claim_no": c.claim_no, "status": c.status.value}


# ── support tickets (helpdesk) ────────────────────────────────────────────────

class TicketIn(BaseModel):
    category: str = Field(pattern=r"^(QUALITY|DELIVERY|BILLING|PRODUCT|OTHER)$")
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=4000)


class ReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


async def _my_ticket(db: AsyncSession, user: PortalUser, ticket_id: uuid.UUID):
    from sqlalchemy.orm import selectinload

    from app.models.helpdesk import HelpdeskTicket

    customer = await _customer(db, user)
    t = (await db.execute(select(HelpdeskTicket).options(selectinload(HelpdeskTicket.comments))
                          .where(HelpdeskTicket.id == ticket_id, HelpdeskTicket.customer_id == customer.id))).scalar_one_or_none()
    if t is None:
        raise HTTPException(404, "Ticket not found")
    return t


def _ticket_out(t, with_thread: bool = False) -> dict:
    out = {"id": str(t.id), "ticket_no": t.ticket_no, "category": t.category.value, "status": t.status.value,
           "subject": t.subject, "created_at": t.created_at.isoformat() if t.created_at else None,
           "resolution_notes": t.resolution_notes}
    if with_thread:  # internal staff notes are never shown to the customer
        out["description"] = t.description if t.source.value == "PORTAL" else None  # staff-entered text stays internal
        out["thread"] = [{"body": c.body, "from_us": c.created_by_id is not None,
                          "at": c.created_at.isoformat() if c.created_at else None} for c in t.comments if not c.is_internal]
    return out


@router.get("/tickets")
async def tickets(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.helpdesk import HelpdeskTicket

    customer = await _customer(db, user)
    rows = (await db.execute(select(HelpdeskTicket).where(HelpdeskTicket.customer_id == customer.id)
                             .order_by(HelpdeskTicket.created_at.desc()).limit(100))).scalars().all()
    return [_ticket_out(t) for t in rows]


@router.get("/tickets/{ticket_id}")
async def ticket(ticket_id: uuid.UUID, user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.helpdesk import TicketAttachment
    from app.services import ticket_attachment_service as files

    t = await _my_ticket(db, user, ticket_id)
    out = _ticket_out(t, with_thread=True)
    rows = (await db.execute(select(TicketAttachment).where(
        TicketAttachment.ticket_id == t.id, TicketAttachment.customer_visible.is_(True))
        .order_by(TicketAttachment.created_at))).scalars().all()
    out["attachments"] = [{k: v for k, v in files.out(a).items() if k != "customer_visible"} for a in rows]
    return out


@router.post("/tickets/{ticket_id}/attachments", status_code=201)
async def add_ticket_file(ticket_id: uuid.UUID, file: UploadFile = File(...),
                          user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    """Attach a photo or document (PDF, PNG, JPG, TXT, CSV, DOCX, XLSX; max 10 MB, 10 per ticket); scanned for malware."""
    from app.models.helpdesk import TicketStatus
    from app.services import ticket_attachment_service as files

    t = await _my_ticket(db, user, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(409, "This ticket is closed; open a new one.")
    att = await files.add(db, t.id, file, from_customer=True, portal_user_id=user.id)
    await db.commit()
    return files.out(att)


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
async def get_ticket_file(ticket_id: uuid.UUID, attachment_id: uuid.UUID,
                          user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.models.helpdesk import TicketAttachment
    from app.services import ticket_attachment_service as files

    t = await _my_ticket(db, user, ticket_id)  # the customer's own ticket only
    a = (await db.execute(select(TicketAttachment).where(
        TicketAttachment.id == attachment_id, TicketAttachment.ticket_id == t.id,
        TicketAttachment.customer_visible.is_(True)))).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "File not found")
    return files.download(a)


@router.post("/tickets", status_code=201)
async def open_ticket(body: TicketIn, user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from datetime import timedelta

    from sqlalchemy import func

    from app.models.helpdesk import SLA_DEFAULTS, HelpdeskTicket, TicketCategory, TicketPriority, TicketSource, TicketStatus

    customer = await _customer(db, user)
    recent = (await db.execute(select(func.count()).select_from(HelpdeskTicket).where(
        HelpdeskTicket.customer_id == customer.id, HelpdeskTicket.source == TicketSource.PORTAL,
        HelpdeskTicket.created_at >= datetime.now(timezone.utc) - timedelta(days=1)))).scalar_one()
    if recent >= 20:
        raise HTTPException(429, "Too many tickets today; please add to an existing ticket.")
    t = HelpdeskTicket(ticket_no=f"TKT-{date.today():%Y%m%d}-P{secrets.token_hex(3).upper()}", customer_id=customer.id,
                       category=TicketCategory(body.category), priority=TicketPriority.MEDIUM, status=TicketStatus.OPEN,
                       source=TicketSource.PORTAL, subject=body.subject,
                       description=f"{body.description}\n\n— {user.full_name} ({user.email}) via partner portal",
                       sla_hours=SLA_DEFAULTS[TicketPriority.MEDIUM])
    db.add(t)
    await db.commit()
    return {"id": str(t.id), "ticket_no": t.ticket_no, "status": t.status.value}


@router.post("/tickets/{ticket_id}/reply", status_code=201)
async def reply(ticket_id: uuid.UUID, body: ReplyIn, user: PortalUser = Depends(ext.get_portal_user),
                db: AsyncSession = Depends(get_db)):
    from app.models.helpdesk import TicketComment, TicketStatus

    t = await _my_ticket(db, user, ticket_id)
    if t.status == TicketStatus.CLOSED:
        raise HTTPException(409, "This ticket is closed; open a new one.")
    # created_by_id stays empty: a customer message (staff replies carry the staff user)
    db.add(TicketComment(ticket_id=t.id, body=f"{body.body}\n\n— {user.full_name}", is_internal=False))
    if t.status == TicketStatus.RESOLVED:
        t.status = TicketStatus.IN_PROGRESS  # the customer says it is not solved yet
    await db.commit()
    return {"status": t.status.value}


# ── feedback (NPS) and loyalty (M40.S01.T001) ────────────────────────────────

class FeedbackIn(BaseModel):
    survey_id: uuid.UUID
    so_id: Optional[uuid.UUID] = None
    score: int = Field(ge=0, le=10)
    comment: Optional[str] = Field(default=None, max_length=2000)


@router.get("/feedback")
async def feedback_open(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.services import customer_feedback_service as fb
    customer = await _customer(db, user)
    return await fb.open_surveys(db, customer.id)


@router.post("/feedback", status_code=201)
async def feedback_answer(body: FeedbackIn, user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.services import customer_feedback_service as fb
    customer = await _customer(db, user)
    try:
        await fb.answer(db, customer.id, body.survey_id, body.so_id, body.score, body.comment, "portal")
    except fb.FeedbackError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return {"detail": "Thank you for your feedback."}


@router.get("/loyalty")
async def loyalty(user: PortalUser = Depends(ext.get_portal_user), db: AsyncSession = Depends(get_db)):
    from app.services import customer_feedback_service as fb
    customer = await _customer(db, user)
    return await fb.loyalty_summary(db, customer.id)
