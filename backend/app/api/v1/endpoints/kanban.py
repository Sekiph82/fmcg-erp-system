from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.kanban import (
    BoardCreate, BoardUpdate, BoardOut,
    ColumnCreate, ColumnUpdate, ColumnOut,
    CardCreate, CardUpdate, CardMoveRequest, CardOut,
    CommentCreate, CommentOut, ActivityOut,
    KanbanDashboard, KBAIRecOut, KBAIRecAck,
)
import app.services.kanban_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=KanbanDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Boards ────────────────────────────────────────────────────────────────────

@router.post("/boards", response_model=BoardOut, status_code=201)
async def create_board(data: BoardCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_board(db, data)


@router.get("/boards", response_model=List[BoardOut])
async def list_boards(
    module_type: Optional[str] = None,
    active_only: bool = False,
    owner_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    boards = await svc.list_boards(db, module_type, active_only, owner_id)
    result = []
    for board in boards:
        bd = {c.name: getattr(board, c.name) for c in board.__table__.columns}
        cols = []
        for col in board.columns:
            cd = {c.name: getattr(col, c.name) for c in col.__table__.columns}
            cd["card_count"] = getattr(col, "_card_count", 0)
            cols.append(cd)
        bd["columns"] = cols
        result.append(bd)
    return result


@router.get("/boards/{board_id}", response_model=BoardOut)
async def get_board(board_id: UUID, db: AsyncSession = Depends(get_db)):
    board = await svc.get_board(db, board_id)
    if not board:
        raise HTTPException(404, "Board not found")
    bd = {c.name: getattr(board, c.name) for c in board.__table__.columns}
    cols = []
    for col in board.columns:
        cd = {c.name: getattr(col, c.name) for c in col.__table__.columns}
        cd["card_count"] = getattr(col, "_card_count", 0)
        cols.append(cd)
    bd["columns"] = cols
    return bd


@router.patch("/boards/{board_id}", response_model=BoardOut)
async def update_board(board_id: UUID, data: BoardUpdate, db: AsyncSession = Depends(get_db)):
    board = await svc.update_board(db, board_id, data)
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@router.post("/boards/seed-defaults")
async def seed_boards(db: AsyncSession = Depends(get_db)):
    created = await svc.seed_default_boards(db)
    return {"created": len(created)}


# ── Columns ───────────────────────────────────────────────────────────────────

@router.post("/boards/{board_id}/columns", response_model=ColumnOut, status_code=201)
async def add_column(board_id: UUID, data: ColumnCreate, db: AsyncSession = Depends(get_db)):
    col = await svc.add_column(db, board_id, data)
    d = {c.name: getattr(col, c.name) for c in col.__table__.columns}
    d["card_count"] = 0
    return d


@router.patch("/columns/{column_id}", response_model=ColumnOut)
async def update_column(column_id: UUID, data: ColumnUpdate, db: AsyncSession = Depends(get_db)):
    col = await svc.update_column(db, column_id, data)
    if not col:
        raise HTTPException(404, "Column not found")
    d = {c.name: getattr(col, c.name) for c in col.__table__.columns}
    d["card_count"] = getattr(col, "_card_count", 0)
    return d


@router.delete("/columns/{column_id}", status_code=204)
async def delete_column(column_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_column(db, column_id)
    if not ok:
        raise HTTPException(404, "Column not found")


# ── Cards ─────────────────────────────────────────────────────────────────────

@router.post("/boards/{board_id}/cards", response_model=CardOut, status_code=201)
async def create_card(board_id: UUID, data: CardCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_card(db, board_id, data)


@router.get("/cards", response_model=List[CardOut])
async def list_cards(
    board_id: Optional[UUID] = None,
    column_id: Optional[UUID] = None,
    assigned_user_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_cards(db, board_id, column_id, assigned_user_id, priority, status, overdue_only)


@router.get("/cards/{card_id}", response_model=CardOut)
async def get_card(card_id: UUID, db: AsyncSession = Depends(get_db)):
    card = await svc.get_card(db, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.patch("/cards/{card_id}", response_model=CardOut)
async def update_card(
    card_id: UUID,
    data: CardUpdate,
    actor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    card = await svc.update_card(db, card_id, data, actor)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.post("/cards/{card_id}/move", response_model=CardOut)
async def move_card(card_id: UUID, data: CardMoveRequest, db: AsyncSession = Depends(get_db)):
    card = await svc.move_card(db, card_id, data)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(card_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_card(db, card_id)
    if not ok:
        raise HTTPException(404, "Card not found")


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/cards/{card_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(card_id: UUID, data: CommentCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_comment(db, card_id, data)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/bottleneck/{board_id}")
async def report_bottleneck(board_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.report_bottleneck(db, board_id)


@router.get("/reports/completion/{board_id}")
async def report_completion(board_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.report_completion(db, board_id)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-workflow-optimizer", response_model=List[KBAIRecOut])
async def run_workflow_optimizer(db: AsyncSession = Depends(get_db)):
    return await svc.run_workflow_optimizer(db)


@router.post("/ai/run-task-prioritizer", response_model=List[KBAIRecOut])
async def run_task_prioritizer(db: AsyncSession = Depends(get_db)):
    return await svc.run_task_prioritizer(db)


@router.get("/ai/recommendations", response_model=List[KBAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=KBAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: KBAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
