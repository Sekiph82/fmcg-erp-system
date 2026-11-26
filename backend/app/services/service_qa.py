"""M50.S01.T006 support QA for the service agent: unresolved-question clusters, answer/citation reviews, resolution /
CSAT / CES metrics by topic and language, knowledge-gap proposals -> approved KB articles, safety complaints.

Honesty rules: a rate is None (not 0) when there is nothing to compute it from; a chat is "contained" only if the agent
answered and never abstained, handed over or escalated a safety report; "confirmed resolved" additionally needs a
satisfied CSAT/CES from the customer. Safety chats are never counted as resolved.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m50_service_agent import KBGapProposal, ServiceAgentTurn
from app.services import kb_retrieval

VERDICTS = ("CORRECT", "WRONG_CITATION", "INACCURATE", "UNSUPPORTED")
UNRESOLVED_OUTCOMES = ("ABSTAINED",)
ESCALATING = ("ABSTAINED", "HANDOFF", "SAFETY")


class QAError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db, user, event: str, target_type: str, target_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None), actor_name=getattr(user, "full_name", None),
                    event_type=event, module="helpdesk", target_type=target_type, target_id=str(target_id), details=details))


async def _turns(db: AsyncSession, days: int) -> list[ServiceAgentTurn]:
    return list((await db.execute(select(ServiceAgentTurn).where(ServiceAgentTurn.created_at >= _now() - timedelta(days=days))
                                  .order_by(ServiceAgentTurn.created_at))).scalars())


# ── clustering ───────────────────────────────────────────────────────────────

def cluster(questions: list[tuple[str, str, str]]) -> list[dict]:
    """questions: (id, text, lang). Greedy: a question joins the first cluster sharing >= a third of its stems.
    ponytail: lexical overlap, no embeddings; chaining is possible. Upgrade to embeddings if clusters blur."""
    groups: list[dict] = []
    for qid, text, lang in questions:
        ts = {w[:5] for w in kb_retrieval.terms(text, True) if w != "povu"}      # 5-letter stems: dilute = dilution = diluted
        if not ts:
            continue
        for g in groups:
            shared = len(ts & g["terms"])
            if shared and shared / min(len(ts), len(g["terms"])) >= 0.34:
                break
        else:
            g = {"terms": set(), "freq": Counter(), "items": []}
            groups.append(g)
        g["terms"] |= ts
        g["freq"].update(ts)
        g["items"].append((qid, text, lang))
    out = []
    for g in groups:
        top = [w for w, _ in sorted(g["freq"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
        out.append({"key": "-".join(sorted(top)), "count": len(g["items"]), "terms": top,
                    "languages": dict(Counter(lang for _, _, lang in g["items"])),
                    "turn_ids": [i for i, _, _ in g["items"]], "samples": [t for _, t, _ in g["items"]][:5]})
    return sorted(out, key=lambda c: (-c["count"], c["key"]))


async def unresolved_clusters(db: AsyncSession, days: int = 30) -> list[dict]:
    rows = [t for t in await _turns(db, days) if t.outcome in UNRESOLVED_OUTCOMES or (t.outcome == "ANSWERED" and (t.csat or 5) <= 2)]
    return cluster([(str(t.id), t.question, t.lang) for t in rows])


# ── metrics ──────────────────────────────────────────────────────────────────

def _avg(xs: list[int]) -> Optional[float]:
    return round(sum(xs) / len(xs), 2) if xs else None


def _rate(a: int, b: int) -> Optional[float]:
    return round(a / b, 3) if b else None


async def metrics(db: AsyncSession, days: int = 30) -> dict:
    turns = await _turns(db, days)
    by_session: dict = {}
    for t in turns:
        by_session.setdefault(t.session_id, []).append(t)
    contained = confirmed = with_feedback = 0
    for ts in by_session.values():
        outs = {t.outcome for t in ts}
        if outs & {"ANSWERED", "ORDER", "TICKET"} and not outs & set(ESCALATING):
            contained += 1
            fb = [t for t in ts if t.csat or t.ces]
            if fb:
                with_feedback += 1
                if all((t.csat or 5) >= 4 and (t.ces or 7) >= 5 for t in fb):
                    confirmed += 1
    answered = sum(t.outcome == "ANSWERED" for t in turns)
    abstained = sum(t.outcome == "ABSTAINED" for t in turns)
    reviewed = [t for t in turns if t.review_verdict]

    def split(key):
        res = {}
        for k in sorted({getattr(t, key) for t in turns}):
            ts = [t for t in turns if getattr(t, key) == k]
            a, b = sum(t.outcome == "ANSWERED" for t in ts), sum(t.outcome == "ABSTAINED" for t in ts)
            res[k] = {"turns": len(ts), "answered": a, "abstained": b, "grounded_rate": _rate(a, a + b),
                      "escalated": sum(t.outcome in ("HANDOFF", "SAFETY") for t in ts), "csat": _avg([t.csat for t in ts if t.csat])}
        return res
    return {"days": days, "turns": len(turns), "sessions": len(by_session),
            "outcomes": dict(Counter(t.outcome for t in turns)), "modes": dict(Counter(t.mode for t in turns)),
            "grounded_rate": _rate(answered, answered + abstained),
            "contained_sessions": contained, "containment_rate": _rate(contained, len(by_session)),
            "confirmed_resolution_rate": _rate(confirmed, with_feedback), "sessions_with_feedback": with_feedback,
            "csat": {"avg": _avg([t.csat for t in turns if t.csat]), "n": sum(1 for t in turns if t.csat)},
            "ces": {"avg": _avg([t.ces for t in turns if t.ces]), "n": sum(1 for t in turns if t.ces)},
            "accuracy": {"reviewed": len(reviewed), "verdicts": dict(Counter(t.review_verdict for t in reviewed)),
                         "correct_rate": _rate(sum(t.review_verdict == "CORRECT" for t in reviewed), len(reviewed)),
                         "citation_ok_rate": _rate(sum(t.review_verdict != "WRONG_CITATION" for t in reviewed), len(reviewed))},
            "safety_escalations": sum(t.outcome == "SAFETY" for t in turns),
            "by_topic": split("topic"), "by_language": split("lang")}


async def record_feedback(db: AsyncSession, sess, csat: Optional[int], ces: Optional[int]) -> bool:
    """The customer's rating applies to the chat's latest agent turn."""
    t = (await db.execute(select(ServiceAgentTurn).where(ServiceAgentTurn.session_id == sess.id, ServiceAgentTurn.outcome != "INJECTION")
                          .order_by(ServiceAgentTurn.created_at.desc()).limit(1))).scalar_one_or_none()
    if t is None:
        return False
    if csat is not None:
        t.csat = csat
    if ces is not None:
        t.ces = ces
    return True


# ── reviews ──────────────────────────────────────────────────────────────────

async def review_queue(db: AsyncSession, limit: int = 50) -> list[dict]:
    """Answered turns nobody has reviewed yet, newest first, with the cited articles' current state."""
    rows = (await db.execute(select(ServiceAgentTurn).where(ServiceAgentTurn.outcome == "ANSWERED", ServiceAgentTurn.review_verdict.is_(None))
                             .order_by(ServiceAgentTurn.created_at.desc()).limit(limit))).scalars().all()
    return [{"id": str(t.id), "question": t.question, "answer": t.answer, "citations": t.citations, "lang": t.lang, "topic": t.topic,
             "mode": t.mode, "csat": t.csat, "at": t.created_at.isoformat()} for t in rows]


