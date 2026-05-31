import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ProjectStatus(str, enum.Enum):
    PLANNING   = "PLANNING"
    ACTIVE     = "ACTIVE"
    ON_HOLD    = "ON_HOLD"
    COMPLETED  = "COMPLETED"
    CANCELLED  = "CANCELLED"


class ProjectTaskStatus(str, enum.Enum):
    TODO        = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED     = "BLOCKED"
    DONE        = "DONE"


class ProjectPriority(str, enum.Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class Project(Base, TimestampMixin):
    """Top-level project container."""
    __tablename__ = "projects"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_no  = Column(String(50), unique=True, nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status      = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.PLANNING, index=True)
    owner_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    start_date  = Column(Date, nullable=True)
    end_date    = Column(Date, nullable=True)
    budget      = Column(Numeric(18, 2), nullable=True)
    actual_cost = Column(Numeric(18, 2), nullable=True)
    notes       = Column(Text, nullable=True)

    owner      = relationship("User", foreign_keys=[owner_id])
    milestones = relationship("ProjectMilestone", back_populates="project",
                              cascade="all, delete-orphan", order_by="ProjectMilestone.due_date")
    tasks      = relationship("ProjectTask", back_populates="project",
                              cascade="all, delete-orphan")


class ProjectMilestone(Base, TimestampMixin):
    """Major checkpoint within a project."""
    __tablename__ = "project_milestones"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id  = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date    = Column(Date, nullable=False)
    is_complete = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="milestones")
    tasks   = relationship("ProjectTask", back_populates="milestone")


class ProjectTask(Base, TimestampMixin):
    """Individual task within a project. Supports sub-tasks via parent_task_id."""
    __tablename__ = "project_tasks"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id     = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id   = Column(UUID(as_uuid=True), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)

    title          = Column(String(500), nullable=False)
    description    = Column(Text, nullable=True)
    status         = Column(Enum(ProjectTaskStatus), nullable=False, default=ProjectTaskStatus.TODO)
    priority       = Column(Enum(ProjectPriority), nullable=False, default=ProjectPriority.MEDIUM)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    start_date     = Column(Date, nullable=True)
    due_date       = Column(Date, nullable=True)
    duration_days  = Column(Integer, nullable=True)
    estimated_hours = Column(Numeric(8, 2), nullable=True)
    actual_hours    = Column(Numeric(8, 2), nullable=True)
    is_critical_path = Column(Boolean, nullable=False, default=False)
    completed_at   = Column(DateTime(timezone=True), nullable=True)

    project      = relationship("Project", back_populates="tasks")
    milestone    = relationship("ProjectMilestone", back_populates="tasks", foreign_keys=[milestone_id])
    assigned_to  = relationship("User", foreign_keys=[assigned_to_id])
    sub_tasks    = relationship("ProjectTask", foreign_keys=[parent_task_id],
                                back_populates="parent_task", lazy="select")
    parent_task  = relationship("ProjectTask", foreign_keys=[parent_task_id],
                                remote_side=[id], back_populates="sub_tasks",
                                uselist=False, lazy="select")
    # Dependencies: tasks this task depends on
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id",
                                cascade="all, delete-orphan", back_populates="task")


class TaskDependency(Base, TimestampMixin):
    """Finish-to-start dependency between project tasks."""
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dep"),)

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id           = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False)

    task        = relationship("ProjectTask", foreign_keys=[task_id], back_populates="dependencies")
    depends_on  = relationship("ProjectTask", foreign_keys=[depends_on_task_id])
