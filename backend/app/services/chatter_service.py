from __future__ import annotations
import re
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from app.models.chatter import (
    Activity, ActivityComment, ActivityAttachment, Mention, ChatterAIRecommendation,
    ReferenceType, ActivityType, Visibility, ChatterAIAgentType, ChatterAIRecStatus,
)
from app.schemas.chatter import (
    ActivityCreate, ActivityPage, CommentCreate, AttachmentCreate, CTAIRecAck,
)


# ── Mention helpers ───────────────────────────────────────────────────────────

def _extract_mentions(message: str) -> List[str]:
    return list(set(re.findall(r"@(\w+)", message or "")))


# ── Core log_activity (exported for cross-module use) ─────────────────────────

async def log_activity(
    db: AsyncSession,
    reference_type: str,
    reference_id: str,
    activity_type: str,
    title: str,
    message: str = "",
    created_by: str = "system",
    visibility: str = "global",
) -> Activity:
    a = Activity(
        reference_type=reference_type,
        reference_id=reference_id,
        activity_type=activity_type,
        title=title,
        message=message,
        created_by=created_by,
        visibility=visibility,
    )
    db.add(a)
    await db.flush()
    for user in _extract_mentions(message):
        db.add(Mention(activity_id=a.activity_id, mentioned_user=user))
    return a


# ── Load helper ───────────────────────────────────────────────────────────────

async def _load_activity(db: AsyncSession, activity_id: str) -> Optional[Activity]:
    result = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.comments),
            selectinload(Activity.attachments),
            selectinload(Activity.mentions),
        )
        .where(Activity.activity_id == activity_id)
    )
    return result.scalar_one_or_none()


# ── Activities ────────────────────────────────────────────────────────────────

