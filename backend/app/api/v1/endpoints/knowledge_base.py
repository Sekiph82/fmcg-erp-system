"""Knowledge Base / Internal Wiki endpoints."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.core.access_control import has_permission
from app.models.knowledge_base import KBCategory, KBArticle, KBArticleFeedback, KBArticleRevision
from app.services.knowledge_base_service import ensure_article_action_allowed

router = APIRouter()


STATUSES = {"DRAFT", "IN_REVIEW", "PUBLISHED", "ARCHIVED"}


def _require_publish(user, why: str) -> None:
    """Editorial gate: publishing, making an article public or changing published content needs
    knowledge_base.publish (editors submit for review instead)."""
    if not has_permission(user, "knowledge_base.publish"):
        raise HTTPException(403, f"{why} needs the Publish Knowledge Base permission; submit for review instead.")


# fields that decide who may read an article; changing them on a public/published article is publishing
VISIBILITY_FIELDS = ("is_internal_only", "company_id", "access_level", "access_scope_type", "access_scope_id",
                     "department_id", "factory_id", "module_key")


def _can_see_unpublished(user, article) -> bool:
    """Drafts, reviews and archives: their author, editors and publishers only (not every reader)."""
    return (has_permission(user, "knowledge_base.edit") or has_permission(user, "knowledge_base.publish")
            or str(getattr(article, "author_id", "")) == str(getattr(user, "id", "")))


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


async def _feedback_summary(db: AsyncSession, article_id) -> dict:
    rows = (await db.execute(select(KBArticleFeedback.helpful, func.count()).where(
        KBArticleFeedback.article_id == article_id).group_by(KBArticleFeedback.helpful))).all()
    counts = {bool(h): n for h, n in rows}
    return {"helpful": counts.get(True, 0), "not_helpful": counts.get(False, 0)}


def _date_or_none(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list,
            dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def list_categories(
    parent_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(KBCategory).where(KBCategory.is_active == True)
    if parent_id:
        q = q.where(KBCategory.parent_id == parent_id)
    else:
        q = q.where(KBCategory.parent_id == None)
    q = q.order_by(KBCategory.display_order, KBCategory.name)
    r = await db.execute(q)
    cats = list(r.scalars())
    rows = []
    for c in cats:
        article_count_r = await db.execute(
            select(func.count()).select_from(KBArticle)
            .where(KBArticle.category_id == c.id, KBArticle.status == "PUBLISHED")
        )
        rows.append({
            "id": str(c.id),
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "display_order": c.display_order,
            "icon": c.icon,
            "article_count": article_count_r.scalar_one(),
        })
    return rows


@router.post("/categories", status_code=201,
             dependencies=[Depends(require_permission("knowledge_base", "create"))])
async def create_category(body: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    cat = KBCategory(
        slug=body["slug"],
        name=body["name"],
        description=body.get("description"),
        parent_id=uuid.UUID(body["parent_id"]) if body.get("parent_id") else None,
        display_order=body.get("display_order", 0),
        icon=body.get("icon"),
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "slug": cat.slug, "name": cat.name}


@router.patch("/categories/{cat_id}",
              dependencies=[Depends(require_permission("knowledge_base", "edit"))])
async def update_category(
    cat_id: uuid.UUID, body: dict,
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user),
):
    r = await db.execute(select(KBCategory).where(KBCategory.id == cat_id))
    cat = r.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    for k in ["name", "description", "display_order", "icon", "is_active"]:
        if k in body:
            setattr(cat, k, body[k])
    await db.commit()
    return {"id": str(cat.id), "name": cat.name}


# ── Articles ──────────────────────────────────────────────────────────────────

@router.get("/articles", response_model=list,
            dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def list_articles(
    category_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(KBArticle).options(
        selectinload(KBArticle.category),
        selectinload(KBArticle.author),
    )
    if category_id:
        q = q.where(KBArticle.category_id == category_id)
    if status:
        q = q.where(KBArticle.status == status)
        if status != "PUBLISHED" and not (has_permission(current_user, "knowledge_base.edit")
                                          or has_permission(current_user, "knowledge_base.publish")):
            q = q.where(KBArticle.author_id == current_user.id)
    else:
        q = q.where(KBArticle.status == "PUBLISHED")
    if search:
        like = _like(search)
        q = q.where(or_(KBArticle.title.ilike(like, escape="\\"), KBArticle.summary.ilike(like, escape="\\"),
                        KBArticle.content_md.ilike(like, escape="\\")))
    q = q.order_by(KBArticle.is_featured.desc(), KBArticle.updated_at.desc()).limit(limit).offset(offset)
    r = await db.execute(q)
    articles = list(r.scalars())
    rows = []
    for a in articles:
        rows.append({
            "id": str(a.id),
            "slug": a.slug,
            "title": a.title,
            "summary": a.summary,
            "category_id": str(a.category_id) if a.category_id else None,
            "category_name": a.category.name if a.category else None,
            "tags": a.tags or [],
            "status": a.status,
            "version": a.version,
            "author_name": a.author.full_name if a.author else None,
            "view_count": a.view_count,
            "is_featured": a.is_featured,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        })
    return rows


@router.get("/articles/{article_id}", response_model=dict,
            dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def get_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(KBArticle).options(
            selectinload(KBArticle.category),
            selectinload(KBArticle.author),
        ).where(KBArticle.id == article_id)
    )
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Article not found")
    ensure_article_action_allowed(current_user, a, "view")
    if a.status != "PUBLISHED" and not _can_see_unpublished(current_user, a):
        raise HTTPException(404, "Article not found")
    feedback = await _feedback_summary(db, a.id)
    a.view_count = (a.view_count or 0) + 1
    out = {
        "feedback": feedback,
        "is_internal_only": a.is_internal_only,
        "id": str(a.id),
        "slug": a.slug,
        "title": a.title,
        "summary": a.summary,
        "content_md": a.content_md,
        "category_id": str(a.category_id) if a.category_id else None,
        "category_name": a.category.name if a.category else None,
        "tags": a.tags or [],
        "status": a.status,
        "version": a.version,
        "author_name": a.author.full_name if a.author else None,
        "view_count": a.view_count,
        "is_featured": a.is_featured,
        "access_level": a.access_level,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    await db.commit()  # after reading: the commit refreshes updated_at server-side
    return out


@router.post("/articles", status_code=201,
             dependencies=[Depends(require_permission("knowledge_base", "create"))])
async def create_article(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if body.get("status", "DRAFT") not in STATUSES:
        raise HTTPException(422, f"status must be one of {sorted(STATUSES)}")
    if body.get("status") == "PUBLISHED":
        _require_publish(current_user, "Publishing")
    if "is_internal_only" in body and not isinstance(body["is_internal_only"], bool):
        raise HTTPException(422, "is_internal_only must be true or false")
    if body.get("is_internal_only") is False:
        _require_publish(current_user, "Making an article public")
    article = KBArticle(
        slug=body["slug"],
        title=body["title"],
        summary=body.get("summary"),
        content_md=body.get("content_md", ""),
        category_id=uuid.UUID(body["category_id"]) if body.get("category_id") else None,
        tags=body.get("tags", []),
        status=body.get("status", "DRAFT"),
        author_id=current_user.id,
        last_editor_id=current_user.id,
        is_featured=body.get("is_featured", False),
        access_level=body.get("access_level", "all"),
        is_internal_only=body.get("is_internal_only", True),
        company_id=uuid.UUID(body["company_id"]) if body.get("company_id") else None,
        department_id=body.get("department_id"),
        factory_id=body.get("factory_id"),
        module_key=body.get("module_key"),
        review_due_date=_date_or_none(body.get("review_due_date")),
        access_scope_type=body.get("access_scope_type"),
        access_scope_id=body.get("access_scope_id"),
    )
    if article.status == "PUBLISHED":
        article.published_at = datetime.utcnow()
        article.published_by_id = current_user.id
    db.add(article)
    await db.flush()
    rev = KBArticleRevision(
        article_id=article.id,
        version_no=1,
        title=article.title,
        content_md=article.content_md,
        change_summary="Initial version",
        changed_by_id=current_user.id,
    )
    db.add(rev)
    await db.commit()
    await db.refresh(article)
    return {"id": str(article.id), "slug": article.slug, "status": article.status}


@router.patch("/articles/{article_id}",
              dependencies=[Depends(require_permission("knowledge_base", "edit"))])
async def update_article(
    article_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Article not found")
    ensure_article_action_allowed(current_user, a, "edit")
    if "status" in body and body["status"] not in STATUSES:
        raise HTTPException(422, f"status must be one of {sorted(STATUSES)}")
    if body.get("status") == "PUBLISHED" and a.status != "PUBLISHED":
        _require_publish(current_user, "Publishing")
    if "is_internal_only" in body and not isinstance(body["is_internal_only"], bool):
        raise HTTPException(422, "is_internal_only must be true or false")
    if body.get("is_internal_only") is False and a.is_internal_only:
        _require_publish(current_user, "Making an article public")
    if (a.status == "PUBLISHED" or not a.is_internal_only) and any(
            k in body and str(body[k] if body[k] is not None else "") != str(getattr(a, k) if getattr(a, k) is not None else "")
            for k in VISIBILITY_FIELDS):
        _require_publish(current_user, "Changing who can read a published or public article")
    if a.status == "PUBLISHED" and any(k in body and body[k] != getattr(a, k) for k in ("title", "summary", "content_md")):
        _require_publish(current_user, "Changing a published article")
    content_changed = False
    if "content_md" in body and body["content_md"] != a.content_md:
        content_changed = True
    for k in [
        "title", "summary", "content_md", "category_id", "tags", "status",
        "is_featured", "access_level", "is_internal_only", "company_id",
        "department_id", "factory_id", "module_key", "review_due_date",
        "access_scope_type", "access_scope_id",
    ]:
        if k in body:
            if k in {"category_id", "company_id"} and body[k]:
                setattr(a, k, uuid.UUID(body[k]))
            elif k == "review_due_date":
                setattr(a, k, _date_or_none(body[k]))
            else:
                setattr(a, k, body[k])
    if body.get("status") == "PUBLISHED" and not a.published_at:
        a.published_at = datetime.utcnow()
        a.published_by_id = current_user.id
    if body.get("status") == "ARCHIVED":
        a.archived_at = datetime.utcnow()
        a.archived_by_id = current_user.id
    a.last_editor_id = current_user.id
    if content_changed:
        a.version = (a.version or 1) + 1
        rev = KBArticleRevision(
            article_id=a.id,
            version_no=a.version,
            title=a.title,
            content_md=a.content_md,
            change_summary=body.get("change_summary", "Updated"),
            changed_by_id=current_user.id,
        )
        db.add(rev)
    await db.commit()
    return {"id": str(a.id), "slug": a.slug, "version": a.version, "status": a.status}


@router.delete("/articles/{article_id}",
               dependencies=[Depends(require_permission("knowledge_base", "delete"))])
async def delete_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Article not found")
    ensure_article_action_allowed(current_user, a, "delete")
    a.status = "ARCHIVED"
    await db.commit()
    return {"ok": True}


@router.get("/articles/{article_id}/revisions", response_model=list,
            dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def list_revisions(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(KBArticleRevision).options(selectinload(KBArticleRevision.changed_by))
        .where(KBArticleRevision.article_id == article_id)
        .order_by(KBArticleRevision.version_no.desc())
    )
    revs = list(r.scalars())
    return [
        {
            "id": str(rev.id),
            "version_no": rev.version_no,
            "title": rev.title,
            "change_summary": rev.change_summary,
            "changed_by_name": rev.changed_by.full_name if rev.changed_by else None,
            "created_at": rev.created_at.isoformat() if rev.created_at else None,
        }
        for rev in revs
    ]


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list,
            dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def search_kb(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    like = f"%{q}%"
    result = await db.execute(
        select(KBArticle).options(selectinload(KBArticle.category))
        .where(
            KBArticle.status == "PUBLISHED",
            or_(KBArticle.title.ilike(like), KBArticle.summary.ilike(like), KBArticle.content_md.ilike(like))
        )
        .order_by(KBArticle.view_count.desc())
        .limit(limit)
    )
    articles = list(result.scalars())
    return [
        {
            "id": str(a.id),
            "slug": a.slug,
            "title": a.title,
            "summary": a.summary,
            "category_name": a.category.name if a.category else None,
            "view_count": a.view_count,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }
        for a in articles
    ]


# ── Dashboard / Stats ─────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def kb_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_r = await db.execute(select(func.count()).select_from(KBArticle))
    published_r = await db.execute(
        select(func.count()).select_from(KBArticle).where(KBArticle.status == "PUBLISHED")
    )
    draft_r = await db.execute(
        select(func.count()).select_from(KBArticle).where(KBArticle.status == "DRAFT")
    )
    cats_r = await db.execute(select(func.count()).select_from(KBCategory).where(KBCategory.is_active == True))
    top_r = await db.execute(
        select(KBArticle).where(KBArticle.status == "PUBLISHED")
        .order_by(KBArticle.view_count.desc()).limit(5)
    )
    top = list(top_r.scalars())
    return {
        "total_articles": total_r.scalar_one(),
        "published": published_r.scalar_one(),
        "drafts": draft_r.scalar_one(),
        "categories": cats_r.scalar_one(),
        "top_articles": [{"id": str(a.id), "title": a.title, "view_count": a.view_count} for a in top],
    }



@router.post("/articles/{article_id}/feedback", status_code=201,
             dependencies=[Depends(require_permission("knowledge_base", "view"))])
async def add_feedback(article_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    a = await db.get(KBArticle, article_id)
    if not a:
        raise HTTPException(404, "Article not found")
    ensure_article_action_allowed(current_user, a, "view")
    if a.status != "PUBLISHED":
        raise HTTPException(409, "Feedback is collected on published articles only.")
    if not isinstance(body.get("helpful"), bool):
        raise HTTPException(422, "helpful must be true or false")
    from sqlalchemy import delete as _delete

    await db.execute(_delete(KBArticleFeedback).where(  # one vote per user: the latest replaces earlier ones
        KBArticleFeedback.article_id == a.id, KBArticleFeedback.user_id == current_user.id))
    db.add(KBArticleFeedback(article_id=a.id, helpful=body["helpful"], comment=(str(body.get("comment") or "")[:1000] or None),
                             source="INTERNAL", user_id=current_user.id, created_at=datetime.now(timezone.utc)))
    await db.commit()
    return await _feedback_summary(db, a.id)
