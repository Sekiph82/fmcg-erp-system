"""New Product Development (NPD) Workflow endpoints.

Prefix: /api/v1/npd-workflow
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.npd import (
    NPDProject, NPDStageGate, NPDPilotBatch,
    NPDStage, NPDCategory, NPDPilotBatchOutcome,
)

router = APIRouter()

_STAGE_ORDER = [
    NPDStage.IDEA, NPDStage.CONCEPT, NPDStage.DEVELOPMENT,
    NPDStage.PILOT, NPDStage.LAUNCH, NPDStage.LAUNCHED,
]

_DEFAULT_REGULATORY = {"allergen_review": False, "label_approved": False, "kebs_check": False, "haccp_review": False, "nutritional_calc": False}
_DEFAULT_LAUNCH = {"bom_approved": False, "label_signed_off": False, "production_plan": False, "sales_plan": False, "regulatory_clearance": False, "pricing_approved": False}
_GATE_DEPARTMENTS = ["R&D", "Marketing", "Operations", "Finance", "Regulatory"]


def _counter() -> str:
    import random
    return f"NPD-{datetime.utcnow().strftime('%Y%m')}-{random.randint(1000,9999)}"


def _proj_out(p: NPDProject) -> dict:
    return {
        "id": str(p.id),
        "project_code": p.project_code,
        "name": p.name,
        "category": p.category,
        "stage": p.stage,
        "description": p.description,
        "target_launch_date": str(p.target_launch_date) if p.target_launch_date else None,
        "estimated_cogs": float(p.estimated_cogs) if p.estimated_cogs else None,
        "estimated_selling_price": float(p.estimated_selling_price) if p.estimated_selling_price else None,
        "bom_recipe_id": p.bom_recipe_id,
        "brand": p.brand,
        "target_market": p.target_market,
        "regulatory_checklist": p.regulatory_checklist,
        "launch_readiness_checklist": p.launch_readiness_checklist,
        "notes": p.notes,
        "created_by": p.created_by,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectIn(BaseModel):
    name: str
    category: NPDCategory = NPDCategory.NEW_PRODUCT
    description: Optional[str] = None
    target_launch_date: Optional[date] = None
    estimated_cogs: Optional[float] = None
    estimated_selling_price: Optional[float] = None
    bom_recipe_id: Optional[str] = None
    brand: Optional[str] = None
    target_market: Optional[str] = None
    notes: Optional[str] = None


@router.post("/projects", status_code=201)
async def create_project(payload: ProjectIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    proj = NPDProject(
        project_code=_counter(),
        name=payload.name,
        category=payload.category,
        description=payload.description,
        target_launch_date=payload.target_launch_date,
        estimated_cogs=payload.estimated_cogs,
        estimated_selling_price=payload.estimated_selling_price,
        bom_recipe_id=payload.bom_recipe_id,
        brand=payload.brand,
        target_market=payload.target_market,
        notes=payload.notes,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
        regulatory_checklist=_DEFAULT_REGULATORY.copy(),
        launch_readiness_checklist=_DEFAULT_LAUNCH.copy(),
    )
    db.add(proj)
    # Seed stage gates for all departments at IDEA stage
    for dept in _GATE_DEPARTMENTS:
        gate = NPDStageGate(project_id=proj.id, stage=NPDStage.IDEA, department=dept)
        db.add(gate)
    await db.commit()
    await db.refresh(proj)
    return _proj_out(proj)


@router.get("/projects")
async def list_projects(
    stage: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(NPDProject)
    if active_only:
        q = q.where(NPDProject.is_active == True)
    if stage:
        q = q.where(NPDProject.stage == stage)
    if category:
        q = q.where(NPDProject.category == category)
    q = q.order_by(desc(NPDProject.created_at)).limit(limit)
    result = await db.execute(q)
    return [_proj_out(p) for p in result.scalars().all()]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(NPDProject)
        .options(selectinload(NPDProject.stage_gates), selectinload(NPDProject.pilot_batches))
        .where(NPDProject.id == uuid.UUID(project_id))
    )
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "NPD project not found")
    out = _proj_out(proj)
    out["stage_gates"] = [
        {"id": str(g.id), "stage": g.stage, "department": g.department,
         "approved_flag": g.approved_flag, "approved_by": g.approved_by,
         "approved_at": g.approved_at.isoformat() if g.approved_at else None,
         "notes": g.notes}
        for g in sorted(proj.stage_gates, key=lambda g: (g.stage, g.department))
    ]
    out["pilot_batches"] = [
        {"id": str(b.id), "batch_ref": b.batch_ref, "batch_no": b.batch_no,
         "qty_produced": float(b.qty_produced) if b.qty_produced else None,
         "uom": b.uom, "outcome": b.outcome,
         "actual_cogs": float(b.actual_cogs) if b.actual_cogs else None,
         "started_at": b.started_at.isoformat() if b.started_at else None,
         "completed_at": b.completed_at.isoformat() if b.completed_at else None,
         "notes": b.notes}
        for b in proj.pilot_batches
    ]
    return out


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(NPDProject).where(NPDProject.id == uuid.UUID(project_id)))
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "NPD project not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(proj, field, val)
    await db.commit()
    return _proj_out(proj)


# ── Stage Advancement ─────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/advance-stage")
async def advance_stage(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Advance project to next stage if all gates for current stage approved."""
    r = await db.execute(
        select(NPDProject)
        .options(selectinload(NPDProject.stage_gates))
        .where(NPDProject.id == uuid.UUID(project_id))
    )
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "NPD project not found")

    if proj.stage in (NPDStage.LAUNCHED, NPDStage.CANCELLED):
        raise HTTPException(400, f"Project already {proj.stage}")

    current_gates = [g for g in proj.stage_gates if g.stage == proj.stage]
    unapproved = [g.department for g in current_gates if not g.approved_flag]
    if unapproved:
        raise HTTPException(400, f"Cannot advance — unapproved gates: {', '.join(unapproved)}")

    idx = _STAGE_ORDER.index(proj.stage)
    if idx + 1 < len(_STAGE_ORDER):
        next_stage = _STAGE_ORDER[idx + 1]
        proj.stage = next_stage
        # Seed gates for next stage
        for dept in _GATE_DEPARTMENTS:
            gate = NPDStageGate(project_id=proj.id, stage=next_stage, department=dept)
            db.add(gate)
        await db.commit()
        return {"stage": next_stage, "message": f"Advanced to {next_stage}"}

    raise HTTPException(400, "Already at final stage")


