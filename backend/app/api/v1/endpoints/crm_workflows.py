"""Visual workflow designer API (M36.S03.T004). CRM-wide view to read and simulate; CRM-wide edit to draft;
publishing, rollback and approval decisions need the CRM approval right."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_db
from app.models.crm import CRMRecord, CRMWorkflow, CRMWorkflowRun, CRMWorkflowVersion
from app.services import crm_workflow_service as wfs

router = APIRouter()
READ = require_any_permission(("crm.view_all", "crm.edit_all"))
EDIT = require_any_permission(("crm.edit_all",))
PUBLISH = require_any_permission(("crm.approve", "crm.approve_all"))


class WorkflowIn(BaseModel):
    name: str = Field(min_length=3, max_length=150)


class GraphIn(BaseModel):
    graph: dict


class SimulateIn(BaseModel):
    graph: dict
    crm_record_id: uuid.UUID
    approvals: str = Field("yes", pattern="^(yes|no)$")


class DecisionIn(BaseModel):
    approve: bool


def _ver(v: CRMWorkflowVersion) -> dict:
    return {"id": str(v.id), "version_no": v.version_no, "status": v.status, "graph": v.graph,
            "published_at": v.published_at.isoformat() if v.published_at else None}


async def _wf(db: AsyncSession, wid: uuid.UUID) -> CRMWorkflow:
    wf = await db.get(CRMWorkflow, wid)
    if wf is None:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.get("")
async def list_workflows(db: AsyncSession = Depends(get_db), _=Depends(READ)):
    wfs_ = (await db.execute(select(CRMWorkflow).order_by(CRMWorkflow.name))).scalars().all()
    return [{"id": str(w.id), "name": w.name, "trigger_event": w.trigger_event, "published_version_id": str(w.published_version_id) if w.published_version_id else None} for w in wfs_]


@router.post("", status_code=201)
async def create_workflow(body: WorkflowIn, db: AsyncSession = Depends(get_db), user=Depends(EDIT)):
    wf = CRMWorkflow(name=body.name.strip(), created_by=user.username)
    db.add(wf)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "A workflow with this name exists.")
    return {"id": str(wf.id)}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(READ)):
    wf = await _wf(db, workflow_id)
    vers = (await db.execute(select(CRMWorkflowVersion).where(CRMWorkflowVersion.workflow_id == wf.id)
                             .order_by(CRMWorkflowVersion.version_no.desc()))).scalars().all()
    runs = (await db.execute(select(CRMWorkflowRun).join(CRMWorkflowVersion, CRMWorkflowVersion.id == CRMWorkflowRun.version_id)
                             .where(CRMWorkflowVersion.workflow_id == wf.id).order_by(CRMWorkflowRun.created_at.desc()).limit(50))).scalars().all()
    from app.models.m47_automation import CRMWorkflowHook
    hook = await db.get(CRMWorkflowHook, wf.id)
    return {"id": str(wf.id), "name": wf.name, "trigger_event": wf.trigger_event, "versions": [_ver(v) for v in vers],
            "webhook": ({"path": f"/api/v1/public/crm-workflow-hooks/{wf.id}", "token_hint": hook.token_hint,
                         "rotated_at": hook.rotated_at.isoformat(),
                         "last_used_at": hook.last_used_at.isoformat() if hook.last_used_at else None} if hook else None),
            "runs": [{"id": str(r.id), "crm_record_id": str(r.crm_record_id), "status": r.status, "log": r.log,
                      "resume_at": r.resume_at.isoformat() if r.resume_at else None} for r in runs]}


@router.post("/{workflow_id}/versions", status_code=201)
async def save_draft(workflow_id: uuid.UUID, body: GraphIn, db: AsyncSession = Depends(get_db), user=Depends(EDIT)):
    wf = await _wf(db, workflow_id)
    n = (await db.execute(select(func.coalesce(func.max(CRMWorkflowVersion.version_no), 0)).where(CRMWorkflowVersion.workflow_id == wf.id))).scalar_one()
    v = CRMWorkflowVersion(workflow_id=wf.id, version_no=n + 1, graph=body.graph, created_by=user.username)
    db.add(v)
    await db.commit()
    return {**_ver(v), "problems": wfs.validate(body.graph) or await wfs.recipient_problems(db, body.graph)}


@router.post("/validate")
async def validate_graph(body: GraphIn, _=Depends(READ)):
    return {"problems": wfs.validate(body.graph)}


@router.post("/simulate")
async def simulate(body: SimulateIn, db: AsyncSession = Depends(get_db), _=Depends(READ)):
    record = await db.get(CRMRecord, body.crm_record_id)
    if record is None:
        raise HTTPException(404, "Record not found")
    try:
        return {"steps": await wfs.simulate(db, body.graph, record, body.approvals)}
    except wfs.WorkflowError as e:
        raise HTTPException(e.status, e.detail)


@router.post("/versions/{version_id}/publish")
async def publish(version_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(PUBLISH)):
    """Publish a draft — or re-publish an archived version (rollback)."""
    v = await db.get(CRMWorkflowVersion, version_id)
    if v is None:
        raise HTTPException(404, "Version not found")
    try:
        await wfs.publish(db, v, user)
    except wfs.WorkflowError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return _ver(v)


@router.post("/runs/{run_id}/decision")
async def decide(run_id: uuid.UUID, body: DecisionIn, db: AsyncSession = Depends(get_db), user=Depends(PUBLISH)):
    try:
        run = await wfs.decide(db, run_id, user, body.approve)
    except wfs.WorkflowError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return {"id": str(run.id), "status": run.status, "log": run.log}


# ── M47.S01.T008 inbound webhook token (approvers only: it opens an entry point into the workflow) ──────────

@router.post("/{workflow_id}/webhook-token", status_code=201)
async def issue_webhook_token(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(PUBLISH)):
    """Create or rotate the token. It is shown once here; only its digest is stored, the old token stops working."""
    wf = await _wf(db, workflow_id)
    token = await wfs.issue_hook_token(db, wf, user)
    await db.commit()
    return {"token": token, "path": f"/api/v1/public/crm-workflow-hooks/{wf.id}", "shown_once": True,
            "usage": "POST JSON {event_id, record_id | email} with header Authorization: Bearer <token>"}


@router.delete("/{workflow_id}/webhook-token", status_code=204)
async def revoke_webhook_token(workflow_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(PUBLISH)):
    wf = await _wf(db, workflow_id)
    if not await wfs.revoke_hook(db, wf, user):
        raise HTTPException(404, "This workflow has no webhook token.")
    await db.commit()
