"""Account-based marketing (M36.S05.T005): target-account groups of ERP customers, buying committees per account,
cross-contact engagement from real activity, coordinated consent-aware campaigns and simple attribution.

Engagement is never a made-up score: every figure is a count/sum of recorded rows (CRM activities, meetings,
e-mails sent and received, helpdesk tickets, sales orders) for the account and its committee addresses.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMAccountContact, CRMAccountGroup, CRMAccountGroupMember

ROLES = ("DECISION_MAKER", "BUYER", "INFLUENCER", "CHAMPION", "USER", "BLOCKER")
KEY_ROLES = ("DECISION_MAKER", "BUYER", "CHAMPION")


class ABMError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


async def committee(db: AsyncSession, customer_id: uuid.UUID) -> list[CRMAccountContact]:
    return list((await db.execute(select(CRMAccountContact).where(CRMAccountContact.customer_id == customer_id)
                                  .order_by(CRMAccountContact.committee_role, CRMAccountContact.full_name))).scalars().all())


async def engagement(db: AsyncSession, customer_id: uuid.UUID, days: int = 90) -> dict:
    """Recorded touches for one account over the last `days`, across all committee contacts."""
    from app.models.crm import CRMActivity, CRMOutboundMessage, CRMRecord
    from app.models.email_integration import EmailMessage
    from app.models.helpdesk import HelpdeskTicket
    from app.models.meetings import MeetingRecord
    from app.models.sales import SalesOrder, SOLine, SOStatus

    since = datetime.now(timezone.utc) - timedelta(days=days)
    naive_since = since.replace(tzinfo=None)
    contacts = await committee(db, customer_id)
    emails = sorted({c.email.lower() for c in contacts if c.email})
    activities = (await db.execute(select(func.count()).select_from(CRMActivity).join(CRMRecord, CRMRecord.id == CRMActivity.crm_record_id)
                                   .where(CRMRecord.assigned_customer_id == customer_id, CRMActivity.created_at >= naive_since))).scalar_one()
    meetings = (await db.execute(select(func.count()).select_from(MeetingRecord).where(
        MeetingRecord.customer_id == customer_id, MeetingRecord.scheduled_at >= naive_since,
        MeetingRecord.status != "CANCELLED"))).scalar_one()
    sent = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.status == "SENT", CRMOutboundMessage.sent_at >= since,
        or_(CRMOutboundMessage.customer_id == customer_id, func.lower(CRMOutboundMessage.to_email).in_(emails or [""]))))).scalar_one()
    received = (await db.execute(select(func.count()).select_from(EmailMessage).where(
        func.lower(EmailMessage.from_email).in_(emails or [""]), EmailMessage.received_at >= since))).scalar_one()
    replied_from = set((await db.execute(select(func.lower(EmailMessage.from_email)).where(
        func.lower(EmailMessage.from_email).in_(emails or [""]), EmailMessage.received_at >= since).distinct())).scalars().all())
    tickets = (await db.execute(select(func.count()).select_from(HelpdeskTicket).where(
        HelpdeskTicket.customer_id == customer_id, HelpdeskTicket.created_at >= naive_since))).scalar_one()
    orders, revenue = (await db.execute(select(func.count(func.distinct(SalesOrder.id)),
                                               func.coalesce(func.sum(SOLine.ordered_quantity * SOLine.unit_price), 0))
                                        .join(SOLine, SOLine.so_id == SalesOrder.id)
                                        .where(SalesOrder.customer_id == customer_id, SalesOrder.status != SOStatus.CANCELLED,
                                               SalesOrder.order_date >= since.date()))).one()
    roles = {c.committee_role for c in contacts}
    return {
        "days": days, "contacts": len(contacts), "contacts_engaged": len(replied_from),
        "key_roles_covered": [r for r in KEY_ROLES if r in roles], "key_roles_missing": [r for r in KEY_ROLES if r not in roles],
        "activities": activities, "meetings": meetings, "emails_sent": sent, "emails_received": received,
        "tickets": tickets, "orders": orders, "order_value": float(revenue or 0),
    }


async def group_overview(db: AsyncSession, group: CRMAccountGroup, days: int = 90) -> dict:
    from app.models.sales import Customer
    members = (await db.execute(select(CRMAccountGroupMember, Customer).join(Customer, Customer.id == CRMAccountGroupMember.customer_id)
                                .where(CRMAccountGroupMember.group_id == group.id).order_by(CRMAccountGroupMember.tier, Customer.name))).all()
    accounts = []
    for m, c in members:
        e = await engagement(db, c.id, days)
        accounts.append({"customer_id": str(c.id), "name": c.name, "code": c.code, "tier": m.tier,
                         "parent_customer_id": None, **e})
    totals = {k: sum(a[k] for a in accounts) for k in ("activities", "meetings", "emails_sent", "emails_received", "orders", "order_value")}
    return {"id": str(group.id), "name": group.name, "description": group.description, "accounts": accounts, "totals": totals,
            "campaign_started_at": group.campaign_started_at.isoformat() if group.campaign_started_at else None,
            "attribution": await attribution(db, group)}


async def attribution(db: AsyncSession, group: CRMAccountGroup) -> Optional[dict]:
    """Orders of the group's accounts since the coordinated campaign started (influenced revenue, not causal)."""
    if group.campaign_started_at is None:
        return None
    from app.models.sales import SalesOrder, SOLine, SOStatus
    ids = select(CRMAccountGroupMember.customer_id).where(CRMAccountGroupMember.group_id == group.id)
    n, value = (await db.execute(select(func.count(func.distinct(SalesOrder.id)), func.coalesce(func.sum(SOLine.ordered_quantity * SOLine.unit_price), 0))
                                 .join(SOLine, SOLine.so_id == SalesOrder.id)
                                 .where(SalesOrder.customer_id.in_(ids), SalesOrder.status != SOStatus.CANCELLED,
                                        SalesOrder.order_date >= group.campaign_started_at.date()))).one()
    return {"since": group.campaign_started_at.date().isoformat(), "orders": n, "order_value": float(value or 0),
            "note": "Orders from the group's accounts after the campaign started — influenced, not proven caused."}


