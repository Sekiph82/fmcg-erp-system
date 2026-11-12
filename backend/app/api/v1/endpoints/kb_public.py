"""Public help centre: published, non-internal, unscoped knowledge articles only (no login).
Allow-listed in module_registry.PUBLIC_ROUTES."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.knowledge_base import KBArticle, KBArticleFeedback
from app.services.crm_lead_capture_service import ip_hash

router = APIRouter()
FEEDBACK_LIMIT = (10, timedelta(hours=1))


def _public():
    # anything internal, unpublished, company-specific or scope-restricted stays private
    return (KBArticle.status == "PUBLISHED", KBArticle.is_internal_only.is_(False), KBArticle.company_id.is_(None),
            KBArticle.access_scope_type.is_(None), KBArticle.access_level == "all", KBArticle.department_id.is_(None),
            KBArticle.factory_id.is_(None), KBArticle.module_key.is_(None))


@router.get("/search")
async def public_search(q: Optional[str] = Query(None, max_length=100), limit: int = Query(20, ge=1, le=50),
                        db: AsyncSession = Depends(get_db)):
    stmt = select(KBArticle).where(*_public())
    if q and q.strip():
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"  # user wildcards are literal
        stmt = stmt.where(or_(KBArticle.title.ilike(like, escape="\\"), KBArticle.summary.ilike(like, escape="\\"),
                              KBArticle.content_md.ilike(like, escape="\\")))
    rows = (await db.execute(stmt.order_by(KBArticle.is_featured.desc(), KBArticle.title).limit(limit))).scalars()
    return [{"slug": a.slug, "title": a.title, "summary": a.summary} for a in rows]


async def _article(db: AsyncSession, slug: str) -> KBArticle:
    a = (await db.execute(select(KBArticle).where(KBArticle.slug == slug[:200], *_public()))).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "Article not found")
    return a


@router.get("/articles/{slug}")
async def public_article(slug: str, db: AsyncSession = Depends(get_db)):
    a = await _article(db, slug)
    out = {"slug": a.slug, "title": a.title, "summary": a.summary, "content_md": a.content_md,
           "updated_at": a.updated_at.isoformat() if a.updated_at else None}
    a.view_count = (a.view_count or 0) + 1
    await db.commit()
    return out


class PublicFeedback(BaseModel):
    helpful: bool
    comment: Optional[str] = Field(None, max_length=1000)


@router.post("/articles/{slug}/feedback", status_code=202)
async def public_feedback(slug: str, body: PublicFeedback, request: Request, db: AsyncSession = Depends(get_db)):
    a = await _article(db, slug)
    # per-IP limit uses the connection address: behind a reverse proxy set FORWARDED_ALLOW_IPS to that proxy
    hashed = ip_hash(request.client.host if request.client else "unknown")
    now = datetime.now(timezone.utc)
    if hashed:
        recent = (await db.execute(select(func.count()).where(
            KBArticleFeedback.ip_hash == hashed, KBArticleFeedback.created_at >= now - FEEDBACK_LIMIT[1]))).scalar()
        if recent >= FEEDBACK_LIMIT[0]:
            raise HTTPException(429, "Too many responses; thank you.")
    db.add(KBArticleFeedback(article_id=a.id, helpful=body.helpful, comment=(body.comment or "").strip() or None,
                             source="PUBLIC", ip_hash=hashed, created_at=now))
    await db.commit()
    return {"status": "received"}
