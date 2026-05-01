from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.kanban import (
    KanbanBoard, KanbanColumn, KanbanCard, KanbanActivity,
    KanbanComment, KBAIRecommendation,
    BoardModuleType, ColumnStageType, CardPriority, CardStatus,
    ActivityEventType, KBAIAgentType, KBAIRecStatus,
)
from app.schemas.kanban import (
    BoardCreate, BoardUpdate, ColumnCreate, ColumnUpdate,
    CardCreate, CardUpdate, CardMoveRequest,
    CommentCreate, KBAIRecAck,
)


# ── Card numbering ────────────────────────────────────────────────────────────

async def _next_card_no(db: AsyncSession, board_id: UUID) -> str:
    result = await db.execute(
        select(func.count(KanbanCard.card_id)).where(KanbanCard.board_id == board_id)
    )
    count = (result.scalar() or 0) + 1
    return f"KB-{count:04d}"


# ── Boards ────────────────────────────────────────────────────────────────────

async def create_board(db: AsyncSession, data: BoardCreate) -> KanbanBoard:
    board = KanbanBoard(**data.model_dump())
    db.add(board)
    await db.flush()
    await db.commit()
    await db.refresh(board)
    return board


async def list_boards(
    db: AsyncSession,
    module_type: Optional[str] = None,
    active_only: bool = False,
    owner_id: Optional[str] = None,
) -> List[KanbanBoard]:
    q = select(KanbanBoard).options(selectinload(KanbanBoard.columns)).order_by(KanbanBoard.board_name)
    if module_type:
        q = q.where(KanbanBoard.module_type == module_type)
    if active_only:
        q = q.where(KanbanBoard.active_flag == True)
    if owner_id:
        q = q.where(KanbanBoard.owner_id == owner_id)
    result = await db.execute(q)
    boards = result.scalars().all()
    for board in boards:
        for col in board.columns:
            cnt_result = await db.execute(
                select(func.count(KanbanCard.card_id)).where(
                    and_(KanbanCard.column_id == col.column_id, KanbanCard.status != CardStatus.ARCHIVED)
                )
            )
            col._card_count = cnt_result.scalar() or 0
    return boards


async def get_board(db: AsyncSession, board_id: UUID) -> Optional[KanbanBoard]:
    result = await db.execute(
        select(KanbanBoard)
        .options(selectinload(KanbanBoard.columns))
        .where(KanbanBoard.board_id == board_id)
    )
    board = result.scalar_one_or_none()
    if board:
        for col in board.columns:
            cnt_result = await db.execute(
                select(func.count(KanbanCard.card_id)).where(
                    and_(KanbanCard.column_id == col.column_id, KanbanCard.status != CardStatus.ARCHIVED)
                )
            )
            col._card_count = cnt_result.scalar() or 0
    return board


async def update_board(db: AsyncSession, board_id: UUID, data: BoardUpdate) -> Optional[KanbanBoard]:
    board = await get_board(db, board_id)
    if not board:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(board, k, v)
    board.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(board)
    return board


