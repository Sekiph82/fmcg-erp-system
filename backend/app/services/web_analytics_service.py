"""First-party website analytics (M44.S01.T009).

Privacy rules:
- Nothing is stored without the visitor's analytics consent (the SDK asks first; the collector checks again).
- The browser's random visitor/session ids are stored only as keyed hashes; no IP address, no user agent, no full
  referrer URL, no query string (only the three UTM fields are kept).
- Bots, crawlers and headless browsers are dropped. A client event id makes retries count once. One visitor can send
  at most MAX_EVENTS_PER_HOUR events; more are dropped.
- A visitor is linked to an e-mail address only when they gave marketing consent and typed the address themselves.
- Events are deleted after WEB_ANALYTICS_RETENTION_DAYS; a visitor can ask for their own events to be deleted.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import WebConsent, WebEvent, WebIdentity

KINDS = ("PAGE", "FORM", "CTA", "CUSTOM")
BOT_RE = re.compile(r"bot|crawl|spider|slurp|headless|preview|lighthouse|pingdom|monitor|curl|wget|python-requests", re.I)
MAX_EVENTS_PER_HOUR = 300


def hashed(kind: str, raw: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"web:{kind}:{raw}".encode(), hashlib.sha256).hexdigest()


def clean_path(path: str) -> str:
    p = urlsplit(path or "/").path or "/"
    return re.sub(r"[^\w\-./~%]", "", p)[:300] or "/"


def referrer_host(ref: Optional[str]) -> Optional[str]:
    host = urlsplit(ref or "").hostname
    return host[:200] if host else None


async def record_consent(db: AsyncSession, visitor: str, analytics: bool, marketing: bool) -> None:
    vh = hashed("v", visitor)
    db.add(WebConsent(visitor_hash=vh, analytics=analytics, marketing=marketing, decided_at=datetime.now(timezone.utc)))
    if not marketing:   # withdrawing marketing consent unlinks the visitor from their e-mail (M44 review)
        await db.execute(delete(WebIdentity).where(WebIdentity.visitor_hash == vh))


async def _latest_consent(db: AsyncSession, vh: str) -> Optional[WebConsent]:
    return (await db.execute(select(WebConsent).where(WebConsent.visitor_hash == vh)
                             .order_by(WebConsent.decided_at.desc()).limit(1))).scalars().first()


async def collect(db: AsyncSession, visitor: str, session: str, events: list[dict], user_agent: str = "") -> dict:
    """Store consented, non-bot, not-yet-seen events. Returns counts of what happened."""
    if BOT_RE.search(user_agent or ""):
        return {"stored": 0, "dropped": len(events), "reason": "bot"}
    vh = hashed("v", visitor)
    consent = await _latest_consent(db, vh)
    if consent is None or not consent.analytics:
        return {"stored": 0, "dropped": len(events), "reason": "no analytics consent"}
    now = datetime.now(timezone.utc)
    recent = (await db.execute(select(func.count()).select_from(WebEvent).where(
        WebEvent.visitor_hash == vh, WebEvent.occurred_at > now - timedelta(hours=1)))).scalar_one()
    stored = 0
    for e in events[: max(0, MAX_EVENTS_PER_HOUR - recent)]:
        if e.get("kind") not in KINDS:
            continue
        res = await db.execute(insert(WebEvent).values(
            id=uuid.uuid4(), visitor_hash=vh, session_id=hashed("s", session), event_id=str(e["event_id"])[:64],
            kind=e["kind"], name=(str(e.get("name"))[:100] if e.get("name") else None), path=clean_path(e.get("path", "/")),
            referrer_host=referrer_host(e.get("referrer")),
            utm_source=(e.get("utm_source") or None), utm_medium=(e.get("utm_medium") or None),
            utm_campaign=(e.get("utm_campaign") or None), occurred_at=now,
        ).on_conflict_do_nothing(constraint="uq_web_event_visitor_event"))
        stored += res.rowcount or 0
    return {"stored": stored, "dropped": len(events) - stored}


async def identify(db: AsyncSession, visitor: str, email: str) -> bool:
    """Link the visitor to an e-mail only with marketing consent on record."""
    vh = hashed("v", visitor)
    consent = await _latest_consent(db, vh)
    if consent is None or not consent.marketing:
        return False
    await db.execute(insert(WebIdentity).values(visitor_hash=vh, email=email.strip().lower()[:254],
                                                linked_at=datetime.now(timezone.utc))
                     .on_conflict_do_update(index_elements=["visitor_hash"],
                                            set_={"email": email.strip().lower()[:254], "linked_at": datetime.now(timezone.utc)}))
    return True


async def forget(db: AsyncSession, visitor: str) -> int:
    """Visitor's own erase request: events, identity and consent log go."""
    vh = hashed("v", visitor)
    n = (await db.execute(delete(WebEvent).where(WebEvent.visitor_hash == vh))).rowcount or 0
    await db.execute(delete(WebIdentity).where(WebIdentity.visitor_hash == vh))
    await db.execute(delete(WebConsent).where(WebConsent.visitor_hash == vh))
    return n