async def list_activities(
    db: AsyncSession,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    created_by: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> ActivityPage:
    q = select(Activity).options(
        selectinload(Activity.comments),
        selectinload(Activity.attachments),
        selectinload(Activity.mentions),
    )
    if reference_type:
        q = q.where(Activity.reference_type == reference_type)
    if reference_id:
        q = q.where(Activity.reference_id == reference_id)
    if activity_type:
        q = q.where(Activity.activity_type == activity_type)
    if created_by:
        q = q.where(Activity.created_by == created_by)
    if search:
        q = q.where(
            or_(
                Activity.title.ilike(f"%{search}%"),
                Activity.message.ilike(f"%{search}%"),
            )
        )

    count_q = select(func.count()).select_from(q.order_by(None).subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(Activity.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    items = result.scalars().all()

    return ActivityPage(
        items=list(items),
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


async def create_activity(db: AsyncSession, data: ActivityCreate) -> Activity:
    a = await log_activity(
        db,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        activity_type=data.activity_type,
        title=data.title,
        message=data.message or "",
        created_by=data.created_by or "system",
        visibility=data.visibility,
    )
    if hasattr(data, "sla_due_at") and data.sla_due_at:
        a.sla_due_at = data.sla_due_at
    await db.commit()
    return await _load_activity(db, a.activity_id)


async def get_activity(db: AsyncSession, activity_id: str) -> Optional[Activity]:
    return await _load_activity(db, activity_id)


async def pin_activity(db: AsyncSession, activity_id: str) -> Activity:
    a = await _load_activity(db, activity_id)
    if not a:
        raise ValueError("Activity not found")
    a.is_pinned = not a.is_pinned
    await db.commit()
    return await _load_activity(db, activity_id)


async def get_feed(db: AsyncSession, limit: int = 50) -> List[Activity]:
    result = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.comments),
            selectinload(Activity.attachments),
            selectinload(Activity.mentions),
        )
        .where(Activity.visibility == Visibility.GLOBAL)
        .order_by(Activity.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_stats(db: AsyncSession) -> dict:
    total_act = (await db.execute(select(func.count()).select_from(Activity))).scalar() or 0
    total_cmt = (await db.execute(
        select(func.count()).select_from(ActivityComment)
        .where(ActivityComment.deleted_flag == False)
    )).scalar() or 0
    pending_mentions = (await db.execute(
        select(func.count()).select_from(Mention)
        .where(Mention.notified_flag == False)
    )).scalar() or 0
    result = await db.execute(
        select(Activity.reference_type, func.count().label("cnt"))
        .group_by(Activity.reference_type)
        .order_by(func.count().desc())
    )
    by_module = [{"reference_type": str(r[0].value if hasattr(r[0], 'value') else r[0]), "count": r[1]} for r in result.all()]
    return {
        "total_activities": total_act,
        "total_comments": total_cmt,
        "pending_mentions": pending_mentions,
        "by_module": by_module,
    }


# ── Comments ──────────────────────────────────────────────────────────────────

async def post_comment(db: AsyncSession, activity_id: str, data: CommentCreate) -> Activity:
    result = await db.execute(select(Activity).where(Activity.activity_id == activity_id))
    if not result.scalar_one_or_none():
        raise ValueError("Activity not found")

    comment = ActivityComment(
        activity_id=activity_id,
        user_id=data.user_id,
        user_name=data.user_name,
        message=data.message,
    )
    db.add(comment)
    await db.flush()

    for user in _extract_mentions(data.message):
        db.add(Mention(
            activity_id=activity_id,
            comment_id=comment.comment_id,
            mentioned_user=user,
        ))

    await db.commit()
    return await _load_activity(db, activity_id)


async def edit_comment(db: AsyncSession, comment_id: str, message: str) -> ActivityComment:
    result = await db.execute(
        select(ActivityComment).where(ActivityComment.comment_id == comment_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise ValueError("Comment not found")
    c.message = message
    c.edited_at = datetime.utcnow()
    await db.commit()
    await db.refresh(c)
    return c


async def delete_comment(db: AsyncSession, comment_id: str) -> None:
    result = await db.execute(
        select(ActivityComment).where(ActivityComment.comment_id == comment_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise ValueError("Comment not found")
    c.deleted_flag = True
    c.message = "[deleted]"
    await db.commit()


# ── Attachments ───────────────────────────────────────────────────────────────

async def add_attachment(db: AsyncSession, activity_id: str, data: AttachmentCreate) -> Activity:
    result = await db.execute(select(Activity).where(Activity.activity_id == activity_id))
    if not result.scalar_one_or_none():
        raise ValueError("Activity not found")

    att = ActivityAttachment(activity_id=activity_id, **data.model_dump())
    db.add(att)

    # Also log an attachment_added activity-comment for visibility
    db.add(Activity(
        reference_type=(await db.execute(
            select(Activity.reference_type).where(Activity.activity_id == activity_id)
        )).scalar(),
        reference_id=(await db.execute(
            select(Activity.reference_id).where(Activity.activity_id == activity_id)
        )).scalar(),
        activity_type=ActivityType.ATTACHMENT_ADDED,
        title=f"Attachment added: {data.file_name}",
        created_by=data.uploaded_by or "system",
    ))

    await db.commit()
    return await _load_activity(db, activity_id)


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def list_ai_recs(db: AsyncSession) -> List[ChatterAIRecommendation]:
    result = await db.execute(
        select(ChatterAIRecommendation).order_by(ChatterAIRecommendation.created_at.desc())
    )
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: str, data: CTAIRecAck) -> ChatterAIRecommendation:
    result = await db.execute(
        select(ChatterAIRecommendation).where(ChatterAIRecommendation.rec_id == rec_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise ValueError("Recommendation not found")
    r.status = data.status
    await db.commit()
    await db.refresh(r)
    return r


async def run_activity_summarizer(db: AsyncSession) -> int:
    result = await db.execute(
        select(Activity.reference_type, Activity.reference_id, func.count().label("cnt"))
        .group_by(Activity.reference_type, Activity.reference_id)
        .having(func.count() > 10)
        .order_by(func.count().desc())
        .limit(8)
    )
    busy_refs = result.all()
    recs = []
    for ref_type, ref_id, cnt in busy_refs:
        type_result = await db.execute(
            select(Activity.activity_type, func.count().label("n"))
            .where(and_(Activity.reference_type == ref_type, Activity.reference_id == ref_id))
            .group_by(Activity.activity_type)
            .order_by(func.count().desc())
        )
        type_counts = {str(r[0].value if hasattr(r[0], 'value') else r[0]): r[1] for r in type_result.all()}
        summary = ", ".join(f"{k}: {v}" for k, v in list(type_counts.items())[:3])
        recs.append(ChatterAIRecommendation(
            agent_type=ChatterAIAgentType.ACTIVITY_SUMMARIZER,
            reference_type=str(ref_type.value if hasattr(ref_type, 'value') else ref_type),
            reference_id=ref_id,
            title=f"High-activity record: {cnt} events",
            body=(
                f"Record {ref_id} ({ref_type}) has {cnt} activities. "
                f"Breakdown — {summary}. "
                "Consider pinning a summary comment to help team members catch up quickly."
            ),
            score=round(min(cnt / 50 * 100, 100), 1),
            rec_metadata={"reference_type": str(ref_type), "reference_id": ref_id, "count": cnt},
        ))
    for r in recs[:5]:
        db.add(r)
    await db.commit()
    return len(recs)


async def run_follow_up_assistant(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=48)
    result = await db.execute(
        select(Mention).where(
            and_(Mention.notified_flag == False, Mention.created_at < cutoff)
        ).limit(20)
    )
    old_mentions = result.scalars().all()
    recs = []
    seen = set()
    for m in old_mentions:
        key = m.mentioned_user
        if key in seen:
            continue
        seen.add(key)
        age_h = round((datetime.utcnow() - m.created_at).total_seconds() / 3600)
        recs.append(ChatterAIRecommendation(
            agent_type=ChatterAIAgentType.FOLLOW_UP_ASSISTANT,
            title=f"Unanswered mention: @{m.mentioned_user}",
            body=(
                f"@{m.mentioned_user} was mentioned {age_h}h ago but has not been notified or responded. "
                "Consider following up or ensuring the notification reached them."
            ),
            score=round(min(age_h / 96 * 100, 100), 1),
            rec_metadata={"mentioned_user": m.mentioned_user, "age_hours": age_h},
        ))
    for r in recs[:8]:
        db.add(r)
    await db.commit()
    return len(recs)


async def run_insight_extractor(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(ActivityComment).where(
            and_(
                ActivityComment.created_at >= cutoff,
                ActivityComment.deleted_flag == False,
            )
        ).limit(500)
    )
    comments = result.scalars().all()

    ISSUE_WORDS = {
        "error", "fail", "failed", "failure", "issue", "problem",
        "delay", "delayed", "broken", "stuck", "urgent", "critical", "wrong",
    }
    issue_msgs: List[str] = []
    for c in comments:
        words = set(c.message.lower().split())
        if words & ISSUE_WORDS:
            issue_msgs.append(c.message[:120])

    recs = []
    if len(issue_msgs) >= 3:
        sample = " | ".join(issue_msgs[:3])
        recs.append(ChatterAIRecommendation(
            agent_type=ChatterAIAgentType.INSIGHT_EXTRACTOR,
            title=f"{len(issue_msgs)} issue-related comments in the last 7 days",
            body=(
                f"Found {len(issue_msgs)} comments containing problem-related keywords "
                f"across {len(comments)} recent comments. "
                f"Sample: \"{sample[:200]}…\". "
                "Review these threads and consider escalating recurring issues."
            ),
            score=round(min(len(issue_msgs) / 20 * 100, 100), 1),
            rec_metadata={"issue_count": len(issue_msgs), "total_comments": len(comments)},
        ))

    # Also flag modules with no activity in 7 days
    active_types_result = await db.execute(
        select(Activity.reference_type).where(Activity.created_at >= cutoff).distinct()
    )
    active_types = {r[0] for r in active_types_result.all()}
    from app.models.chatter import ReferenceType as RT
    for ref_type in RT:
        if ref_type.value not in active_types and ref_type != RT.OTHER:
            recs.append(ChatterAIRecommendation(
                agent_type=ChatterAIAgentType.INSIGHT_EXTRACTOR,
                title=f"No activity logged for {ref_type.value} in 7 days",
                body=(
                    f"The {ref_type.value} module has had no chatter activity in the past 7 days. "
                    "This may indicate low engagement or missing system-event hooks."
                ),
                score=40.0,
                rec_metadata={"reference_type": ref_type.value},
            ))

    for r in recs[:8]:
        db.add(r)
    await db.commit()
    return len(recs)


# ── Cross-Module Timeline ─────────────────────────────────────────────────────

async def get_timeline(
    db: AsyncSession,
    reference_types: Optional[List[str]] = None,
    created_by: Optional[str] = None,
    search: Optional[str] = None,
    sla_overdue_only: bool = False,
    page: int = 1,
    per_page: int = 30,
) -> dict:
    q = select(Activity).options(
        selectinload(Activity.comments),
        selectinload(Activity.mentions),
    )
    if reference_types:
        q = q.where(Activity.reference_type.in_(reference_types))
    if created_by:
        q = q.where(Activity.created_by == created_by)
    if search:
        q = q.where(or_(Activity.title.ilike(f"%{search}%"), Activity.message.ilike(f"%{search}%")))
    if sla_overdue_only:
        now = datetime.utcnow()
        q = q.where(and_(Activity.sla_due_at.isnot(None), Activity.sla_due_at < now))

    count_q = select(func.count()).select_from(q.order_by(None).subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(Activity.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    items = (await db.execute(q)).scalars().all()

    module_counts_result = await db.execute(
        select(Activity.reference_type, func.count().label("cnt"))
        .group_by(Activity.reference_type)
        .order_by(func.count().desc())
    )
    module_breakdown = [{"module": r[0], "count": r[1]} for r in module_counts_result.all()]

    sla_breached_count = (await db.execute(
        select(func.count()).select_from(Activity)
        .where(and_(Activity.sla_due_at.isnot(None), Activity.sla_due_at < datetime.utcnow()))
    )).scalar() or 0

    return {
        "items": list(items),
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
        "module_breakdown": module_breakdown,
        "sla_breached_count": sla_breached_count,
    }


async def get_sla_breached(db: AsyncSession, limit: int = 50) -> List[Activity]:
    now = datetime.utcnow()
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.comments), selectinload(Activity.mentions))
        .where(and_(Activity.sla_due_at.isnot(None), Activity.sla_due_at < now))
        .order_by(Activity.sla_due_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def create_activity_with_sla(db: AsyncSession, data) -> Activity:
    a = await log_activity(
        db,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        activity_type=data.activity_type,
        title=data.title,
        message=data.message or "",
        created_by=data.created_by or "system",
        visibility=data.visibility,
    )
    if data.sla_due_at:
        a.sla_due_at = data.sla_due_at
    await db.commit()
    return await _load_activity(db, a.activity_id)