async def seed_default_boards(db: AsyncSession) -> List[KanbanBoard]:
    defaults = [
        ("CRM-PIPELINE", "CRM Sales Pipeline", BoardModuleType.CRM,
         ["New Lead", "Contacted", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]),
        ("RECRUITMENT", "Recruitment Pipeline", BoardModuleType.RECRUITMENT,
         ["Applied", "Screening", "Interview 1", "Interview 2", "Offer", "Hired", "Rejected"]),
        ("TASKS", "General Task Board", BoardModuleType.TASKS,
         ["Backlog", "To Do", "In Progress", "Review", "Done"]),
        ("APPROVALS", "Approval Workflow", BoardModuleType.APPROVALS,
         ["Pending", "Under Review", "Approved", "Rejected"]),
        ("OPERATIONS", "Operations Board", BoardModuleType.OPERATIONS,
         ["Not Started", "In Progress", "Blocked", "Completed"]),
    ]
    created = []
    for code, name, mtype, col_names in defaults:
        existing = await db.execute(select(KanbanBoard).where(KanbanBoard.board_code == code))
        if not existing.scalar_one_or_none():
            board = KanbanBoard(board_code=code, board_name=name, module_type=mtype, visibility="global")
            db.add(board)
            await db.flush()
            final_types = {"Won", "Hired", "Done", "Approved", "Completed"}
            failure_types = {"Lost", "Rejected"}
            for i, cname in enumerate(col_names):
                stage = ColumnStageType.FINAL_SUCCESS if cname in final_types else \
                        ColumnStageType.FINAL_FAILURE if cname in failure_types else \
                        ColumnStageType.NORMAL
                colors = ["#6366f1","#8b5cf6","#3b82f6","#0ea5e9","#14b8a6","#22c55e","#ef4444"]
                col = KanbanColumn(board_id=board.board_id, column_name=cname,
                                   sequence=i, stage_type=stage, color=colors[i % len(colors)])
                db.add(col)
            created.append(board)
    if created:
        await db.commit()
    return created


# ── Columns ───────────────────────────────────────────────────────────────────

async def add_column(db: AsyncSession, board_id: UUID, data: ColumnCreate) -> KanbanColumn:
    col = KanbanColumn(board_id=board_id, **data.model_dump())
    db.add(col)
    await db.commit()
    await db.refresh(col)
    col._card_count = 0
    return col


async def update_column(db: AsyncSession, column_id: UUID, data: ColumnUpdate) -> Optional[KanbanColumn]:
    result = await db.execute(select(KanbanColumn).where(KanbanColumn.column_id == column_id))
    col = result.scalar_one_or_none()
    if not col:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(col, k, v)
    await db.commit()
    await db.refresh(col)
    cnt_result = await db.execute(
        select(func.count(KanbanCard.card_id)).where(KanbanCard.column_id == column_id)
    )
    col._card_count = cnt_result.scalar() or 0
    return col


async def delete_column(db: AsyncSession, column_id: UUID) -> bool:
    result = await db.execute(select(KanbanColumn).where(KanbanColumn.column_id == column_id))
    col = result.scalar_one_or_none()
    if not col:
        return False
    await db.delete(col)
    await db.commit()
    return True


# ── Cards ─────────────────────────────────────────────────────────────────────

