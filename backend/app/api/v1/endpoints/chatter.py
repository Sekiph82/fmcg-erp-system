from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.db.session import get_db
from app.core.access_control import require_any_permission
from app.core.deps import get_current_user
from app.schemas.chatter import (
    ActivityOut, ActivityCreate, ActivityPage,
    CommentCreate, CommentOut, CommentEdit,
    AttachmentCreate, AttachmentOut,
    CTAIRecOut, CTAIRecAck,
)
from app.services import chatter_service

router = APIRouter()

# M47.S01.T003: chatter on a business record needs view rights on that record's module; authors come from the session.
MODULE_OF = {
    "sales_order": "sales", "invoice": "sales", "quotation": "sales", "quote": "sales", "customer": "sales", "shipment": "sales",
    "discount_decision": "sales", "payment": "finance", "journal": "finance", "purchase_order": "procurement",
    "supplier": "procurement", "rfq": "procurement", "production_order": "production", "batch": "production",
    "qc_inspection": "quality", "ticket": "quality", "complaint": "quality", "recall": "quality", "crm_record": "crm",
    "employee": "hr", "leave_request": "hr", "payroll": "payroll", "product": "products", "inventory": "inventory",
    "expense_claim": "expenses", "expense": "expenses", "timesheet": "hr", "appraisal": "hr", "hr_document": "hr",
    "document": "documents",
}
# M47 review: unmapped types fail closed. Generic notes stay open; any other unknown type needs a staff-admin right.
OPEN_TYPES = {"", "note", "task", "general"}
STAFF = ("users.view", "roles.view", "roles.edit")
ADMIN = require_any_permission(STAFF)          # cross-record stats and the AI batch routes


def _may(user, reference_type: Optional[str]) -> bool:
    from app.core.access_control import has_any_permission
    rt = (reference_type or "").strip().lower()
    if rt in OPEN_TYPES or getattr(user, "is_superuser", False):
        return True
    module = MODULE_OF.get(rt)
    return has_any_permission(user, (f"{module}.view",) if module else STAFF)


def _need(user, reference_type: Optional[str]) -> None:
    if not _may(user, reference_type):
        raise HTTPException(403, "You do not have access to this record's activity.")


def _visible(items, user):
    return [a for a in items if _may(user, getattr(a, "reference_type", None) if not isinstance(a, dict) else a.get("reference_type"))]


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
    current_user=Depends(get_current_user),
):
    if reference_type:
        _need(current_user, reference_type)
    out = await chatter_service.list_activities(
        db, reference_type, reference_id, activity_type,
        created_by, search, page, per_page,
    )
    if not reference_type and hasattr(out, "items"):
        out.items = _visible(out.items, current_user)
    return out


@router.post("/activities", response_model=ActivityOut)
async def create_activity(data: ActivityCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need(current_user, data.reference_type)
    data = data.model_copy(update={"created_by": current_user.full_name or current_user.username})   # never from the body
    return await chatter_service.create_activity(db, data)


@router.get("/activities/{activity_id}", response_model=ActivityOut)
async def get_activity(activity_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await chatter_service.get_activity(db, activity_id)
    if not a or not _may(current_user, getattr(a, "reference_type", None)):
        raise HTTPException(404, "Activity not found")
    return a


@router.post("/activities/{activity_id}/pin", response_model=ActivityOut)
async def pin_activity(activity_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await chatter_service.get_activity(db, activity_id)
    if a is None or not _may(current_user, getattr(a, "reference_type", None)):
        raise HTTPException(404, "Activity not found")
    try:
        return await chatter_service.pin_activity(db, activity_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/feed", response_model=List[ActivityOut])
async def get_feed(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return _visible(await chatter_service.get_feed(db, limit), current_user)


@router.get("/stats", dependencies=[Depends(ADMIN)])
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
    current_user=Depends(get_current_user),
):
    ref_list = [r.strip() for r in reference_types.split(",")] if reference_types else None
    out = await chatter_service.get_timeline(db, reference_types=ref_list, created_by=created_by, search=search, sla_overdue_only=sla_overdue_only, page=page, per_page=per_page)
    out["items"] = _visible(out["items"], current_user)
    out["module_breakdown"] = [m for m in out["module_breakdown"] if _may(current_user, m["module"])]
    return out


@router.get("/sla/breached", response_model=List[ActivityOut])
async def get_sla_breached(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return _visible(await chatter_service.get_sla_breached(db, limit), current_user)


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/comment", response_model=ActivityOut)
async def post_comment(
    activity_id: str, data: CommentCreate, db: AsyncSession = Depends(get_db)
, current_user=Depends(get_current_user)
):
    data = data.model_copy(update={"user_id": str(current_user.id), "user_name": current_user.full_name or current_user.username})
    a = await chatter_service.get_activity(db, activity_id)
    if a is not None:
        _need(current_user, getattr(a, "reference_type", None))
    try:
        return await chatter_service.post_comment(db, activity_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: str, data: CommentEdit, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    await _own_comment(db, comment_id, current_user)
    try:
        return await chatter_service.edit_comment(db, comment_id, data.message)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _own_comment(db, comment_id, current_user)
    try:
        await chatter_service.delete_comment(db, comment_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Attachments ───────────────────────────────────────────────────────────────

@router.post("/activities/{activity_id}/attach", response_model=ActivityOut)
async def add_attachment(
    activity_id: str, data: AttachmentCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    a = await chatter_service.get_activity(db, activity_id)
    if a is not None:
        _need(current_user, getattr(a, "reference_type", None))
    data = data.model_copy(update={"uploaded_by": current_user.full_name or current_user.username})
    try:
        return await chatter_service.add_attachment(db, activity_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI ────────────────────────────────────────────────────────────────────────

@router.get("/ai/recs", response_model=List[CTAIRecOut], dependencies=[Depends(ADMIN)])
async def list_ai_recs(db: AsyncSession = Depends(get_db)):
    return await chatter_service.list_ai_recs(db)


@router.post("/ai/run/activity-summarizer", dependencies=[Depends(ADMIN)])
async def run_activity_summarizer(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_activity_summarizer(db)
    return {"generated": count}


@router.post("/ai/run/follow-up-assistant", dependencies=[Depends(ADMIN)])
async def run_follow_up_assistant(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_follow_up_assistant(db)
    return {"generated": count}


@router.post("/ai/run/insight-extractor", dependencies=[Depends(ADMIN)])
async def run_insight_extractor(db: AsyncSession = Depends(get_db)):
    count = await chatter_service.run_insight_extractor(db)
    return {"generated": count}


@router.patch("/ai/recs/{rec_id}", response_model=CTAIRecOut, dependencies=[Depends(ADMIN)])
async def ack_ai_rec(rec_id: str, data: CTAIRecAck, db: AsyncSession = Depends(get_db)):
    try:
        return await chatter_service.ack_ai_rec(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))



async def _own_comment(db: AsyncSession, comment_id: str, user) -> None:
    from app.models.chatter import ActivityComment
    c = await db.get(ActivityComment, comment_id)
    if c is None:
        raise HTTPException(404, "Comment not found")
    if not (getattr(user, "is_superuser", False) or (c.user_id and c.user_id == str(user.id))):
        raise HTTPException(403, "Only the author can change this comment.")
