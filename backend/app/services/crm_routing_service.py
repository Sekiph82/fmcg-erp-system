"""Lead rotation and routing, deal-stage approvals, deal splits and handoffs (M43.S01.T014).

Routing: active rules in priority order; the first rule whose conditions match a new unassigned lead assigns it.
ROUND_ROBIN cycles through the rule's people; WEIGHTED uses smooth weighted round robin (deterministic, fair over
time); FIXED always picks the first. People who are inactive or marked unavailable are skipped. The rule row is
locked while choosing, so concurrent leads never get the same slot twice.
Stage approvals: a rule on a stage (optionally only above an expected value) means entering that stage needs an
APPROVED request; the first attempt files the request and is refused; the requester can never approve their own.
Splits: shares per person must total exactly 100 %; on a won deal each share can be credited to commissions through
the existing commission engine (deduplicated per order and person).
Handoff: when a deal is won, one briefing for service/finance (customer, contacts, value, promised terms, plan steps
and open tasks) is created once.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import (CRMDealSplit, CRMHandoff, CRMRecord, CRMRoutingRule, CRMStageApprovalRequest,
                            CRMStageApprovalRule)

CONDITION_KEYS = ("source_type", "source_detail", "sales_region_id", "territory_id", "industry_segment",
                  "record_type", "min_expected_revenue")


def matches(rule: CRMRoutingRule, rec: CRMRecord) -> bool:
    for key, want in (rule.conditions or {}).items():
        if want in (None, ""):
            continue
        if key == "min_expected_revenue":
            if Decimal(str(rec.expected_revenue or 0)) < Decimal(str(want)):
                return False
            continue
        have = getattr(rec, key, None)
        have = getattr(have, "value", have)
        if str(have or "").lower() != str(want).lower():
            return False
    return True


async def _available(db: AsyncSession, user_ids: list[str]) -> list[str]:
    from app.models.user import User
    from app.models.voip import VoiceAgentProfile
    active = {str(u) for u in (await db.execute(select(User.id).where(
        User.id.in_([UUID(u) for u in user_ids]), User.is_active.is_(True)))).scalars()}
    away = {str(p.user_id) for p in (await db.execute(select(VoiceAgentProfile).where(
        VoiceAgentProfile.user_id.in_([UUID(u) for u in user_ids]), VoiceAgentProfile.available.is_(False)))).scalars()}
    return [u for u in user_ids if u in active and u not in away]


def pick(rule: CRMRoutingRule, people: list[str]) -> str:
    state = dict(rule.state or {})
    if rule.method == "FIXED":
        return people[0]
    if rule.method == "WEIGHTED":
        weights = {p: max(1, int((rule.weights or {}).get(p, 1))) for p in people}
        current = {p: int(state.get("cw", {}).get(p, 0)) + weights[p] for p in people}
        chosen = max(people, key=lambda p: (current[p], -people.index(p)))
        current[chosen] -= sum(weights.values())
        state["cw"] = current
    else:
        last = state.get("last")
        idx = (people.index(last) + 1) % len(people) if last in people else 0
        chosen = people[idx]
    state["last"] = chosen
    rule.state = state
    return chosen


async def route(db: AsyncSession, rec: CRMRecord) -> Optional[str]:
    """Assign an unassigned new lead by the first matching rule. Caller commits."""
    if rec.assigned_rep_id:
        return None
    rules = (await db.execute(select(CRMRoutingRule).where(CRMRoutingRule.active.is_(True))
                              .order_by(CRMRoutingRule.priority))).scalars().all()
    for r in rules:
        if not matches(r, rec):
            continue
        locked = (await db.execute(select(CRMRoutingRule).where(CRMRoutingRule.id == r.id).with_for_update()
                                   .execution_options(populate_existing=True))).scalar_one()
        people = await _available(db, [str(u) for u in (locked.user_ids or [])])
        if not people:
            continue
        rec.assigned_rep_id = pick(locked, people)
        rec.notes = ((rec.notes or "") + f"\n[Routing] assigned by rule '{locked.name}'")[-20000:]
        return rec.assigned_rep_id
    return None


async def check_stage_approval(db: AsyncSession, rec: CRMRecord, new_stage_id, requester_id) -> None:
    rule = (await db.execute(select(CRMStageApprovalRule).where(
        CRMStageApprovalRule.stage_id == new_stage_id, CRMStageApprovalRule.active.is_(True)))).scalars().first()
    if rule is None:
        return
    if rule.min_expected_revenue is not None and Decimal(str(rec.expected_revenue or 0)) < rule.min_expected_revenue:
        return
    req = (await db.execute(select(CRMStageApprovalRequest).where(
        CRMStageApprovalRequest.crm_record_id == rec.id, CRMStageApprovalRequest.stage_id == new_stage_id)
        .order_by(CRMStageApprovalRequest.requested_at.desc()))).scalars().first()
    if req is not None and req.status == "APPROVED":
        return
    if req is None or req.status == "REJECTED":
        db.add(CRMStageApprovalRequest(crm_record_id=rec.id, stage_id=new_stage_id, rule_id=rule.id,
                                       requested_by_id=requester_id, status="PENDING",
                                       requested_at=datetime.now(timezone.utc)))
        await db.flush()
        await db.commit()                      # keep the request even though the move is refused
    raise HTTPException(409, {"code": "approval_required", "message": f"Moving this deal to the stage needs approval "
                              f"('{rule.name}'); a request is waiting for an approver."})


async def decide(db: AsyncSession, req: CRMStageApprovalRequest, approver, approve: bool, reason: Optional[str]) -> None:
    if req.status != "PENDING":
        raise HTTPException(409, "Already decided.")
    if req.requested_by_id == approver.id:
        raise HTTPException(403, "You cannot approve your own request.")
    req.status = "APPROVED" if approve else "REJECTED"
    req.decided_by_id, req.decided_at, req.reason = approver.id, datetime.now(timezone.utc), (reason or None)


def validate_splits(splits: list[tuple[str, Decimal]]) -> None:
    if not splits:
        return
    users = [u for u, _ in splits]
    if len(set(users)) != len(users):
        raise HTTPException(422, "Each person can appear once.")
    if any(p <= 0 for _, p in splits) or sum(p for _, p in splits) != Decimal("100"):
        raise HTTPException(422, "Shares must be positive and total exactly 100%.")


async def credit_splits(db: AsyncSession, rec: CRMRecord, final_value: Decimal, order_id: Optional[UUID],
                        actor_id) -> list[dict]:
    from app.schemas.commissions import CommissionCalcRequest
    from app.services.commissions_service import calculate_commission
    splits = (await db.execute(select(CRMDealSplit).where(CRMDealSplit.crm_record_id == rec.id))).scalars().all()
    out = []
    for s in splits:
        base = (final_value * s.share_pct / Decimal("100")).quantize(Decimal("0.01"))
        if base <= 0:
            continue
        try:
            txn = await calculate_commission(db, CommissionCalcRequest(
                sales_order_id=order_id, sales_rep_id=s.user_id, base_amount=base, calculation_date=date.today(),
                notes=f"Deal split {s.share_pct}% of {rec.company_name}"), actor_id)
            out.append({"user_id": str(s.user_id), "base": float(base), "commission_txn_id": str(txn.id)})
        except ValueError as e:                # already credited (dedupe) or no rule
            out.append({"user_id": str(s.user_id), "base": float(base), "skipped": str(e)})
    return out


async def handoff(db: AsyncSession, rec: CRMRecord) -> CRMHandoff:
    """Create the won-deal briefing once."""
    from app.models.crm import CRMActivity, CRMActivityResult, CRMDealPlan
    from app.services.crm_contact_service import contacts_for
    existing = (await db.execute(select(CRMHandoff).where(CRMHandoff.crm_record_id == rec.id))).scalar_one_or_none()
    if existing:
        return existing
    contacts = [f"{c.full_name} ({label})" + (f" {c.email}" if c.email else "") for c, label in await contacts_for(db, "crm_record", rec.id)]
    plan = (await db.execute(select(CRMDealPlan).where(CRMDealPlan.crm_record_id == rec.id))).scalar_one_or_none()
    open_tasks = [a.subject for a in (await db.execute(select(CRMActivity).where(
        CRMActivity.crm_record_id == rec.id, CRMActivity.result_status == CRMActivityResult.PLANNED))).scalars()]
    brief = {"customer": rec.company_name, "value": f"{rec.currency} {float(rec.expected_revenue or 0):,.2f}",
             "contacts": contacts, "promises": [s["title"] for s in (plan.steps if plan else []) if s.get("owner") == "us" and not s.get("done")],
             "open_tasks": open_tasks, "notes": (rec.notes or "")[-2000:]}
    h = CRMHandoff(crm_record_id=rec.id, brief=brief, created_at=datetime.now(timezone.utc), status="OPEN")
    db.add(h)
    await db.flush()
    return h
