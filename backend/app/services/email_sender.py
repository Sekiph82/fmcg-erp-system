"""Email OTP sender. Dev mode: console log. Prod: stdlib smtplib."""
from __future__ import annotations
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(to_email: str, otp: str) -> None:
    if settings.OTP_DEV_DELIVERY_MODE:
        logger.info("[DEV OTP EMAIL] To=%s OTP=%s (dev mode — not sent)", to_email, otp)
        return

    if not settings.SMTP_HOST:
        raise RuntimeError(
            "Email OTP delivery not configured. Set SMTP_HOST (and optionally SMTP_USERNAME/PASSWORD)."
        )

    await asyncio.to_thread(_send_smtp, to_email, otp)


def _send_smtp(to_email: str, otp: str) -> None:
    subject = f"Your {settings.PROJECT_NAME} verification code"
    body = (
        f"Your verification code is: {otp}\n\n"
        f"This code expires in 5 minutes. Do not share it with anyone."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
