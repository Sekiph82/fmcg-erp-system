from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class BoardModuleType(str, PyEnum):
    CRM = "crm"
    RECRUITMENT = "recruitment"
    TASKS = "tasks"
    APPROVALS = "approvals"
    CUSTOM = "custom"
    OPERATIONS = "operations"
    PROJECTS = "projects"


class BoardVisibility(str, PyEnum):
    PRIVATE = "private"
    TEAM = "team"
    GLOBAL = "global"


class ColumnStageType(str, PyEnum):
    NORMAL = "normal"
    FINAL_SUCCESS = "final_success"
    FINAL_FAILURE = "final_failure"


class CardPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CardStatus(str, PyEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class ActivityEventType(str, PyEnum):
    CREATED = "created"
    MOVED = "moved"
    ASSIGNED = "assigned"
    PRIORITY_CHANGED = "priority_changed"
    COMMENTED = "commented"
    DUE_DATE_SET = "due_date_set"
    STATUS_CHANGED = "status_changed"
    ARCHIVED = "archived"


class KBAIAgentType(str, PyEnum):
    WORKFLOW_OPTIMIZER = "workflow_optimizer"
    TASK_PRIORITIZER = "task_prioritizer"


class KBAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class KanbanBoard(Base):
    __tablename__ = "kanban_boards"

    board_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_code = Column(String(50), unique=True, nullable=False)
    board_name = Column(String(200), nullable=False)
    module_type = Column(Enum(BoardModuleType), nullable=False, default=BoardModuleType.CUSTOM)
    description = Column(Text, nullable=True)
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    visibility = Column(Enum(BoardVisibility), default=BoardVisibility.TEAM, nullable=False)
    active_flag = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    columns = relationship("KanbanColumn", back_populates="board", cascade="all, delete-orphan",
                           order_by="KanbanColumn.sequence")
    cards = relationship("KanbanCard", back_populates="board", lazy="dynamic")


class KanbanColumn(Base):
    __tablename__ = "kanban_columns"

    column_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("kanban_boards.board_id"), nullable=False)
    column_name = Column(String(100), nullable=False)
    sequence = Column(Integer, nullable=False, default=0)
    stage_type = Column(Enum(ColumnStageType), default=ColumnStageType.NORMAL, nullable=False)
    color = Column(String(20), nullable=True, default="#6366f1")
    wip_limit = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("KanbanBoard", back_populates="columns")
    cards = relationship("KanbanCard", back_populates="column", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("board_id", "sequence", name="uq_kanban_col_board_seq"),
    )


class KanbanCard(Base):
    __tablename__ = "kanban_cards"

    card_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("kanban_boards.board_id"), nullable=False)
    column_id = Column(UUID(as_uuid=True), ForeignKey("kanban_columns.column_id"), nullable=False)
    card_no = Column(String(30), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String(200), nullable=True)
    assigned_user_id = Column(String(100), nullable=True)
    assigned_user_name = Column(String(200), nullable=True)
    due_date = Column(Date, nullable=True)
    priority = Column(Enum(CardPriority), default=CardPriority.NORMAL, nullable=False)
    status = Column(Enum(CardStatus), default=CardStatus.ACTIVE, nullable=False)
    tags = Column(String(500), nullable=True)
    position = Column(Integer, default=0)
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    board = relationship("KanbanBoard", back_populates="cards")
    column = relationship("KanbanColumn", back_populates="cards")
    activities = relationship("KanbanActivity", back_populates="card", cascade="all, delete-orphan",
                              order_by="KanbanActivity.created_at.desc()")
    comments = relationship("KanbanComment", back_populates="card", cascade="all, delete-orphan",
                            order_by="KanbanComment.created_at.desc()")


class KanbanActivity(Base):
    __tablename__ = "kanban_activities"

    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("kanban_cards.card_id"), nullable=False)
    board_id = Column(UUID(as_uuid=True), nullable=True)
    event_type = Column(Enum(ActivityEventType), nullable=False)
    actor_id = Column(String(100), nullable=True)
    actor_name = Column(String(200), nullable=True)
    from_value = Column(String(300), nullable=True)
    to_value = Column(String(300), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    card = relationship("KanbanCard", back_populates="activities")


class KanbanComment(Base):
    __tablename__ = "kanban_comments"

    comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("kanban_cards.card_id"), nullable=False)
    author_id = Column(String(100), nullable=True)
    author_name = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    card = relationship("KanbanCard", back_populates="comments")


class KBAIRecommendation(Base):
    __tablename__ = "kb_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(KBAIAgentType), nullable=False)
    status = Column(Enum(KBAIRecStatus), default=KBAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    board_id = Column(UUID(as_uuid=True), nullable=True)
    column_id = Column(UUID(as_uuid=True), nullable=True)
    card_id = Column(UUID(as_uuid=True), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
