"""Sales playbooks, guided selling and deal plans (M43.S01.T010).

Playbook = versioned checklist for a call, visit, qualification or a pipeline stage: questions (text / yes-no /
number / choice), required flags, conditional display (show_if {key, equals}), optional mapping of an answer onto a
whitelisted CRM field, and stage guidance text. Lifecycle DRAFT → PENDING_APPROVAL → PUBLISHED (approved by a
company-wide CRM editor who is not the author) → RETIRED when a newer version of the same family is published.
A run stores the exact version answered, so later edits never rewrite history.
Stage gate: a published stage playbook with blocks_stage_exit=True must have a completed run before the deal leaves
that stage (enforced in crm_stage_gate.check_stage_exit).
Deal plan (mutual action plan): dated steps owned by us or the customer, shared with the customer contact through
a revocable link (token stored as SHA-256); the customer may tick only customer-owned steps.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMDealPlan, CRMPlaybook, CRMPlaybookRun, CRMRecord, CRMStatus

# answer → CRM field (only these; values validated by type)
FIELD_MAP = {"expected_revenue": "number", "expected_close_date": "date", "industry_segment": "text",
             "contact_phone": "text", "contact_person_name": "text", "next_action_date": "date", "notes": "append"}


class PlaybookError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def validate_questions(questions: list[dict]) -> list[dict]:
    keys, out = set(), []
    for q in questions:
        key = str(q.get("key", "")).strip()
        if not key or key in keys or len(key) > 40:
            raise PlaybookError(f"Question keys must be unique and short: {key!r}")
        keys.add(key)
        qtype = q.get("type", "text")
        if qtype not in ("text", "yesno", "number", "choice"):
            raise PlaybookError(f"Unknown question type {qtype!r}")
        if qtype == "choice" and not q.get("choices"):
            raise PlaybookError(f"Question {key!r} needs choices")
        if q.get("maps_to") and q["maps_to"] not in FIELD_MAP:
            raise PlaybookError(f"Question {key!r} cannot write to {q['maps_to']!r}")
        cond = q.get("show_if")
        if cond and cond.get("key") not in keys:
            raise PlaybookError(f"Question {key!r} depends on a later or unknown question")
        out.append({"key": key, "text": str(q.get("text", ""))[:500], "type": qtype, "required": bool(q.get("required")),
                    "choices": [str(c)[:100] for c in q.get("choices") or []][:20], "maps_to": q.get("maps_to"),
                    "show_if": {"key": cond["key"], "equals": cond.get("equals")} if cond else None,
                    "help": str(q.get("help") or "")[:500] or None})
    return out


def visible(questions: list[dict], answers: dict) -> list[dict]:
    return [q for q in questions if not q.get("show_if") or answers.get(q["show_if"]["key"]) == q["show_if"]["equals"]]


def check_answers(questions: list[dict], answers: dict, complete: bool) -> dict:
    shown = visible(questions, answers)
    clean = {}
    for q in shown:
        v = answers.get(q["key"])
        if v in (None, ""):
            if complete and q["required"]:
                raise PlaybookError(f"Answer required: {q['text'] or q['key']}")
            continue
        if q["type"] == "yesno" and not isinstance(v, bool):
            raise PlaybookError(f"{q['key']}: yes or no")
        if q["type"] == "number":
            try:
                v = float(Decimal(str(v)))
            except InvalidOperation:
                raise PlaybookError(f"{q['key']}: a number") from None
        if q["type"] == "choice" and v not in q["choices"]:
            raise PlaybookError(f"{q['key']}: choose one of the options")
        clean[q["key"]] = v if not isinstance(v, str) else v[:2000]
    return clean


def apply_mapping(rec: CRMRecord, questions: list[dict], answers: dict) -> list[str]:
    changed = []
    for q in visible(questions, answers):
        field, v = q.get("maps_to"), answers.get(q["key"])
        if not field or v in (None, ""):
            continue
        kind = FIELD_MAP[field]
        if kind == "number":
            setattr(rec, field, Decimal(str(v)))
        elif kind == "date":
            setattr(rec, field, date.fromisoformat(str(v)))
        elif kind == "append":
            rec.notes = ((rec.notes or "") + f"\n[Playbook] {q['text']}: {v}")[-20000:]
        else:
            setattr(rec, field, str(v)[:200])
        changed.append(field)
    return changed


async def publish(db: AsyncSession, pb: CRMPlaybook, approver) -> None:
    if pb.status != "PENDING_APPROVAL":
        raise PlaybookError("Only a playbook waiting for approval can be published.", 409)
    if pb.created_by_id == approver.id:
        raise PlaybookError("The author cannot approve their own playbook.", 403)
    for old in (await db.execute(select(CRMPlaybook).where(CRMPlaybook.family_id == pb.family_id,
                                                           CRMPlaybook.status == "PUBLISHED"))).scalars():
        old.status = "RETIRED"
    await db.flush()          # retire first: only one PUBLISHED version per family (partial unique index)
    pb.status, pb.approved_by_id, pb.approved_at = "PUBLISHED", approver.id, datetime.now(timezone.utc)


async def new_version(db: AsyncSession, pb: CRMPlaybook, author_id) -> CRMPlaybook:
    top = (await db.execute(select(func.max(CRMPlaybook.version)).where(CRMPlaybook.family_id == pb.family_id))).scalar_one()
    clone = CRMPlaybook(family_id=pb.family_id, version=(top or 0) + 1, name=pb.name, purpose=pb.purpose,
                        stage_id=pb.stage_id, guidance=pb.guidance, questions=pb.questions,
                        blocks_stage_exit=pb.blocks_stage_exit, status="DRAFT", created_by_id=author_id)
    db.add(clone)
    await db.flush()
    return clone


async def outcome_report(db: AsyncSession, family_id: uuid.UUID) -> dict:
    """Runs and deal outcomes with vs without a completed run of this playbook family (no causal claim)."""
    ids = [r for r in (await db.execute(select(CRMPlaybook.id).where(CRMPlaybook.family_id == family_id))).scalars()]
    runs = (await db.execute(select(CRMPlaybookRun).where(CRMPlaybookRun.playbook_id.in_(ids)))).scalars().all()
    done_records = {r.crm_record_id for r in runs if r.completed}
    closed = (await db.execute(select(CRMRecord.id, CRMRecord.status).where(
        CRMRecord.status.in_((CRMStatus.WON, CRMStatus.LOST))))).all()

    def rate(rows):
        won = sum(1 for _, s in rows if s == CRMStatus.WON)
        return {"closed": len(rows), "won": won, "win_rate": round(won / len(rows), 3) if rows else None}
    return {"runs": len(runs), "completed": sum(1 for r in runs if r.completed),
            "with_playbook": rate([x for x in closed if x[0] in done_records]),
            "without_playbook": rate([x for x in closed if x[0] not in done_records]),
            "note": "Comparison only; it does not show the playbook caused the difference."}


def share_token() -> tuple[str, str]:
    t = secrets.token_urlsafe(24)
    return t, hashlib.sha256(t.encode()).hexdigest()


async def plan_by_token(db: AsyncSession, token: str) -> Optional[CRMDealPlan]:
    h = hashlib.sha256((token or "").encode()).hexdigest()
    plan = (await db.execute(select(CRMDealPlan).where(CRMDealPlan.share_token_hash == h))).scalar_one_or_none()
    return plan if plan and plan.shared else None


def clean_steps(steps: list[dict[str, Any]]) -> list[dict]:
    out = []
    for i, s in enumerate(steps[:50]):
        title = str(s.get("title") or "").strip()[:200]
        if not title:
            raise PlaybookError("Every step needs a title.")
        owner = s.get("owner") if s.get("owner") in ("us", "customer") else "us"
        due = s.get("due_date")
        out.append({"id": s.get("id") or uuid.uuid4().hex[:8], "title": title, "owner": owner,
                    "due_date": date.fromisoformat(due).isoformat() if due else None, "done": bool(s.get("done"))})
    return out
