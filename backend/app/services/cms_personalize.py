"""M46.S01.T004 CRM-driven personalization and adaptive testing for CMS pages.

Who is the visitor?
- The browser sends its random analytics visitor id (povu-analytics.js); it is only ever used as a keyed hash.
- A visitor is "known" when they gave marketing consent AND linked an e-mail (web_identities), or are signed in to the
  customer portal. CRM data (lifecycle stage, marketing audiences) is used ONLY for a verified identity — the signed-in
  portal user's own e-mail — because a self-typed e-mail is unverified and would turn targeted blocks into an oracle
  about someone else's CRM record (M46 gate review).
- Rule metadata (audience, slot, fallback, experiment) is stripped from the public response.
- No consent, withdrawn consent, or no id → anonymous fallback: rules needing CRM data never match, and fallback
  blocks show. The page response never contains the e-mail, contact or audience names.
- Personalized responses are marked private/no-store so a shared cache never hands one visitor's page to another;
  anonymous responses are identical for everyone and may be cached.

Experiments: blocks carrying {"experiment": {"key", "variant"}} are alternatives. AB splits by a stable hash of the
visitor; BANDIT uses Thompson sampling over observed conversions (Beta posteriors) and is sticky per visitor.
Views and conversions are recorded only with analytics consent.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import CmsExperiment, CmsExperimentEvent, CmsPage
from app.services import web_analytics_service as wa


@dataclass
class Visitor:
    vh: Optional[str] = None
    analytics: bool = False
    known: bool = False
    lifecycle: Optional[str] = None
    segments: set = field(default_factory=set)
    locale: str = "en"

    @property
    def personalized(self) -> bool:
        return self.known


async def visitor(db: AsyncSession, raw: Optional[str], locale: str, portal_user=None) -> Visitor:
    from app.models.crm import CRMContact, MarketingAudience, MarketingAudienceMember, WebIdentity
    v = Visitor(locale=locale)
    if raw and len(raw) >= 8:
        v.vh = wa.hashed("v", raw[:100])
        consent = await wa._latest_consent(db, v.vh)
        v.analytics = bool(consent and consent.analytics)
        if consent and consent.marketing and await db.get(WebIdentity, v.vh) is not None:
            v.known = True                       # self-declared: no CRM data is used for it
    if portal_user is not None and portal_user.email:
        email = portal_user.email.strip().lower()  # verified by the portal sign-in
        v.known = True
        v.lifecycle = (await db.execute(select(CRMContact.lifecycle_stage).where(func.lower(CRMContact.email) == email).limit(1))).scalar_one_or_none()
        v.segments = set((await db.execute(select(MarketingAudience.name).join(
            MarketingAudienceMember, MarketingAudienceMember.audience_id == MarketingAudience.id).where(MarketingAudienceMember.email == email))).scalars())
    return v


def matches(aud: dict, v: Visitor) -> bool:
    if not aud:
        return True
    if "known" in aud and aud["known"] != v.known:
        return False
    if aud.get("locale") and v.locale not in aud["locale"]:
        return False
    if aud.get("lifecycle") and (v.lifecycle or "").upper() not in {x.upper() for x in aud["lifecycle"]}:
        return False
    if aud.get("segment") and not (v.segments & set(aud["segment"])):
        return False
    return True


def _crm_rule(aud: dict) -> bool:
    return bool(aud.get("lifecycle") or aud.get("segment") or aud.get("known") is True)


RULE_KEYS = ("audience", "slot", "fallback", "experiment")


def strip(blocks: list) -> list:
    """Remove targeting rules from blocks before they leave the server."""
    out = []
    for b in blocks:
        b = {k: v for k, v in b.items() if k not in RULE_KEYS}
        for k in ("left", "right", "blocks"):
            if isinstance(b.get(k), list):
                b[k] = strip(b[k])
        out.append(b)
    return out


def _nested(b: dict, fn) -> dict:
    return {**b, **{k: fn(b[k]) for k in ("left", "right", "blocks") if isinstance(b.get(k), list)}}


def personalize(blocks: list, v: Visitor) -> list:
    """Drop blocks whose audience does not match; in a slot, fallback blocks show only if nothing targeted showed.
    Applies inside columns and embedded sections too."""
    shown = [b for b in blocks if not b.get("fallback") and matches(b.get("audience") or {}, v)]
    filled = {b["slot"] for b in shown if b.get("slot") and _crm_rule(b.get("audience") or {})}
    out = []
    for b in blocks:
        if b.get("fallback"):
            if b.get("slot") not in filled:
                out.append(b)
        elif b in shown:
            out.append(_nested(b, lambda x: personalize(x, v)))
    return out


def _experiment_groups(blocks: list, groups: dict) -> dict:
    for b in blocks:
        if b.get("experiment"):
            vs = groups.setdefault(b["experiment"]["key"], [])
            if b["experiment"]["variant"] not in vs:
                vs.append(b["experiment"]["variant"])
        for k in ("left", "right", "blocks"):
            if isinstance(b.get(k), list):
                _experiment_groups(b[k], groups)
    return groups


def _keep(blocks: list, picked: dict) -> list:
    return [_nested(b, lambda x: _keep(x, picked)) for b in blocks
            if not b.get("experiment") or picked.get(b["experiment"]["key"]) == b["experiment"]["variant"]]


def _beta_pick(variants: list[str], counts: dict) -> str:
    draws = {k: random.betavariate(1 + counts.get(k, {}).get("c", 0), 1 + counts.get(k, {}).get("n", 0) - counts.get(k, {}).get("c", 0))
             for k in variants}
    return max(draws, key=draws.get)


async def _experiment(db: AsyncSession, page: CmsPage, key: str, variants: list[str]) -> CmsExperiment:
    e = (await db.execute(select(CmsExperiment).where(CmsExperiment.page_id == page.id, CmsExperiment.key == key))).scalar_one_or_none()
    if e is None:
        e = CmsExperiment(page_id=page.id, key=key, mode="AB", variants=variants, counts={}, status="RUNNING")
        db.add(e)
        await db.flush()
    elif sorted(e.variants) != sorted(variants):
        e.variants = variants
    return e


async def choose(db: AsyncSession, page: CmsPage, blocks: list, v: Visitor) -> tuple[list, dict]:
    """Keep one variant per experiment. Returns (blocks, {experiment key: variant})."""
    groups = _experiment_groups(blocks, {})
    picked: dict[str, str] = {}
    for key, variants in groups.items():
        e = await _experiment(db, page, key, variants)
        if e.status != "RUNNING" or not v.vh:
            picked[key] = (e.counts or {}).get("winner") or variants[0]      # control for anonymous-without-id
            continue
        prior = (await db.execute(select(CmsExperimentEvent.variant).where(CmsExperimentEvent.experiment_id == e.id,
                 CmsExperimentEvent.visitor_hash == v.vh, CmsExperimentEvent.kind == "VIEW"))).scalar_one_or_none()
        if prior in variants:
            picked[key] = prior
            continue
        if e.mode == "BANDIT":
            picked[key] = _beta_pick(variants, e.counts or {})
        else:
            picked[key] = variants[int(hashlib.sha256(f"{v.vh}:{e.id}".encode()).hexdigest(), 16) % len(variants)]
        if v.analytics:
            res = await db.execute(insert(CmsExperimentEvent).values(experiment_id=e.id, visitor_hash=v.vh, variant=picked[key], kind="VIEW")
                                   .on_conflict_do_nothing(constraint="uq_cms_exp_event"))
            if res.rowcount:
                c = dict(e.counts or {})
                c[picked[key]] = {**c.get(picked[key], {"n": 0, "c": 0}), "n": c.get(picked[key], {}).get("n", 0) + 1}
                e.counts = c
    return _keep(blocks, picked), picked


async def convert(db: AsyncSession, page: CmsPage, key: str, raw_visitor: str) -> bool:
    """Attribute a conversion to the variant the visitor saw (once per visitor; needs analytics consent)."""
    vh = wa.hashed("v", raw_visitor[:100])
    consent = await wa._latest_consent(db, vh)
    if not (consent and consent.analytics):
        return False
    e = (await db.execute(select(CmsExperiment).where(CmsExperiment.page_id == page.id, CmsExperiment.key == key))).scalar_one_or_none()
    if e is None:
        return False
    seen = (await db.execute(select(CmsExperimentEvent.variant).where(CmsExperimentEvent.experiment_id == e.id,
            CmsExperimentEvent.visitor_hash == vh, CmsExperimentEvent.kind == "VIEW"))).scalar_one_or_none()
    if seen is None:
        return False
    res = await db.execute(insert(CmsExperimentEvent).values(experiment_id=e.id, visitor_hash=vh, variant=seen, kind="CONVERT")
                           .on_conflict_do_nothing(constraint="uq_cms_exp_event"))
    if res.rowcount:
        c = dict(e.counts or {})
        c[seen] = {**c.get(seen, {"n": 0, "c": 0}), "c": c.get(seen, {}).get("c", 0) + 1}
        e.counts = c
    return bool(res.rowcount)


def stats(e: CmsExperiment, draws: int = 4000, seed: int = 7) -> dict:
    """Per-variant views, conversions and rate; probability each variant is best (Beta posterior simulation)."""
    rng = random.Random(seed)
    counts = e.counts or {}
    wins = {k: 0 for k in e.variants}
    for _ in range(draws):
        d = {k: rng.betavariate(1 + counts.get(k, {}).get("c", 0), 1 + counts.get(k, {}).get("n", 0) - counts.get(k, {}).get("c", 0)) for k in e.variants}
        wins[max(d, key=d.get)] += 1
    rows = []
    for k in e.variants:
        n, c = counts.get(k, {}).get("n", 0), counts.get(k, {}).get("c", 0)
        rows.append({"variant": k, "views": n, "conversions": c, "rate": round(c / n, 4) if n else None, "p_best": round(wins[k] / draws, 3)})
    total = sum(r["views"] for r in rows)
    return {"key": e.key, "mode": e.mode, "status": e.status, "variants": rows, "views": total,
            "enough_data": total >= 100 and all(r["views"] >= 30 for r in rows)}


async def forget_visitor(db: AsyncSession, raw_visitor: str) -> int:
    from sqlalchemy import delete
    vh = wa.hashed("v", raw_visitor[:100])
    return (await db.execute(delete(CmsExperimentEvent).where(CmsExperimentEvent.visitor_hash == vh))).rowcount or 0
