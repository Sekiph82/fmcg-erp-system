"""Short notices to shops on their phone: WhatsApp when a WhatsApp sender is set up, else SMS (Africa's Talking or
Twilio), else nothing (logged). Credentials come from Integrations → Provider keys (provider_credentials.py).

Used for "your order is on the way" when the driver starts the trip (owner 2026-11-20).
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


def channel() -> Optional[str]:
    if settings.WHATSAPP_PHONE_NUMBER_ID and settings.WHATSAPP_ACCESS_TOKEN:
        return "whatsapp"
    if settings.SMS_PROVIDER in ("africastalking", "twilio") and settings.SMS_ACCOUNT_SID and settings.SMS_AUTH_TOKEN:
        return "sms"
    return None


async def send_sms(to: str, body: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        if settings.SMS_PROVIDER == "africastalking":
            sandbox = settings.SMS_ACCOUNT_SID == "sandbox"
            url = f"https://api.{'sandbox.' if sandbox else ''}africastalking.com/version1/messaging"
            data = {"username": settings.SMS_ACCOUNT_SID, "to": to, "message": body}
            if settings.SMS_SENDER_ID:
                data["from"] = settings.SMS_SENDER_ID
            resp = await client.post(url, data=data, headers={"apiKey": settings.SMS_AUTH_TOKEN, "Accept": "application/json"})
        elif settings.SMS_PROVIDER == "twilio":
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.SMS_ACCOUNT_SID}/Messages.json",
                data={"From": settings.SMS_SENDER_ID, "To": to, "Body": body},
                auth=(settings.SMS_ACCOUNT_SID, settings.SMS_AUTH_TOKEN))
        else:
            raise RuntimeError("SMS is not set up")
    if resp.status_code >= 400:
        raise RuntimeError(f"SMS provider answered HTTP {resp.status_code}")


async def send_whatsapp(to: str, body: str) -> None:
    from app.api.v1.endpoints.whatsapp import _meta_send_text

    _, error = await _meta_send_text(settings.WHATSAPP_PHONE_NUMBER_ID, settings.WHATSAPP_ACCESS_TOKEN, to, body)
    if error:
        raise RuntimeError(f"WhatsApp: {error[:200]}")


async def notify_customer(phone: Optional[str], body: str) -> str:
    """Returns how it went: whatsapp / sms / no-phone / not-configured / failed. Never raises."""
    if not phone or len(phone.strip()) < 9:
        return "no-phone"
    via = channel()
    if via is None:
        log.info("customer notice not sent (no WhatsApp/SMS provider set up): %s", body[:80])
        return "not-configured"
    if via == "whatsapp":   # M47.S01.T003: a customer who replied STOP gets no WhatsApp notice (SMS if configured)
        try:
            from app.api.v1.endpoints.whatsapp import send_blocked_reason
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                blocked = await send_blocked_reason(db, phone.strip())
        except Exception:
            blocked = "consent check unavailable"
        if blocked:
            sms_ok = settings.SMS_PROVIDER in ("africastalking", "twilio") and settings.SMS_ACCOUNT_SID and settings.SMS_AUTH_TOKEN
            if not sms_ok:
                log.info("customer notice not sent by WhatsApp: %s", blocked)
                return "opted-out"
            via = "sms"
    try:
        await (send_whatsapp if via == "whatsapp" else send_sms)(phone.strip(), body)
        return via
    except Exception as exc:  # a notice must never break the trip
        log.warning("customer notice via %s to %s failed: %s", via, phone, exc)
        return "failed"


async def notify_trip_started(trip_id) -> dict:
    """Each shop on a trip that has just left: 'your order is on the way' with the portal link."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.delivery import TripOrder
    from app.models.sales import Customer, SalesOrder, Shipment

    counts: dict = {}
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(TripOrder.delivery_sequence, SalesOrder.order_no, Customer.name, Customer.phone)
                                 .join(Shipment, Shipment.id == TripOrder.shipment_id)
                                 .join(SalesOrder, SalesOrder.id == Shipment.so_id)
                                 .join(Customer, Customer.id == SalesOrder.customer_id)
                                 .where(TripOrder.trip_id == trip_id).order_by(TripOrder.delivery_sequence))).all()
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/portal"
    for _seq, order_no, name, phone in rows:
        body = (f"{settings.PROJECT_NAME}: hello {name}, your order {order_no} is on the way today. "
                f"Follow it live: {link}")
        result = await notify_customer(phone, body)
        counts[result] = counts.get(result, 0) + 1
    return counts