async def campaign_company(db: AsyncSession, group: CRMAccountGroup, company_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
    """M48.S01.T023 (audit F4): one campaign speaks for one company. Without `company_id` the group's accounts must
    all belong to the same company (or none); a mixed group needs an explicit company_id."""
    from app.models.sales import Customer
    companies = set((await db.execute(select(Customer.company_id).join(
        CRMAccountGroupMember, CRMAccountGroupMember.customer_id == Customer.id)
        .where(CRMAccountGroupMember.group_id == group.id).distinct())).scalars().all())
    if company_id is not None:
        if company_id not in companies:
            raise ABMError(422, "No account of this group belongs to that company.")
        return company_id
    if len(companies) > 1:
        raise ABMError(422, "This group has accounts of several companies; choose company_id.")
    return next(iter(companies), None)


async def run_campaign(db: AsyncSession, group: CRMAccountGroup, subject: str, body: str, roles: Optional[list[str]],
                       created_by: str, company_id: Optional[uuid.UUID] = None, before_queue=None) -> dict:
    """Queue one e-mail per committee contact of the group's accounts of one company through the consent-aware outbox
    (contacts without consent are suppressed by the outbox, never sent). Idempotent per group + subject + address.
    `before_queue(n_recipients)` runs before anything is queued (cap and approval checks)."""
    from app.models.sales import Customer
    from app.services import crm_outbound_service as outbound
    if roles and set(roles) - set(ROLES):
        raise ABMError(422, "Unknown committee role.")
    rows = (await db.execute(select(CRMAccountContact, Customer).join(Customer, Customer.id == CRMAccountContact.customer_id)
                             .join(CRMAccountGroupMember, and_(CRMAccountGroupMember.customer_id == CRMAccountContact.customer_id,
                                                               CRMAccountGroupMember.group_id == group.id))
                             .where(CRMAccountContact.email.is_not(None),
                                    Customer.company_id.is_(None) if company_id is None else Customer.company_id == company_id))).all()
    targets, seen = [], set()
    for contact, customer in rows:
        if roles and contact.committee_role not in roles:
            continue
        email = outbound.norm(contact.email)
        if not email or email in seen:
            continue
        seen.add(email)
        targets.append((contact, customer, email))
    if before_queue is not None:
        await before_queue(len(targets))
    queued = suppressed = 0
    key = uuid.uuid5(uuid.NAMESPACE_URL, f"{group.id}:{subject}:{body}").hex[:12]
    for contact, customer, email in targets:
        text = body.replace("{contact_name}", contact.full_name).replace("{company_name}", customer.name)
        msg = await outbound.queue(db, to_email=email, subject=subject.replace("{company_name}", customer.name)[:300], body=text,
                                   purpose="CAMPAIGN", dedupe_key=f"abm:{key}:{email}", customer_id=customer.id,
                                   created_by=f"abm:{created_by}"[:100])
        if msg.status in ("QUEUED", "SENT"):
            queued += 1
        else:
            suppressed += 1
    if queued and group.campaign_started_at is None:
        group.campaign_started_at = datetime.now(timezone.utc)
    await db.flush()
    return {"queued": queued, "suppressed": suppressed}
