"""Dynamic audiences and lookalike preparation (M44.S01.T010).

Rules: {"all": [cond, ...], "exclude": [cond, ...]}; cond = {"field", "op", "value"}.
Fields: channel, city, country, region, segment, customer_type (customer master), lifecycle (CRM contact with the same
e-mail), orders_90d, days_since_last_order (non-draft, non-cancelled sales orders).
Ops: eq, ne, in, not_in, gte, lte, empty, not_empty.

Members need an e-mail and, when require_consent (default), marketing consent SUBSCRIBED. Matched-but-blocked
customers are counted, never exported.

Export is a SHA-256 hash of the normalised e-mail (the format ad platforms accept for customer lists); it is off
until AUDIENCE_EXPORT_ENABLED. Uploading to an ad platform needs a configured provider adapter (M44.S01.T002–T005);
until then upload is refused. "Similar customers" is a local, explainable score against the audience's profile —
it is NOT a platform lookalike and is labelled as such.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMContact, CRMContactConsent, MarketingAudience, MarketingAudienceMember
from app.models.sales import Customer, SalesOrder, SOStatus

FIELDS = ("channel", "city", "country", "region", "segment", "customer_type", "lifecycle", "orders_90d", "days_since_last_order")
NUMERIC = ("orders_90d", "days_since_last_order")
OPS = ("eq", "ne", "in", "not_in", "gte", "lte", "empty", "not_empty")


class AudienceError(ValueError):
    pass


def validate(rules: Any) -> dict:
    if not isinstance(rules, dict):
        raise AudienceError("Rules must be an object with 'all' and optional 'exclude'.")
    out = {}
    for part in ("all", "exclude"):
        conds = rules.get(part) or []
        if not isinstance(conds, list) or len(conds) > 20:
            raise AudienceError(f"'{part}' must be a list of up to 20 conditions.")
        clean = []
        for c in conds:
            f, op, v = c.get("field"), c.get("op"), c.get("value")
            if f not in FIELDS or op not in OPS:
                raise AudienceError(f"Unknown field or operator: {f!r} {op!r}")
            if f in NUMERIC and op in ("gte", "lte", "eq", "ne"):
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    raise AudienceError(f"{f} needs a number") from None
            elif op in ("in", "not_in"):
                v = [str(x)[:100] for x in (v if isinstance(v, list) else [v])][:50]
            elif op not in ("empty", "not_empty"):
                v = str(v)[:100]
            clean.append({"field": f, "op": op, "value": v})
        out[part] = clean
    if not out["all"]:
        raise AudienceError("Add at least one condition.")
    return out


def _test(c: dict, facts: dict) -> bool:
    x, op, v = facts.get(c["field"]), c["op"], c["value"]
    if op == "empty":
        return x in (None, "")
    if op == "not_empty":
        return x not in (None, "")
    if x is None:
        return False
    if c["field"] in NUMERIC:
        return {"eq": x == v, "ne": x != v, "gte": x >= v, "lte": x <= v}.get(op, False)
    xs = str(x).upper()
    if op == "eq":
        return xs == str(v).upper()
    if op == "ne":
        return xs != str(v).upper()
    vs = {str(i).upper() for i in v}
    return xs in vs if op == "in" else xs not in vs


def matches(rules: dict, facts: dict) -> bool:
    return all(_test(c, facts) for c in rules["all"]) and not any(_test(c, facts) for c in rules.get("exclude", []))


async def _facts(db: AsyncSession, today: Optional[date] = None) -> list[tuple[Customer, dict]]:
    """Facts per active customer. ponytail: loads all customers in Python; push rules into SQL past ~100k customers."""
    today = today or date.today()
    counts = dict((await db.execute(select(SalesOrder.customer_id, func.count()).where(
        SalesOrder.status.notin_([SOStatus.DRAFT, SOStatus.CANCELLED]),
        SalesOrder.order_date >= date.fromordinal(today.toordinal() - 90)).group_by(SalesOrder.customer_id))).all())
    last = dict((await db.execute(select(SalesOrder.customer_id, func.max(SalesOrder.order_date)).where(
        SalesOrder.status.notin_([SOStatus.DRAFT, SOStatus.CANCELLED])).group_by(SalesOrder.customer_id))).all())
    stages = dict((await db.execute(select(CRMContact.email, CRMContact.lifecycle_stage)
                                    .where(CRMContact.email.isnot(None)))).all())
    out = []
    for c in (await db.execute(select(Customer).where(Customer.is_active.is_(True)))).scalars():
        email = (c.email or "").strip().lower() or None
        out.append((c, {
            "email": email, "channel": getattr(c.channel, "value", c.channel), "city": c.city, "country": c.country,
            "region": c.region, "segment": c.segment, "customer_type": getattr(c.customer_type, "value", c.customer_type),
            "lifecycle": stages.get(email) if email else None, "orders_90d": float(counts.get(c.id, 0)),
            "days_since_last_order": float((today - last[c.id]).days) if c.id in last else None}))
    return out


async def _consented(db: AsyncSession) -> set[str]:
    return set((await db.execute(select(func.lower(CRMContactConsent.email))
                                 .where(CRMContactConsent.status == "SUBSCRIBED"))).scalars())


async def evaluate(db: AsyncSession, rules: dict, require_consent: bool = True) -> dict:
    facts, ok = await _facts(db), await _consented(db)
    members, blocked = [], 0
    for c, f in facts:
        if not matches(rules, f):
            continue
        if not f["email"] or (require_consent and f["email"] not in ok):
            blocked += 1
            continue
        members.append((c, f))
    return {"members": members, "blocked": blocked}


async def recompute(db: AsyncSession, aud: MarketingAudience) -> MarketingAudience:
    res = await evaluate(db, aud.rules, aud.require_consent)
    now = datetime.now(timezone.utc)
    await db.execute(delete(MarketingAudienceMember).where(MarketingAudienceMember.audience_id == aud.id))
    seen = set()
    for c, f in res["members"]:
        if c.id not in seen:
            seen.add(c.id)
            db.add(MarketingAudienceMember(audience_id=aud.id, customer_id=c.id, email=f["email"], added_at=now))
    aud.member_count, aud.blocked_count, aud.computed_at = len(seen), res["blocked"], now
    await db.flush()
    return aud


def sha256_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


async def hashed_export(db: AsyncSession, aud: MarketingAudience) -> str:
    """Members as SHA-256 e-mails. Consent is checked again now: whoever unsubscribed after the last recompute is
    left out (M44 review)."""
    rows = set((await db.execute(select(MarketingAudienceMember.email).where(MarketingAudienceMember.audience_id == aud.id))).scalars())
    if aud.require_consent:
        rows &= await _consented(db)
    return "email_sha256\n" + "".join(sha256_email(e) + "\n" for e in sorted(rows))


async def similar(db: AsyncSession, aud: MarketingAudience, limit: int = 25) -> dict:
    """Score consented non-members against the members' profile: share of members with the same channel / region /
    customer type, plus closeness in order frequency. Every score lists its reasons."""
    facts, ok = await _facts(db), await _consented(db)
    member_ids = set((await db.execute(select(MarketingAudienceMember.customer_id)
                                       .where(MarketingAudienceMember.audience_id == aud.id))).scalars())
    mem = [f for c, f in facts if c.id in member_ids]
    if len(mem) < 5:
        return {"label": "local similarity score — not an ad-platform lookalike", "candidates": [],
                "note": "Needs at least 5 members to describe the audience."}
    shares = {k: Counter(f[k] for f in mem) for k in ("channel", "region", "customer_type")}
    avg_orders = sum(f["orders_90d"] for f in mem) / len(mem)
    out = []
    for c, f in facts:
        if c.id in member_ids or not f["email"] or f["email"] not in ok:
            continue
        reasons, score = [], 0.0
        for k, w in (("channel", 0.4), ("region", 0.2), ("customer_type", 0.2)):
            share = shares[k][f[k]] / len(mem) if f[k] is not None else 0
            if share:
                score += w * share
                reasons.append(f"{k} {f[k]}: {round(share * 100)}% of members")
        closeness = 1 - min(1.0, abs(f["orders_90d"] - avg_orders) / max(avg_orders, 1))
        score += 0.2 * closeness
        reasons.append(f"{int(f['orders_90d'])} orders in 90 days vs members' average {avg_orders:.1f}")
        out.append({"customer_id": str(c.id), "name": c.name, "score": round(score, 3), "reasons": reasons})
    out.sort(key=lambda r: -r["score"])
    return {"label": "local similarity score — not an ad-platform lookalike", "candidates": out[:limit]}
