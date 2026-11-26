"""M45.S01.T019 service routing, conditional SLAs with business hours and pause, CSAT/CES/post-chat surveys.

Routing: the ticket category may need a skill (settings "service" → category_skills); among AVAILABLE agents with
that skill and below capacity, the one assigned longest ago gets it (round robin). Nobody available → unassigned.
SLA: the first active policy (lowest sort) matching priority, channel and key-account tier; due times count business
hours (time zone, weekdays, opening hours, holidays) when the policy says so; "waiting for customer" pauses the timers
and resume shifts the due times by the paused time. A tick marks breaches and notifies the assignee.
Surveys: on close, one CSAT and one CES survey per ticket (portal link + e-mail when the customer has an address);
after a chat, one post-chat survey. Each survey is answered once.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_desk import AgentProfile, SLAPolicy, Survey, TicketSLA

DEFAULTS = {"time_zone": "Africa/Nairobi", "weekdays": [0, 1, 2, 3, 4, 5], "open": "08:00", "close": "17:00", "holidays": [],
            "category_skills": {"QUALITY": "quality", "DELIVERY": "delivery", "BILLING": "billing"}}
SCALES = {"CSAT": (1, 5), "CES": (1, 7), "POST_CHAT": (1, 5)}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def settings_get(db: AsyncSession) -> dict:
    from app.models.customer_intel import CISetting
    row = await db.get(CISetting, "service")
    return {**DEFAULTS, **({k: v for k, v in row.value.items() if k in DEFAULTS} if row else {})}


async def settings_put(db: AsyncSession, value: dict, user: str) -> dict:
    from app.models.customer_intel import CISetting
    clean = {k: v for k, v in value.items() if k in DEFAULTS}
    if "time_zone" in clean:
        ZoneInfo(clean["time_zone"])
    for k in ("open", "close"):
        if k in clean:
            time.fromisoformat(clean[k])
    row = await db.get(CISetting, "service")
    if row is None:
        db.add(CISetting(key="service", value=clean, updated_by=user))
    else:
        row.value, row.updated_by, row.updated_at = {**row.value, **clean}, user, _now()
    await db.flush()
    return await settings_get(db)


# ── business hours ───────────────────────────────────────────────────────────

def add_business_hours(start: datetime, hours: float, cfg: dict) -> datetime:
    tz = ZoneInfo(cfg["time_zone"])
    o, c = time.fromisoformat(cfg["open"]), time.fromisoformat(cfg["close"])
    holidays = {date.fromisoformat(h) for h in cfg.get("holidays", [])}
    cur, left = start.astimezone(tz), timedelta(hours=hours)
    for _ in range(3660):          # at most ten years of days
        day_open = cur.replace(hour=o.hour, minute=o.minute, second=0, microsecond=0)
        day_close = cur.replace(hour=c.hour, minute=c.minute, second=0, microsecond=0)
        if cur.weekday() not in cfg["weekdays"] or cur.date() in holidays or cur >= day_close:
            cur = (cur + timedelta(days=1)).replace(hour=o.hour, minute=o.minute, second=0, microsecond=0)
            continue
        cur = max(cur, day_open)
        if cur + left <= day_close:
            return (cur + left).astimezone(timezone.utc)
        left -= day_close - cur
        cur = (cur + timedelta(days=1)).replace(hour=o.hour, minute=o.minute, second=0, microsecond=0)
    raise ValueError("Business hours never open.")


# ── routing and SLA on creation ──────────────────────────────────────────────

async def route(db: AsyncSession, ticket) -> Optional[uuid.UUID]:
    from app.models.helpdesk import HelpdeskTicket, TicketStatus
    if ticket.assigned_to_id:
        return ticket.assigned_to_id
    cfg = await settings_get(db)
    skill = cfg["category_skills"].get(getattr(ticket.category, "value", str(ticket.category)))
    open_counts = dict((await db.execute(select(HelpdeskTicket.assigned_to_id, func.count()).where(
        HelpdeskTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED]),
        HelpdeskTicket.assigned_to_id.is_not(None)).group_by(HelpdeskTicket.assigned_to_id))).all())
    agents = (await db.execute(select(AgentProfile).where(AgentProfile.presence == "AVAILABLE")
                               .order_by(AgentProfile.last_assigned_at.asc().nullsfirst()).with_for_update())).scalars().all()
    for a in agents:
        if skill and skill not in (a.skills or []):
            continue
        if open_counts.get(a.user_id, 0) >= a.capacity:
            continue
        ticket.assigned_to_id, a.last_assigned_at = a.user_id, _now()
        return a.user_id
    return None


async def _tier(db: AsyncSession, customer_id) -> Optional[int]:
    from app.models.crm import CRMAccountGroupMember
    if not customer_id:
        return None
    return (await db.execute(select(func.min(CRMAccountGroupMember.tier)).where(CRMAccountGroupMember.customer_id == customer_id))).scalar()


async def policy_for(db: AsyncSession, ticket) -> Optional[SLAPolicy]:
    tier = await _tier(db, ticket.customer_id)
    pr, ch = getattr(ticket.priority, "value", ticket.priority), getattr(ticket.source, "value", ticket.source)
    rows = (await db.execute(select(SLAPolicy).where(SLAPolicy.active.is_(True)).order_by(SLAPolicy.sort))).scalars()
    for p in rows:
        if (p.priority in (None, pr)) and (p.channel in (None, ch)) and (p.customer_tier in (None, tier)):
            return p
    return None


async def start_sla(db: AsyncSession, ticket) -> TicketSLA:
    cfg = await settings_get(db)
    p = await policy_for(db, ticket)
    start = ticket.created_at or _now()
    fr, rs = (p.first_response_hours, p.resolution_hours) if p else (min(ticket.sla_hours, 8), ticket.sla_hours)
    bh = p.business_hours if p else False

    def due(h):
        return add_business_hours(start, h, cfg) if bh else start + timedelta(hours=h)
    s = TicketSLA(ticket_id=ticket.id, policy_id=p.id if p else None, first_response_due=due(fr), resolution_due=due(rs))
    db.add(s)
    return s


async def on_created(db: AsyncSession, ticket) -> None:
    await db.flush()
    await route(db, ticket)
    await start_sla(db, ticket)
    await db.flush()


async def pause(db: AsyncSession, ticket_id) -> TicketSLA:
    s = await db.get(TicketSLA, ticket_id, with_for_update=True)
    if s is None:
        raise ValueError("No SLA for this ticket.")
    if s.paused_at is None:
        s.paused_at = _now()
    return s


async def resume(db: AsyncSession, ticket_id) -> TicketSLA:
    s = await db.get(TicketSLA, ticket_id, with_for_update=True)
    if s is None:
        raise ValueError("No SLA for this ticket.")
    if s.paused_at is not None:
        gap = _now() - s.paused_at
        s.first_response_due += gap
        s.resolution_due += gap
        s.paused_at = None
    return s


async def tick(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Mark breaches (paused timers never breach) and notify the assignee once."""
    from app.models.helpdesk import HelpdeskTicket, TicketStatus
    from app.models.notifications import Notification, NotificationChannel, NotificationPriority, NotificationStatus, NotificationType
    now = now or _now()
    n = 0
    rows = (await db.execute(select(TicketSLA, HelpdeskTicket).join(HelpdeskTicket, HelpdeskTicket.id == TicketSLA.ticket_id).where(
        TicketSLA.paused_at.is_(None), HelpdeskTicket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        or_(TicketSLA.breached_first.is_(False), TicketSLA.breached_resolution.is_(False))))).all()
    for s, t in rows:
        hit = []
        if not s.breached_first and t.first_response_at is None and now > s.first_response_due:
            s.breached_first = True
            hit.append("first response")
        if not s.breached_resolution and now > s.resolution_due:
            s.breached_resolution = True
            hit.append("resolution")
        if hit:
            n += 1
            if t.assigned_to_id:
                db.add(Notification(user_id=str(t.assigned_to_id), title=f"SLA breached: {t.ticket_no}", message=f"{', '.join(hit)} time passed.",
                                    notification_type=NotificationType.WARNING, priority=NotificationPriority.HIGH, channel=NotificationChannel.IN_APP,
                                    status=NotificationStatus.SENT, sent_at=datetime.utcnow(), reference_type="ticket", reference_id=str(t.id), module="helpdesk"))
    await db.flush()
    return n


