"""Service desk (M45.S01.T019). Prefix /api/v1/service-desk (helpdesk view rights; configuration: crm.edit_all).
Public survey answers: /api/v1/public/survey/{token}."""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.helpdesk import HelpdeskTicket
from app.models.service_desk import AgentProfile, Macro, QAReview, SLAPolicy, Survey, TicketSLA, TicketView
from app.services import service_desk_service as sd

router = APIRouter()
public = APIRouter()


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("crm.edit_all", "helpdesk.edit_all"))):
        raise HTTPException(403, "Only service administrators change this.")


async def _ticket(db, tid) -> HelpdeskTicket:
    t = await db.get(HelpdeskTicket, tid)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    return t


@router.get("/overview")
async def overview(days: int = 30, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    agents = (await db.execute(select(AgentProfile))).scalars().all()
    pols = (await db.execute(select(SLAPolicy).order_by(SLAPolicy.sort))).scalars().all()
    return {"report": await sd.report(db, days), "settings": await sd.settings_get(db),
            "agents": [{"user_id": str(a.user_id), "skills": a.skills, "capacity": a.capacity, "presence": a.presence} for a in agents],
            "policies": [{"id": str(p.id), "name": p.name, "priority": p.priority, "channel": p.channel, "customer_tier": p.customer_tier,
                          "first_response_hours": p.first_response_hours, "resolution_hours": p.resolution_hours,
                          "business_hours": p.business_hours, "sort": p.sort, "active": p.active} for p in pols],
            "macros": [{"id": str(m.id), "name": m.name, "body": m.body, "set_status": m.set_status} for m in (await db.execute(select(Macro).order_by(Macro.name))).scalars()],
            "views": [{"id": str(v.id), "name": v.name, "filters": v.filters, "shared": v.shared} for v in (await db.execute(
                select(TicketView).where((TicketView.owner_id == current_user.id) | TicketView.shared.is_(True)))).scalars()]}


@router.put("/settings")
async def put_settings(body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        out = await sd.settings_put(db, body, current_user.username)
    except Exception as e:
        raise HTTPException(422, f"Invalid settings: {e}")
    await db.commit()
    return out


class AgentIn(BaseModel):
    skills: list[str] = Field(default_factory=list)
    capacity: int = Field(10, ge=1, le=200)


@router.put("/agents/{user_id}")
async def put_agent(user_id: uuid.UUID, body: AgentIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    a = await db.get(AgentProfile, user_id) or AgentProfile(user_id=user_id)
    a.skills, a.capacity = [s.strip().lower() for s in body.skills if s.strip()], body.capacity
    db.add(a)
    await db.commit()
    return {"ok": True}


class PresenceIn(BaseModel):
    presence: Literal["AVAILABLE", "AWAY", "OFFLINE"]


@router.put("/me/presence")
async def presence(body: PresenceIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await db.get(AgentProfile, current_user.id)
    if a is None:
        raise HTTPException(404, "You are not set up as a service agent.")
    a.presence = body.presence
    await db.commit()
    return {"presence": a.presence}


class PolicyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = None
    channel: Optional[Literal["PHONE", "EMAIL", "PORTAL", "WHATSAPP", "MANUAL"]] = None
    customer_tier: Optional[int] = Field(None, ge=1, le=3)
    first_response_hours: float = Field(gt=0, le=720)
    resolution_hours: float = Field(gt=0, le=2160)
    business_hours: bool = True
    sort: int = 100
    active: bool = True


@router.post("/policies", status_code=201)
async def add_policy(body: PolicyIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    if body.first_response_hours > body.resolution_hours:
        raise HTTPException(422, "First response cannot be later than resolution.")
    p = SLAPolicy(**body.model_dump())
    db.add(p)
    await db.commit()
    return {"id": str(p.id)}


@router.get("/tickets/{tid}")
async def ticket_panel(tid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """SLA timers, hand-off summary, reply recommendations from approved articles, QA reviews."""
    from app.services import kb_retrieval
    t = await _ticket(db, tid)
    s = await db.get(TicketSLA, tid)
    recs = await kb_retrieval.search(db, f"{t.subject} {t.description or ''}", limit=3, min_score=1.0)
    qa = (await db.execute(select(QAReview).where(QAReview.ticket_id == tid))).scalars().all()
    return {"sla": None if s is None else {"first_response_due": s.first_response_due.isoformat(), "resolution_due": s.resolution_due.isoformat(),
                                           "paused": s.paused_at is not None, "breached_first": s.breached_first,
                                           "breached_resolution": s.breached_resolution},
            "handoff": await sd.handoff_summary(db, t),
            "recommendations": [{"title": h.title, "summary": h.summary, "link": f"/kb/{h.slug}"} for h in recs],
            "qa": [{"reviewer": q.reviewer, "scores": q.scores, "total": q.total, "notes": q.notes} for q in qa]}


@router.post("/tickets/{tid}/{action}")
async def sla_action(tid: uuid.UUID, action: Literal["pause", "resume", "route"], db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    t = await _ticket(db, tid)
    try:
        if action == "pause":
            await sd.pause(db, tid)
        elif action == "resume":
            await sd.resume(db, tid)
        else:
            await sd.route(db, t)
    except ValueError as e:
        raise HTTPException(409, str(e))
    await db.commit()
    return {"ok": True, "assigned_to_id": str(t.assigned_to_id) if t.assigned_to_id else None}


class MacroIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=5000)
    set_status: Optional[Literal["IN_PROGRESS", "RESOLVED"]] = None


@router.post("/macros", status_code=201)
async def add_macro(body: MacroIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    m = Macro(**body.model_dump(), created_by=current_user.username)
    db.add(m)
    await db.commit()
    return {"id": str(m.id)}


@router.post("/tickets/{tid}/macro/{mid}")
async def apply_macro(tid: uuid.UUID, mid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    from app.models.helpdesk import TicketComment, TicketStatus
    t, m = await _ticket(db, tid), await db.get(Macro, mid)
    if m is None:
        raise HTTPException(404, "Macro not found")
    db.add(TicketComment(ticket_id=t.id, body=m.body.replace("{ticket_no}", t.ticket_no), is_internal=False, created_by_id=current_user.id))
    if t.first_response_at is None:
        t.first_response_at = datetime.now(timezone.utc)
    if m.set_status:
        t.status = TicketStatus(m.set_status)
    await db.commit()
    return {"ok": True}


class QAIn(BaseModel):
    accuracy: int = Field(ge=1, le=5)
    tone: int = Field(ge=1, le=5)
    resolution: int = Field(ge=1, le=5)
    notes: Optional[str] = Field(None, max_length=2000)


@router.post("/tickets/{tid}/qa", status_code=201)
async def qa(tid: uuid.UUID, body: QAIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    t = await _ticket(db, tid)
    if t.assigned_to_id == current_user.id:
        raise HTTPException(403, "Agents do not review their own tickets.")
    sc = body.model_dump(exclude={"notes"})
    db.add(QAReview(ticket_id=t.id, agent_id=t.assigned_to_id, reviewer=current_user.username, scores=sc,
                    total=round(sum(sc.values()) / len(sc), 2), notes=body.notes))
    await db.commit()
    return {"ok": True}


class ViewIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: dict
    shared: bool = False


@router.post("/views", status_code=201)
async def add_view(body: ViewIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if body.shared:
        _admin(current_user)
    v = TicketView(**body.model_dump(), owner_id=current_user.id)
    db.add(v)
    await db.commit()
    return {"id": str(v.id)}


@public.get("/{token}")
async def survey(token: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Survey).where(Survey.token_hash == sd._digest(token)))).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Survey not found")
    q = {"CSAT": "How satisfied are you with the help you got?", "CES": "How easy was it to get your issue handled?",
         "POST_CHAT": "How was your chat with us?"}[s.kind]
    lo, hi = sd.SCALES[s.kind]
    return {"kind": s.kind, "question": q, "min": lo, "max": hi, "answered": s.answered_at is not None}


class AnswerIn(BaseModel):
    score: int
    comment: Optional[str] = Field(None, max_length=2000)


@public.post("/{token}")
async def survey_answer(token: str, body: AnswerIn, db: AsyncSession = Depends(get_db)):
    try:
        await sd.answer(db, token, body.score, body.comment)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409 if "already" in str(e) else 422, str(e))
    await db.commit()
    return {"ok": True}
