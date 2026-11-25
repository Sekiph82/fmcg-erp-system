"""Customer payment links (M45.S01.T021).
Staff (prefix /api/v1/payment-links): create (shown once), list per invoice, revoke — sales.create / finance.create.
Public (prefix /api/v1/public/pay): GET /{token} page data; POST /{token}/mpesa start an STK push. Settlement comes
only from the Daraja callback (/integrations/mpesa/callback)."""
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
from app.models.payments_hub import PaymentLink, PaymentLinkAttempt
from app.services import payment_link_service as pls

router = APIRouter(dependencies=[Depends(require_any_permission(("sales.create", "finance.create", "sales.view", "finance.view")))])
public = APIRouter()
WRITE = ("sales.create", "finance.create")


def _fail(e: pls.LinkError):
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


@router.get("")
async def list_links(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PaymentLink).where(PaymentLink.invoice_id == invoice_id).order_by(PaymentLink.created_at.desc()))).scalars()
    out = []
    for l in rows:
        atts = (await db.execute(select(PaymentLinkAttempt).where(PaymentLinkAttempt.link_id == l.id))).scalars()
        out.append({"id": str(l.id), "status": l.status, "settled_amount": str(l.settled_amount), "expires_at": l.expires_at.isoformat(),
                    "attempts": [{"amount": str(a.amount), "status": a.status, "receipt": a.receipt, "simulated": a.simulated} for a in atts]})
    return out


@router.post("/{lid}/revoke", dependencies=[Depends(require_any_permission(WRITE))])
async def revoke(lid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    l = await db.get(PaymentLink, lid)
    if l is None:
        raise HTTPException(404, "Link not found")
    if l.status == "ACTIVE":
        l.status, l.revoked_at = "REVOKED", pls._now()
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


@public.get("/{token}/card")
async def card(token: str, db: AsyncSession = Depends(get_db)):
    try:
        await pls.resolve(db, token)
    except pls.LinkError as e:
        _fail(e)
    raise HTTPException(503, "Card payments are NOT_CONFIGURED: a card provider is activated only with owner authorization (M47).")