# ── surveys ─────────────────────────────────────────────────────────────────

def _digest(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


async def create_survey(db: AsyncSession, kind: str, subject_id, customer_id=None, agent_id=None) -> Optional[str]:
    """The token, or None if this survey was already sent (sent once)."""
    from sqlalchemy.dialects.postgresql import insert
    token = secrets.token_urlsafe(24)
    res = await db.execute(insert(Survey).values(id=uuid.uuid4(), kind=kind, subject_id=subject_id, customer_id=customer_id, agent_id=agent_id,
                                                 token_hash=_digest(token), sent_at=_now())
                           .on_conflict_do_nothing(constraint="uq_sd_survey_once"))
    return token if res.rowcount else None


async def on_closed(db: AsyncSession, ticket) -> dict:
    from app.core.config import settings
    from app.models.sales import Customer
    tokens = {}
    for kind in ("CSAT", "CES"):
        tok = await create_survey(db, kind, ticket.id, ticket.customer_id, ticket.assigned_to_id)
        if tok:
            tokens[kind] = tok
    cust = await db.get(Customer, ticket.customer_id) if ticket.customer_id else None
    if tokens and cust is not None and cust.email:
        from app.services import crm_outbound_service as outbound
        base = settings.PUBLIC_APP_URL.rstrip("/")
        await outbound.queue(db, to_email=cust.email, subject=f"How did we do? Ticket {ticket.ticket_no}",
                             body=(f"Thank you for contacting POVU about '{ticket.subject}'.\n\n"
                                   f"How satisfied are you? {base}/survey/{tokens.get('CSAT', '')}\n"
                                   f"How easy was it to get help? {base}/survey/{tokens.get('CES', '')}"),
                             purpose="MANUAL", dedupe_key=f"survey:{ticket.id}", customer_id=cust.id, created_by="helpdesk")
    return tokens


async def answer(db: AsyncSession, token: str, score: int, comment: Optional[str]) -> Survey:
    s = (await db.execute(select(Survey).where(Survey.token_hash == _digest(token or "")).with_for_update())).scalar_one_or_none()
    if s is None:
        raise LookupError("Survey not found.")
    if s.answered_at is not None:
        raise ValueError("This survey was already answered.")
    lo, hi = SCALES[s.kind]
    if not lo <= score <= hi:
        raise ValueError(f"Score must be {lo}–{hi}.")
    s.score, s.comment, s.answered_at = score, (comment or "")[:2000] or None, _now()
    if s.kind == "CSAT":
        from app.models.helpdesk import HelpdeskTicket
        t = await db.get(HelpdeskTicket, s.subject_id)
        if t is not None:
            t.customer_satisfaction = score
    await db.flush()
    return s


async def report(db: AsyncSession, days: int = 30) -> dict:
    from app.models.helpdesk import HelpdeskTicket
    since = _now() - timedelta(days=days)
    out = {}
    for kind in SCALES:
        n, avg = (await db.execute(select(func.count(Survey.id), func.avg(Survey.score)).where(
            Survey.kind == kind, Survey.answered_at >= since))).one()
        sent = (await db.execute(select(func.count()).select_from(Survey).where(Survey.kind == kind, Survey.sent_at >= since))).scalar_one()
        out[kind] = {"sent": sent, "answered": n, "average": round(float(avg), 2) if avg is not None else None}
    total, breached = (await db.execute(select(func.count(TicketSLA.ticket_id),
                                               func.count().filter(TicketSLA.breached_first | TicketSLA.breached_resolution))
                                        .join(HelpdeskTicket, HelpdeskTicket.id == TicketSLA.ticket_id)
                                        .where(HelpdeskTicket.created_at >= since))).one()
    out["sla"] = {"tickets": total, "breached": breached, "met_pct": round(100 * (total - breached) / total, 1) if total else None}
    return out


async def handoff_summary(db: AsyncSession, ticket) -> str:
    """Rule-based hand-off note: who, what, priority, SLA state, last customer-facing comments."""
    from app.models.helpdesk import TicketComment
    from app.models.sales import Customer
    cust = await db.get(Customer, ticket.customer_id) if ticket.customer_id else None
    sla = await db.get(TicketSLA, ticket.id)
    last = (await db.execute(select(TicketComment).where(TicketComment.ticket_id == ticket.id, TicketComment.is_internal.is_(False))
                             .order_by(TicketComment.created_at.desc()).limit(3))).scalars().all()
    lines = [f"{ticket.ticket_no} · {getattr(ticket.priority, 'value', ticket.priority)} · {getattr(ticket.status, 'value', ticket.status)}",
             f"Customer: {cust.name if cust else 'unknown'}", f"Issue: {ticket.subject}"]
    if sla:
        lines.append(f"SLA: resolution due {sla.resolution_due:%Y-%m-%d %H:%M} UTC" + (" (paused)" if sla.paused_at else "")
                     + (" — BREACHED" if sla.breached_first or sla.breached_resolution else ""))
    lines += [f"Recent: {c.body[:160]}" for c in reversed(last)]
    return "\n".join(lines)


# ── M47.S01.T010 configurable ticket pipelines ───────────────────────────────
# A pipeline has ordered stages; each stage maps to a TicketStatus (status-based screens, SLA ticks and reports keep
# working) and may pause the SLA timers ("waiting on customer"). The default pipeline is created on first use; a ticket
# without a stage row sits in the default pipeline at the first stage of its status.
DEFAULT_STAGES = [("New", "OPEN", False), ("In progress", "IN_PROGRESS", False), ("Waiting on customer", "IN_PROGRESS", True),
                  ("Escalated", "ESCALATED", False), ("Resolved", "RESOLVED", False), ("Closed", "CLOSED", False)]


def _stage_specs(stages: list[dict]) -> list[tuple[str, str, bool]]:
    from app.models.helpdesk import TicketStatus
    if not 1 <= len(stages) <= 20:
        raise ValueError("A pipeline needs 1–20 stages.")
    out, names = [], set()
    for s in stages:
        name = str(s.get("name") or "").strip()[:100]
        status = str(s.get("status") or "")
        if not name or name.lower() in names:
            raise ValueError("Stage names must be filled and different.")
        if status not in TicketStatus.__members__:
            raise ValueError(f"Stage {name}: status must be one of {', '.join(TicketStatus.__members__)}.")
        names.add(name.lower())
        out.append((name, status, bool(s.get("pauses_sla"))))
    return out


async def create_pipeline(db: AsyncSession, name: str, stages: list[dict], is_default: bool = False):
    from app.models.helpdesk import HelpdeskPipeline, HelpdeskPipelineStage
    specs = _stage_specs(stages)
    p = HelpdeskPipeline(name=name.strip()[:100], is_default=is_default, created_at=_now())
    p.stages = [HelpdeskPipelineStage(name=n, status=st, pauses_sla=ps, sort=i) for i, (n, st, ps) in enumerate(specs)]
    db.add(p)
    await db.flush()
    return p


async def default_pipeline(db: AsyncSession):
    from sqlalchemy import text
    from sqlalchemy.orm import selectinload
    from app.models.helpdesk import HelpdeskPipeline
    q = select(HelpdeskPipeline).options(selectinload(HelpdeskPipeline.stages)).where(HelpdeskPipeline.is_default.is_(True))
    p = (await db.execute(q)).scalars().first()
    if p is None:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('helpdesk_default_pipeline'))"))
        p = (await db.execute(q)).scalars().first()
        if p is None:
            await create_pipeline(db, "Support", [{"name": n, "status": s, "pauses_sla": ps} for n, s, ps in DEFAULT_STAGES], True)
            p = (await db.execute(q.execution_options(populate_existing=True))).scalars().first()
    return p


