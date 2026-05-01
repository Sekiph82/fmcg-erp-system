from __future__ import annotations
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel

from app.models.kanban import (
    BoardModuleType, BoardVisibility, ColumnStageType,
    CardPriority, CardStatus, ActivityEventType,
    KBAIAgentType, KBAIRecStatus,
)


# ── Column ────────────────────────────────────────────────────────────────────

class ColumnCreate(BaseModel):
    column_name: str
    sequence: int = 0
    stage_type: ColumnStageType = ColumnStageType.NORMAL
    color: str = "#6366f1"
    wip_limit: Optional[int] = None
    description: Optional[str] = None


class ColumnUpdate(BaseModel):
    column_name: Optional[str] = None
    sequence: Optional[int] = None
    stage_type: Optional[ColumnStageType] = None
    color: Optional[str] = None
    wip_limit: Optional[int] = None
    description: Optional[str] = None


class ColumnOut(BaseModel):
    column_id: UUID
    board_id: UUID
    column_name: str
    sequence: int
    stage_type: ColumnStageType
    color: str
    wip_limit: Optional[int]
    description: Optional[str]
    card_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ── Comment ───────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    body: str


class CommentOut(BaseModel):
    comment_id: UUID
    card_id: UUID
    author_id: Optional[str]
    author_name: Optional[str]
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityOut(BaseModel):
    activity_id: UUID
    card_id: UUID
    event_type: ActivityEventType
    actor_id: Optional[str]
    actor_name: Optional[str]
    from_value: Optional[str]
    to_value: Optional[str]
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Card ──────────────────────────────────────────────────────────────────────

class CardCreate(BaseModel):
    column_id: UUID
    title: str
    description: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_user_name: Optional[str] = None
    due_date: Optional[date] = None
    priority: CardPriority = CardPriority.NORMAL
    tags: Optional[str] = None
    created_by: Optional[str] = None


class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_user_name: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[CardPriority] = None
    status: Optional[CardStatus] = None
    tags: Optional[str] = None


class CardMoveRequest(BaseModel):
    target_column_id: UUID
    position: int = 0
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None


class CardOut(BaseModel):
    card_id: UUID
    board_id: UUID
    column_id: UUID
    card_no: Optional[str]
    title: str
    description: Optional[str]
    reference_type: Optional[str]
    reference_id: Optional[str]
    assigned_user_id: Optional[str]
    assigned_user_name: Optional[str]
    due_date: Optional[date]
    priority: CardPriority
    status: CardStatus
    tags: Optional[str]
    position: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    activities: List[ActivityOut] = []
    comments: List[CommentOut] = []

    class Config:
        from_attributes = True


# ── Board ─────────────────────────────────────────────────────────────────────

class BoardCreate(BaseModel):
    board_code: str
    board_name: str
    module_type: BoardModuleType = BoardModuleType.CUSTOM
    description: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    visibility: BoardVisibility = BoardVisibility.TEAM


class BoardUpdate(BaseModel):
    board_name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[BoardVisibility] = None
    active_flag: Optional[bool] = None


class BoardOut(BaseModel):
    board_id: UUID
    board_code: str
    board_name: str
    module_type: BoardModuleType
    description: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str]
    visibility: BoardVisibility
    active_flag: bool
    created_at: datetime
    columns: List[ColumnOut] = []

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class KanbanDashboard(BaseModel):
    total_boards: int
    active_boards: int
    total_cards: int
    active_cards: int
    overdue_cards: int
    blocked_cards: int
    done_cards: int
    cards_by_priority: dict
    cards_by_module: list
    top_assignees: list


# ── AI ────────────────────────────────────────────────────────────────────────

class KBAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: KBAIAgentType
    status: KBAIRecStatus
    title: str
    body: str
    board_id: Optional[UUID]
    column_id: Optional[UUID]
    card_id: Optional[UUID]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class KBAIRecAck(BaseModel):
    status: KBAIRecStatus
    actioned_by: Optional[str] = None


BoardOut.model_rebuild()
CardOut.model_rebuild()
