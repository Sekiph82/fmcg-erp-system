"""M50.S01.T003 external company enrichment: generic provider interface + People Data Labs Company Enrichment adapter.

Official contract (People Data Labs, API v5, docs checked 2026-11-26):
  https://docs.peopledatalabs.com/docs/reference-company-enrichment-api
  https://docs.peopledatalabs.com/docs/input-parameters-company-enrichment-api
  https://docs.peopledatalabs.com/docs/output-response-company-enrichment-api
  GET https://api.peopledatalabs.com/v5/company/enrich, header ``X-Api-Key``; inputs name / website / profile / ticker;
  ``min_likelihood`` (default 2) makes a weak match a 404 instead of a 200; 200 body = {status, likelihood (1-10), ...Company
  Schema fields (name, website, industry, size, employee_count, founded, linkedin_url, location{locality, region, country})};
  empty fields are null; 404 = no match, 400 bad parameters, 401 bad key, 402 credits exhausted, 429 rate limited.
Person-level enrichment is NOT implemented: it needs a per-person lawful basis this ERP does not hold.

Settings (getattr): PDL_API_KEY (str, ""), PDL_BASE_URL (str, https://api.peopledatalabs.com).
Rules: nothing is requested until the key exists AND enrichment is enabled AND a licence/consent basis is recorded;
every value is a PROPOSAL with provider, request reference, retrieval time, confidence (likelihood/10) and expiry;
a human-verified field is never overwritten; applying needs a person (crm.edit_all); revoke restores the old value.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.customer_data import VerifiedField
from app.models.m50_prospecting import M50EnrichmentProposal
from app.services.m50_research_service import get_setting

APPLY_COLUMNS = {"city": "city", "region": "region", "segment": "segment"}   # customer columns a proposal may update
DISPLAY_ONLY = ("website", "employee_count", "founded", "linkedin_url")       # shown, never applied
FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "yahoo.co.ke"}


class EnrichError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


class ProviderResult:
    def __init__(self, matched: bool, likelihood: int = 0, fields: Optional[dict] = None, ref: str = ""):
        self.matched, self.likelihood, self.fields, self.ref = matched, likelihood, fields or {}, ref


class PdlCompanyProvider:
    name = "pdl"

    async def enrich_company(self, *, name: str, website: Optional[str], min_likelihood: int) -> ProviderResult:
        key = getattr(settings, "PDL_API_KEY", "")
        if not key:
            raise EnrichError(409, "PDL_API_KEY is not configured.")
        base = (getattr(settings, "PDL_BASE_URL", "") or "https://api.peopledatalabs.com").rstrip("/")
        params = {"name": name, "min_likelihood": min_likelihood, "titlecase": "true"}
        if website:
            params["website"] = website
        last = "Enrichment provider unavailable."
        async with provider_client(timeout=10.0) as c:
            for attempt in range(3):
                try:
                    r = await c.get(f"{base}/v5/company/enrich", params=params, headers={"X-Api-Key": key})
                except EgressBlocked as e:
                    raise EnrichError(503, f"Blocked by egress policy: {e}") from None
                except httpx.HTTPError:
                    r = None
                if r is not None:
                    if r.status_code == 200:
                        d = r.json()
                        loc = d.get("location") or {}
                        f = {"city": loc.get("locality"), "region": loc.get("region"), "segment": d.get("industry"),
                             "website": d.get("website"), "employee_count": d.get("employee_count"),
                             "founded": d.get("founded"), "linkedin_url": d.get("linkedin_url")}
                        return ProviderResult(True, int(d.get("likelihood") or 0), {k: str(v) for k, v in f.items() if v not in (None, "")},
                                              ref=f"pdl company/enrich v5 name={name[:60]}")
                    if r.status_code == 404:
                        return ProviderResult(False, ref=f"pdl company/enrich v5 name={name[:60]}")   # no match is a result, not an error
                    if r.status_code in (400, 401):
                        raise EnrichError(502, "The enrichment provider rejected the request or the API key.")
                    if r.status_code == 402:
                        raise EnrichError(402, "The enrichment account has no credits left.")
                    if r.status_code not in (429, 500, 502, 503, 504):
                        raise EnrichError(502, f"Enrichment provider error {r.status_code}.")
                    last = "Enrichment provider rate limit reached." if r.status_code == 429 else f"Enrichment provider error {r.status_code}."
                    await asyncio.sleep(min(float(r.headers.get("Retry-After", 0) or 0), 2.0) or 0.2 * 2 ** attempt)
                else:
                    await asyncio.sleep(0.2 * 2 ** attempt)
        raise EnrichError(502, last)


PROVIDERS = {"pdl": PdlCompanyProvider}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def status(db: AsyncSession) -> dict:
    row = await get_setting(db, "ENRICHMENT")
    reasons = []
    if row.provider not in PROVIDERS:
        reasons.append("No enrichment provider selected.")
    elif not getattr(settings, "PDL_API_KEY", ""):
        reasons.append("No provider API key is configured (PDL_API_KEY).")
    if not row.enabled:
        reasons.append("Enrichment is switched off in settings.")
    if not row.licensed or not (row.license_note or "").strip():
        reasons.append("A licence / consent basis has not been recorded.")
    return {"state": "OK" if not reasons else "NOT_CONFIGURED", "provider": row.provider or None, "reasons": reasons,
            "retention_days": row.retention_days, "min_likelihood": int((row.config or {}).get("min_likelihood", 6))}


def _domain(email: Optional[str]) -> Optional[str]:
    d = (email or "").rsplit("@", 1)[-1].lower() if "@" in (email or "") else None
    return d if d and d not in FREE_MAIL else None


async def preview(db: AsyncSession, customer_id: uuid.UUID, user: str) -> list[M50EnrichmentProposal]:
    """Ask the provider about one customer and store proposals (duplicates of an earlier proposal are skipped)."""
    from app.models.sales import Customer
    st = await status(db)
    if st["state"] != "OK":
        raise EnrichError(409, "Enrichment is not configured: " + " ".join(st["reasons"]))
    c = await db.get(Customer, customer_id)
    if c is None:
        raise EnrichError(404, "Customer not found")
    row = await get_setting(db, "ENRICHMENT")
    res = await PROVIDERS[row.provider]().enrich_company(name=c.name, website=_domain(c.email), min_likelihood=st["min_likelihood"])
    if not res.matched:
        return []
    have = {(p.field, p.value) for p in (await db.execute(select(M50EnrichmentProposal).where(
        M50EnrichmentProposal.customer_id == c.id, M50EnrichmentProposal.provider == row.provider,
        M50EnrichmentProposal.status != "REVOKED"))).scalars()}
    out = []
    for f, v in res.fields.items():
        if (f, v[:500]) in have:
            continue
        p = M50EnrichmentProposal(customer_id=c.id, provider=row.provider, field=f, value=v[:500], source_ref=res.ref,
                                  confidence=round(res.likelihood / 10, 2), consent_basis=(row.license_note or "")[:300],
                                  retrieved_at=_now(), expires_at=_now() + timedelta(days=row.retention_days))
        db.add(p)
        out.append(p)
    await db.flush()
    return out


def view(p: M50EnrichmentProposal, current: Optional[dict] = None) -> dict:
    return {"id": str(p.id), "field": p.field, "value": p.value, "provider": p.provider, "source_ref": p.source_ref,
            "confidence": p.confidence, "status": p.status, "retrieved_at": p.retrieved_at.isoformat(),
            "expires_at": p.expires_at.isoformat(), "expired": p.expires_at < _now(), "applicable": p.field in APPLY_COLUMNS,
            "current": (current or {}).get(p.field)}


async def apply(db: AsyncSession, pid: uuid.UUID, user, overwrite: bool = False) -> dict:
    from app.models.sales import Customer
    from app.services import pat_service as pats
    p = await db.get(M50EnrichmentProposal, pid)
    if p is None:
        raise EnrichError(404, "Proposal not found")
    if p.status != "PROPOSED":
        raise EnrichError(409, "Already decided.")
    if p.expires_at < _now():
        raise EnrichError(409, "This proposal has expired; request it again.")
    col = APPLY_COLUMNS.get(p.field)
    if not col:
        raise EnrichError(409, f"{p.field} is shown for information only and has no customer field.")
    c = await db.get(Customer, p.customer_id, with_for_update=True)
    cur = getattr(c, col)
    if cur and cur != p.value:
        if (await db.execute(select(VerifiedField.id).where(VerifiedField.customer_id == c.id, VerifiedField.field == p.field))).first():
            raise EnrichError(409, f"{p.field} is verified; un-verify it first if it really changed.")
        if not overwrite:
            raise EnrichError(409, f"{p.field} already has a different value ({cur}); confirm the overwrite.")
    p.applied_old = cur
    setattr(c, col, p.value)
    p.status, p.decided_by, p.decided_at = "APPLIED", user.username, _now()
    pats.audit(db, user, "M50_ENRICHMENT_APPLIED", "customer", str(c.id),
               {"field": p.field, "old": cur, "new": p.value, "provider": p.provider, "ref": p.source_ref})
    return {"field": p.field, "old": cur, "new": p.value}


async def reject(db: AsyncSession, pid: uuid.UUID, user) -> None:
    from app.services import pat_service as pats
    p = await db.get(M50EnrichmentProposal, pid)
    if p is None or p.status != "PROPOSED":
        raise EnrichError(404, "Proposal not found")
    p.status, p.decided_by, p.decided_at = "REJECTED", user.username, _now()
    pats.audit(db, user, "M50_ENRICHMENT_REJECTED", "customer", str(p.customer_id), {"field": p.field})


async def revoke(db: AsyncSession, pid: uuid.UUID, user) -> dict:
    """Consent/licence withdrawn for one value: restore the value that was there (unless a person changed it since)."""
    from app.models.sales import Customer
    from app.services import pat_service as pats
    p = await db.get(M50EnrichmentProposal, pid)
    if p is None or p.status == "REVOKED":
        raise EnrichError(404, "Proposal not found")
    restored = False
    if p.status == "APPLIED":
        c = await db.get(Customer, p.customer_id, with_for_update=True)
        col = APPLY_COLUMNS[p.field]
        if getattr(c, col) == p.value:
            setattr(c, col, p.applied_old)
            restored = True
    p.status, p.decided_by, p.decided_at = "REVOKED", user.username, _now()
    pats.audit(db, user, "M50_ENRICHMENT_REVOKED", "customer", str(p.customer_id), {"field": p.field, "restored": restored})
    return {"restored": restored}


async def purge(db: AsyncSession, *, customer_id: Optional[uuid.UUID] = None, expired_only: bool = False) -> int:
    """Delete stored proposals (not applied customer values): expired ones, or everything for one customer."""
    q = delete(M50EnrichmentProposal)
    if customer_id:
        q = q.where(M50EnrichmentProposal.customer_id == customer_id)
    if expired_only:
        q = q.where(M50EnrichmentProposal.expires_at < _now())
    if not customer_id and not expired_only:
        raise EnrichError(422, "Say which customer, or purge expired only.")
    return (await db.execute(q)).rowcount or 0