async def ticket_stage(db: AsyncSession, ticket) -> tuple:
    from app.models.helpdesk import HelpdeskPipelineStage, HelpdeskTicketStage
    row = await db.get(HelpdeskTicketStage, ticket.id)
    if row is not None:
        return row.pipeline_id, await db.get(HelpdeskPipelineStage, row.stage_id)
    p = await default_pipeline(db)
    status = getattr(ticket.status, "value", ticket.status)
    return p.id, next((s for s in p.stages if s.status == status), None)


async def move_ticket(db: AsyncSession, ticket, stage_id) -> dict:
    """Move to a stage (of any pipeline): sets the mapped status and its timestamps, pauses / resumes the SLA."""
    from app.models.helpdesk import HelpdeskPipelineStage, HelpdeskTicketStage, TicketStatus
    st = await db.get(HelpdeskPipelineStage, stage_id)
    if st is None:
        raise LookupError("Stage not found.")
    await default_pipeline(db)
    status = TicketStatus(st.status)
    ticket.status = status
    now = _now()
    if status == TicketStatus.RESOLVED and ticket.resolved_at is None:
        ticket.resolved_at = now
    if status == TicketStatus.CLOSED and ticket.closed_at is None:
        ticket.closed_at = now
    if status in (TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED):
        ticket.resolved_at = ticket.closed_at = None
    if await db.get(TicketSLA, ticket.id) is not None:
        await (pause(db, ticket.id) if st.pauses_sla else resume(db, ticket.id))
    row = await db.get(HelpdeskTicketStage, ticket.id)
    if row is None:
        db.add(HelpdeskTicketStage(ticket_id=ticket.id, pipeline_id=st.pipeline_id, stage_id=st.id, moved_at=now))
    else:
        row.pipeline_id, row.stage_id, row.moved_at = st.pipeline_id, st.id, now
    await db.flush()
    return {"ticket_id": str(ticket.id), "pipeline_id": str(st.pipeline_id), "stage_id": str(st.id), "stage": st.name,
            "status": status.value, "sla_paused": st.pauses_sla}


