from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.project import ProjectStatus, ProjectTaskStatus, ProjectPriority


# ── Milestone schemas ─────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    name:        str
    description: Optional[str] = None
    due_date:    date


class MilestoneUpdate(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str] = None
    due_date:    Optional[date] = None
    is_complete: Optional[bool] = None


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           uuid.UUID
    project_id:   uuid.UUID
    name:         str
    description:  Optional[str]
    due_date:     date
    is_complete:  bool
    completed_at: Optional[datetime]
    created_at:   datetime


# ── Task dependency ───────────────────────────────────────────────────────────

class DependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    task_id:             uuid.UUID
    depends_on_task_id:  uuid.UUID


# ── Task schemas ──────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    project_id:     uuid.UUID
    milestone_id:   Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None
    title:          str
    description:    Optional[str] = None
    priority:       ProjectPriority = ProjectPriority.MEDIUM
    assigned_to_id: Optional[uuid.UUID] = None
    start_date:     Optional[date] = None
    due_date:       Optional[date] = None
    duration_days:  Optional[int]  = None
    estimated_hours: Optional[Decimal] = None
    is_critical_path: bool = False


class TaskUpdate(BaseModel):
    milestone_id:   Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None
    title:          Optional[str] = None
    description:    Optional[str] = None
    status:         Optional[ProjectTaskStatus] = None
    priority:       Optional[ProjectPriority]   = None
    assigned_to_id: Optional[uuid.UUID] = None
    start_date:     Optional[date] = None
    due_date:       Optional[date] = None
    duration_days:  Optional[int]  = None
    estimated_hours: Optional[Decimal] = None
    actual_hours:    Optional[Decimal] = None
    is_critical_path: Optional[bool] = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    project_id:      uuid.UUID
    milestone_id:    Optional[uuid.UUID]
    parent_task_id:  Optional[uuid.UUID]
    title:           str
    description:     Optional[str]
    status:          ProjectTaskStatus
    priority:        ProjectPriority
    assigned_to_id:  Optional[uuid.UUID]
    assigned_to_name: Optional[str] = None
    start_date:      Optional[date]
    due_date:        Optional[date]
    duration_days:   Optional[int]
    estimated_hours: Optional[Decimal]
    actual_hours:    Optional[Decimal]
    is_critical_path: bool
    completed_at:    Optional[datetime]
    created_at:      datetime
    depends_on_ids:  List[uuid.UUID] = []


# ── Project schemas ───────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name:        str
    description: Optional[str] = None
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    budget:      Optional[Decimal] = None
    notes:       Optional[str] = None


class ProjectUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    status:      Optional[ProjectStatus] = None
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    budget:      Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    notes:       Optional[str] = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           uuid.UUID
    project_no:   str
    name:         str
    description:  Optional[str]
    status:       ProjectStatus
    owner_id:     Optional[uuid.UUID]
    owner_name:   Optional[str] = None
    start_date:   Optional[date]
    end_date:     Optional[date]
    budget:       Optional[Decimal]
    actual_cost:  Optional[Decimal]
    notes:        Optional[str]
    created_at:   datetime
    task_count:   int = 0
    done_count:   int = 0
    milestone_count: int = 0


class ProjectDetail(ProjectRead):
    milestones: List[MilestoneRead] = []
    tasks:      List[TaskRead]      = []


# ── Gantt row (used by frontend to render bars) ───────────────────────────────

class GanttTask(BaseModel):
    id:              uuid.UUID
    title:           str
    status:          ProjectTaskStatus
    priority:        ProjectPriority
    milestone_id:    Optional[uuid.UUID]
    parent_task_id:  Optional[uuid.UUID]
    start_date:      Optional[date]
    due_date:        Optional[date]
    duration_days:   Optional[int]
    assigned_to_name: Optional[str]
    is_critical_path: bool
    depends_on_ids:  List[uuid.UUID] = []
    pct_complete:    int = 0  # 0-100, derived from status


class GanttResponse(BaseModel):
    project_id:  uuid.UUID
    project_no:  str
    project_name: str
    start_date:  Optional[date]
    end_date:    Optional[date]
    milestones:  List[MilestoneRead] = []
    tasks:       List[GanttTask]     = []


# ── Dashboard ─────────────────────────────────────────────────────────────────

class ProjectDashboard(BaseModel):
    total_projects:    int
    planning_count:    int
    active_count:      int
    on_hold_count:     int
    completed_count:   int
    cancelled_count:   int
    total_tasks:       int
    overdue_tasks:     int
    blocked_tasks:     int
