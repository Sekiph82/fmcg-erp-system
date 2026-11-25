"""Playbooks, guided selling and deal plans (M43.S01.T010). Prefix /api/v1/crm-playbooks.

Authors: anyone with company-wide CRM edit rights (crm.edit_all) drafts and submits; a different crm.edit_all user
approves. Reps run published playbooks on records they may edit (same commercial scope as the CRM record).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.crm import CRMDealPlan, CRMPlaybook, CRMPlaybookRun
from app.services import crm_playbook_service as pbs

router = APIRouter()


def _editor(u) -> bool:
    return u.is_superuser or has_permission(u, "crm.edit_all")


async def _record(db, record_id, user, action="edit"):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    return await _scoped_record(db, record_id, user, action)


def _fail(e: pbs.PlaybookError) -> HTTPException:
    return HTTPException(e.status_code, str(e))


class PlaybookIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    purpose: Literal["CALL", "VISIT", "QUALIFICATION", "STAGE"]
    stage_id: Optional[uuid.UUID] = None
    guidance: Optional[str] = Field(None, max_length=5000)
    questions: list[dict[str, Any]] = Field(min_length=1, max_length=60)
    blocks_stage_exit: bool = False


def _out(p: CRMPlaybook) -> dict:
    return {"id": str(p.id), "family_id": str(p.family_id), "version": p.version, "name": p.name, "purpose": p.purpose,
            "stage_id": str(p.stage_id) if p.stage_id else None, "guidance": p.guidance, "questions": p.questions,
            "blocks_stage_exit": p.blocks_stage_exit, "status": p.status,
            "approved_at": p.approved_at.isoformat() if p.approved_at else None}


@router.get("")
async def list_playbooks(status: Optional[str] = None, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    q = select(CRMPlaybook).order_by(CRMPlaybook.name, CRMPlaybook.version.desc())
    if status:
        q = q.where(CRMPlaybook.status == status)
    elif not _editor(current_user):
        q = q.where(CRMPlaybook.status == "PUBLISHED")       # reps see only what they may run
    return [_out(p) for p in (await db.execute(q.limit(500))).scalars()]


@router.post("", status_code=201)
async def create_playbook(body: PlaybookIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not _editor(current_user):
        raise HTTPException(403, "Only company-wide CRM editors write playbooks.")
    if body.purpose == "STAGE" and not body.stage_id:
        raise HTTPException(422, "A stage playbook needs a stage.")
    try:
        questions = pbs.validate_questions(body.questions)
    except pbs.PlaybookError as e:
        raise _fail(e) from None
    p = CRMPlaybook(family_id=uuid.uuid4(), version=1, name=body.name, purpose=body.purpose, stage_id=body.stage_id,
                    guidance=body.guidance, questions=questions, blocks_stage_exit=body.blocks_stage_exit and body.purpose == "STAGE",
                    status="DRAFT", created_by_id=current_user.id)
    db.add(p)
    await db.commit()
    return _out(p)


@router.put("/{playbook_id}")
async def edit_draft(playbook_id: uuid.UUID, body: PlaybookIn, db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    p = await db.get(CRMPlaybook, playbook_id)
    if p is None or not _editor(current_user):
        raise HTTPException(404, "Playbook not found")
    if p.status != "DRAFT":
        raise HTTPException(409, "Only drafts can be edited; create a new version.")
    try:
        p.questions = pbs.validate_questions(body.questions)
    except pbs.PlaybookError as e:
        raise _fail(e) from None
    p.name, p.purpose, p.stage_id, p.guidance = body.name, body.purpose, body.stage_id, body.guidance
    p.blocks_stage_exit = body.blocks_stage_exit and body.purpose == "STAGE"
    await db.commit()
    return _out(p)


@router.post("/{playbook_id}/lifecycle/{action}")
async def lifecycle(playbook_id: uuid.UUID, action: Literal["submit", "approve", "reject", "new-version", "retire"],
                    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    p = await db.get(CRMPlaybook, playbook_id)
    if p is None or not _editor(current_user):
        raise HTTPException(404, "Playbook not found")
    try:
        if action == "submit":
            if p.status != "DRAFT":
                raise pbs.PlaybookError("Only a draft can be submitted.", 409)
            p.status = "PENDING_APPROVAL"
        elif action == "approve":
            await pbs.publish(db, p, current_user)
        elif action == "reject":
            if p.status != "PENDING_APPROVAL":
                raise pbs.PlaybookError("Nothing to reject.", 409)
            p.status = "DRAFT"
        elif action == "retire":
            p.status = "RETIRED"
        else:
            p = await pbs.new_version(db, p, current_user.id)
    except pbs.PlaybookError as e:
        raise _fail(e) from None
    db.add(AuditLog(actor_id=current_user.id, event_type=f"PLAYBOOK_{action.upper().replace('-', '_')}", module="crm",
                    target_type="crm_playbook", target_id=str(p.id), target_name=f"{p.name} v{p.version}"))
    await db.commit()
    return _out(p)


@router.get("/{family_id}/report")
async def report(family_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (_editor(current_user) or has_permission(current_user, "crm.view_all")):
        raise HTTPException(403, "Managers only.")
    return await pbs.outcome_report(db, family_id)


# ── guided selling on a record ────────────────────────────────────────────────

@router.get("/records/{record_id}/guide")
async def record_guide(record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Published playbooks that apply to this record now (its stage first) and its run history."""
    rec = await _record(db, record_id, current_user, "view")
    pbs_now = (await db.execute(select(CRMPlaybook).where(CRMPlaybook.status == "PUBLISHED"))).scalars().all()
    applicable = [p for p in pbs_now if p.purpose != "STAGE" or (rec.stage_id and p.stage_id == rec.stage_id)]
    runs = (await db.execute(select(CRMPlaybookRun).where(CRMPlaybookRun.crm_record_id == rec.id)
                             .order_by(CRMPlaybookRun.created_at.desc()))).scalars().all()
    return {"playbooks": [_out(p) for p in sorted(applicable, key=lambda p: (p.purpose != "STAGE", p.name))],
            "runs": [{"id": str(r.id), "playbook_id": str(r.playbook_id), "answers": r.answers, "completed": r.completed,
                      "completed_at": r.completed_at.isoformat() if r.completed_at else None} for r in runs]}


