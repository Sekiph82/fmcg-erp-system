from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.db.session import get_db
from app.schemas.chatter import (
    ActivityOut, ActivityCreate, ActivityPage,
    CommentCreate, CommentOut, CommentEdit,
    AttachmentCreate, AttachmentOut,
    CTAIRecOut, CTAIRecAck,
)
from app.services import chatter_service

router = APIRouter()


# ── Activities ────────────────────────────────────────────────────────────────

@router.get("/activities", response_model=ActivityPage)
async def list_activities(
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    created_by: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await chatter_service.list_activities(
        db, reference_type, reference_id, activity_type,
        created_by, search, page, per_page,
    )


@router.post("/activities", response_model=ActivityOut)
async def create_activity(data: ActivityCreate, db: AsyncSession = Depends(get_db)):
    return await chatter_service.create_activity(db, data)


@router.get("/activities/{activity_id}", response_model=ActivityOut)
async def get_activity(activity_id: str, db: AsyncSession = Depends(get_db)):
    a = await chatter_service.get_activity(db, activity_id)
    if not a:
        raise HTTPException(404, "Activity not found")
    return a


@router.post("/activities/{activity_id}/pin", response_model=ActivityOut)
async def pin_activity(activity_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await chatter_service.pin_activity(db, activity_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/feed", response_model=List[ActivityOut])
async def get_feed(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    return await chatter_service.get_feed(db, limit)


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await chatter_service.get_stats(db)


@router.get("/timeline")
async def get_timeline(
    reference_types: Optional[str] = None,
    created_by: Optional[str] = None,
    search: Optional[str] = None,
    sla_overdue_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    ref_list = [r.strip() for r in reference_types.split(",")] if reference_types else None
    return await chatter_service.get_timeline(db, reference_types=ref_list, created_by=created_by, search=search, sla_overdue_only=sla_overdue_only, page=page, per_page=per_page)


@router.get("/sla/breached", response_model=List[ActivityOut])
async def get_sla_breached(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    return await chatter_service.get_sla_breached(db, limit)


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/comment", response_model=ActivityOut)
async def post_comment(
    activity_id: str, data: CommentCreate, db: AsyncSession = Depends(get_db)
):
    try:
        return await chatter_service.post_comment(db, activity_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: str, data: CommentEdit, db: AsyncSession = Depends(get_db)
):
    try:
        return await chatter_service.edit_comment(db, comment_id, data.message)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await chatter_service.delete_comment(db, comment_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Attachments ───────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/attach", response_model=ActivityOut)
async def add_attachment(
    activity_id: str, data: AttachmentCreate, db: AsyncSession = Depends(get_db)
):
    try:
        return await chatter_service.add_attachment(db, activity_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI ────────────────────────────────────────────────────────────────────────

@router.get("/ai/recs", response_model=List[CTAIRecOut])
async def list_ai_recs(db: AsyncSession = Depends(get_db)):
    return await chatter_service.list_ai_recs(db)


@router.post("/ai/run/activity-summarizer")
async def run_activity_summarizer(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_activity_summarizer(db)
    return {"generated": count}


@router.post("/ai/run/follow-up-assistant")
async def run_follow_up_assistant(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_follow_up_assistant(db)
    return {"generated": count}


@router.post("/ai/run/insight-extractor")
async def run_insight_extractor(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_insight_extractor(db)
    return {"generated": count}


@router.patch("/ai/recs/{rec_id}", response_model=CTAIRecOut)
async def ack_ai_rec(rec_id: str, data: CTAIRecAck, db: AsyncSession = Depends(get_db)):
    try:
        return await chatter_service.ack_ai_rec(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
