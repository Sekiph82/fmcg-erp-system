"""SMS OTP sender. Dev mode: console log. Prod: Twilio REST API via httpx."""
from __future__ import annotations
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_sms(to_number: str, otp: str) -> None:
    if settings.OTP_DEV_DELIVERY_MODE:
        logger.info("[DEV OTP SMS] To=%s OTP=%s (dev mode — not sent)", to_number, otp)
        return

    if not settings.SMS_PROVIDER or not settings.SMS_ACCOUNT_SID:
        raise RuntimeError(
            "SMS OTP delivery not configured. Set SMS_PROVIDER=twilio and SMS_ACCOUNT_SID/SMS_AUTH_TOKEN."
        )

    if settings.SMS_PROVIDER == "twilio":
        await _send_twilio(to_number, otp)
    else:
        raise RuntimeError(f"Unknown SMS provider: {settings.SMS_PROVIDER!r}")


async def _send_twilio(to_number: str, otp: str) -> None:
    import httpx

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.SMS_ACCOUNT_SID}/Messages.json"
    )
    body = f"Your {settings.PROJECT_NAME} code: {otp}. Expires in 5 minutes."

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            data={"From": settings.SMS_SENDER_ID, "To": to_number, "Body": body},
            auth=(settings.SMS_ACCOUNT_SID, settings.SMS_AUTH_TOKEN),
        )

    if resp.status_code >= 400:
        raise RuntimeError(f"Twilio SMS delivery failed (HTTP {resp.status_code})")
