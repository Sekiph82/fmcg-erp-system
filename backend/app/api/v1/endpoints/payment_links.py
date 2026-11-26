"""Customer payment links (M45.S01.T021) + card payments through Pesapal hosted checkout (M48.S01.T010).
Staff (prefix /api/v1/payment-links): create (shown once), list per invoice, revoke — sales.create / finance.create;
card: provider config / IPN registration / live request+approve (finance.approve, two people), hosted checkout for a
link (sales.create / finance.create), status refresh, refund request (finance.create/edit) and decision (another
finance.approve user), reconciliation view.
Public (prefix /api/v1/public/pay): GET /{token} page data; POST /{token}/mpesa start an STK push; POST /{token}/card
start a hosted card checkout (returns the provider's redirect_url). Settlement comes only from the Daraja callback
(/integrations/mpesa/callback) or a verified Pesapal status query (/public/card-ipn, card_payments_public.py)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.m48_payments import CardPayment
from app.models.payments_hub import PaymentLink, PaymentLinkAttempt
from app.services import card_payment_service as cards
from app.services import payment_link_service as pls

router = APIRouter(dependencies=[Depends(require_any_permission(("sales.create", "finance.create", "sales.view", "finance.view")))])
public = APIRouter()
WRITE = ("sales.create", "finance.create")
REFUND_REQ = ("finance.create", "finance.edit")
FIN_APPROVE = ("finance.approve",)
EMAIL = r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$"


def _fail(e):
    raise HTTPException(e.status, str(e))


class LinkIn(BaseModel):
    invoice_id: uuid.UUID
    days: int = Field(14, ge=1, le=60)
    allow_partial: bool = True


@router.post("", status_code=201, dependencies=[Depends(require_any_permission(WRITE))])
async def create(body: LinkIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        link, token = await pls.create(db, body.invoice_id, current_user.id, body.days, body.allow_partial)
    except pls.LinkError as e:
        _fail(e)
    from app.services import pat_service as pats
    pats.audit(db, current_user, "PAYMENT_LINK_CREATED", "invoice", str(body.invoice_id), {"link": str(link.id)})
    await db.commit()
    return {"id": str(link.id), "url": f"{settings.PUBLIC_APP_URL.rstrip('/')}/pay/{token}", "expires_at": link.expires_at.isoformat()}


def _card_out(p: CardPayment) -> dict:
    return {"id": str(p.id), "status": p.status, "settlement": p.settlement, "simulated": p.simulated,
            "amount": str(p.amount), "currency": p.currency, "redirect_url": p.redirect_url if p.status == "PENDING" else None,
            "status_description": p.status_description}


@router.get("")
async def list_links(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PaymentLink).where(PaymentLink.invoice_id == invoice_id).order_by(PaymentLink.created_at.desc()))).scalars()
    out = []
    for l in rows:
        atts = (await db.execute(select(PaymentLinkAttempt).where(PaymentLinkAttempt.link_id == l.id))).scalars()
        cps = (await db.execute(select(CardPayment).where(CardPayment.link_id == l.id).order_by(CardPayment.created_at))).scalars()
        out.append({"id": str(l.id), "status": l.status, "settled_amount": str(l.settled_amount), "expires_at": l.expires_at.isoformat(),
                    "currency": l.currency, "allow_partial": l.allow_partial,
                    "attempts": [{"amount": str(a.amount), "status": a.status, "receipt": a.receipt, "simulated": a.simulated} for a in atts],
                    "card_payments": [_card_out(p) for p in cps]})
    return out


# ── card provider (Pesapal) set-up ───────────────────────────────────────────

class CardConfigIn(BaseModel):
    environment: str = Field(pattern=r"^(SANDBOX|LIVE)$")
    consumer_key: str = Field(min_length=8, max_length=200)
    consumer_secret: str = Field(min_length=8, max_length=200)
    base_url: Optional[str] = Field(None, max_length=200, pattern=r"^https?://")


@router.get("/card/config")
async def card_config(db: AsyncSession = Depends(get_db)):
    return cards.view(await cards.config(db))


@router.put("/card/config", dependencies=[Depends(require_any_permission(FIN_APPROVE))])
async def save_card_config(body: CardConfigIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        cfg = await cards.save_config(db, current_user, body.environment, body.consumer_key, body.consumer_secret, body.base_url)
    except cards.CardError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    return cards.view(cfg)


@router.post("/card/config/{action}", dependencies=[Depends(require_any_permission(FIN_APPROVE))])
async def card_config_action(action: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    fn = {"register-ipn": cards.register_ipn, "request-live": cards.request_live, "approve-live": cards.approve_live}.get(action)
    if fn is None:
        raise HTTPException(404, "Unknown action")
    try:
        cfg = await fn(db, current_user)
    except cards.CardError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    return cards.view(cfg)


# ── card payments ────────────────────────────────────────────────────────────

class CardIn(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, le=Decimal("100000000"))
    email: Optional[str] = Field(None, max_length=254, pattern=EMAIL)
    phone: Optional[str] = Field(None, min_length=9, max_length=20, pattern=r"^[+0-9 ]+$")


@router.get("/reconciliation")
async def reconciliation(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cards.reconciliation(db, invoice_id)
    except cards.CardError as e:
        _fail(e)


@router.post("/card-payments/{pid}/refresh", dependencies=[Depends(require_any_permission(WRITE + REFUND_REQ))])
async def refresh_card(pid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        p = await cards.refresh(db, pid, force=True)
    except cards.CardError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    await db.refresh(p)
    return _card_out(p)


class RefundIn(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))
    reason: str = Field(min_length=3, max_length=255)


@router.post("/card-payments/{pid}/refund", status_code=201, dependencies=[Depends(require_any_permission(REFUND_REQ))])
async def request_refund(pid: uuid.UUID, body: RefundIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        r = await cards.request_refund(db, current_user, pid, body.amount, body.reason)
    except cards.CardError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    return {"id": str(r.id), "status": r.status}


@router.post("/card-refunds/{rid}/{decision}", dependencies=[Depends(require_any_permission(FIN_APPROVE))])
async def decide_refund(rid: uuid.UUID, decision: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if decision not in ("approve", "reject"):
        raise HTTPException(404, "Unknown decision")
    try:
        r = await cards.decide_refund(db, current_user, rid, decision == "approve")
    except cards.CardError as e:
        await db.rollback()
        _fail(e)
    status, message = r.status, r.provider_message
    await db.commit()
    return {"id": str(rid), "status": status, "message": message}


@router.post("/{lid}/card", status_code=201, dependencies=[Depends(require_any_permission(WRITE))])
async def staff_card(lid: uuid.UUID, body: CardIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Hosted checkout for a link, e.g. to send the redirect URL to the customer; the card is typed on Pesapal's page."""
    link = (await db.execute(select(PaymentLink).where(PaymentLink.id == lid).with_for_update()
                             .execution_options(populate_existing=True))).scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "Link not found")
    try:
        p = await cards.start_checkout(db, link, body.amount, body.email, body.phone, current_user)
    except cards.CardError as e:
        await db.commit()          # keep a FAILED attempt (counts toward the hourly limit, visible to finance)
        _fail(e)
    await db.commit()
    await db.refresh(p)
    return _card_out(p)


