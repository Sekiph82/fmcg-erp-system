"""M45.S01.T001–T003 prospecting, company research and enrichment from authorized sources.

Sources are local imports the company is allowed to use (each with a licence note and a retention date) or provider
adapters, which stay NOT_CONFIGURED until an account exists (M47). Nothing is scraped and nothing is invented:
- a fact always carries its source and citation (source name, row, column) and its age;
- two sources disagreeing → "conflict"; no source → "unknown";
- a proposal changes customer data only after a person approves it, a verified field is never overwritten, and an
  existing different value needs an explicit overwrite;
- outreach to a prospect is a draft that becomes an AI request: a different person approves the e-mail, and the
  outbox applies suppression.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_data import DataSource, ProspectRecord, ProspectRun, ResearchFact, VerifiedField

PROSPECT_FIELDS = ("company_name", "city", "region", "channel", "segment", "size_band", "email", "phone", "website",
                   "tax_id", "notes")
ENRICH_FIELDS = {"phone": "phone", "email": "email", "city": "city", "region": "region", "segment": "segment",
                 "tax_id": "tax_id", "website": None}   # website has no customer column: shown, never applied
LEGAL = re.compile(r"\b(ltd|limited|co|company|enterprises?|plc|llc|inc|the|and|&)\b")


class DataError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def norm_name(v: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", LEGAL.sub(" ", (v or "").lower())).strip()


def norm_phone(v: Optional[str]) -> Optional[str]:
    d = re.sub(r"\D", "", v or "")
    if not d:
        return None
    if d.startswith("0") and len(d) == 10:
        d = "254" + d[1:]
    if d.startswith("254") and len(d) == 12:
        return "+" + d
    return "+" + d if len(d) >= 9 else None


def norm_email(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip().lower()
    return v if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) else None


def norm_tax(v: Optional[str]) -> Optional[str]:
    v = re.sub(r"\s", "", (v or "")).upper()
    return v if re.fullmatch(r"[AP]\d{9}[A-Z]", v) else None


def normalize(field: str, value: Any) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    s = str(value).strip()
    if field == "phone":
        return norm_phone(s)
    if field == "email":
        return norm_email(s)
    if field == "tax_id":
        return norm_tax(s)
    if field == "size_band":
        return s.upper()[:1] if s.upper()[:1] in ("S", "M", "L") else None
    if field == "website":
        return s if re.match(r"^https?://", s) else f"https://{s}"
    return re.sub(r"\s+", " ", s)[:255]


# ── import (shared by T001–T003) ─────────────────────────────────────────────

async def import_source(db: AsyncSession, *, name: str, license_note: str, rows: list[dict], mapping: dict[str, str],
                        retention_days: int, user: str) -> dict:
    bad = [k for k in mapping if k not in PROSPECT_FIELDS]
    if bad or "company_name" not in mapping:
        raise DataError(422, "Mapping must include company_name and only known fields: " + ", ".join(PROSPECT_FIELDS))
    if not license_note.strip():
        raise DataError(422, "Say why the company may use this data (licence note).")
    src = DataSource(name=name, kind="LOCAL_IMPORT", license_note=license_note.strip(), imported_by=user,
                     expires_at=_now() + timedelta(days=max(1, min(retention_days, 1825))))
    db.add(src)
    await db.flush()
    seen, stored, errors = set(), 0, []
    for i, raw in enumerate(rows[:20000], start=1):
        vals = {f: normalize(f, raw.get(col)) for f, col in mapping.items()}
        if not vals.get("company_name"):
            errors.append({"row": i, "error": "company_name missing"})
            continue
        for f in ("phone", "email", "tax_id"):
            if raw.get(mapping.get(f, "")) and not vals.get(f):
                errors.append({"row": i, "error": f"{f} not valid, left empty"})
        key = (norm_name(vals["company_name"]), vals.get("phone") or vals.get("email"))
        if key in seen:
            errors.append({"row": i, "error": "duplicate of an earlier row, skipped"})
            continue
        seen.add(key)
        db.add(ProspectRecord(source_id=src.id, row_no=i, norm_name=key[0], **{f: vals.get(f) for f in PROSPECT_FIELDS}))
        stored += 1
    src.rows = stored
    await db.flush()
    return {"source_id": str(src.id), "stored": stored, "errors": errors[:200]}


async def purge_expired(db: AsyncSession) -> int:
    res = await db.execute(delete(DataSource).where(DataSource.expires_at < _now()))
    return res.rowcount or 0


def provider_status() -> dict:
    from app.core.config import settings
    return {"enrichment_provider": "CONFIGURED" if getattr(settings, "ENRICHMENT_PROVIDER_KEY", "") else "NOT_CONFIGURED",
            "note": "External company data needs a licensed provider account (M47). Only imported, authorized sources are used."}


# ── T001 prospecting ─────────────────────────────────────────────────────────

CRITERIA = {"city": 3, "region": 2, "channel": 3, "segment": 2, "size_bands": 2, "keywords": 2}


async def _customer_keys(db: AsyncSession) -> tuple[set, set, set]:
    from app.models.sales import Customer
    names, phones, emails = set(), set(), set()
    for n, p, e in (await db.execute(select(Customer.name, Customer.phone, Customer.email))).all():
        names.add(norm_name(n))
        if norm_phone(p):
            phones.add(norm_phone(p))
        if norm_email(e):
            emails.add(norm_email(e))
    return names, phones, emails


def score(p: dict, criteria: dict) -> tuple[float, list[dict], float, list[str]]:
    pts, evidence, known, unknown = 0.0, [], 0, []
    used = [k for k in CRITERIA if criteria.get(k)]
    for k in used:
        want = criteria[k]
        field = {"size_bands": "size_band", "keywords": None}.get(k, k)
        if k == "keywords":
            text = f"{p['company_name']} {p.get('notes') or ''} {p.get('segment') or ''}".lower()
            hits = [w for w in want if w.lower() in text]
            known += 1
            if hits:
                pts += CRITERIA[k] * len(hits) / len(want)
                evidence.append({"criterion": k, "value": ", ".join(hits), "citation": p["citation"]})
            continue
        val = p.get(field)
        if val is None:
            unknown.append(field)
            continue
        known += 1
        ok = val.upper() in [x.upper() for x in want] if isinstance(want, list) else val.lower() == str(want).lower()
        if ok:
            pts += CRITERIA[k]
            evidence.append({"criterion": k, "value": val, "citation": f"{p['citation']}, column {field}"})
    max_pts = sum(CRITERIA[k] for k in used) or 1
    return round(pts / max_pts, 3), evidence, round(known / (len(used) or 1), 2), unknown


async def prospect(db: AsyncSession, criteria: dict, user: str, limit: int = 50) -> ProspectRun:
    from app.models.crm import CRMRecord, CRMRecordType, CRMStatus
    criteria = {k: v for k, v in criteria.items() if k in CRITERIA or k == "exclude_customers"}
    cands: list[dict] = []
    for p, src in (await db.execute(select(ProspectRecord, DataSource).join(DataSource, DataSource.id == ProspectRecord.source_id)
                                    .where(DataSource.expires_at > _now()).limit(20000))).all():
        cands.append({"kind": "prospect", "id": str(p.id), "company_name": p.company_name, "city": p.city, "region": p.region,
                      "channel": p.channel, "segment": p.segment, "size_band": p.size_band, "email": p.email, "phone": p.phone,
                      "notes": p.notes, "citation": f"{src.name}, row {p.row_no}", "source_age_days": (_now() - src.imported_at).days})
    for r in (await db.execute(select(CRMRecord).where(CRMRecord.record_type == CRMRecordType.LEAD, CRMRecord.status == CRMStatus.OPEN)
                               .limit(5000))).scalars():
        cands.append({"kind": "lead", "id": str(r.id), "company_name": r.company_name, "city": getattr(r, "city", None),
                      "region": None, "channel": r.channel_id, "segment": r.industry_segment, "size_band": None,
                      "email": r.contact_email, "phone": getattr(r, "contact_phone", None), "notes": r.notes,
                      "citation": f"CRM lead {r.lead_code or r.id}", "source_age_days": None})
    names, phones, emails = await _customer_keys(db) if criteria.get("exclude_customers", True) else (set(), set(), set())
    results = []
    for c in cands:
        if norm_name(c["company_name"]) in names or norm_phone(c["phone"]) in phones or norm_email(c["email"]) in emails:
            continue
        s, ev, conf, unk = score(c, criteria)
        if s > 0:
            results.append({**{k: c[k] for k in ("kind", "id", "company_name", "city", "channel", "segment", "email")},
                            "score": s, "confidence": conf, "unknown": unk, "evidence": ev,
                            "can_email": bool(norm_email(c["email"])), "source_age_days": c["source_age_days"]})
    results.sort(key=lambda r: (-r["score"], -r["confidence"], r["company_name"]))
    run = ProspectRun(criteria=criteria, results=results[:limit], created_by=user)
    db.add(run)
    await db.flush()
    return run


def draft(result: dict, sender: str) -> dict:
    """Outreach text built only from evidence; nothing about the prospect is invented."""
    why = "; ".join(f"{e['criterion']} {e['value']}" for e in result["evidence"]) or "your business profile"
    return {"subject": "POVU products for " + result["company_name"],
            "body": (f"Hello {result['company_name']} team,\n\nWe supply POVU drinks to outlets like yours ({why}). "
                     "Would you like our price list and delivery days for your area?\n\n"
                     f"Kind regards,\n{sender}\nReply STOP and we will not contact you again.")}


# ── T002 research / T003 enrichment ──────────────────────────────────────────

async def research(db: AsyncSession, customer_id: uuid.UUID) -> dict:
    """Collect sourced facts for a customer from authorized sources (stored as proposals) and show them per field."""
    from app.models.sales import Customer
    c = await db.get(Customer, customer_id)
    if c is None:
        raise DataError(404, "Customer not found")
    keys = [ProspectRecord.norm_name == norm_name(c.name)]
    if norm_phone(c.phone):
        keys.append(ProspectRecord.phone == norm_phone(c.phone))
    if norm_tax(c.tax_id):
        keys.append(ProspectRecord.tax_id == norm_tax(c.tax_id))
    rows = (await db.execute(select(ProspectRecord, DataSource).join(DataSource, DataSource.id == ProspectRecord.source_id)
                             .where(or_(*keys), DataSource.expires_at > _now()).limit(50))).all()
    existing = {(f.field, f.value, f.source_id) for f in (await db.execute(select(ResearchFact).where(
        ResearchFact.subject_type == "customer", ResearchFact.subject_id == customer_id))).scalars()}
    for p, src in rows:
        strong = (norm_phone(c.phone) and p.phone == norm_phone(c.phone)) or (norm_tax(c.tax_id) and p.tax_id == norm_tax(c.tax_id))
        for f in ENRICH_FIELDS:
            v = getattr(p, f, None)
            if v and (f, v, src.id) not in existing:
                db.add(ResearchFact(subject_type="customer", subject_id=customer_id, field=f, value=v, source_id=src.id,
                                    citation=f"{src.name}, row {p.row_no}, column {f}", confidence=0.8 if strong else 0.5,
                                    retrieved_at=src.imported_at))
                existing.add((f, v, src.id))
    await db.flush()
    return await view(db, c)


async def view(db: AsyncSession, c) -> dict:
    facts = list((await db.execute(select(ResearchFact).where(ResearchFact.subject_type == "customer", ResearchFact.subject_id == c.id)
                                   .order_by(ResearchFact.retrieved_at.desc()))).scalars())
    verified = set((await db.execute(select(VerifiedField.field).where(VerifiedField.customer_id == c.id))).scalars())
    out = []
    for f in ENRICH_FIELDS:
        cand = [x for x in facts if x.field == f and x.status != "REJECTED"]
        values = {x.value for x in cand}
        out.append({"field": f, "current": getattr(c, f, None) if ENRICH_FIELDS[f] else None, "verified": f in verified,
                    "applicable": ENRICH_FIELDS[f] is not None, "unknown": not cand, "conflict": len(values) > 1,
                    "candidates": [{"id": str(x.id), "value": x.value, "citation": x.citation, "confidence": x.confidence,
                                    "status": x.status, "age_days": (_now() - x.retrieved_at).days} for x in cand]})
    return {"customer_id": str(c.id), "name": c.name, "fields": out, "provider": provider_status()}


async def apply_fact(db: AsyncSession, fact_id: uuid.UUID, user, overwrite: bool = False) -> dict:
    from app.models.sales import Customer
    from app.services import pat_service as pats
    fact = await db.get(ResearchFact, fact_id)
    if fact is None or fact.subject_type != "customer":
        raise DataError(404, "Proposal not found")
    if fact.status != "PROPOSED":
        raise DataError(409, "Already decided.")
    col = ENRICH_FIELDS.get(fact.field)
    if not col:
        raise DataError(409, f"{fact.field} has no customer field to update.")
    c = await db.get(Customer, fact.subject_id, with_for_update=True)
    cur = getattr(c, col)
    if cur and cur != fact.value:
        if (await db.execute(select(VerifiedField.id).where(VerifiedField.customer_id == c.id, VerifiedField.field == fact.field))).first():
            raise DataError(409, f"{fact.field} is verified; un-verify it first if it really changed.")
        if not overwrite:
            raise DataError(409, f"{fact.field} already has a different value ({cur}); confirm the overwrite.")
    setattr(c, col, fact.value)
    fact.status, fact.decided_by, fact.decided_at = "APPLIED", user.username, _now()
    pats.audit(db, user, "ENRICHMENT_APPLIED", "customer", str(c.id),
               {"field": fact.field, "old": cur, "new": fact.value, "citation": fact.citation})
    return {"field": fact.field, "old": cur, "new": fact.value}


async def reject_fact(db: AsyncSession, fact_id: uuid.UUID, user) -> None:
    fact = await db.get(ResearchFact, fact_id)
    if fact is None or fact.status != "PROPOSED":
        raise DataError(404, "Proposal not found")
    fact.status, fact.decided_by, fact.decided_at = "REJECTED", user.username, _now()


async def set_verified(db: AsyncSession, customer_id: uuid.UUID, field: str, user, verified: bool) -> None:
    from sqlalchemy.dialects.postgresql import insert
    if field not in ENRICH_FIELDS:
        raise DataError(422, "Unknown field")
    if verified:
        await db.execute(insert(VerifiedField).values(id=uuid.uuid4(), customer_id=customer_id, field=field, verified_by=user.username,
                                                      verified_at=_now()).on_conflict_do_nothing(constraint="uq_cd_verified_field"))
    else:
        await db.execute(delete(VerifiedField).where(VerifiedField.customer_id == customer_id, VerifiedField.field == field))


# ── business card (T003 extension) ───────────────────────────────────────────

def parse_card(text: str) -> dict:
    """Fields from the text of a business card (from the phone's text recognition or typed). Every field must be
    confirmed by the user before a contact is created; nothing is saved here."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()][:20]
    out: dict[str, dict] = {}

    def put(k, v, conf):
        if v and k not in out:
            out[k] = {"value": v, "confidence": conf}
    for l in lines:
        if m := re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", l):
            put("email", m.group(0).lower(), 0.95)
        elif re.search(r"(\+?\d[\d\s()-]{7,})", l) and norm_phone(l):
            put("phone", norm_phone(l), 0.85)
        elif re.search(r"(www\.|https?://)\S+", l, re.I):
            put("website", normalize("website", re.search(r"(www\.|https?://)\S+", l, re.I).group(0)), 0.9)
        elif re.search(r"\b(ltd|limited|enterprises?|company|co\.|distributors?|supermarket|shop|stores?)\b", l, re.I):
            put("company", l, 0.7)
        elif re.search(r"\b(manager|director|buyer|owner|officer|head|ceo|cfo|procurement|sales|purchasing)\b", l, re.I):
            put("job_title", l, 0.7)
    for l in lines:   # the first plain two/three-word line is usually the person's name
        if re.fullmatch(r"[A-Z][a-zA-Z'-]+(\s[A-Z][a-zA-Z'-]+){1,2}", l) and l not in [v["value"] for v in out.values()]:
            put("full_name", l, 0.6)
            break
    return {"fields": out, "ocr_engine": "NOT_CONFIGURED", "note": "Use your phone's text recognition or type the card; "
            "check every field before saving."}
