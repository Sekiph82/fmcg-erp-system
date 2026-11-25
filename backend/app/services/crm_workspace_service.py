"""Sales workspace and productivity (M43.S01.T013).

- Task queues and repeating tasks on crm_activities: completing a repeating task creates the next one exactly once.
- Snippets and multiple e-mail signatures per user.
- Per-contact e-mail frequency cap (CRM_CONTACT_EMAIL_CAP_PER_WEEK, 0 = off) shared by manual, sequence and campaign
  mail: checked when queuing and again right before sending (crm_outbound_service._blocked_reason).
- Send-time suggestion from first-party evidence only (hours when this person opened tracked mail); with too little
  evidence it says so instead of guessing. No lift is claimed.
- Deal summary assembled from stored facts (stage, value, activities, quote, e-mail, open tasks) — nothing invented.
- Rep productivity: activities, calls, e-mails, meetings and won deals per person for a period.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import (CRMActivity, CRMActivityResult, CRMEmailEvent, CRMOutboundMessage, CRMPipelineStage,
                            CRMRecord, CRMStatus, CRMWinLoss)

RECURRENCE = {"DAILY": timedelta(days=1), "WEEKLY": timedelta(weeks=1), "MONTHLY": None}
MIN_OPENS_FOR_SUGGESTION = 3


def _next_due(due: datetime, rule: str, every: int) -> datetime:
    if rule == "MONTHLY":
        m = due.month - 1 + every
        y, m = due.year + m // 12, m % 12 + 1
        day = min(due.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30,
                            31, 30, 31][m - 1])
        return due.replace(year=y, month=m, day=day)
    return due + RECURRENCE[rule] * every


async def spawn_next(db: AsyncSession, act: CRMActivity) -> Optional[CRMActivity]:
    """After completing a repeating task: create the next occurrence once (idempotent per parent + due)."""
    if not act.recurrence_rule or act.recurrence_rule not in RECURRENCE:
        return None
    base = act.due_datetime or act.activity_datetime or datetime.utcnow()
    nxt = _next_due(base, act.recurrence_rule, max(1, act.recurrence_every or 1))
    if act.recurrence_until and nxt.date() > act.recurrence_until:
        return None
    root = act.recurrence_parent_id or act.id
    exists = (await db.execute(select(CRMActivity.id).where(CRMActivity.recurrence_parent_id == root,
                                                            CRMActivity.due_datetime == nxt))).first()
    if exists:
        return None
    child = CRMActivity(crm_record_id=act.crm_record_id, activity_type=act.activity_type, subject=act.subject,
                        description=act.description, due_datetime=nxt, assigned_to=act.assigned_to,
                        created_by=act.created_by, result_status=CRMActivityResult.PLANNED, queue=act.queue,
                        recurrence_rule=act.recurrence_rule, recurrence_every=act.recurrence_every,
                        recurrence_until=act.recurrence_until, recurrence_parent_id=root)
    db.add(child)
    await db.flush()
    return child


async def frequency_blocked(db: AsyncSession, email: str, purpose: str) -> Optional[str]:
    cap = int(getattr(settings, "CRM_CONTACT_EMAIL_CAP_PER_WEEK", 0) or 0)
    if cap <= 0 or purpose == "INVOICE":
        return None
    n = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.to_email == email, CRMOutboundMessage.purpose != "INVOICE",
        or_(and_(CRMOutboundMessage.status == "SENT",
                 CRMOutboundMessage.sent_at >= datetime.now(timezone.utc) - timedelta(days=7)),
            CRMOutboundMessage.status == "SENDING")))).scalar_one()
    return f"frequency cap: {n} e-mails in 7 days (limit {cap})" if n >= cap else None


async def send_time(db: AsyncSession, email: str, tz_name: str = "Africa/Nairobi") -> dict:
    from zoneinfo import ZoneInfo
    rows = (await db.execute(select(CRMEmailEvent.occurred_at).join(
        CRMOutboundMessage, CRMOutboundMessage.id == CRMEmailEvent.message_id).where(
        CRMOutboundMessage.to_email == email.strip().lower(), CRMEmailEvent.kind == "OPEN",
        CRMEmailEvent.is_machine.is_(False)))).scalars().all()
    if len(rows) < MIN_OPENS_FOR_SUGGESTION:
        return {"suggested_hour": None, "evidence": len(rows),
                "reason": "Not enough opens by this person to suggest a time; send in their business hours."}
    hours = Counter(r.astimezone(ZoneInfo(tz_name)).hour for r in rows)
    hour, n = hours.most_common(1)[0]
    return {"suggested_hour": hour, "time_zone": tz_name, "evidence": len(rows),
            "reason": f"{n} of {len(rows)} recorded opens were around {hour:02d}:00 {tz_name}. An indicator, not a guarantee."}


async def deal_summary(db: AsyncSession, rec: CRMRecord) -> dict:
    st = await db.get(CRMPipelineStage, rec.stage_id) if rec.stage_id else None
    acts = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == rec.id)
                             .order_by(func.coalesce(CRMActivity.completed_datetime, CRMActivity.activity_datetime,
                                                     CRMActivity.due_datetime).desc().nullslast()).limit(5))).scalars().all()
    open_tasks = [a for a in acts if a.result_status == CRMActivityResult.PLANNED]
    mails = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.crm_record_id == rec.id, CRMOutboundMessage.status == "SENT"))).scalar_one()
    lines = [f"{rec.company_name}: {getattr(rec.status, 'value', rec.status)}"
             + (f" in stage '{st.stage_name}'" if st else "")
             + (f", {rec.currency} {float(rec.expected_revenue or 0):,.0f} expected" if rec.expected_revenue else "")
             + (f", close by {rec.expected_close_date.isoformat()}" if rec.expected_close_date else "") + "."]
    if acts:
        lines.append("Recent: " + "; ".join(f"{getattr(a.activity_type, 'value', a.activity_type).lower()} '{a.subject}'"
                                            f" ({getattr(a.result_status, 'value', a.result_status).lower()})" for a in acts[:3]) + ".")
    lines.append(f"{mails} CRM e-mail(s) sent." + (" A quotation is linked." if rec.linked_quotation_id else " No quotation yet."))
    if open_tasks:
        lines.append(f"Open: {len(open_tasks)} planned task(s), next '{open_tasks[0].subject}'.")
    elif rec.status == CRMStatus.OPEN:
        lines.append("No planned next step — add one.")
    return {"record_id": str(rec.id), "summary": " ".join(lines), "facts_only": True}


async def productivity(db: AsyncSession, since: date, until: date) -> list[dict]:
    from app.models.meetings import MeetingRecord
    from app.models.user import User
    from app.models.voip import CallLog
    lo, hi = datetime.combine(since, datetime.min.time()), datetime.combine(until + timedelta(days=1), datetime.min.time())
    acts = dict((await db.execute(select(CRMActivity.assigned_to, func.count()).where(
        CRMActivity.result_status == CRMActivityResult.COMPLETED, CRMActivity.completed_datetime >= lo,
        CRMActivity.completed_datetime < hi).group_by(CRMActivity.assigned_to))).all())
    calls = dict((await db.execute(select(CallLog.agent_id, func.count()).where(
        CallLog.started_at >= lo, CallLog.started_at < hi).group_by(CallLog.agent_id))).all())
    meetings = dict((await db.execute(select(MeetingRecord.host_id, func.count()).where(
        MeetingRecord.scheduled_at >= lo, MeetingRecord.scheduled_at < hi, MeetingRecord.status == "COMPLETED")
        .group_by(MeetingRecord.host_id))).all())
    mails = dict((await db.execute(select(CRMOutboundMessage.created_by, func.count()).where(
        CRMOutboundMessage.purpose == "MANUAL", CRMOutboundMessage.status == "SENT",
        CRMOutboundMessage.sent_at >= lo.replace(tzinfo=timezone.utc), CRMOutboundMessage.sent_at < hi.replace(tzinfo=timezone.utc))
        .group_by(CRMOutboundMessage.created_by))).all())
    won = (await db.execute(select(CRMRecord.assigned_rep_id, CRMRecord.currency, func.count(), func.sum(CRMWinLoss.final_revenue))
                            .join(CRMWinLoss, CRMWinLoss.crm_record_id == CRMRecord.id).where(
        CRMWinLoss.final_status == "WON", CRMWinLoss.close_date >= since, CRMWinLoss.close_date <= until)
        .group_by(CRMRecord.assigned_rep_id, CRMRecord.currency))).all()
    users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
    out = []
    for u in users:
        key = str(u.id)
        row = {"user_id": key, "name": u.full_name, "activities": acts.get(key, 0) + acts.get(u.username, 0),
               "calls": calls.get(u.id, 0), "meetings": meetings.get(u.id, 0), "emails": mails.get(u.username, 0),
               "won": {cur: {"deals": n, "value": float(v or 0)} for rep, cur, n, v in won if rep == key}}
        if row["activities"] or row["calls"] or row["meetings"] or row["emails"] or row["won"]:
            out.append(row)
    return sorted(out, key=lambda r: -(r["activities"] + r["calls"] + r["meetings"] + r["emails"]))