async def purge_expired(db: AsyncSession, now: Optional[datetime] = None) -> int:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=settings.WEB_ANALYTICS_RETENTION_DAYS)
    n = (await db.execute(delete(WebEvent).where(WebEvent.occurred_at < cutoff))).rowcount or 0
    # identities and consent records of visitors with no event left in the retention window go too (M44 review)
    stale = select(WebEvent.visitor_hash).where(WebEvent.occurred_at >= cutoff)
    await db.execute(delete(WebIdentity).where(WebIdentity.visitor_hash.not_in(stale)))
    await db.execute(delete(WebConsent).where(WebConsent.decided_at < cutoff, WebConsent.visitor_hash.not_in(stale)))
    return n


async def _events(db: AsyncSession, since: datetime, limit: int = 200_000) -> list[WebEvent]:
    # ponytail: reports scan raw events in Python; move to SQL aggregates / rollup table if traffic passes ~200k/period
    return list((await db.execute(select(WebEvent).where(WebEvent.occurred_at >= since)
                                  .order_by(WebEvent.occurred_at).limit(limit))).scalars().all())


async def summary(db: AsyncSession, days: int) -> dict:
    evs = await _events(db, datetime.now(timezone.utc) - timedelta(days=days))
    pages = [e for e in evs if e.kind == "PAGE"]
    first_touch: dict[str, str] = {}
    for e in evs:
        first_touch.setdefault(e.visitor_hash, e.utm_source or (f"referral:{e.referrer_host}" if e.referrer_host else "direct"))
    return {"visitors": len({e.visitor_hash for e in evs}), "sessions": len({e.session_id for e in evs}),
            "page_views": len(pages),
            "top_pages": Counter(e.path for e in pages).most_common(10),
            "sources": Counter(first_touch.values()).most_common(10),
            "events": Counter(f"{e.kind}:{e.name}" for e in evs if e.kind != "PAGE").most_common(10),
            "identified_visitors": (await db.execute(select(func.count()).select_from(WebIdentity))).scalar_one(),
            "note": "Consented visitors only; bots dropped. Sources are first touch in the period."}


async def funnel(db: AsyncSession, steps: list[str], days: int) -> list[dict]:
    """Visitors reaching each step in order (a step is a page path or KIND:name)."""
    evs = await _events(db, datetime.now(timezone.utc) - timedelta(days=days))
    per: dict[str, list[WebEvent]] = defaultdict(list)
    for e in evs:
        per[e.visitor_hash].append(e)

    def match(e: WebEvent, step: str) -> bool:
        return e.path == step if step.startswith("/") else f"{e.kind}:{e.name}" == step

    reached = [0] * len(steps)
    for seq in per.values():
        i = 0
        for e in seq:
            if i < len(steps) and match(e, steps[i]):
                reached[i] += 1
                i += 1
    return [{"step": s, "visitors": n, "of_previous": (round(n / reached[i - 1], 3) if i and reached[i - 1] else None)}
            for i, (s, n) in enumerate(zip(steps, reached))]


async def journey(db: AsyncSession, email: str) -> dict:
    """An identified contact's website journey (all their linked visitor ids), with first-touch source."""
    vhs = list((await db.execute(select(WebIdentity.visitor_hash).where(WebIdentity.email == email.strip().lower()))).scalars())
    if not vhs:
        return {"email": email, "linked": False, "events": [], "first_touch": None}
    evs = list((await db.execute(select(WebEvent).where(WebEvent.visitor_hash.in_(vhs)).order_by(WebEvent.occurred_at)
                                 .limit(500))).scalars())
    ft = evs[0] if evs else None
    return {"email": email, "linked": True,
            "first_touch": ({"source": ft.utm_source or ft.referrer_host or "direct", "medium": ft.utm_medium,
                             "campaign": ft.utm_campaign, "at": ft.occurred_at.isoformat()} if ft else None),
            "events": [{"at": e.occurred_at.isoformat(), "kind": e.kind, "name": e.name, "path": e.path} for e in evs]}


async def deal_journey(db: AsyncSession, record_id: uuid.UUID) -> dict:
    """Deal-level web journey (M45.S01.T024): the merged journeys of the contacts associated with the deal."""
    from app.models.crm import CRMContact, CRMContactAssociation
    emails = sorted({e for e in (await db.execute(select(CRMContact.email).join(
        CRMContactAssociation, CRMContactAssociation.contact_id == CRMContact.id).where(
        CRMContactAssociation.object_type == "crm_record", CRMContactAssociation.object_id == record_id,
        CRMContact.email.is_not(None)))).scalars()})
    per = [await journey(db, e) for e in emails]
    events = sorted(({**ev, "email": j["email"]} for j in per for ev in j["events"]), key=lambda x: x["at"])
    firsts = [j["first_touch"] for j in per if j["first_touch"]]
    return {"record_id": str(record_id), "contacts": len(emails), "linked": sum(1 for j in per if j["linked"]),
            "first_touch": min(firsts, key=lambda f: f["at"]) if firsts else None, "events": events[:500]}
