"""M50.S01.T004 third-party buyer-intent feed (company level only).

No vendor is named: the adapter reads a documented generic feed schema, delivered as a CSV/JSON export or a webhook
payload the staff user imports (the provider contract of any licensed intent vendor maps onto it through ``mapping``).

Feed event schema (one object per signal):
  company_name  (required)   domain  (optional, e.g. "dukamoja.example.com")   topic (required, e.g. "bulk detergent")
  strength      (0..max)     observed_at (ISO 8601, required)                  event_id (optional, provider's id)
Any person-level field in the payload (email, name, phone, ip, ...) is DROPPED and counted: only the company is
resolved, and no claim about an individual is stored. Resolution: exact e-mail domain of exactly one customer
(DOMAIN, 0.9) or exact normalised name of exactly one customer (NAME, 0.6); otherwise NONE and the event never scores.

Rules: import needs INTENT enabled + licensed + a consent basis; duplicates (same feed/company/topic/day) are skipped;
events older than ``stale_days`` (90) or weaker than ``min_strength`` (0.1) are skipped and counted; each event expires
``retention_days`` after it was observed; score = min(100, 50 * sum(strength * match_confidence * 0.5^(age/half_life)))
with half_life_days 14; withdrawing consent marks events WITHDRAWN and they stop scoring at once. The first-party score
(customer_intel_service, ci_*) is never mixed in: the API shows both side by side.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m50_prospecting import M50IntentAlert, M50IntentEvent
from app.services.customer_data_service import norm_name
from app.services.m50_research_service import get_setting

DEFAULTS = {"half_life_days": 14, "stale_days": 90, "min_strength": 0.1, "alert_threshold": 40, "cooldown_days": 7,
            "scale_max": 1.0}
PERSON_FIELDS = {"email", "person_email", "person_name", "full_name", "first_name", "last_name", "phone", "ip", "ip_address",
                 "job_title", "linkedin", "user_id", "cookie_id", "device_id"}
FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "yahoo.co.ke"}


class IntentError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def cfg(db: AsyncSession) -> dict:
    row = await get_setting(db, "INTENT")
    return {**DEFAULTS, **(row.config or {})}


async def status(db: AsyncSession) -> dict:
    row = await get_setting(db, "INTENT")
    reasons = []
    if not row.enabled:
        reasons.append("The intent feed is switched off in settings.")
    if not row.licensed or not (row.license_note or "").strip():
        reasons.append("A licence / consent basis for the feed has not been recorded.")
    return {"state": "OK" if not reasons else "NOT_CONFIGURED", "reasons": reasons, "retention_days": row.retention_days,
            "config": await cfg(db), "provider": row.provider or "generic-feed"}


async def resolve(db: AsyncSession, name: str, domain: Optional[str]) -> tuple[Optional[uuid.UUID], str, float]:
    from app.models.sales import Customer
    domain = (domain or "").strip().lower().removeprefix("www.") or None
    if domain and domain not in FREE_MAIL:
        ids = list((await db.execute(select(Customer.id).where(func.lower(Customer.email).like(f"%@{domain}")))).scalars())
        if len(ids) == 1:
            return ids[0], "DOMAIN", 0.9
    key = norm_name(name)
    if key:
        rows = list((await db.execute(select(Customer.id, Customer.name))).all())
        ids = [i for i, n in rows if norm_name(n) == key]
        if len(ids) == 1:
            return ids[0], "NAME", 0.6
    return None, "NONE", 0.0


def _parse_dt(v) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def import_events(db: AsyncSession, *, feed: str, events: list[dict], mapping: Optional[dict], consent_basis: str,
                        user: str) -> dict:
    st = await status(db)
    if st["state"] != "OK":
        raise IntentError(409, "Intent feed is not configured: " + " ".join(st["reasons"]))
    if not consent_basis.strip():
        raise IntentError(422, "Record the consent / licence basis of this import.")
    c, row = st["config"], await get_setting(db, "INTENT")
    m = {"company_name": "company_name", "domain": "domain", "topic": "topic", "strength": "strength",
         "observed_at": "observed_at", "event_id": "event_id", **(mapping or {})}
    out = {"stored": 0, "duplicates": 0, "stale": 0, "weak": 0, "invalid": 0, "unresolved": 0, "person_fields_dropped": 0, "alerts": 0}
    touched: set[uuid.UUID] = set()
    for raw in events[:5000]:
        out["person_fields_dropped"] += sum(1 for k in raw if k.lower() in PERSON_FIELDS)
        name, topic = str(raw.get(m["company_name"]) or "").strip(), str(raw.get(m["topic"]) or "").strip()
        obs = _parse_dt(raw.get(m["observed_at"]))
        try:
            strength = float(raw.get(m["strength"])) / float(c["scale_max"] or 1)
        except (TypeError, ValueError):
            strength = None
        if not name or not topic or obs is None or strength is None or not 0 <= strength <= 1:
            out["invalid"] += 1
            continue
        if obs < _now() - timedelta(days=c["stale_days"]) or obs + timedelta(days=row.retention_days) < _now():
            out["stale"] += 1
            continue
        if strength < c["min_strength"]:
            out["weak"] += 1
            continue
        domain = (str(raw.get(m["domain"]) or "").strip().lower().removeprefix("www.") or None)
        key = hashlib.sha256(f"{feed}|{norm_name(name)}|{domain or ''}|{topic.lower()}|{obs.date()}".encode()).hexdigest()
        if (await db.execute(select(M50IntentEvent.id).where(M50IntentEvent.dedup_key == key))).first():
            out["duplicates"] += 1
            continue
        cid, method, conf = await resolve(db, name, domain)
        if cid is None:
            out["unresolved"] += 1
        else:
            touched.add(cid)
        db.add(M50IntentEvent(dedup_key=key, feed=feed[:100], company_name=name[:255], domain=domain, customer_id=cid,
                              match_method=method, match_confidence=conf, topic=topic[:100], strength=round(strength, 3),
                              observed_at=obs, expires_at=obs + timedelta(days=row.retention_days),
                              consent_basis=consent_basis[:300], imported_by=user))
        await db.flush()
        out["stored"] += 1
    for cid in touched:
        out["alerts"] += await evaluate(db, cid)
    return out


async def score(db: AsyncSession, customer_id: uuid.UUID, now: Optional[datetime] = None) -> dict:
    now, c = now or _now(), await cfg(db)
    evs = (await db.execute(select(M50IntentEvent).where(
        M50IntentEvent.customer_id == customer_id, M50IntentEvent.status == "ACTIVE", M50IntentEvent.expires_at > now))).scalars().all()
    parts, total = [], 0.0
    for e in sorted(evs, key=lambda x: x.observed_at, reverse=True):
        age = max((now - e.observed_at).total_seconds() / 86400, 0)
        pts = e.strength * e.match_confidence * 0.5 ** (age / c["half_life_days"])
        total += pts
        parts.append({"topic": e.topic, "feed": e.feed, "observed_at": e.observed_at.isoformat(), "age_days": round(age, 1),
                      "match": e.match_method, "points": round(pts * 50, 1), "consent_basis": e.consent_basis})
    return {"score": round(min(100.0, total * 50), 1), "events": parts, "source": "third-party feed (company level)"}


async def evaluate(db: AsyncSession, customer_id: uuid.UUID) -> int:
    c, s = await cfg(db), await score(db, customer_id)
    if s["score"] < c["alert_threshold"]:
        return 0
    recent = (await db.execute(select(M50IntentAlert.id).where(
        M50IntentAlert.customer_id == customer_id, M50IntentAlert.created_at > _now() - timedelta(days=c["cooldown_days"])))).first()
    if recent:
        return 0
    db.add(M50IntentAlert(customer_id=customer_id, score=s["score"],
                          reasons=[f'{e["topic"]} ({e["feed"]}, {e["age_days"]} d old, +{e["points"]})' for e in s["events"][:5]]))
    await db.flush()
    return 1


async def withdraw(db: AsyncSession, *, feed: Optional[str], domain: Optional[str], company_name: Optional[str], user) -> dict:
    """Consent withdrawn for a feed, a domain or a company: events stop scoring now; open alerts that no longer hold go."""
    from app.services import pat_service as pats
    if not (feed or domain or company_name):
        raise IntentError(422, "Say which feed, domain or company.")
    q = select(M50IntentEvent).where(M50IntentEvent.status == "ACTIVE")
    if feed:
        q = q.where(M50IntentEvent.feed == feed)
    if domain:
        q = q.where(M50IntentEvent.domain == domain.lower())
    if company_name:
        q = q.where(func.lower(M50IntentEvent.company_name) == company_name.lower())
    evs = (await db.execute(q)).scalars().all()
    cids = {e.customer_id for e in evs if e.customer_id}
    for e in evs:
        e.status = "WITHDRAWN"
    await db.flush()
    c, removed = await cfg(db), 0
    for cid in cids:
        if (await score(db, cid))["score"] < c["alert_threshold"]:
            removed += (await db.execute(delete(M50IntentAlert).where(M50IntentAlert.customer_id == cid,
                                                                      M50IntentAlert.acknowledged_at.is_(None)))).rowcount or 0
    pats.audit(db, user, "M50_INTENT_CONSENT_WITHDRAWN", "intent_feed", feed or domain or company_name,
               {"events": len(evs), "alerts_removed": removed})
    return {"withdrawn": len(evs), "alerts_removed": removed}


async def purge_expired(db: AsyncSession) -> int:
    return (await db.execute(delete(M50IntentEvent).where((M50IntentEvent.expires_at < _now()) | (M50IntentEvent.status == "WITHDRAWN")))).rowcount or 0


async def first_party_and_third_party(db: AsyncSession, customer_id: uuid.UUID) -> dict:
    from app.services import customer_intel_service as cis
    return {"first_party": await cis.intent(db, customer_id), "third_party": await score(db, customer_id)}
