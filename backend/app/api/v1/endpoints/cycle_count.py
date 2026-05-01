"""Cycle Count endpoints."""
from __future__ import annotations
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.cycle_count import ABCClass, AdjustmentStatus, PlanStatus, TaskStatus
from app.schemas.cycle_count import (
    ABCClassificationOut, AdjustmentApprove, AdjustmentOut, AdjustmentReject,
    CountEntryCreate, CountEntryOut, CycleCountDashboard,
    PlanCreate, PlanOut, PlanUpdate, TaskCreate, TaskOut, TaskUpdate,
)
import app.services.cycle_count_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=CycleCountDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[PlanOut])
async def list_plans(
    warehouse_id: Optional[UUID] = None,
    status: Optional[PlanStatus] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_plans(db, warehouse_id=warehouse_id, status=status, skip=skip, limit=limit)


@router.post("/plans", response_model=PlanOut, status_code=201)
async def create_plan(
    data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.create_plan(db, data, user_id=current_user.id)


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_plan(db, plan_id)
    if not obj:
        raise HTTPException(404, "Plan not found")
    return obj


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def update_plan(plan_id: UUID, data: PlanUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_plan(db, plan_id, data)
    if not obj:
        raise HTTPException(404, "Plan not found")
    return obj


@router.post("/plans/{plan_id}/generate-tasks")
async def generate_tasks(
    plan_id: UUID,
    target_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    plan = await svc.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    tasks = await svc.generate_tasks(db, plan, target_date or date.today())
    await svc.update_plan(db, plan_id, PlanUpdate(status=PlanStatus.ACTIVE))
    return {"generated": len(tasks), "detail": f"Created {len(tasks)} task(s) for {target_date or date.today()}"}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks", response_model=List[TaskOut])
async def list_tasks(
    plan_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    status: Optional[TaskStatus] = None,
    assigned_to_id: Optional[UUID] = None,
    scheduled_date: Optional[date] = None,
    skip: int = 0,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_tasks(
        db,
        plan_id=plan_id, warehouse_id=warehouse_id, status=status,
        assigned_to_id=assigned_to_id, scheduled_date=scheduled_date,
        skip=skip, limit=limit,
    )


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_task(db, data)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_task(db, task_id)
    if not obj:
        raise HTTPException(404, "Task not found")
    return obj


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_task(db, task_id, data)
    if not obj:
        raise HTTPException(404, "Task not found")
    return obj


# ── Count Entries ─────────────────────────────────────────────────────────────

@router.get("/entries", response_model=List[CountEntryOut])
async def list_entries(
    task_id: Optional[UUID] = None,
    within_tolerance: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_entries(db, task_id=task_id, within_tolerance=within_tolerance, skip=skip, limit=limit)


@router.post("/entries", response_model=CountEntryOut, status_code=201)
async def create_count_entry(
    data: CountEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Fetch plan tolerance from task's plan
    task = await svc.get_task(db, data.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    plan = await svc.get_plan(db, task.plan_id)
    tolerance = plan.variance_tolerance_pct if plan else 2.0
    auto_approve = plan.auto_approve_within_tolerance if plan else True
    try:
        return await svc.create_count_entry(
            db, data, user_id=current_user.id,
            tolerance_pct=tolerance, auto_approve=auto_approve,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Adjustments ───────────────────────────────────────────────────────────────

@router.get("/adjustments", response_model=List[AdjustmentOut])
async def list_adjustments(
    status: Optional[AdjustmentStatus] = None,
    skip: int = 0,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_adjustments(db, status=status, skip=skip, limit=limit)


@router.post("/adjustments/approve")
async def approve_adjustments(
    data: AdjustmentApprove,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await svc.approve_adjustments(db, data, approver_id=current_user.id)
    return {"approved": count, "posted": count}


@router.post("/adjustments/reject")
async def reject_adjustments(
    data: AdjustmentReject,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await svc.reject_adjustments(db, data, reviewer_id=current_user.id)
    return {"rejected": count}


# ── ABC Classification ────────────────────────────────────────────────────────

@router.get("/abc", response_model=List[ABCClassificationOut])
async def list_abc(
    warehouse_id: Optional[UUID] = None,
    abc_class: Optional[ABCClass] = None,
    skip: int = 0,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_abc_classifications(db, warehouse_id=warehouse_id, abc_class=abc_class, skip=skip, limit=limit)


@router.post("/abc/classify")
async def run_abc_classification(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    count = await svc.run_abc_classification(db, warehouse_id)
    return {"classified": count, "warehouse_id": str(warehouse_id)}


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/accuracy")
async def report_accuracy(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.accuracy_report(db, days=days)


@router.get("/reports/variance")
async def report_variance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.variance_report(db, days=days)


@router.get("/reports/completion")
async def report_completion(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await svc.completion_report(db, days=days)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/ai/variance-analyzer")
async def ai_variance_analyzer(db: AsyncSession = Depends(get_db)):
    return await svc.ai_variance_analyzer(db)


@router.get("/ai/count-optimizer")
async def ai_count_optimizer(db: AsyncSession = Depends(get_db)):
    return await svc.ai_count_optimizer(db)
