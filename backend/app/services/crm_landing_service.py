"""Landing pages and A/B tests (M36.S05.T002).

- A landing page shows one of its variants (headline, text, call to action) and the attached lead form.
- Assignment is consistent: SHA-256(page id + visitor id) picks a variant by weight, so a visitor always sees the
  same variant; the raw visitor id is never stored (only its keyed hash).
- A view and a conversion count once per visitor; conversions are real, non-spam lead-form submissions
  (consent is enforced by the lead form itself).
- Statistics guard against early calls: no winner until every variant has the minimum sample and at least
  5 conversions, and the difference to the control is significant (two-sided two-proportion z-test, p < 0.05).
"""
from __future__ import annotations

import hashlib
import hmac
import math
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMLandingEvent, CRMLandingPage, CRMLandingVariant

MIN_CONVERSIONS = 5
VIEWS_PER_CONNECTION_HOUR = 30      # more page views from one connection are shown but not counted


def visitor_hash(page_id: uuid.UUID, visitor: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"lp:{page_id}:{visitor}".encode(), hashlib.sha256).hexdigest()


def assign(page_id: uuid.UUID, visitor: str, variants: list[CRMLandingVariant]) -> CRMLandingVariant:
    """Deterministic weighted choice (same visitor → same variant while the weights stay the same)."""
    live = sorted([v for v in variants if v.is_active and v.weight > 0], key=lambda v: v.key)
    if not live:
        raise ValueError("no active variant")
    total = sum(v.weight for v in live)
    point = int(hashlib.sha256(f"{page_id}:{visitor}".encode()).hexdigest(), 16) % total
    for v in live:
        if point < v.weight:
            return v
        point -= v.weight
    return live[-1]


async def page_by_slug(db: AsyncSession, slug: str, live_only: bool = True) -> Optional[CRMLandingPage]:
    page = (await db.execute(select(CRMLandingPage).where(CRMLandingPage.slug == slug[:80]))).scalar_one_or_none()
    if page is None or (live_only and page.status != "LIVE"):
        return None
    return page


async def variants(db: AsyncSession, page_id: uuid.UUID) -> list[CRMLandingVariant]:
    return list((await db.execute(select(CRMLandingVariant).where(CRMLandingVariant.page_id == page_id)
                                  .order_by(CRMLandingVariant.key))).scalars().all())


def ip_hash(ip: Optional[str]) -> Optional[str]:
    return hmac.new(settings.SECRET_KEY.encode(), f"lp-ip:{ip}".encode(), hashlib.sha256).hexdigest() if ip else None


async def seen_variant(db: AsyncSession, page: CRMLandingPage, visitor: str) -> Optional[CRMLandingVariant]:
    """The variant this visitor was shown (pinned at the first counted view)."""
    vid = (await db.execute(select(CRMLandingEvent.variant_id).where(
        CRMLandingEvent.page_id == page.id, CRMLandingEvent.visitor_hash == visitor_hash(page.id, visitor),
        CRMLandingEvent.kind == "VIEW"))).scalar_one_or_none()
    return await db.get(CRMLandingVariant, vid) if vid else None


async def record(db: AsyncSession, page: CRMLandingPage, variant: CRMLandingVariant, visitor: str, kind: str,
                 ip: Optional[str] = None) -> bool:
    """Count once per visitor and kind; views beyond the per-connection hourly cap are not counted."""
    from datetime import datetime, timedelta, timezone
    h = ip_hash(ip)
    if kind == "VIEW" and h:
        recent = (await db.execute(select(func.count()).select_from(CRMLandingEvent).where(
            CRMLandingEvent.ip_hash == h, CRMLandingEvent.kind == "VIEW",
            CRMLandingEvent.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)))).scalar_one()
        if recent >= VIEWS_PER_CONNECTION_HOUR:
            return False
    res = await db.execute(insert(CRMLandingEvent).values(
        id=uuid.uuid4(), page_id=page.id, variant_id=variant.id, visitor_hash=visitor_hash(page.id, visitor), kind=kind,
        ip_hash=h, created_at=func.now()).on_conflict_do_nothing(index_elements=["page_id", "visitor_hash", "kind"]))
    return bool(res.rowcount)


def _z_test(c1: int, n1: int, c2: int, n2: int) -> Optional[float]:
    if not n1 or not n2:
        return None
    p = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (c2 / n2 - c1 / n1) / se
    return math.erfc(abs(z) / math.sqrt(2))  # two-sided p-value


def _wilson(c: int, n: int) -> Optional[tuple[float, float]]:
    if not n:
        return None
    z, ph = 1.96, c / n
    d = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / d
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, mid - half) * 100, 2), round(min(1.0, mid + half) * 100, 2)


async def stats(db: AsyncSession, page: CRMLandingPage) -> dict:
    vs = await variants(db, page.id)
    counts = {(v, k): n for v, k, n in (await db.execute(
        select(CRMLandingEvent.variant_id, CRMLandingEvent.kind, func.count()).where(CRMLandingEvent.page_id == page.id)
        .group_by(CRMLandingEvent.variant_id, CRMLandingEvent.kind))).all()}
    rows = []
    for v in vs:
        n, c = counts.get((v.id, "VIEW"), 0), counts.get((v.id, "CONVERT"), 0)
        rows.append({"id": str(v.id), "key": v.key, "headline": v.headline, "weight": v.weight, "active": v.is_active,
                     "views": n, "conversions": c, "rate_pct": round(c * 100 / n, 2) if n else None, "ci95_pct": _wilson(c, n)})
    control = rows[0] if rows else None
    enough = bool(rows) and all(r["views"] >= page.min_sample and r["conversions"] >= MIN_CONVERSIONS for r in rows if r["active"])
    best, verdict = None, "Not enough data yet — keep the test running."
    if control and enough:
        for r in rows[1:]:
            r["p_value"] = _z_test(control["conversions"], control["views"], r["conversions"], r["views"])
        sig = [r for r in rows[1:] if r.get("p_value") is not None and r["p_value"] < 0.05]
        if sig:
            best = max(sig, key=lambda r: r["rate_pct"] or 0)
            better = (best["rate_pct"] or 0) > (control["rate_pct"] or 0)
            verdict = f"Variant {best['key']} {'beats' if better else 'is worse than'} {control['key']} (p = {best['p_value']:.3f})."
        else:
            verdict = "No significant difference between the variants."
    return {"page": {"id": str(page.id), "slug": page.slug, "status": page.status, "min_sample": page.min_sample},
            "variants": rows, "enough_data": enough, "verdict": verdict}
