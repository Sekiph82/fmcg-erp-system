"""M36.S02.T001 website lead capture into the native CRM: validated public submissions with honeypot
spam trap, database-backed rate limits (safe across API workers), consent capture, UTM/source
attribution and deduplication onto existing open leads."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import (
    CRMActivity, CRMActivityResult, CRMActivityType, CRMLeadForm, CRMLeadSubmission, CRMRecord, CRMRecordType,
    CRMSourceType, CRMStatus,
)

PER_IP_LIMIT = (5, timedelta(minutes=10))
PER_FORM_LIMIT = (30, timedelta(minutes=1))


class LeadSubmission(BaseModel):
    company_name: Optional[str] = Field(None, max_length=200)   # required unless left out for a known visitor
    contact_person_name: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50, pattern=r"^[0-9+()\-\s]{6,50}$")
    message: Optional[str] = Field(None, max_length=2000)
    consent: bool = False
    website: Optional[str] = Field(None, max_length=200)  # honeypot: hidden from people, filled by bots
    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=100)
    utm_term: Optional[str] = Field(None, max_length=100)
    utm_content: Optional[str] = Field(None, max_length=100)
    referrer: Optional[str] = Field(None, max_length=500)
    landing_page: Optional[str] = Field(None, max_length=500)
    visitor: Optional[str] = Field(None, min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")   # analytics visitor id


class MissingField(Exception):
    pass


# ── M47.S01.T010 form shortening ("skip if known") ──────────────────────────
SKIPPABLE = ("company_name", "contact_person_name", "contact_email", "contact_phone")


async def skip_list(db: AsyncSession, form: CRMLeadForm) -> list[str]:
    from app.models.m47_platform import LeadFormSetting
    row = await db.get(LeadFormSetting, form.id)
    return [f for f in (row.skip_if_known if row else []) if f in SKIPPABLE]


async def set_skip_list(db: AsyncSession, form: CRMLeadForm, fields: list[str]) -> list[str]:
    from app.models.m47_platform import LeadFormSetting
    bad = [f for f in fields if f not in SKIPPABLE]
    if bad:
        raise ValueError(f"Cannot skip: {', '.join(bad)}.")
    row = await db.get(LeadFormSetting, form.id)
    clean = sorted(set(fields))
    if row is None:
        db.add(LeadFormSetting(form_id=form.id, skip_if_known=clean))
    else:
        row.skip_if_known = clean
    return clean


async def known_values(db: AsyncSession, visitor: Optional[str]) -> dict[str, str]:
    """Values we already hold for a recognised visitor: a web identity (exists only with marketing consent) whose
    latest consent still allows marketing, linked by e-mail to a CRM contact. Server-side only, never sent back."""
    from app.models.crm import CRMContact, CRMContactAssociation, WebIdentity
    from app.models.sales import Customer
    from app.services import web_analytics_service as wa
    if not visitor:
        return {}
    vh = wa.hashed("v", visitor)
    consent = await wa._latest_consent(db, vh)
    ident = await db.get(WebIdentity, vh)
    if consent is None or not consent.marketing or ident is None:
        return {}
    c = (await db.execute(select(CRMContact).where(func.lower(CRMContact.email) == ident.email.lower()))).scalars().first()
    if c is None:
        return {}
    company = (await db.execute(select(Customer.name).join(CRMContactAssociation, CRMContactAssociation.object_id == Customer.id)
                                .where(CRMContactAssociation.contact_id == c.id, CRMContactAssociation.object_type == "customer")
                                .limit(1))).scalar()
    vals = {"company_name": company, "contact_person_name": c.full_name, "contact_email": c.email, "contact_phone": c.phone}
    return {k: v for k, v in vals.items() if v}


async def omitted(db: AsyncSession, form: CRMLeadForm, visitor: Optional[str]) -> list[str]:
    skip = await skip_list(db, form)
    if not skip:
        return []
    known = await known_values(db, visitor)
    return [f for f in skip if f in known]


class RateLimited(Exception):
    pass


class ConsentRequired(Exception):
    pass


def ip_hash(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()


def _clean(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


async def _check_rate(db: AsyncSession, form: CRMLeadForm, hashed: Optional[str], now: datetime) -> None:
    if hashed:
        n = (await db.execute(select(func.count()).where(
            CRMLeadSubmission.ip_hash == hashed, CRMLeadSubmission.received_at >= now - PER_IP_LIMIT[1]))).scalar()
        if n >= PER_IP_LIMIT[0]:
            raise RateLimited()
    n = (await db.execute(select(func.count()).where(
        CRMLeadSubmission.form_id == form.id, CRMLeadSubmission.received_at >= now - PER_FORM_LIMIT[1]))).scalar()
    if n >= PER_FORM_LIMIT[0]:
        raise RateLimited()


async def submit(db: AsyncSession, form: CRMLeadForm, body: LeadSubmission, ip: Optional[str]) -> CRMLeadSubmission:
    """Record the submission and create or update the lead. Commits. Raises RateLimited / ConsentRequired."""
    from app.services import crm_intelligence_service as intel
    from app.services.crm_pipeline_service import _next_lead_code

    now = datetime.now(timezone.utc)
    hashed = ip_hash(ip)
    await _check_rate(db, form, hashed, now)
    if body.visitor:   # fields the form left out for a recognised visitor are filled from what we hold
        skipped = await omitted(db, form, body.visitor)
        if skipped:
            known = await known_values(db, body.visitor)
            body = body.model_copy(update={f: known[f] for f in skipped if not getattr(body, f)})
    if not (body.company_name or "").strip() and not _clean(body.website):
        raise MissingField("Company is required.")
    email = str(body.contact_email).lower() if body.contact_email else None
    sub = CRMLeadSubmission(
        form_id=form.id, received_at=now, ip_hash=hashed, status="ACCEPTED", contact_email=email,
        consent_given=body.consent, consent_text=form.consent_text if body.consent else None,
        utm_source=_clean(body.utm_source), utm_medium=_clean(body.utm_medium), utm_campaign=_clean(body.utm_campaign),
        utm_term=_clean(body.utm_term), utm_content=_clean(body.utm_content), referrer=_clean(body.referrer),
        landing_page=_clean(body.landing_page))
    if _clean(body.website):  # honeypot filled: keep a trace, create nothing
        sub.status, sub.contact_email = "SPAM", None
        db.add(sub)
        await db.commit()
        return sub
    if form.require_consent and not body.consent:
        sub.status, sub.contact_email = "REJECTED", None  # counted by the rate limit, nothing else kept
        db.add(sub)
        await db.commit()
        raise ConsentRequired()
    phone = _clean(body.contact_phone)
    if email and body.consent and form.consent_text:
        from app.services.crm_outbound_service import record_consent

        await record_consent(db, email, "SUBSCRIBED", f"form:{form.slug}", form.consent_text)  # never lifts an unsubscribe
    existing = None
    if email:  # dedupe on e-mail only, and only within the form's own company: a visitor typing someone
        # else's address must not reach leads of another company
        company = CRMRecord.company_id == form.company_id if form.company_id else CRMRecord.company_id.is_(None)
        existing = (await db.execute(select(CRMRecord).where(
            CRMRecord.record_type == CRMRecordType.LEAD, CRMRecord.status == CRMStatus.OPEN,
            func.lower(CRMRecord.contact_email) == email, company)
            .order_by(CRMRecord.created_at).limit(1))).scalar_one_or_none()
    attribution = ", ".join(f"{k}={v}" for k, v in (("utm_source", sub.utm_source), ("utm_medium", sub.utm_medium),
                                                    ("utm_campaign", sub.utm_campaign)) if v)
    if existing is not None:
        sub.status, sub.crm_record_id = "DUPLICATE", existing.id
        db.add(CRMActivity(crm_record_id=existing.id, activity_type=CRMActivityType.NOTE,
                           subject=f"Web form {form.slug}: submitted again", result_status=CRMActivityResult.COMPLETED,
                           completed_datetime=now.replace(tzinfo=None),
                           description=(body.message or "")[:2000] or None, notes=attribution or None))
        db.add(sub)
        await db.commit()
        return sub
    for attempt in range(3):  # lead codes are sequential; retry if a concurrent submission took ours
        try:
            async with db.begin_nested():
                lead = CRMRecord(
                    record_type=CRMRecordType.LEAD, lead_code=await _next_lead_code(db),
                    company_name=body.company_name.strip(), contact_person_name=_clean(body.contact_person_name),
                    contact_email=email, contact_phone=phone, source_type=CRMSourceType.WEBSITE,
                    source_detail=f"form:{form.slug}" + (f" {attribution}" if attribution else ""),
                    assigned_rep_id=form.assigned_rep_id, territory_id=form.territory_id, company_id=form.company_id,
                    branch_id=form.branch_id, sales_region_id=form.sales_region_id, sales_team_id=form.sales_team_id,
                    notes=_clean(body.message), created_by="web-form", activities=[], interest_lines=[])
                db.add(lead)
                await db.flush()
            break
        except IntegrityError:
            if attempt == 2:
                raise
    sub.crm_record_id = lead.id
    db.add(sub)
    from app.services import crm_routing_service
    await crm_routing_service.route(db, lead)          # M47.S01.T002: form leads go through lead routing too
    await intel.rescore(db, lead, await intel.active_rules(db), "web-form", has_history=False)
    await db.commit()
    return sub
