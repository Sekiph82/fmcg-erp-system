"""
Project Management — Gantt + Dependencies
──────────────────────────────────────────
Prefix: /api/v1/projects

Routes:
  GET  /                           – list projects
  POST /                           – create project
  GET  /dashboard                  – KPI stats
  GET  /{id}                       – project detail (tasks + milestones)
  PATCH /{id}                      – update project
  DELETE /{id}                     – delete project

  POST /{id}/milestones            – add milestone
  PATCH /{id}/milestones/{mid}     – update milestone
  DELETE /{id}/milestones/{mid}    – delete milestone

  POST /{id}/tasks                 – add task
  PATCH /tasks/{tid}               – update task
  DELETE /tasks/{tid}              – delete task
  POST /tasks/{tid}/complete       – mark task DONE
  POST /tasks/{tid}/deps           – add dependency
  DELETE /tasks/{tid}/deps/{dep_id}– remove dependency

  GET  /{id}/gantt                 – gantt payload for frontend
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as _PydanticBase
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.project import (
    Project, ProjectMilestone, ProjectTask, TaskDependency,
    ProjectStatus, ProjectTaskStatus,
)
from app.models.user import User
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectRead, ProjectDetail,
    MilestoneCreate, MilestoneUpdate, MilestoneRead,
    TaskCreate, TaskUpdate, TaskRead,
    GanttTask, GanttResponse, ProjectDashboard,
)

router = APIRouter()

PCT_MAP = {
    ProjectTaskStatus.TODO:        0,
    ProjectTaskStatus.IN_PROGRESS: 50,
    ProjectTaskStatus.BLOCKED:     25,
    ProjectTaskStatus.DONE:        100,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_proj_no(seq: int) -> str:
    year = date.today().year
    return f"PRJ-{year}-{str(seq + 1).zfill(4)}"


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.milestones),
            selectinload(Project.tasks)
                .selectinload(ProjectTask.assigned_to),
            selectinload(Project.tasks)
                .selectinload(ProjectTask.dependencies),
        )
        .where(Project.id == project_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


async def _get_task_or_404(db: AsyncSession, task_id: uuid.UUID) -> ProjectTask:
    result = await db.execute(
        select(ProjectTask)
        .options(
            selectinload(ProjectTask.assigned_to),
            selectinload(ProjectTask.dependencies),
        )
        .where(ProjectTask.id == task_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    return t


def _task_read(t: ProjectTask) -> TaskRead:
    r = TaskRead.model_validate(t)
    if t.assigned_to:
        r.assigned_to_name = getattr(t.assigned_to, "full_name", None) or t.assigned_to.username
    r.depends_on_ids = [d.depends_on_task_id for d in t.dependencies]
    return r


def _project_read(p: Project) -> ProjectRead:
    r = ProjectRead.model_validate(p)
    if p.owner:
        r.owner_name = getattr(p.owner, "full_name", None) or p.owner.username
    r.task_count = len(p.tasks)
    r.done_count = sum(1 for t in p.tasks if t.status == ProjectTaskStatus.DONE)
    r.milestone_count = len(p.milestones)
    return r


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ProjectRead])
async def list_projects(
    status: Optional[ProjectStatus] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks), selectinload(Project.milestones))
        .order_by(Project.created_at.desc())
        .offset(skip).limit(limit)
    )
    if status:
        q = q.where(Project.status == status)
    projects = list((await db.execute(q)).scalars().all())
    return [_project_read(p) for p in projects]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ProjectDashboard)
async def project_dashboard(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    status_counts: dict = {}
    for s in ProjectStatus:
        r = await db.execute(select(func.count(Project.id)).where(Project.status == s))
        status_counts[s.value] = r.scalar() or 0

    total_tasks_r = await db.execute(select(func.count(ProjectTask.id)))
    total_tasks = total_tasks_r.scalar() or 0

    today = date.today()
    overdue_r = await db.execute(
        select(func.count(ProjectTask.id)).where(
            ProjectTask.due_date < today,
            ProjectTask.status != ProjectTaskStatus.DONE,
        )
    )
    overdue = overdue_r.scalar() or 0

    blocked_r = await db.execute(
        select(func.count(ProjectTask.id)).where(ProjectTask.status == ProjectTaskStatus.BLOCKED)
    )
    blocked = blocked_r.scalar() or 0

    return ProjectDashboard(
        total_projects=sum(status_counts.values()),
        planning_count=status_counts.get("PLANNING", 0),
        active_count=status_counts.get("ACTIVE", 0),
        on_hold_count=status_counts.get("ON_HOLD", 0),
        completed_count=status_counts.get("COMPLETED", 0),
        cancelled_count=status_counts.get("CANCELLED", 0),
        total_tasks=total_tasks,
        overdue_tasks=overdue,
        blocked_tasks=blocked,
    )


# ── Create project ────────────────────────────────────────────────────────────

@router.post("/", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seq_r = await db.execute(select(func.count(Project.id)))
    seq = seq_r.scalar() or 0
    proj = Project(
        project_no=_next_proj_no(seq),
        name=body.name,
        description=body.description,
        status=ProjectStatus.PLANNING,
        owner_id=current_user.id,
        start_date=body.start_date,
        end_date=body.end_date,
        budget=body.budget,
        notes=body.notes,
    )
    db.add(proj)
    await db.commit()
    p = await _get_project_or_404(db, proj.id)
    return _project_read(p)


# ── Get project detail ────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    p = await _get_project_or_404(db, project_id)
    r = ProjectDetail.model_validate(p)
    if p.owner:
        r.owner_name = getattr(p.owner, "full_name", None) or p.owner.username
    r.task_count = len(p.tasks)
    r.done_count = sum(1 for t in p.tasks if t.status == ProjectTaskStatus.DONE)
    r.milestone_count = len(p.milestones)
    r.milestones = [MilestoneRead.model_validate(m) for m in p.milestones]
    r.tasks = [_task_read(t) for t in p.tasks]
    return r


# ── Update project ────────────────────────────────────────────────────────────

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    p = await _get_project_or_404(db, project_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    await db.commit()
    p = await _get_project_or_404(db, project_id)
    return _project_read(p)


# ── Delete project ────────────────────────────────────────────────────────────

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    p = await _get_project_or_404(db, project_id)
    await db.delete(p)
    await db.commit()


# ── Milestones ────────────────────────────────────────────────────────────────

@router.post("/{project_id}/milestones", response_model=MilestoneRead, status_code=201)
async def add_milestone(
    project_id: uuid.UUID,
    body: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_project_or_404(db, project_id)
    m = ProjectMilestone(project_id=project_id, name=body.name, description=body.description, due_date=body.due_date)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return MilestoneRead.model_validate(m)


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=MilestoneRead)
async def update_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(ProjectMilestone).where(
        ProjectMilestone.id == milestone_id, ProjectMilestone.project_id == project_id,
    ))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Milestone not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    if body.is_complete is True and m.completed_at is None:
        m.completed_at = datetime.now(tz=timezone.utc)
    elif body.is_complete is False:
        m.completed_at = None
    await db.commit()
    await db.refresh(m)
    return MilestoneRead.model_validate(m)


@router.delete("/{project_id}/milestones/{milestone_id}", status_code=204)
async def delete_milestone(project_id: uuid.UUID, milestone_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(ProjectMilestone).where(
        ProjectMilestone.id == milestone_id, ProjectMilestone.project_id == project_id,
    ))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Milestone not found")
    await db.delete(m)
    await db.commit()


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def add_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_project_or_404(db, project_id)
    t = ProjectTask(
        project_id=project_id,
        milestone_id=body.milestone_id,
        parent_task_id=body.parent_task_id,
        title=body.title,
        description=body.description,
        status=ProjectTaskStatus.TODO,
        priority=body.priority,
        assigned_to_id=body.assigned_to_id,
        start_date=body.start_date,
        due_date=body.due_date,
        duration_days=body.duration_days,
        estimated_hours=body.estimated_hours,
        is_critical_path=body.is_critical_path,
    )
    db.add(t)
    await db.commit()
    return _task_read(await _get_task_or_404(db, t.id))


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    t = await _get_task_or_404(db, task_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    if body.status == ProjectTaskStatus.DONE and t.completed_at is None:
        t.completed_at = datetime.now(tz=timezone.utc)
    elif body.status and body.status != ProjectTaskStatus.DONE:
        t.completed_at = None
    await db.commit()
    return _task_read(await _get_task_or_404(db, task_id))


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    t = await _get_task_or_404(db, task_id)
    await db.delete(t)
    await db.commit()


@router.post("/tasks/{task_id}/complete", response_model=TaskRead)
async def complete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    t = await _get_task_or_404(db, task_id)
    t.status = ProjectTaskStatus.DONE
    t.completed_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return _task_read(await _get_task_or_404(db, task_id))


# ── Dependencies ──────────────────────────────────────────────────────────────

class _DepReq(_PydanticBase):
    depends_on_task_id: uuid.UUID


@router.post("/tasks/{task_id}/deps", response_model=TaskRead, status_code=201)
async def add_dependency(
    task_id: uuid.UUID,
    body: _DepReq,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if task_id == body.depends_on_task_id:
        raise HTTPException(422, "A task cannot depend on itself")
    # Check existing
    existing = await db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == body.depends_on_task_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(422, "Dependency already exists")
    dep = TaskDependency(task_id=task_id, depends_on_task_id=body.depends_on_task_id)
    db.add(dep)
    await db.commit()
    return _task_read(await _get_task_or_404(db, task_id))


@router.delete("/tasks/{task_id}/deps/{dep_task_id}", status_code=204)
async def remove_dependency(
    task_id: uuid.UUID,
    dep_task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == dep_task_id,
        )
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dependency not found")
    await db.delete(d)
    await db.commit()


# ── Gantt ─────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/gantt", response_model=GanttResponse)
async def get_gantt(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    p = await _get_project_or_404(db, project_id)

    gantt_tasks: List[GanttTask] = []
    for t in sorted(p.tasks, key=lambda x: (x.start_date or date(9999, 1, 1), x.created_at)):
        assigned_name = None
        if t.assigned_to:
            assigned_name = getattr(t.assigned_to, "full_name", None) or t.assigned_to.username
        gt = GanttTask(
            id=t.id,
            title=t.title,
            status=t.status,
            priority=t.priority,
            milestone_id=t.milestone_id,
            parent_task_id=t.parent_task_id,
            start_date=t.start_date,
            due_date=t.due_date,
            duration_days=t.duration_days,
            assigned_to_name=assigned_name,
            is_critical_path=t.is_critical_path,
            depends_on_ids=[d.depends_on_task_id for d in t.dependencies],
            pct_complete=PCT_MAP.get(t.status, 0),
        )
        gantt_tasks.append(gt)

    return GanttResponse(
        project_id=p.id,
        project_no=p.project_no,
        project_name=p.name,
        start_date=p.start_date,
        end_date=p.end_date,
        milestones=[MilestoneRead.model_validate(m) for m in p.milestones],
        tasks=gantt_tasks,
    )
