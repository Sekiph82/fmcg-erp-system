"""Verification for unauthenticated provider callbacks (no ERP session exists for them)."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request

from app.core.config import settings


def _missing_secret(name: str) -> None:
    # Fail closed in production; development keeps sandbox simulations usable.
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=503, detail=f"{name} is not configured; callback rejected.")


async def verify_mpesa_callback(request: Request) -> None:
    """Daraja callbacks carry no signature: require the shared secret embedded in the callback URL.

    Configure MPESA_CALLBACK_URL as ``https://<host>/api/v1/.../mpesa/callback?token=<MPESA_CALLBACK_SECRET>``.
    """
    secret = settings.MPESA_CALLBACK_SECRET
    if not secret:
        _missing_secret("MPESA_CALLBACK_SECRET")
        return
    if not hmac.compare_digest(request.query_params.get("token", ""), secret):
        raise HTTPException(status_code=403, detail="Invalid callback token.")


async def verify_meta_signature(request: Request) -> None:
    """Meta webhooks sign the raw body with the app secret in X-Hub-Signature-256."""
    secret = settings.WHATSAPP_APP_SECRET
    if not secret:
        _missing_secret("WHATSAPP_APP_SECRET")
        return
    body = await request.body()
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("X-Hub-Signature-256", ""), expected):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")
