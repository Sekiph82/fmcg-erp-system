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
    company_name: str = Field(min_length=1, max_length=200)
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
    await intel.rescore(db, lead, await intel.active_rules(db), "web-form", has_history=False)
    await db.commit()
    return sub