@router.post("/{lid}/revoke", dependencies=[Depends(require_any_permission(WRITE))])
async def revoke(lid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    l = await db.get(PaymentLink, lid, with_for_update=True)
    if l is None:
        raise HTTPException(404, "Link not found")
    if l.status == "ACTIVE":
        l.status, l.revoked_at = "REVOKED", pls._now()
        cards._audit(db, current_user, "PAYMENT_LINK_REVOKED", "payment_link", str(l.id), {})
    await db.commit()
    return {"status": l.status}


@public.get("/{token}")
async def page(token: str, db: AsyncSession = Depends(get_db)):
    try:
        return await pls.public_view(db, await pls.resolve(db, token))
    except pls.LinkError as e:
        _fail(e)


class PayIn(BaseModel):
    phone: str = Field(min_length=9, max_length=20, pattern=r"^[+0-9 ]+$")
    amount: Optional[Decimal] = Field(None, gt=0)


@public.post("/{token}/mpesa")
async def pay(token: str, body: PayIn, db: AsyncSession = Depends(get_db)):
    try:
        a = await pls.pay_mpesa(db, token, body.phone, body.amount)
    except pls.LinkError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    return {"attempt_id": str(a.id), "amount": str(a.amount), "simulated": a.simulated,
            "message": ("Simulated: no real money moves (M-Pesa is not activated yet)." if a.simulated else
                        "Check your phone and enter your M-Pesa PIN to pay.")}


@public.post("/{token}/card")
async def card(token: str, body: CardIn, db: AsyncSession = Depends(get_db)):
    """Start a hosted card checkout; the payer goes to the provider's page (we never see the card)."""
    try:
        link = await pls.resolve(db, token, lock=True)
        p = await cards.start_checkout(db, link, body.amount, body.email, body.phone)
    except pls.LinkError as e:
        await db.rollback()
        _fail(e)
    except cards.CardError as e:
        await db.commit()
        _fail(e)
    out = {"redirect_url": p.redirect_url, "amount": str(p.amount), "currency": p.currency, "simulated": p.simulated,
           "message": "Test checkout: no real money moves." if p.simulated else "Continue on the secure Pesapal page."}
    await db.commit()
    return out
