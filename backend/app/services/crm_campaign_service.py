"""M36.S02.T005 segment e-mail campaigns on the consent-aware outbox.

Audience: active customers whose CRM profile is in the campaign segment and that have an e-mail (limited to
the campaign's company when set, so one company's campaign never reaches another's customers). At the
scheduled time the campaign is expanded into CAMPAIGN outbox messages with dedupe key
"camp:<campaign>:<address>" (one message per address, however often the expansion runs). The outbox
enforces consent and suppression and does the rate-limited delivery. Metrics come straight from the outbox
rows and from sales orders the recipients placed within 30 days after the send (last-touch, stated plainly).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMEmailCampaign, CRMOutboundMessage
from app.models.marketing import CRMProfile
from app.models.sales import Customer, SalesOrder
from app.services import crm_outbound_service as outbound

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
ATTRIBUTION_WINDOW = timedelta(days=30)


def render(text: str, customer: Customer) -> str:
    values = {"contact_name": customer.contact_person or customer.name or "", "company_name": customer.name or ""}
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), text)


def _audience(campaign: CRMEmailCampaign):
    q = (select(Customer).join(CRMProfile, CRMProfile.customer_id == Customer.id)
         .where(CRMProfile.segment_id == campaign.segment_id, Customer.is_active.is_(True),
                Customer.email.isnot(None), Customer.email != ""))
    if campaign.company_id:
        q = q.where(Customer.company_id == campaign.company_id)
    return q


async def audience_preview(db: AsyncSession, campaign: CRMEmailCampaign) -> dict:
    customers = (await db.execute(_audience(campaign))).scalars().all()
    emails = {outbound.norm(c.email) for c in customers}
    subscribed = 0
    for e in emails:
        consent = await outbound.consent_for(db, e)
        subscribed += bool(consent and consent.status == "SUBSCRIBED")
    return {"customers": len(customers), "addresses": len(emails), "with_consent": subscribed}


async def expand_due(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Queue messages for campaigns whose time has come (SKIP LOCKED, idempotent per address). Commits."""
    now = now or datetime.now(timezone.utc)
    due = (await db.execute(select(CRMEmailCampaign).where(
        CRMEmailCampaign.status == "SCHEDULED", CRMEmailCampaign.scheduled_at <= now)
        .with_for_update(skip_locked=True))).scalars().all()
    total = 0
    for campaign in due:
        seen = set()
        for customer in (await db.execute(_audience(campaign))).scalars().all():
            email = outbound.norm(customer.email)
            if email in seen:
                continue
            seen.add(email)
            await outbound.queue(db, to_email=email, subject=render(campaign.subject, customer),
                                 body=render(campaign.body, customer), purpose="CAMPAIGN",
                                 dedupe_key=f"camp:{campaign.id}:{email}", customer_id=customer.id,
                                 created_by=f"campaign:{campaign.name}"[:100])
        campaign.status, campaign.queued_at, campaign.audience_size = "QUEUED", now, len(seen)
        total += len(seen)
    await db.commit()
    return total


async def stats(db: AsyncSession, campaign: CRMEmailCampaign) -> dict:
    rows = dict((await db.execute(select(CRMOutboundMessage.status, func.count()).where(
        CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%")).group_by(CRMOutboundMessage.status))).all())
    converted = 0
    if campaign.queued_at:
        sent_to = select(CRMOutboundMessage.customer_id).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%"), CRMOutboundMessage.status == "SENT")
        converted = (await db.execute(select(func.count(func.distinct(SalesOrder.customer_id))).where(
            SalesOrder.customer_id.in_(sent_to), SalesOrder.created_at >= campaign.queued_at,
            SalesOrder.created_at < campaign.queued_at + ATTRIBUTION_WINDOW))).scalar() or 0
    return {"by_status": rows, "converted_customers": converted,
            "attribution": "customers who received the e-mail and placed an order within 30 days"}
