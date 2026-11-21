"""Conversation intelligence (M36.S05.T004): objections, themes, questions and next steps from consented call
transcripts and staff-handled website chats, with a coaching review workflow.

Rules that keep it honest:
- Opt-in: nothing is analysed unless CONVERSATION_INTELLIGENCE_ENABLED is on; a call needs recording consent and a
  transcript; a chat must have reached a person (bot-only chats are not coaching material).
- Every finding carries a verbatim quote from the source and its character offset; an AI suggestion whose quote is not
  found in the text is dropped. No sentiment or "quality" score is produced — only counts of quoted findings.
- Access: the agent sees and analyses their own calls; managers (crm.view_all / crm.edit_all) see all; only managers
  review (approve/reject + coaching note).
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.config import settings
from app.models.crm import CRMConversationInsight

MANAGER_VIEW = ("crm.view_all", "crm.edit_all")
MANAGER_EDIT = ("crm.edit_all",)
KINDS = ("objection", "theme", "question", "next_step")

RULES: list[tuple[str, str, re.Pattern]] = [
    ("objection", "price", re.compile(r"[^.?!\n]*\b(too (expensive|costly|high)|price is high|cheaper|discount|bei (ni )?ghali|reduce the price)\b[^.?!\n]*[.?!]?", re.I)),
    ("objection", "credit", re.compile(r"[^.?!\n]*\b(credit|pay later|on account|cash flow|terms)\b[^.?!\n]*[.?!]?", re.I)),
    ("objection", "delivery", re.compile(r"[^.?!\n]*\b(late deliver\w*|delivery (was|is) late|did not arrive|didn't arrive|missing cartons?|short deliver\w*)\b[^.?!\n]*[.?!]?", re.I)),
    ("objection", "competitor", re.compile(r"[^.?!\n]*\b(competitor|other brand|another supplier|cheaper brand)\b[^.?!\n]*[.?!]?", re.I)),
    ("objection", "quality", re.compile(r"[^.?!\n]*\b(leak\w*|damaged|broken|expired|bad quality|complain\w*)\b[^.?!\n]*[.?!]?", re.I)),
    ("theme", "product", re.compile(r"[^.?!\n]*\bPOVU\b[^.?!\n]*[.?!]?", re.I)),
    ("question", "question", re.compile(r"[^.?!\n]{8,}\?")),
    ("next_step", "follow_up", re.compile(r"[^.?!\n]*\b(i will|we will|i'll|we'll|call (you )?back|send (you )?(the )?(quote|price list)|next week|tomorrow)\b[^.?!\n]*[.?!]?", re.I)),
]


class IntelError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def is_manager(user) -> bool:
    return bool(getattr(user, "is_superuser", False)) or has_any_permission(user, MANAGER_VIEW)


async def source_text(db: AsyncSession, source_type: str, source_id: uuid.UUID, user) -> tuple[str, Optional[uuid.UUID]]:
    """(text, owner user id) for an allowed source; raises IntelError otherwise."""
    if not settings.CONVERSATION_INTELLIGENCE_ENABLED:
        raise IntelError(409, "Conversation intelligence is not switched on for this company.")
    if source_type == "call":
        from app.models.voip import CallLog
        c = await db.get(CallLog, source_id)
        if c is None or not (is_manager(user) or c.agent_id == user.id):
            raise IntelError(404, "Call not found")
        if not c.recording_consent or not c.transcript:
            raise IntelError(422, "Only calls with recording consent and a transcript can be analysed.")
        return c.transcript, c.agent_id
    if source_type == "chat":
        from app.models.crm import CRMChatMessage, CRMChatSession
        sess = await db.get(CRMChatSession, source_id)
        if sess is None or not is_manager(user):
            raise IntelError(404, "Chat not found")
        msgs = (await db.execute(select(CRMChatMessage).where(CRMChatMessage.session_id == sess.id)
                                 .order_by(CRMChatMessage.created_at))).scalars().all()
        if not any(m.sender == "AGENT" for m in msgs):
            raise IntelError(422, "Only chats handled by a person are analysed.")
        text = "\n".join(f"{'Customer' if m.sender == 'VISITOR' else 'Agent' if m.sender == 'AGENT' else 'Bot'}: {m.body}" for m in msgs)
        return text, None
    raise IntelError(404, "Unknown source")


def extract(text: str) -> list[dict]:
    """Rule-based findings, each with the exact quote and where it is in the text."""
    out, seen = [], set()
    for kind, label, rx in RULES:
        for m in rx.finditer(text):
            quote = m.group(0).strip()
            if len(quote) < 4 or (kind, quote) in seen:
                continue
            seen.add((kind, quote))
            out.append({"kind": kind, "label": label, "quote": quote[:300], "offset": text.find(quote)})
    return sorted(out, key=lambda f: (KINDS.index(f["kind"]), f["offset"]))


def verified(text: str, suggestions: list) -> list[dict]:
    """Keep only AI findings whose quote is verbatim in the text (source-linked, nothing invented)."""
    out = []
    for s in suggestions or []:
        if not isinstance(s, dict) or s.get("kind") not in KINDS:
            continue
        quote = str(s.get("quote") or "").strip()
        pos = text.find(quote) if quote else -1
        if pos < 0 or len(quote) < 4:
            continue
        out.append({"kind": s["kind"], "label": str(s.get("label") or s["kind"])[:40], "quote": quote[:300], "offset": pos})
    return out


async def analyse(db: AsyncSession, source_type: str, source_id: uuid.UUID, user) -> CRMConversationInsight:
    text, owner = await source_text(db, source_type, source_id, user)
    findings, engine = extract(text), "rules"
    from app.services.ai_provider import get_ai_provider
    provider = get_ai_provider()
    if type(provider).__name__ != "MockProvider" and len(text) > 40:
        try:
            obj, _ = await provider.generate_structured_output(
                "Find sales objections, themes, customer questions and agreed next steps in this conversation. "
                "Quote the exact words.\n\n" + text[:12000],
                system="You extract findings. Every quote must be copied exactly from the text.",
                schema_hint='{"findings": [{"kind": "objection|theme|question|next_step", "label": "short", "quote": "exact words"}]}')
            ai = verified(text, (obj or {}).get("findings", []))
            if ai:
                keys = {(f["kind"], f["quote"]) for f in findings}
                findings += [f for f in ai if (f["kind"], f["quote"]) not in keys]
                engine = "rules+ai"
        except Exception:
            pass  # rules alone; the AI is optional
    counts = {k: sum(1 for f in findings if f["kind"] == k) for k in KINDS}
    row = (await db.execute(select(CRMConversationInsight).where(CRMConversationInsight.source_type == source_type,
                                                                CRMConversationInsight.source_id == source_id))).scalar_one_or_none()
    if row is None:
        row = CRMConversationInsight(source_type=source_type, source_id=source_id, agent_id=owner)
        db.add(row)
    row.findings, row.counts, row.engine, row.status = findings, counts, engine, "PENDING_REVIEW"
    row.analysed_by_id, row.analysed_at = user.id, datetime.now(timezone.utc)
    row.reviewed_by_id = row.reviewed_at = row.coaching_note = None
    await db.flush()
    return row


async def review(db: AsyncSession, insight_id: uuid.UUID, user, status: str, note: Optional[str]) -> CRMConversationInsight:
    if not (getattr(user, "is_superuser", False) or has_any_permission(user, MANAGER_EDIT)):
        raise IntelError(403, "Only a sales manager can review conversations.")
    row = await db.get(CRMConversationInsight, insight_id)
    if row is None:
        raise IntelError(404, "Insight not found")
    if row.agent_id is not None and row.agent_id == user.id:
        raise IntelError(409, "You cannot review your own conversation.")
    row.status, row.coaching_note = status, (note or None)
    row.reviewed_by_id, row.reviewed_at = user.id, datetime.now(timezone.utc)
    await db.flush()
    return row


def visible(q, user):
    return q if is_manager(user) else q.where(CRMConversationInsight.agent_id == user.id)
