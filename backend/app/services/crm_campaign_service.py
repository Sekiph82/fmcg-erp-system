"""M36.S02.T005 segment e-mail campaigns on the consent-aware outbox.

Audience: active customers of the campaign's company (required) whose CRM profile is in the campaign's active
segment and that have an e-mail, so one company's campaign never reaches another's customers. At the
scheduled time the campaign is expanded into CAMPAIGN outbox messages with dedupe key
"camp:<campaign>:<address>" (one message per address, however often the expansion runs). The outbox
enforces consent and suppression and does the rate-limited delivery. Metrics come straight from the outbox
rows and from real (not draft/cancelled) sales orders of the campaign's company that a recipient placed within
30 days after their own e-mail was actually sent. Not exclusive: an order can count for more than one campaign.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMEmailCampaign, CRMOutboundMessage
from app.models.marketing import CRMProfile, CustomerSegment
from app.models.sales import Customer, SalesOrder, SOStatus
from app.services import crm_outbound_service as outbound

logger = logging.getLogger(__name__)
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
PLACEHOLDERS = {"contact_name", "company_name"}
ATTRIBUTION_WINDOW = timedelta(days=30)


def unknown_placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER.findall(text)) - PLACEHOLDERS


def render(text: str, customer: Customer) -> str:
    values = {"contact_name": customer.contact_person or customer.name or "Customer",
              "company_name": customer.name or "your company"}
    # only known placeholders are replaced; any other {text} is left exactly as written
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def _audience(campaign: CRMEmailCampaign):
    # deterministic order: when customers share an address, the oldest customer is the recipient of record
    return (select(Customer).join(CRMProfile, CRMProfile.customer_id == Customer.id)
            .join(CustomerSegment, CustomerSegment.id == CRMProfile.segment_id)
            .where(CRMProfile.segment_id == campaign.segment_id, CustomerSegment.is_active.is_(True),
                   Customer.company_id == campaign.company_id, Customer.is_active.is_(True),
                   Customer.email.isnot(None), Customer.email != "")
            .order_by(Customer.created_at, Customer.id))


async def audience_preview(db: AsyncSession, campaign: CRMEmailCampaign) -> dict:
    customers = (await db.execute(_audience(campaign))).scalars().all()
    emails = {outbound.norm(c.email) for c in customers}
    subscribed = 0
    for e in emails:
        consent = await outbound.consent_for(db, e)
        subscribed += bool(consent and consent.status == "SUBSCRIBED")
    return {"customers": len(customers), "addresses": len(emails), "with_consent": subscribed}


async def expand_due(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Queue messages for campaigns whose time has come, one campaign per transaction (SKIP LOCKED, idempotent
    per address). A campaign that fails is marked FAILED (rolled back, nothing queued) and never blocks the others."""
    now = now or datetime.now(timezone.utc)
    total, failed = 0, set()
    while True:
        q = select(CRMEmailCampaign).where(CRMEmailCampaign.status == "SCHEDULED", CRMEmailCampaign.scheduled_at <= now)
        if failed:
            q = q.where(CRMEmailCampaign.id.notin_(failed))
        campaign = (await db.execute(q.order_by(CRMEmailCampaign.scheduled_at).limit(1)
                                     .with_for_update(skip_locked=True))).scalar_one_or_none()
        if campaign is None:
            return total
        cid = campaign.id
        try:
            total += await _expand_one(db, campaign, now)
            await db.commit()
        except Exception:
            logger.exception("Campaign %s expansion failed", cid)
            await db.rollback()
            failed.add(cid)
            row = (await db.execute(select(CRMEmailCampaign).where(CRMEmailCampaign.id == cid)
                                    .with_for_update(skip_locked=True))).scalar_one_or_none()
            if row is not None and row.status == "SCHEDULED":
                row.status = "FAILED"
            await db.commit()


async def _expand_one(db: AsyncSession, campaign: CRMEmailCampaign, now: datetime) -> int:
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
    return len(seen)


async def stats(db: AsyncSession, campaign: CRMEmailCampaign) -> dict:
    rows = dict((await db.execute(select(CRMOutboundMessage.status, func.count()).where(
        CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%")).group_by(CRMOutboundMessage.status))).all())
    # each recipient's own send time opens their 30-day window; draft/cancelled and other companies' orders never count
    converted = (await db.execute(select(func.count(func.distinct(SalesOrder.customer_id))).join(
        CRMOutboundMessage, CRMOutboundMessage.customer_id == SalesOrder.customer_id).where(
        CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%"), CRMOutboundMessage.status == "SENT",
        CRMOutboundMessage.sent_at.isnot(None), SalesOrder.created_at >= CRMOutboundMessage.sent_at,
        SalesOrder.created_at < CRMOutboundMessage.sent_at + ATTRIBUTION_WINDOW,
        SalesOrder.status.notin_((SOStatus.DRAFT, SOStatus.CANCELLED)),
        SalesOrder.company_id == campaign.company_id))).scalar() or 0
    return {"by_status": rows, "converted_customers": converted,
            "attribution": "customers who received the e-mail and placed a confirmed order within 30 days of their send"}
