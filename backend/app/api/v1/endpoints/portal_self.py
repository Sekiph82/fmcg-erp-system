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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
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
async def login(body: LoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    from app.models.portal import PortalAccountStatus

    key = await ext.login_guard("portal", body.email)
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

    if not ext.check_password(body.current_password, user.password_hash)[0]:
        raise HTTPException(400, "Current password is incorrect.")
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
    so = SalesOrder(order_no=f"WEB-{date.today():%y%m%d}-{secrets.token_hex(5).upper()}", customer_id=customer.id,
                    order_date=date.today(), requested_delivery_date=body.requested_delivery_date,
                    status=SOStatus.DRAFT, currency=customer.currency, payment_method=PaymentMethod.CREDIT,
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
    for n, (product, qty, price) in enumerate(priced, start=1):
        db.add(SOLine(so_id=so.id, line_no=n, product_id=product.id, ordered_quantity=qty, unit=product.uom.value,
                      unit_price=price, cost_price=product.standard_cost))
    await svc._log_activity(db, str(user.id), str(user.portal_account_id), PortalActivityType.SUBMIT_ORDER,
                            "sales_order", str(so.id))
    await db.commit()
    total = sum((q * p for _, q, p in priced), Decimal("0"))
    return {"id": str(so.id), "order_no": so.order_no, "status": so.status.value, "currency": so.currency,
            "total": float(total) if user.account.can_view_prices else None, "duplicate": False}


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