async def review(db: AsyncSession, user, turn_id, verdict: str, note: Optional[str]) -> ServiceAgentTurn:
    if verdict not in VERDICTS:
        raise QAError("Unknown verdict.")
    t = await db.get(ServiceAgentTurn, turn_id)
    if t is None or t.outcome != "ANSWERED":
        raise QAError("Only answered turns are reviewed.")
    if verdict != "CORRECT" and not (note or "").strip():
        raise QAError("A note is needed when the answer is not correct.")
    t.review_verdict, t.reviewed_by, t.reviewed_at, t.review_note = verdict, user.username, _now(), (note or "").strip() or None
    _audit(db, user, "SERVICE_AGENT_REVIEW", "sa_turn", t.id, {"verdict": verdict})
    return t


# ── knowledge gaps ───────────────────────────────────────────────────────────

async def propose_gap(db: AsyncSession, user, *, cluster_key: str, title: str, summary: Optional[str], content_md: str,
                      days: int = 30, target_article_id=None) -> KBGapProposal:
    cl = next((c for c in await unresolved_clusters(db, days) if c["key"] == cluster_key), None)
    if cl is None:
        raise QAError("That cluster no longer exists in this period.")
    dup = (await db.execute(select(KBGapProposal).where(KBGapProposal.cluster_key == cluster_key, KBGapProposal.status == "PROPOSED"))).scalar_one_or_none()
    if dup is not None:
        raise QAError("There is already an open proposal for this cluster.")
    p = KBGapProposal(cluster_key=cluster_key, topic=Counter([t for t in await _topics(db, cl["turn_ids"])]).most_common(1)[0][0],
                      sample_questions=cl["samples"], question_count=cl["count"], languages=cl["languages"], proposed_title=title.strip()[:300],
                      proposed_summary=(summary or "").strip() or None, proposed_content_md=content_md, target_article_id=target_article_id,
                      created_by=user.username)
    db.add(p)
    await db.flush()
    _audit(db, user, "KB_GAP_PROPOSED", "kb_gap", p.id, {"cluster": cluster_key, "questions": cl["count"]})
    return p


