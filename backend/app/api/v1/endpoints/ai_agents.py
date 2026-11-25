"""AI agent builder and scheduler (M45.S01.T008/T009). Prefix /api/v1/ai-agents.

View: ai.view. Build/run: ai.create or ai.edit. Publishing a version needs a second person with ai.approve (or
superuser). Emergency stop and rates: superuser or ai.approve.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.ai_hub import AIAgent, AIAgentJob, AIAgentVersion
from app.services import agent_service as ags
from app.services import pat_service as pats

router = APIRouter(dependencies=[Depends(require_any_permission(("ai.view", "ai.edit", "ai.create", "ai.approve")))])


def _can(u, *perms):
    if not (u.is_superuser or has_any_permission(u, perms)):
        raise HTTPException(403, f"Needs {' or '.join(perms)}.")


def _fail(e: ags.AgentError):
    raise HTTPException(422, str(e))


async def _agent(db, aid) -> AIAgent:
    a = await db.get(AIAgent, aid)
    if a is None:
        raise HTTPException(404, "Agent not found")
    return a


def _out(a: AIAgent) -> dict:
    return {"id": str(a.id), "name": a.name, "template": a.template, "status": a.status, "stopped": a.stopped,
            "current_version": a.current_version, "schedule": a.schedule, "budgets": {**ags.DEFAULT_BUDGETS, **(a.budgets or {})},
            "next_run_at": a.next_run_at.isoformat() if a.next_run_at else None,
            "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None, "created_by": a.created_by}


def _job(j: AIAgentJob) -> dict:
    return {"id": str(j.id), "agent_id": str(j.agent_id), "version": j.version, "trigger": j.trigger, "status": j.status,
            "attempts": j.attempts, "tokens": j.tokens, "cost": str(j.cost), "error": j.error, "trace": j.trace,
            "created_at": j.created_at.isoformat(), "finished_at": j.finished_at.isoformat() if j.finished_at else None}


@router.get("/catalog")
async def catalog():
    return {"tools": {k: {"label": v["label"], "write": v["write"]} for k, v in ags.TOOLS.items()},
            "templates": {k: {"name": v["name"], "description": v["description"], "definition": v["definition"]}
                          for k, v in ags.TEMPLATES.items()}}


@router.get("")
async def agents(db: AsyncSession = Depends(get_db)):
    rows = list((await db.execute(select(AIAgent).order_by(AIAgent.name))).scalars())
    return {"agents": [_out(a) for a in rows], "settings": await ags.settings_get(db)}


class AgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    template: Optional[str] = Field(None, max_length=30)
    definition: Optional[dict] = None
    schedule: Optional[dict] = None
    budgets: Optional[dict] = None


def _clean_schedule(s: Optional[dict]) -> Optional[dict]:
    if not s:
        return None
    if s.get("every_minutes"):
        return {"every_minutes": max(5, min(10080, int(s["every_minutes"])))}
    if s.get("daily_at"):
        from zoneinfo import ZoneInfo
        try:
            hh, mm = (int(x) for x in str(s["daily_at"]).split(":"))
            assert 0 <= hh < 24 and 0 <= mm < 60
            ZoneInfo(s.get("time_zone") or "Africa/Nairobi")
        except Exception:
            raise HTTPException(422, "Schedule: daily_at must be HH:MM and time_zone a valid IANA zone.")
        return {"daily_at": f"{hh:02d}:{mm:02d}", "time_zone": s.get("time_zone") or "Africa/Nairobi"}
    raise HTTPException(422, "Schedule needs every_minutes or daily_at.")


def _clean_budgets(b: Optional[dict]) -> dict:
    out = dict(ags.DEFAULT_BUDGETS)
    for k, v in (b or {}).items():
        if k in out:
            if not isinstance(v, (int, float)) or v < 0:
                raise HTTPException(422, f"Budget {k} must be a positive number.")
            out[k] = v
    return out


@router.post("", status_code=201)
async def create(body: AgentIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "ai.create", "ai.edit")
    defn = body.definition or (ags.TEMPLATES[body.template]["definition"] if body.template in ags.TEMPLATES else None)
    if defn is None:
        raise HTTPException(422, "Give a definition or a known template.")
    try:
        ags.validate(defn)
    except ags.AgentError as e:
        _fail(e)
    a = AIAgent(name=body.name, template=body.template, run_as_id=current_user.id, schedule=_clean_schedule(body.schedule),
                budgets=_clean_budgets(body.budgets), created_by=current_user.username)
    db.add(a)
    await db.flush()
    db.add(AIAgentVersion(agent_id=a.id, version=1, definition=defn, created_by=current_user.username))
    pats.audit(db, current_user, "AI_AGENT_CREATED", "ai_agent", str(a.id), {"template": body.template})
    await db.commit()
    return _out(a)


@router.get("/{aid}")
async def detail(aid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await _agent(db, aid)
    vers = (await db.execute(select(AIAgentVersion).where(AIAgentVersion.agent_id == aid).order_by(AIAgentVersion.version.desc()))).scalars()
    jobs = (await db.execute(select(AIAgentJob).where(AIAgentJob.agent_id == aid).order_by(AIAgentJob.created_at.desc()).limit(20))).scalars()
    return {**_out(a), "versions": [{"version": v.version, "status": v.status, "definition": v.definition, "created_by": v.created_by,
                                     "approved_by": v.approved_by, "created_at": v.created_at.isoformat()} for v in vers],
            "jobs": [_job(j) for j in jobs]}


class VersionIn(BaseModel):
    definition: dict


@router.post("/{aid}/versions", status_code=201)
async def new_version(aid: uuid.UUID, body: VersionIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "ai.create", "ai.edit")
    a = await _agent(db, aid)
    try:
        ags.validate(body.definition)
    except ags.AgentError as e:
        _fail(e)
    n = (await db.execute(select(func.max(AIAgentVersion.version)).where(AIAgentVersion.agent_id == aid))).scalar() or 0
    db.add(AIAgentVersion(agent_id=a.id, version=n + 1, definition=body.definition, created_by=current_user.username))
    await db.commit()
    return {"version": n + 1}


@router.post("/{aid}/versions/{v}/{action}")
async def version_action(aid: uuid.UUID, v: int, action: Literal["request", "approve", "reject", "rollback"],
                         db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await _agent(db, aid)
    ver = (await db.execute(select(AIAgentVersion).where(AIAgentVersion.agent_id == aid, AIAgentVersion.version == v))).scalar_one_or_none()
    if ver is None:
        raise HTTPException(404, "Version not found")
    if action == "request":
        _can(current_user, "ai.create", "ai.edit")
        if ver.status not in ("DRAFT", "REJECTED"):
            raise HTTPException(409, "Only a draft can be sent for approval.")
        ver.status, ver.approved_by = "PENDING", None
    elif action in ("approve", "reject"):
        _can(current_user, "ai.approve")
        if ver.status != "PENDING":
            raise HTTPException(409, "Nothing waiting for approval.")
        if current_user.username == ver.created_by:
            raise HTTPException(403, "A second person must approve an agent version.")
        if action == "reject":
            ver.status = "REJECTED"
        else:
            ver.status, ver.approved_by = "PUBLISHED", current_user.username
            a.current_version = v
    else:   # rollback: run an earlier published version again
        _can(current_user, "ai.approve")
        if ver.status != "PUBLISHED":
            raise HTTPException(409, "Only a published version can be rolled back to.")
        a.current_version = v
    pats.audit(db, current_user, f"AI_AGENT_VERSION_{action.upper()}", "ai_agent", str(a.id), {"version": v})
    await db.commit()
    return _out(a)


class AgentPatch(BaseModel):
    status: Optional[Literal["ACTIVE", "PAUSED", "DRAFT"]] = None
    stopped: Optional[bool] = None
    schedule: Optional[dict] = None
    budgets: Optional[dict] = None
    name: Optional[str] = Field(None, min_length=1, max_length=120)


@router.patch("/{aid}")
async def patch(aid: uuid.UUID, body: AgentPatch, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await _agent(db, aid)
    if body.stopped is not None:
        _can(current_user, "ai.approve") if not body.stopped else _can(current_user, "ai.edit", "ai.approve")
        a.stopped = body.stopped     # anyone who edits agents may stop one; only an approver restarts it
    if body.status is not None:
        _can(current_user, "ai.edit", "ai.approve")
        if body.status == "ACTIVE" and not a.current_version:
            raise HTTPException(409, "Publish a version first.")
        a.status = body.status
        a.next_run_at = ags.next_run(a.schedule, ags._now()) if body.status == "ACTIVE" else None
    if body.schedule is not None:
        _can(current_user, "ai.edit")
        a.schedule = _clean_schedule(body.schedule)
        a.next_run_at = ags.next_run(a.schedule, ags._now()) if a.status == "ACTIVE" else None
    if body.budgets is not None:
        _can(current_user, "ai.approve")
        a.budgets = _clean_budgets(body.budgets)
    if body.name:
        a.name = body.name
    pats.audit(db, current_user, "AI_AGENT_CHANGED", "ai_agent", str(a.id), body.model_dump(exclude_none=True))
    await db.commit()
    return _out(a)


class RunIn(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    simulate: bool = False
    version: Optional[int] = None
    idempotency_key: Optional[str] = Field(None, max_length=100)


@router.post("/{aid}/run")
async def run_now(aid: uuid.UUID, body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Simulate any version (no writes, no approvals, no budget use) or run the published one now."""
    _can(current_user, "ai.create", "ai.edit")
    a = await _agent(db, aid)
    cfg = await ags.settings_get(db)
    if not body.simulate:
        start = ags._now().replace(hour=0, minute=0, second=0, microsecond=0)
        mine = (await db.execute(select(func.count()).select_from(AIAgentJob).where(
            AIAgentJob.requested_by == current_user.id, AIAgentJob.trigger == "MANUAL", AIAgentJob.created_at >= start))).scalar_one()
        if mine >= cfg["user_manual_runs_per_day"]:
            raise HTTPException(429, "You reached your manual agent runs for today.")
    v = body.version if body.simulate and body.version else a.current_version
    if not v:
        raise HTTPException(409, "No published version: simulate a draft version instead.")
    key = body.idempotency_key or uuid.uuid4().hex
    job = AIAgentJob(agent_id=a.id, version=v, trigger="SIMULATE" if body.simulate else "MANUAL",
                     idempotency_key=f"run:{a.id}:{key}"[:150], requested_by=current_user.id, input=body.input)
    old = (await db.execute(select(AIAgentJob).where(AIAgentJob.idempotency_key == job.idempotency_key))).scalar_one_or_none()
    if old is not None:
        return _job(old)
    db.add(job)
    await db.flush()
    await ags.execute_job(db, job)
    await db.commit()
    return _job(job)


@router.post("/events/{name}")
async def fire_event(name: str, payload: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Queue every active agent whose trigger is this event (webhook-style trigger)."""
    _can(current_user, "ai.edit")
    n = 0
    key = str(payload.get("event_id") or uuid.uuid4().hex)[:60]
    for a in (await db.execute(select(AIAgent).where(AIAgent.status == "ACTIVE", AIAgent.stopped.is_(False)))).scalars():
        ver = (await db.execute(select(AIAgentVersion).where(AIAgentVersion.agent_id == a.id,
                                                             AIAgentVersion.version == a.current_version))).scalar_one_or_none()
        trig = (ver.definition.get("trigger") or {}) if ver else {}
        if trig.get("type") == "event" and trig.get("event") == name:
            await ags.enqueue(db, a, "EVENT", f"event:{a.id}:{name}:{key}", current_user.id, payload)
            n += 1
    await db.commit()
    return {"queued": n}


@router.put("/settings/governance")
async def put_settings(body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "ai.approve")
    out = await ags.settings_put(db, body, current_user.username)
    pats.audit(db, current_user, "AI_AGENT_SETTINGS", "ai_settings", "agents", body)
    await db.commit()
    return out
