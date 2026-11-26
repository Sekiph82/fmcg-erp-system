"""Sales workspace (M43.S01.T013). Prefix /api/v1/crm-workspace."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import CRMActivity, CRMActivityResult, CRMEmailSignature, CRMRecord, CRMSnippet, CRMStatus
from app.services import crm_workspace_service as ws

VIEW = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region")
router = APIRouter(dependencies=[Depends(require_any_permission(VIEW))])


@router.get("/today")
async def today(queue: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """My work: tasks due today or overdue (optionally one queue), open deals without a next step."""
    me = (str(current_user.id), current_user.username)
    end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    q = select(CRMActivity).where(CRMActivity.assigned_to.in_(me), CRMActivity.result_status == CRMActivityResult.PLANNED,
                                  or_(CRMActivity.due_datetime < end, CRMActivity.due_datetime.is_(None)))
    if queue:
        q = q.where(CRMActivity.queue == queue)
    tasks = (await db.execute(q.order_by(CRMActivity.due_datetime.asc().nullslast()).limit(200))).scalars().all()
    queues = sorted({t.queue for t in (await db.execute(select(CRMActivity).where(
        CRMActivity.assigned_to.in_(me), CRMActivity.result_status == CRMActivityResult.PLANNED,
        CRMActivity.queue.is_not(None)))).scalars()})
    deals = (await db.execute(select(CRMRecord).where(CRMRecord.assigned_rep_id == str(current_user.id),
                                                      CRMRecord.status == CRMStatus.OPEN).limit(200))).scalars().all()
    planned = {a.crm_record_id for a in (await db.execute(select(CRMActivity).where(
        CRMActivity.crm_record_id.in_([d.id for d in deals] or [uuid.uuid4()]),
        CRMActivity.result_status == CRMActivityResult.PLANNED))).scalars()}
    return {"queues": queues,
            "tasks": [{"id": str(t.id), "record_id": str(t.crm_record_id), "subject": t.subject, "queue": t.queue,
                       "type": getattr(t.activity_type, "value", t.activity_type),
                       "due": t.due_datetime.isoformat() if t.due_datetime else None,
                       "overdue": bool(t.due_datetime and t.due_datetime < datetime.utcnow()),
                       "repeats": t.recurrence_rule} for t in tasks],
            "deals_without_next_step": [{"id": str(d.id), "company_name": d.company_name} for d in deals if d.id not in planned]}


@router.post("/tasks/calendar-sync")
async def task_calendar_sync(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """M47.S01.T009: push my open tasks with due times to my connected calendar now (the 5-minute loop does it too)."""
    from app.services.calendar_sync_service import push_tasks_safely
    out = await push_tasks_safely(db, current_user.id)
    await db.commit()
    return out


@router.get("/records/{record_id}/summary")
async def summary(record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    rec = await _scoped_record(db, record_id, current_user, "view")
    return await ws.deal_summary(db, rec)


@router.get("/send-time")
async def send_time(email: str = Query(..., max_length=254), tz: str = Query("Africa/Nairobi", max_length=64),
                    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from sqlalchemy import func as _f
    from app.models.crm import CRMOutboundMessage
    mine = (await db.execute(select(_f.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.to_email == email.strip().lower(),
        CRMOutboundMessage.created_by == current_user.username))).scalar_one()
    if not (mine or current_user.is_superuser or has_permission(current_user, "crm.view_all")):
        raise HTTPException(403, "Only for contacts you have e-mailed.")      # review M43 #14
    return await ws.send_time(db, email, tz)


@router.get("/productivity")
async def productivity(since: date, until: date, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if until < since or (until - since).days > 366:
        raise HTTPException(422, "Choose a period of at most a year.")
    rows = await ws.productivity(db, since, until)
    if current_user.is_superuser or has_permission(current_user, "crm.view_all"):
        return rows
    return [r for r in rows if r["user_id"] == str(current_user.id)]


class SnippetIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    shortcut: Optional[str] = Field(None, max_length=30)
    body: str = Field(min_length=1, max_length=10000)
    shared: bool = False


@router.get("/snippets")
async def list_snippets(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(CRMSnippet).where(or_(CRMSnippet.owner_user_id == current_user.id,
                                                          CRMSnippet.owner_user_id.is_(None))).order_by(CRMSnippet.name))).scalars()
    return [{"id": str(s.id), "name": s.name, "shortcut": s.shortcut, "body": s.body, "shared": s.owner_user_id is None} for s in rows]


@router.post("/snippets", status_code=201)
async def add_snippet(body: SnippetIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if body.shared and not (current_user.is_superuser or has_permission(current_user, "crm.edit_all")):
        raise HTTPException(403, "Only CRM managers can share snippets with everyone.")
    s = CRMSnippet(name=body.name, shortcut=body.shortcut, body=body.body, owner_user_id=None if body.shared else current_user.id)
    db.add(s)
    await db.commit()
    return {"id": str(s.id)}


class SignatureIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=2000)
    is_default: bool = False


@router.get("/signatures")
async def list_signatures(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(CRMEmailSignature).where(CRMEmailSignature.user_id == current_user.id)
                             .order_by(CRMEmailSignature.name))).scalars()
    return [{"id": str(s.id), "name": s.name, "body": s.body, "is_default": s.is_default} for s in rows]


@router.post("/signatures", status_code=201)
async def add_signature(body: SignatureIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if body.is_default:
        await db.execute(update(CRMEmailSignature).where(CRMEmailSignature.user_id == current_user.id).values(is_default=False))
    s = CRMEmailSignature(user_id=current_user.id, **body.model_dump())
    db.add(s)
    await db.commit()
    return {"id": str(s.id)}