async def board(db: AsyncSession, pipeline_id) -> dict:
    from sqlalchemy.orm import selectinload
    from app.models.helpdesk import HelpdeskPipeline, HelpdeskTicket, HelpdeskTicketStage
    p = (await db.execute(select(HelpdeskPipeline).options(selectinload(HelpdeskPipeline.stages))
                          .where(HelpdeskPipeline.id == pipeline_id))).scalars().first()
    if p is None:
        raise LookupError("Pipeline not found.")
    cols = {s.id: [] for s in p.stages}
    rows = (await db.execute(select(HelpdeskTicket, HelpdeskTicketStage.stage_id).join(
        HelpdeskTicketStage, HelpdeskTicketStage.ticket_id == HelpdeskTicket.id).where(
        HelpdeskTicketStage.pipeline_id == p.id).order_by(HelpdeskTicket.created_at.desc()).limit(500))).all()
    tickets = [(t, sid) for t, sid in rows]
    if p.is_default:                                 # tickets never moved sit at the first stage of their status
        first = {}
        for s in p.stages:
            first.setdefault(s.status, s.id)
        loose = (await db.execute(select(HelpdeskTicket).where(~select(HelpdeskTicketStage.ticket_id).where(
            HelpdeskTicketStage.ticket_id == HelpdeskTicket.id).exists()).order_by(HelpdeskTicket.created_at.desc()).limit(500))).scalars()
        tickets += [(t, first.get(getattr(t.status, "value", t.status))) for t in loose]
    for t, sid in tickets:
        if sid in cols:
            cols[sid].append({"id": str(t.id), "ticket_no": t.ticket_no, "priority": getattr(t.priority, "value", t.priority),
                              "status": getattr(t.status, "value", t.status)})
    return {"id": str(p.id), "name": p.name, "is_default": p.is_default,
            "stages": [{"id": str(s.id), "name": s.name, "status": s.status, "pauses_sla": s.pauses_sla, "tickets": cols[s.id]}
                       for s in p.stages]}
