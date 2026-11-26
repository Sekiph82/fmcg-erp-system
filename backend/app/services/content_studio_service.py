"""M46.S01.T003 AI brand voice and content studio.

- Drafts only: nothing here publishes. An approved draft can be copied into a CMS page draft, e-mail design or social
  post, which then goes through that channel's own review/publish rules.
- Engine: with a monthly AI budget > 0 and a real provider configured, the provider writes the first draft inside the
  budget (the call is refused once the month's estimated spend would pass the cap). Otherwise — and whenever the
  provider is the mock or fails — a deterministic template engine assembles the draft from the brief and approved
  evidence. The engine used and the estimated cost are stored on the draft.
- Every draft is reviewed against the brand profile: terminology is corrected, banned terms and sentences that make a
  claim (numbers, percentages, claim words) without citing approved evidence [E:<id>] are findings. A draft with
  error findings cannot be approved; approval needs a second person.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import CsBrandProfile, CsDraft, CsUsage

CHANNELS = {"web": 6000, "blog": 12000, "email": 4000, "social": 280, "sms": 160, "whatsapp": 1000}
TEMPLATES = {
    "product_launch": "Introduce a product: what it is, who it is for, where to buy.",
    "promotion": "Announce a time-limited offer with the conditions.",
    "how_to": "Explain how to use or store a product, step by step.",
    "faq": "Answer the common questions about a topic.",
    "announcement": "Share company news.",
}
PRICE_PER_1K = 0.01          # conservative per-1k-token estimate used for the budget gate (USD)
CITE = re.compile(r"\[E:([\w-]{1,40})\]")
NUMBER_CLAIM = re.compile(r"\d+\s*(%|percent|x\b|times)|#1|number one|best|cheapest|healthiest|guarantee", re.I)


class StudioError(ValueError):
    pass


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def review(profile: CsBrandProfile, text: str, channel: str) -> tuple[str, list[dict]]:
    """Apply terminology; report banned terms, uncited claims, unknown citations and length. Returns (text, findings)."""
    findings: list[dict] = []
    for wrong, right in (profile.terminology or {}).items():
        pat = re.compile(rf"\b{re.escape(wrong)}\b", re.I)
        if pat.search(text):
            text = pat.sub(right, text)
            findings.append({"level": "info", "code": "terminology", "message": f"“{wrong}” changed to “{right}”."})
    for term in profile.banned_terms or []:
        if re.search(rf"\b{re.escape(term)}\b", text, re.I):
            findings.append({"level": "error", "code": "banned_term", "message": f"Banned term: “{term}”."})
    evidence = {str(e.get("id")) for e in profile.evidence or []}
    claim_words = [w.lower() for w in profile.claim_terms or []]
    for s in _sentences(text):
        cites = CITE.findall(s)
        for c in cites:
            if c not in evidence:
                findings.append({"level": "error", "code": "unknown_evidence", "message": f"Cites evidence E:{c} that is not approved."})
        is_claim = bool(NUMBER_CLAIM.search(CITE.sub("", s))) or any(w in s.lower() for w in claim_words)
        if is_claim and not cites:
            findings.append({"level": "error", "code": "uncited_claim", "message": f"Claim without approved evidence: “{s[:120]}”."})
    limit = CHANNELS[channel]
    if len(CITE.sub("", text)) > limit:
        findings.append({"level": "error", "code": "too_long", "message": f"{len(text)} characters; {channel} allows {limit}."})
    return text, findings


def _template_draft(profile: CsBrandProfile, channel: str, template: str, brief: str, evidence_ids: list[str]) -> str:
    facts = [e for e in profile.evidence or [] if str(e.get("id")) in evidence_ids]
    lines = [brief.strip().rstrip(".") + "."]
    lines += [f'{f["text"].rstrip(".")}. [E:{f["id"]}]' for f in facts]
    if template == "how_to":
        lines.insert(1, "Here is how:")
    elif template == "promotion":
        lines.append("Offer terms apply; ask your POVU distributor for details.")
    elif template == "faq":
        lines = [f"Q: {brief.strip().rstrip('?')}?", "A: " + " ".join(lines[1:] or ["Contact our team for the details."])]
    text = "\n".join(lines) if channel in ("web", "blog", "email") else " ".join(lines)
    limit = CHANNELS[channel]
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


async def _usage(db: AsyncSession, profile: CsBrandProfile) -> CsUsage:
    u = (await db.execute(select(CsUsage).where(CsUsage.profile_id == profile.id, CsUsage.month == _month()))).scalar_one_or_none()
    if u is None:
        u = CsUsage(profile_id=profile.id, month=_month(), spent=0.0, calls=0)
        db.add(u)
        await db.flush()
    return u


async def generate(db: AsyncSession, profile: CsBrandProfile, channel: str, template: str, brief: str, evidence_ids: list[str],
                   user, source: Optional[CsDraft] = None) -> CsDraft:
    if channel not in CHANNELS or template not in TEMPLATES:
        raise StudioError("Unknown channel or template")
    brief = brief.strip()[:2000]
    if len(brief) < 10:
        raise StudioError("Write a brief of at least 10 characters")
    engine, cost, body = "rules", 0.0, None
    budget = float(profile.monthly_budget or 0)
    if budget > 0:
        from app.services.ai_provider import get_ai_provider
        provider = get_ai_provider()
        name = type(provider).__name__.replace("Provider", "").lower()
        usage = await _usage(db, profile)
        est = PRICE_PER_1K * 2          # ~2k tokens per draft, checked before the call
        if name != "mock" and usage.spent + est <= budget:
            facts = "\n".join(f'[E:{e["id"]}] {e["text"]}' for e in profile.evidence or [] if str(e.get("id")) in evidence_ids)
            system = (f"You write marketing copy for {profile.name}. Voice: {profile.voice}\nNever use: {', '.join(profile.banned_terms or [])}.\n"
                      f"Only state facts from the evidence list and cite them as [E:id]. Max {CHANNELS[channel]} characters. Draft only.")
            try:
                r = await provider.generate_text(f"Task: {TEMPLATES[template]}\nChannel: {channel}\nBrief: {brief}\nEvidence:\n{facts or '(none)'}", system=system)
                body = (r.text or "").strip()
                cost = PRICE_PER_1K * ((getattr(r, "prompt_tokens", 0) or 0) + (getattr(r, "completion_tokens", 0) or 0)) / 1000
                engine = getattr(r, "provider", name) or name
                usage.spent, usage.calls = usage.spent + cost, usage.calls + 1
            except Exception:                     # provider down: deterministic draft instead, nothing invented
                body = None
    if not body:
        engine, cost = "rules", 0.0
        body = _template_draft(profile, channel, template, brief, evidence_ids)
    body, findings = review(profile, body, channel)
    d = CsDraft(profile_id=profile.id, channel=channel, template=template, brief=brief, body=body, engine=engine,
                cost=Decimal(str(round(cost, 4))), findings=findings, status="DRAFT", source_id=source.id if source else None,
                created_by=user.username, history=[{"at": datetime.now(timezone.utc).isoformat(), "by": user.username,
                                                    "action": "repurposed" if source else "generated", "engine": engine}])
    db.add(d)
    return d


def edit(profile: CsBrandProfile, d: CsDraft, body: str, user) -> None:
    if d.status not in ("DRAFT", "REJECTED"):
        raise StudioError("Only drafts can be edited")
    body, findings = review(profile, body[:20000], d.channel)
    d.history = [*(d.history or []), {"at": datetime.now(timezone.utc).isoformat(), "by": user.username, "action": "edited", "previous": d.body}]
    d.body, d.findings, d.status = body, findings, "DRAFT"


def submit(d: CsDraft, user) -> None:
    if d.status != "DRAFT":
        raise StudioError("Only a draft can be submitted")
    d.status = "IN_REVIEW"
    d.history = [*(d.history or []), {"at": datetime.now(timezone.utc).isoformat(), "by": user.username, "action": "submitted"}]


def decide(d: CsDraft, user, ok: bool, note: str = "") -> None:
    if d.status != "IN_REVIEW":
        raise StudioError("Only a draft in review can be decided")
    if d.created_by == user.username or any(h.get("by") == user.username and h.get("action") == "edited" for h in d.history or []):
        raise StudioError("A different person must approve (the author or an editor cannot)")
    if ok and any(f["level"] == "error" for f in d.findings or []):
        raise StudioError("Resolve the error findings before approving")
    d.status = "APPROVED" if ok else "REJECTED"
    d.approved_by = user.username if ok else None
    d.history = [*(d.history or []), {"at": datetime.now(timezone.utc).isoformat(), "by": user.username,
                                     "action": "approved" if ok else "rejected", "note": note[:300]}]