class RunIn(BaseModel):
    playbook_id: uuid.UUID
    answers: dict[str, Any] = Field(default_factory=dict)
    complete: bool = False
    run_id: Optional[uuid.UUID] = None


@router.post("/records/{record_id}/runs")
async def save_run(record_id: uuid.UUID, body: RunIn, db: AsyncSession = Depends(get_db),
                   current_user=Depends(get_current_user)):
    rec = await _record(db, record_id, current_user, "edit")
    p = await db.get(CRMPlaybook, body.playbook_id)
    if p is None or p.status != "PUBLISHED":
        raise HTTPException(422, "Only a published playbook can be run.")
    try:
        answers = pbs.check_answers(p.questions, body.answers, body.complete)
    except pbs.PlaybookError as e:
        raise _fail(e) from None
    run = await db.get(CRMPlaybookRun, body.run_id) if body.run_id else None
    if run is not None and (run.crm_record_id != rec.id or run.completed):
        raise HTTPException(409, "That run is finished or belongs to another record.")
    if run is None:
        run = CRMPlaybookRun(playbook_id=p.id, crm_record_id=rec.id, user_id=current_user.id,
                             created_at=datetime.now(timezone.utc))
        db.add(run)
    run.answers = answers
    changed = []
    if body.complete:
        run.completed, run.completed_at = True, datetime.now(timezone.utc)
        changed = pbs.apply_mapping(rec, p.questions, answers)
    await db.commit()
    return {"id": str(run.id), "completed": run.completed, "updated_fields": changed}


# ── deal plan (mutual action plan) ────────────────────────────────────────────

class PlanIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    steps: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


def _plan_out(p: CRMDealPlan, link: Optional[str] = None) -> dict:
    return {"id": str(p.id), "title": p.title, "steps": p.steps, "shared": p.shared, "share_url": link}


@router.get("/records/{record_id}/plan")
async def get_plan(record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rec = await _record(db, record_id, current_user, "view")
    plan = (await db.execute(select(CRMDealPlan).where(CRMDealPlan.crm_record_id == rec.id))).scalar_one_or_none()
    return _plan_out(plan) if plan else None


@router.put("/records/{record_id}/plan")
async def save_plan(record_id: uuid.UUID, body: PlanIn, db: AsyncSession = Depends(get_db),
                    current_user=Depends(get_current_user)):
    rec = await _record(db, record_id, current_user, "edit")
    try:
        steps = pbs.clean_steps(body.steps)
    except (pbs.PlaybookError, ValueError) as e:
        raise HTTPException(422, str(e)) from None
    plan = (await db.execute(select(CRMDealPlan).where(CRMDealPlan.crm_record_id == rec.id))).scalar_one_or_none()
    if plan is None:
        plan = CRMDealPlan(crm_record_id=rec.id, title=body.title, steps=steps)
        db.add(plan)
    plan.title, plan.steps = body.title, steps
    await db.commit()
    return _plan_out(plan)


@router.post("/records/{record_id}/plan/share")
async def share_plan(record_id: uuid.UUID, on: bool = True, db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """Share with the customer (new link each time; the previous link stops working) or stop sharing."""
    rec = await _record(db, record_id, current_user, "edit")
    plan = (await db.execute(select(CRMDealPlan).where(CRMDealPlan.crm_record_id == rec.id))).scalar_one_or_none()
    if plan is None:
        raise HTTPException(404, "No plan yet")
    link = None
    if on:
        token, plan.share_token_hash = pbs.share_token()
        link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/plan/{token}"
    else:
        plan.share_token_hash = None
    plan.shared = on
    await db.commit()
    return _plan_out(plan, link)