async def create_card(db: AsyncSession, board_id: UUID, data: CardCreate) -> KanbanCard:
    card_no = await _next_card_no(db, board_id)
    card = KanbanCard(board_id=board_id, card_no=card_no, **data.model_dump())
    db.add(card)
    await db.flush()
    activity = KanbanActivity(
        card_id=card.card_id, board_id=board_id,
        event_type=ActivityEventType.CREATED,
        actor_id=data.created_by, actor_name=data.created_by,
        to_value=data.title,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(card)
    return card


async def get_card(db: AsyncSession, card_id: UUID) -> Optional[KanbanCard]:
    result = await db.execute(
        select(KanbanCard)
        .options(
            selectinload(KanbanCard.activities),
            selectinload(KanbanCard.comments),
        )
        .where(KanbanCard.card_id == card_id)
    )
    return result.scalar_one_or_none()


async def list_cards(
    db: AsyncSession,
    board_id: Optional[UUID] = None,
    column_id: Optional[UUID] = None,
    assigned_user_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False,
) -> List[KanbanCard]:
    q = (
        select(KanbanCard)
        .options(selectinload(KanbanCard.activities), selectinload(KanbanCard.comments))
        .where(KanbanCard.status != CardStatus.ARCHIVED)
        .order_by(KanbanCard.position, KanbanCard.created_at)
    )
    if board_id:
        q = q.where(KanbanCard.board_id == board_id)
    if column_id:
        q = q.where(KanbanCard.column_id == column_id)
    if assigned_user_id:
        q = q.where(KanbanCard.assigned_user_id == assigned_user_id)
    if priority:
        q = q.where(KanbanCard.priority == priority)
    if status:
        q = q.where(KanbanCard.status == status)
    if overdue_only:
        q = q.where(and_(KanbanCard.due_date < date.today(), KanbanCard.status == CardStatus.ACTIVE))
    result = await db.execute(q)
    return result.scalars().all()


async def update_card(db: AsyncSession, card_id: UUID, data: CardUpdate, actor: Optional[str] = None) -> Optional[KanbanCard]:
    card = await get_card(db, card_id)
    if not card:
        return None
    changes = data.model_dump(exclude_none=True)
    for k, v in changes.items():
        old_val = getattr(card, k, None)
        setattr(card, k, v)
        evt = None
        if k == "assigned_user_id":
            evt = ActivityEventType.ASSIGNED
        elif k == "priority":
            evt = ActivityEventType.PRIORITY_CHANGED
        elif k == "status":
            evt = ActivityEventType.STATUS_CHANGED
        elif k == "due_date":
            evt = ActivityEventType.DUE_DATE_SET
        if evt:
            db.add(KanbanActivity(
                card_id=card_id, board_id=card.board_id, event_type=evt,
                actor_id=actor, actor_name=actor,
                from_value=str(old_val) if old_val else None, to_value=str(v),
            ))
    card.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(card)
    return card


async def move_card(db: AsyncSession, card_id: UUID, data: CardMoveRequest) -> Optional[KanbanCard]:
    card = await get_card(db, card_id)
    if not card:
        return None
    # get column names for activity log
    from_col_result = await db.execute(select(KanbanColumn).where(KanbanColumn.column_id == card.column_id))
    from_col = from_col_result.scalar_one_or_none()
    to_col_result = await db.execute(select(KanbanColumn).where(KanbanColumn.column_id == data.target_column_id))
    to_col = to_col_result.scalar_one_or_none()

    old_column_id = card.column_id
    card.column_id = data.target_column_id
    card.position = data.position
    card.updated_at = datetime.utcnow()

    # auto status on final columns
    if to_col:
        if to_col.stage_type == ColumnStageType.FINAL_SUCCESS:
            card.status = CardStatus.DONE
        elif to_col.stage_type == ColumnStageType.FINAL_FAILURE:
            card.status = CardStatus.ARCHIVED
        else:
            card.status = CardStatus.ACTIVE

    activity = KanbanActivity(
        card_id=card_id, board_id=card.board_id,
        event_type=ActivityEventType.MOVED,
        actor_id=data.actor_id, actor_name=data.actor_name,
        from_value=from_col.column_name if from_col else str(old_column_id),
        to_value=to_col.column_name if to_col else str(data.target_column_id),
    )
    db.add(activity)
    await db.commit()
    await db.refresh(card)
    return card


async def delete_card(db: AsyncSession, card_id: UUID) -> bool:
    card = await get_card(db, card_id)
    if not card:
        return False
    card.status = CardStatus.ARCHIVED
    card.updated_at = datetime.utcnow()
    db.add(KanbanActivity(
        card_id=card_id, board_id=card.board_id,
        event_type=ActivityEventType.ARCHIVED,
        to_value="archived",
    ))
    await db.commit()
    return True


# ── Comments ──────────────────────────────────────────────────────────────────

async def add_comment(db: AsyncSession, card_id: UUID, data: CommentCreate) -> KanbanComment:
    comment = KanbanComment(card_id=card_id, **data.model_dump())
    db.add(comment)
    db.add(KanbanActivity(
        card_id=card_id, event_type=ActivityEventType.COMMENTED,
        actor_id=data.author_id, actor_name=data.author_name, note=data.body[:100],
    ))
    await db.commit()
    await db.refresh(comment)
    return comment


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    total_boards = (await db.execute(select(func.count(KanbanBoard.board_id)))).scalar() or 0
    active_boards = (await db.execute(select(func.count(KanbanBoard.board_id)).where(KanbanBoard.active_flag == True))).scalar() or 0
    total_cards = (await db.execute(select(func.count(KanbanCard.card_id)))).scalar() or 0
    active_cards = (await db.execute(select(func.count(KanbanCard.card_id)).where(KanbanCard.status == CardStatus.ACTIVE))).scalar() or 0
    overdue_cards = (await db.execute(
        select(func.count(KanbanCard.card_id)).where(
            and_(KanbanCard.due_date < date.today(), KanbanCard.status == CardStatus.ACTIVE)
        )
    )).scalar() or 0
    blocked_cards = (await db.execute(select(func.count(KanbanCard.card_id)).where(KanbanCard.status == CardStatus.BLOCKED))).scalar() or 0
    done_cards = (await db.execute(select(func.count(KanbanCard.card_id)).where(KanbanCard.status == CardStatus.DONE))).scalar() or 0

    priority_result = await db.execute(
        select(KanbanCard.priority, func.count(KanbanCard.card_id).label("c"))
        .where(KanbanCard.status != CardStatus.ARCHIVED)
        .group_by(KanbanCard.priority)
    )
    cards_by_priority = {r.priority: r.c for r in priority_result.all()}

    module_result = await db.execute(
        select(KanbanBoard.module_type, func.count(KanbanCard.card_id).label("c"))
        .join(KanbanCard, KanbanBoard.board_id == KanbanCard.board_id)
        .where(KanbanCard.status != CardStatus.ARCHIVED)
        .group_by(KanbanBoard.module_type)
        .order_by(func.count(KanbanCard.card_id).desc())
    )
    cards_by_module = [{"module": r.module_type, "count": r.c} for r in module_result.all()]

    assignee_result = await db.execute(
        select(KanbanCard.assigned_user_name, func.count(KanbanCard.card_id).label("c"))
        .where(and_(KanbanCard.assigned_user_id.isnot(None), KanbanCard.status == CardStatus.ACTIVE))
        .group_by(KanbanCard.assigned_user_name)
        .order_by(func.count(KanbanCard.card_id).desc())
        .limit(5)
    )
    top_assignees = [{"user": r.assigned_user_name, "count": r.c} for r in assignee_result.all()]

    return {
        "total_boards": total_boards, "active_boards": active_boards,
        "total_cards": total_cards, "active_cards": active_cards,
        "overdue_cards": overdue_cards, "blocked_cards": blocked_cards,
        "done_cards": done_cards, "cards_by_priority": cards_by_priority,
        "cards_by_module": cards_by_module, "top_assignees": top_assignees,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_bottleneck(db: AsyncSession, board_id: UUID) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(KanbanColumn, func.count(KanbanCard.card_id).label("card_count"))
        .outerjoin(KanbanCard, and_(KanbanColumn.column_id == KanbanCard.column_id, KanbanCard.status == CardStatus.ACTIVE))
        .where(KanbanColumn.board_id == board_id)
        .group_by(KanbanColumn.column_id, KanbanColumn.column_name, KanbanColumn.sequence, KanbanColumn.wip_limit)
        .order_by(KanbanColumn.sequence)
    )
    rows = []
    for col, card_count in result.all():
        over_wip = bool(col.wip_limit and card_count > col.wip_limit)
        rows.append({
            "column_id": str(col.column_id), "column_name": col.column_name,
            "card_count": card_count, "wip_limit": col.wip_limit,
            "over_wip_limit": over_wip,
        })
    return rows


async def report_completion(db: AsyncSession, board_id: UUID) -> Dict[str, Any]:
    total = (await db.execute(select(func.count(KanbanCard.card_id)).where(KanbanCard.board_id == board_id))).scalar() or 0
    done = (await db.execute(select(func.count(KanbanCard.card_id)).where(
        and_(KanbanCard.board_id == board_id, KanbanCard.status == CardStatus.DONE)
    ))).scalar() or 0
    return {"total": total, "done": done, "completion_rate_pct": round(done / total * 100, 1) if total else 0}


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_workflow_optimizer(db: AsyncSession) -> List[KBAIRecommendation]:
    boards_result = await db.execute(select(KanbanBoard).where(KanbanBoard.active_flag == True))
    boards = boards_result.scalars().all()
    recs = []
    for board in boards:
        bottlenecks = await report_bottleneck(db, board.board_id)
        for b in bottlenecks:
            if b["over_wip_limit"]:
                rec = KBAIRecommendation(
                    agent_type=KBAIAgentType.WORKFLOW_OPTIMIZER,
                    title=f"WIP limit exceeded: {b['column_name']} on {board.board_name}",
                    body=(
                        f"Column '{b['column_name']}' has {b['card_count']} cards "
                        f"but the WIP limit is {b['wip_limit']}. "
                        f"Consider pulling from earlier stages or reassigning cards."
                    ),
                    board_id=board.board_id,
                    column_id=UUID(b["column_id"]),
                    score=b["card_count"],
                )
                db.add(rec)
                recs.append(rec)
        # High card concentration (>60% in one column)
        for b in bottlenecks:
            total = sum(x["card_count"] for x in bottlenecks)
            if total > 0 and b["card_count"] / total > 0.6 and b["card_count"] > 5:
                rec = KBAIRecommendation(
                    agent_type=KBAIAgentType.WORKFLOW_OPTIMIZER,
                    title=f"Bottleneck detected: {b['column_name']} on {board.board_name}",
                    body=(
                        f"Column '{b['column_name']}' contains {int(b['card_count']/total*100)}% "
                        f"of all cards ({b['card_count']}/{total}). "
                        f"This is a workflow bottleneck — review capacity and throughput."
                    ),
                    board_id=board.board_id,
                    column_id=UUID(b["column_id"]),
                    score=b["card_count"],
                )
                db.add(rec)
                recs.append(rec)
    if recs:
        await db.commit()
    return recs[:15]


async def run_task_prioritizer(db: AsyncSession) -> List[KBAIRecommendation]:
    today = date.today()
    # Overdue cards
    overdue_result = await db.execute(
        select(KanbanCard)
        .where(and_(KanbanCard.due_date < today, KanbanCard.status == CardStatus.ACTIVE))
        .order_by(KanbanCard.due_date)
        .limit(20)
    )
    overdue = overdue_result.scalars().all()
    recs = []
    for card in overdue:
        days_late = (today - card.due_date).days
        rec = KBAIRecommendation(
            agent_type=KBAIAgentType.TASK_PRIORITIZER,
            title=f"Overdue card: {card.title[:60]}",
            body=(
                f"Card '{card.title}' (#{card.card_no}) is {days_late} day(s) overdue. "
                f"Priority: {card.priority}. Assigned to: {card.assigned_user_name or 'Unassigned'}. "
                f"Review and update or reassign."
            ),
            board_id=card.board_id,
            card_id=card.card_id,
            score=days_late,
        )
        db.add(rec)
        recs.append(rec)
    # Unassigned critical cards
    critical_result = await db.execute(
        select(KanbanCard).where(
            and_(KanbanCard.priority == CardPriority.CRITICAL,
                 KanbanCard.assigned_user_id.is_(None),
                 KanbanCard.status == CardStatus.ACTIVE)
        ).limit(10)
    )
    for card in critical_result.scalars().all():
        rec = KBAIRecommendation(
            agent_type=KBAIAgentType.TASK_PRIORITIZER,
            title=f"Unassigned critical card: {card.title[:60]}",
            body=(
                f"Critical card '{card.title}' (#{card.card_no}) has no assignee. "
                f"Assign immediately to prevent delays."
            ),
            board_id=card.board_id,
            card_id=card.card_id,
            score=100,
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs[:15]


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None) -> List[KBAIRecommendation]:
    q = select(KBAIRecommendation).order_by(KBAIRecommendation.created_at.desc())
    if status:
        q = q.where(KBAIRecommendation.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: KBAIRecAck) -> Optional[KBAIRecommendation]:
    result = await db.execute(select(KBAIRecommendation).where(KBAIRecommendation.rec_id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    if data.actioned_by:
        rec.actioned_by = data.actioned_by
        rec.actioned_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rec)
    return rec
