"""Deliverability (M44.S01.T011).
Public: POST /public/mail-events/{provider} (signature verified; allow-listed). Staff: /deliverability/* diagnostics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_db
from app.models.crm import CRMContactConsent, MailFeedbackEvent
from app.services import deliverability_service as dv

public_router = APIRouter()
router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view", "marketing.edit", "crm.view_all")))])


@public_router.post("/{provider}")
async def mail_events(provider: Literal["mailgun", "sendgrid", "generic"], request: Request, db: AsyncSession = Depends(get_db),
                      x_twilio_email_event_webhook_signature: str = Header(""),
                      x_twilio_email_event_webhook_timestamp: str = Header(""), x_povu_signature: str = Header("")):
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "Too large")
    try:
        if provider == "mailgun":
            import json
            events = dv.verify_mailgun(json.loads(raw or b"{}"))
        elif provider == "sendgrid":
            events = dv.verify_sendgrid(raw, x_twilio_email_event_webhook_signature, x_twilio_email_event_webhook_timestamp)
        else:
            events = dv.verify_generic(raw, x_povu_signature)
    except dv.FeedbackError as e:
        raise HTTPException(e.status_code, str(e)) from None
    except ValueError:
        raise HTTPException(400, "Unreadable event body") from None
    counts = await dv.apply(db, provider, events)
    await db.commit()
    return counts


@router.get("/summary")
async def summary(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    kinds = dict((await db.execute(select(MailFeedbackEvent.kind, func.count()).where(
        MailFeedbackEvent.received_at >= since).group_by(MailFeedbackEvent.kind))).all())
    ignored = (await db.execute(select(func.count()).select_from(MailFeedbackEvent).where(
        MailFeedbackEvent.received_at >= since, MailFeedbackEvent.applied.is_(False),
        MailFeedbackEvent.kind.in_(("BOUNCED", "COMPLAINED", "UNSUBSCRIBED"))))).scalar_one()
    suppressed = dict((await db.execute(select(CRMContactConsent.status, func.count()).where(
        CRMContactConsent.status.in_(("BOUNCED", "COMPLAINED", "UNSUBSCRIBED"))).group_by(CRMContactConsent.status))).all())
    from app.core.config import settings
    return {"events": kinds, "unmatched_ignored": ignored, "suppressed": suppressed,
            "providers": {"mailgun": bool(settings.MAIL_EVENTS_MAILGUN_SIGNING_KEY),
                          "sendgrid": bool(settings.MAIL_EVENTS_SENDGRID_PUBLIC_KEY),
                          "generic": bool(settings.MAIL_EVENTS_GENERIC_SECRET)}}


@router.get("/dns-plan")
async def dns_plan(domain: str = Query(..., max_length=253), relay_include: str = Query("", max_length=200)):
    try:
        return dv.dns_plan(domain, relay_include)
    except dv.FeedbackError as e:
        raise HTTPException(e.status_code, str(e)) from None


class CheckIn(BaseModel):
    spf: str = Field("", max_length=1000)
    dkim: str = Field("", max_length=5000)
    dmarc: str = Field("", max_length=1000)
    relay_include: str = Field("", max_length=200)


@router.post("/check")
async def check(body: CheckIn):
    return dv.check_records(body.spf, body.dkim, body.dmarc, body.relay_include)
