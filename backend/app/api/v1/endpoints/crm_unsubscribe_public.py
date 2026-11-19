"""Public unsubscribe (no login): signed token from every CRM e-mail. Allow-listed in PUBLIC_ROUTES.
GET only validates (mail scanners prefetch links); the visitor's click or the RFC 8058 one-click POST
unsubscribes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_outbound_service as outbound

router = APIRouter()


def _email(t: str) -> str:
    email = outbound.email_from_token(t[:600])
    if not email:
        raise HTTPException(404, "This unsubscribe link is not valid.")
    return email


def _masked(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


@router.get("")
async def check_unsubscribe(t: str = Query(..., max_length=600), db: AsyncSession = Depends(get_db)):
    email = _email(t)
    consent = await outbound.consent_for(db, email)
    return {"email": _masked(email), "unsubscribed": bool(consent and consent.status in outbound.SUPPRESSING)}


@router.post("")
async def unsubscribe(t: str = Query(..., max_length=600), db: AsyncSession = Depends(get_db)):
    email = _email(t)
    consent = await outbound.consent_for(db, email)
    if not (consent and consent.status in outbound.SUPPRESSING):
        await outbound.record_consent(db, email, "UNSUBSCRIBED", "unsubscribe-link")
        await db.commit()
    return {"email": _masked(email), "unsubscribed": True}