async def _topics(db, turn_ids) -> list[str]:
    ids = [uuid.UUID(i) for i in turn_ids]
    return [r for r in (await db.execute(select(ServiceAgentTurn.topic).where(ServiceAgentTurn.id.in_(ids)))).scalars()] or ["other"]


async def edit_gap(db: AsyncSession, user, gap_id, *, title: str, summary: Optional[str], content_md: str) -> KBGapProposal:
    p = await db.get(KBGapProposal, gap_id)
    if p is None or p.status != "PROPOSED":
        raise QAError("Only open proposals can be edited.")
    p.proposed_title, p.proposed_summary, p.proposed_content_md = title.strip()[:300], (summary or "").strip() or None, content_md
    _audit(db, user, "KB_GAP_EDITED", "kb_gap", p.id, {})
    return p


async def decide_gap(db: AsyncSession, user, gap_id, approve: bool, note: Optional[str]) -> KBGapProposal:
    """Two-person rule: the proposer cannot approve; approving publishes (or updates) the public KB article."""
    from app.models.knowledge_base import KBArticle, KBArticleRevision
    p = await db.get(KBGapProposal, gap_id, with_for_update=True)
    if p is None or p.status != "PROPOSED":
        raise QAError("This proposal is already decided.")
    if approve:
        if p.created_by == user.username:
            raise QAError("A second person must approve: you wrote this proposal.")
        if not p.proposed_content_md.strip():
            raise QAError("The article has no content yet.")
        if kb_retrieval.INSTRUCTION_IN_DOC.search(f"{p.proposed_title} {p.proposed_summary or ''} {p.proposed_content_md}"):
            raise QAError("The text contains instruction-like wording and cannot become an answer source.")
        now = datetime.utcnow()
        art = await db.get(KBArticle, p.target_article_id) if p.target_article_id else None
        if art is not None:
            db.add(KBArticleRevision(article_id=art.id, version_no=art.version or 1, title=art.title, content_md=art.content_md,
                                     change_summary=f"Before knowledge-gap update {p.id}", changed_by_id=user.id))
            art.title, art.summary, art.content_md = p.proposed_title, p.proposed_summary, p.proposed_content_md
            art.version, art.last_editor_id = (art.version or 1) + 1, user.id
            art.status, art.is_internal_only, art.published_by_id, art.published_at = "PUBLISHED", False, user.id, now
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", p.proposed_title.lower()).strip("-")[:60] or "article"
            art = KBArticle(slug=f"{slug}-{uuid.uuid4().hex[:6]}", title=p.proposed_title, summary=p.proposed_summary,
                            content_md=p.proposed_content_md, status="PUBLISHED", is_internal_only=False, access_level="all", tags=["gap"],
                            author_id=user.id, last_editor_id=user.id, published_by_id=user.id, published_at=now)
            db.add(art)
        await db.flush()
        p.article_id = art.id
    p.status, p.decided_by, p.decision_note, p.decided_at = ("APPROVED" if approve else "REJECTED"), user.username, (note or None), _now()
    _audit(db, user, "KB_GAP_APPROVED" if approve else "KB_GAP_REJECTED", "kb_gap", p.id, {"article": str(p.article_id) if p.article_id else None})
    return p


async def retest(db: AsyncSession, question: str) -> dict:
    """What the agent would cite for this question right now (no model call, nothing stored)."""
    hits = await kb_retrieval.search(db, question, glossary=True)
    return {"grounded": bool(hits), "citations": [{"slug": h.slug, "title": h.title, "version": h.version, "kind": h.kind} for h in hits]}


# ── safety ───────────────────────────────────────────────────────────────────

async def safety_cases(db: AsyncSession, days: int = 90) -> list[dict]:
    from app.models.consumer_complaints import ConsumerComplaint
    out = []
    for t in [x for x in await _turns(db, days) if x.outcome == "SAFETY"]:
        c = await db.get(ConsumerComplaint, t.complaint_id) if t.complaint_id else None
        out.append({"turn_id": str(t.id), "at": t.created_at.isoformat(), "lang": t.lang, "lot_number": t.lot_number,
                    "complaint_ref": c.complaint_ref if c else None, "complaint_status": c.status.value if c else None,
                    "product": c.product_name if c else None, "regulatory_report_required": c.regulatory_report_required if c else None})
    return list(reversed(out))
