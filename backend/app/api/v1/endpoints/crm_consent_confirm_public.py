"""M48.S01.T022 public double opt-in confirmation (no login): signed, expiring token from the CONSENT e-mail.
Allow-listed in PUBLIC_ROUTES. GET only validates (mail scanners prefetch links); the visitor's button POST confirms,
storing the time and a keyed hash of the connection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_outbound_service as outbound
from app.services.crm_lead_capture_service import ip_hash

router = APIRouter()


def _email(t: str) -> str:
    email = outbound.email_from_confirm_token(t[:700])
    if not email:
        raise HTTPException(404, "This confirmation link is not valid or has expired.")
    return email


def _masked(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def _state(email: str, row) -> dict:
    status = row.status if row is not None else None
    return {"email": _masked(email), "subscribed": status == "SUBSCRIBED", "pending": status == "PENDING",
            "blocked": status in outbound.SUPPRESSING}


@router.get("")
async def check_confirmation(t: str = Query(..., max_length=700), db: AsyncSession = Depends(get_db)):
    email = _email(t)
    return _state(email, await outbound.consent_for(db, email))


@router.post("")
async def confirm_subscription(request: Request, t: str = Query(..., max_length=700), db: AsyncSession = Depends(get_db)):
    email = _email(t)
    row = await outbound.confirm(db, email, ip_hash(request.client.host if request.client else None))
    await db.commit()
    if row is None:
        raise HTTPException(404, "This confirmation link is not valid or has expired.")
    return _state(email, row)