# ── Stage Gate Approval ───────────────────────────────────────────────────────

class GateApproveIn(BaseModel):
    approved_by: str
    notes: Optional[str] = None


@router.post("/projects/{project_id}/gates/{gate_id}/approve")
async def approve_gate(
    project_id: str,
    gate_id: str,
    payload: GateApproveIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(NPDStageGate).where(
            NPDStageGate.id == uuid.UUID(gate_id),
            NPDStageGate.project_id == uuid.UUID(project_id),
        )
    )
    gate = r.scalar_one_or_none()
    if not gate:
        raise HTTPException(404, "Gate not found")
    gate.approved_flag = True
    gate.approved_by = payload.approved_by
    gate.approved_at = datetime.utcnow()
    gate.notes = payload.notes
    await db.commit()
    return {"gate_id": gate_id, "approved": True, "approved_by": payload.approved_by}


# ── Checklist Updates ─────────────────────────────────────────────────────────

class ChecklistUpdate(BaseModel):
    checklist_type: str  # "regulatory" | "launch"
    key: str
    value: bool


@router.patch("/projects/{project_id}/checklist")
async def update_checklist(
    project_id: str,
    payload: ChecklistUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(NPDProject).where(NPDProject.id == uuid.UUID(project_id)))
    proj = r.scalar_one_or_none()
    if not proj:
        raise HTTPException(404, "NPD project not found")
    if payload.checklist_type == "regulatory":
        chk = dict(proj.regulatory_checklist or {})
        chk[payload.key] = payload.value
        proj.regulatory_checklist = chk
    else:
        chk = dict(proj.launch_readiness_checklist or {})
        chk[payload.key] = payload.value
        proj.launch_readiness_checklist = chk
    await db.commit()
    return {"checklist_type": payload.checklist_type, "key": payload.key, "value": payload.value}


# ── Pilot Batches ─────────────────────────────────────────────────────────────

class PilotBatchIn(BaseModel):
    batch_ref: str
    qty_produced: Optional[float] = None
    uom: str = "KG"
    actual_cogs: Optional[float] = None
    outcome: NPDPilotBatchOutcome = NPDPilotBatchOutcome.IN_PROGRESS
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


@router.post("/projects/{project_id}/pilot-batches", status_code=201)
async def add_pilot_batch(
    project_id: str,
    payload: PilotBatchIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(func.count()).select_from(NPDPilotBatch).where(NPDPilotBatch.project_id == uuid.UUID(project_id))
    )
    batch_no = (r.scalar() or 0) + 1

    def _dt(s: Optional[str]):
        return datetime.fromisoformat(s) if s else None

    batch = NPDPilotBatch(
        project_id=uuid.UUID(project_id),
        batch_ref=payload.batch_ref,
        batch_no=batch_no,
        qty_produced=payload.qty_produced,
        uom=payload.uom,
        actual_cogs=payload.actual_cogs,
        outcome=payload.outcome,
        started_at=_dt(payload.started_at),
        completed_at=_dt(payload.completed_at),
        notes=payload.notes,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return {"id": str(batch.id), "batch_ref": batch.batch_ref, "batch_no": batch_no, "outcome": batch.outcome}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def npd_dashboard(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    by_stage_r = await db.execute(
        select(NPDProject.stage, func.count().label("cnt"))
        .where(NPDProject.is_active == True)
        .group_by(NPDProject.stage)
    )
    by_stage = {r.stage: r.cnt for r in by_stage_r.all()}
    total = sum(by_stage.values())

    upcoming_r = await db.execute(
        select(NPDProject)
        .where(NPDProject.is_active == True, NPDProject.target_launch_date.isnot(None))
        .order_by(NPDProject.target_launch_date.asc())
        .limit(5)
    )
    upcoming = [
        {"name": p.name, "stage": p.stage, "target_launch_date": str(p.target_launch_date)}
        for p in upcoming_r.scalars().all()
    ]

    return {"total_active": total, "by_stage": by_stage, "upcoming_launches": upcoming}
