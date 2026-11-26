"""Pesapal API 3.0 notifications (M48.S01.T010). Prefix /api/v1/public/card-ipn; no login (allow-listed in PUBLIC_ROUTES).

Pesapal IPNs are not signed (https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/registeripnurl), so
nothing in the request is trusted: an IPN or the payer's return only names an OrderTrackingId we already issued; we then
ask GetTransactionStatus ourselves (card_payment_service.refresh) and act on that answer alone. Replays are idempotent
(row lock + settlement claim) and inside a 5 s window are answered without re-querying the provider.
  GET  /pesapal?OrderTrackingId=&OrderNotificationType=IPNCHANGE&OrderMerchantReference=   (we register GET)
  POST /pesapal {OrderTrackingId, OrderNotificationType, OrderMerchantReference}            (same, if registered as POST)
  GET  /return?OrderTrackingId=&OrderMerchantReference=   payer's browser after checkout (callback_url): plain page
"""
from __future__ import annotations

import html

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.m48_payments import CardPayment
from app.services import card_payment_service as cards

router = APIRouter()


async def _handle(db: AsyncSession, tracking_id: str, merchant_ref: str) -> CardPayment | None:
    p = (await db.execute(select(CardPayment).where(CardPayment.order_tracking_id == tracking_id))).scalar_one_or_none()
    if p is None or (merchant_ref and merchant_ref != p.merchant_reference):
        return None
    try:
        p = await cards.refresh(db, p.id, notified=True)
    except cards.CardError:
        await db.rollback()
        return None
    await db.commit()
    return p


async def _ipn(db: AsyncSession, tracking_id: str, kind: str, merchant_ref: str) -> JSONResponse:
    p = await _handle(db, tracking_id, merchant_ref)
    # documented acknowledgement; status 500 tells Pesapal to try again later (unknown order or status not verified)
    return JSONResponse({"orderNotificationType": kind, "orderTrackingId": tracking_id,
                         "orderMerchantReference": merchant_ref, "status": 200 if p is not None else 500})


@router.get("/pesapal")
async def ipn_get(OrderTrackingId: str = Query(..., min_length=8, max_length=64),
                  OrderNotificationType: str = Query("IPNCHANGE", max_length=20),
                  OrderMerchantReference: str = Query("", max_length=50), db: AsyncSession = Depends(get_db)):
    return await _ipn(db, OrderTrackingId, OrderNotificationType, OrderMerchantReference)


class IpnIn(BaseModel):
    OrderTrackingId: str = Field(min_length=8, max_length=64)
    OrderNotificationType: str = Field("IPNCHANGE", max_length=20)
    OrderMerchantReference: str = Field("", max_length=50)


@router.post("/pesapal")
async def ipn_post(body: IpnIn, db: AsyncSession = Depends(get_db)):
    return await _ipn(db, body.OrderTrackingId, body.OrderNotificationType, body.OrderMerchantReference)


@router.get("/return", response_class=HTMLResponse)
async def payer_return(OrderTrackingId: str = Query(..., min_length=8, max_length=64),
                       OrderMerchantReference: str = Query("", max_length=50), db: AsyncSession = Depends(get_db)):
    p = await _handle(db, OrderTrackingId, OrderMerchantReference)
    if p is None:
        msg = "We could not confirm this payment yet. If you paid, it will show on your invoice once Pesapal confirms it."
    elif p.status == "COMPLETED":
        msg = f"Thank you: {p.currency} {p.amount} received" + (" (test payment, no real money)." if p.simulated else ".")
    elif p.status in ("FAILED", "INVALID"):
        msg = "The card payment did not go through. You can try again from your payment link."
    else:
        msg = "Your payment is being processed. You can close this page."
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                        f"<title>POVU payment</title><p style='font-family:sans-serif;margin:2rem'>{html.escape(msg)}</p>")
