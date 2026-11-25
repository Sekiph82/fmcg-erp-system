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


def variant_for(campaign: CRMEmailCampaign, email: str) -> str:
    """Deterministic A/B split (same recipient, same variant on every retry)."""
    if not campaign.ab_split_pct:
        return "A"
    import hashlib
    h = int(hashlib.sha256(f"{campaign.id}:{email}".encode()).hexdigest()[:8], 16) % 100
    return "B" if h < campaign.ab_split_pct else "A"


async def _send_after(db: AsyncSession, campaign: CRMEmailCampaign, email: str, now: datetime) -> Optional[datetime]:
    """Send-time optimisation: the recipient's usual opening hour within the next 24 h (first-party evidence only)."""
    if not campaign.send_time_optimize:
        return None
    from zoneinfo import ZoneInfo
    from app.services.crm_workspace_service import send_time
    hint = await send_time(db, email)
    if hint["suggested_hour"] is None:
        return None
    tz = ZoneInfo(hint["time_zone"])
    local = now.astimezone(tz)
    at = local.replace(hour=hint["suggested_hour"], minute=0, second=0, microsecond=0)
    if at <= local:
        at = at + timedelta(days=1)
    return at.astimezone(timezone.utc)


async def _expand_one(db: AsyncSession, campaign: CRMEmailCampaign, now: datetime) -> int:
    from app.models.crm import CRMContact, EmailDesign
    from app.services import email_design_service as eds
    seen = set()
    for customer in (await db.execute(_audience(campaign))).scalars().all():
        email = outbound.norm(customer.email)
        if email in seen:
            continue
        seen.add(email)
        variant = variant_for(campaign, email)                # M44.S01.T012 A/B
        subject = campaign.variant_b_subject if variant == "B" and campaign.variant_b_subject else campaign.subject
        body = campaign.variant_b_body if variant == "B" and campaign.variant_b_body else campaign.body
        design_id = campaign.variant_b_design_id if variant == "B" and campaign.variant_b_design_id else campaign.design_id
        text, html_body = render(body, customer), None
        if design_id:                                         # M44.S01.T001 designed e-mail
            d = await db.get(EmailDesign, design_id)
            contact = (await db.execute(select(CRMContact).where(CRMContact.email == email))).scalars().first()
            vals = {"company_name": customer.name, "contact_name": getattr(customer, "contact_person", None) or customer.name,
                    "lifecycle": contact.lifecycle_stage if contact else None,
                    "channel": getattr(getattr(customer, "channel", None), "value", getattr(customer, "channel", None))}
            vals["first_name"] = (vals["contact_name"] or "").split(" ")[0]
            text, html_body = eds.render_text(d.document, vals), eds.render_html(d.document, vals, d.preheader or "")
        msg = await outbound.queue(db, to_email=email, subject=render(subject, customer),
                                   body=text, body_html=html_body, purpose="CAMPAIGN",
                                   dedupe_key=f"camp:{campaign.id}:{email}", customer_id=customer.id,
                                   created_by=f"campaign:{campaign.name}"[:100],
                                   track=bool(campaign.track_engagement),
                                   send_after=await _send_after(db, campaign, email, now))
        msg.ab_variant = variant if campaign.ab_split_pct else None
    campaign.status, campaign.queued_at, campaign.audience_size = "QUEUED", now, len(seen)
    return len(seen)


async def ab_result(db: AsyncSession, campaign: CRMEmailCampaign, min_per_arm: int = 100) -> dict:
    """Human click rate per variant; a winner only when both arms are large enough and a two-proportion z-test
    gives p < 0.05. Otherwise 'no winner' — never a declared winner from noise."""
    import math
    from app.models.crm import CRMEmailEvent, CRMOutboundMessage
    arms = {}
    for v in ("A", "B"):
        sent = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%"), CRMOutboundMessage.ab_variant == v,
            CRMOutboundMessage.status == "SENT"))).scalar_one()
        clicked = (await db.execute(select(func.count(func.distinct(CRMEmailEvent.message_id))).join(
            CRMOutboundMessage, CRMOutboundMessage.id == CRMEmailEvent.message_id).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{campaign.id}:%"), CRMOutboundMessage.ab_variant == v,
            CRMEmailEvent.kind == "CLICK", CRMEmailEvent.is_machine.is_(False)))).scalar_one()
        arms[v] = {"sent": sent, "clicked": clicked, "rate": round(clicked / sent, 4) if sent else None}
    a, b = arms["A"], arms["B"]
    result = {"arms": arms, "winner": None, "p_value": None, "rule": f"two-proportion z-test, p<0.05, ≥{min_per_arm} per arm"}
    if a["sent"] >= min_per_arm and b["sent"] >= min_per_arm:
        p = (a["clicked"] + b["clicked"]) / (a["sent"] + b["sent"])
        se = math.sqrt(p * (1 - p) * (1 / a["sent"] + 1 / b["sent"])) if 0 < p < 1 else 0
        if se:
            z = (b["rate"] - a["rate"]) / se
            pv = math.erfc(abs(z) / math.sqrt(2))
            result["p_value"] = round(pv, 4)
            if pv < 0.05:
                result["winner"] = "B" if z > 0 else "A"
    result["verdict"] = result["winner"] or "no winner (not enough evidence)"
    return result


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
