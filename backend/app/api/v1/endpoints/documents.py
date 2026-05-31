"""Document Management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.documents import Document, DocumentStatus, DocumentCategory, DocumentTag
from app.schemas.documents import (
    DocumentCreate, DocumentUpdate, DocumentApprove,
    DocumentRead, DocumentShort, DocumentVersionHistory,
)
from app.services.document_access_service import ensure_document_action_allowed

router = APIRouter()


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[DocumentShort],
            dependencies=[Depends(require_permission("documents", "view"))])
async def list_documents(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    related_entity_type: Optional[str] = Query(None),
    related_entity_id: Optional[str] = Query(None),
    owner_user_id: Optional[uuid.UUID] = Query(None),
    latest_only: bool = Query(True),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(Document)
    if latest_only:
        q = q.where(Document.is_latest == True)
    if category:
        q = q.where(Document.category == category)
    if status:
        q = q.where(Document.status == status)
    if related_entity_type:
        q = q.where(Document.related_entity_type == related_entity_type)
    if related_entity_id:
        q = q.where(Document.related_entity_id == related_entity_id)
    if owner_user_id:
        q = q.where(Document.owner_user_id == owner_user_id)
    if search:
        q = q.where(Document.title.ilike(f"%{search}%"))
    q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ── Entity documents helper ───────────────────────────────────────────────────

@router.get("/by-entity/", response_model=List[DocumentShort],
            dependencies=[Depends(require_permission("documents", "view"))])
async def list_documents_for_entity(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return all documents linked to a specific ERP entity."""
    result = await db.execute(
        select(Document)
        .where(
            Document.related_entity_type == entity_type,
            Document.related_entity_id == entity_id,
        )
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=DocumentRead, status_code=201,
             dependencies=[Depends(require_permission("documents", "create"))])
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = body.model_dump()
    prev_id = data.pop("previous_version_id", None)
    owner_user_id = data.pop("owner_user_id", None)

    # If superseding, mark previous version as not-latest
    if prev_id:
        prev = await db.get(Document, prev_id)
        if prev:
            prev.is_latest = False

    doc = Document(
        **data,
        previous_version_id=prev_id,
        owner_user_id=owner_user_id or current_user.id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ── Get single ────────────────────────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentRead,
            dependencies=[Depends(require_permission("documents", "view"))])
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}", response_model=DocumentRead,
              dependencies=[Depends(require_permission("documents", "edit"))])
async def update_document(
    doc_id: uuid.UUID,
    body: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "edit")
    for k, v in body.model_dump(exclude_none=True).items():
        if k == "status":
            raise HTTPException(422, "Use explicit document lifecycle endpoints to change status")
        setattr(doc, k, v)
    doc.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(doc)
    return doc


# ── Approve ───────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/approve", response_model=DocumentRead,
             dependencies=[Depends(require_permission("documents", "approve"))])
async def approve_document(
    doc_id: uuid.UUID,
    body: DocumentApprove,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "approve")
    if doc.status != DocumentStatus.DRAFT:
        raise HTTPException(400, f"Document is already {doc.status.value}")
    doc.status = DocumentStatus.APPROVED
    doc.approved_by_id = current_user.id
    doc.approved_at = datetime.now(timezone.utc)
    if body.effective_date:
        doc.effective_date = body.effective_date
    if body.expiry_date:
        doc.expiry_date = body.expiry_date
    await db.commit()
    await db.refresh(doc)
    return doc


# ── Obsolete ──────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/obsolete", response_model=DocumentRead,
             dependencies=[Depends(require_permission("documents", "approve"))])
async def obsolete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "obsolete")
    doc.status = DocumentStatus.OBSOLETE
    doc.is_latest = False
    doc.obsolete_at = datetime.now(timezone.utc)
    doc.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(doc)
    return doc


# ── Archive ───────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/archive", response_model=DocumentRead,
             dependencies=[Depends(require_permission("documents", "approve"))])
async def archive_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "archive")
    doc.status = DocumentStatus.ARCHIVED
    doc.is_latest = False
    doc.archived_at = datetime.now(timezone.utc)
    doc.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(doc)
    return doc


# ── New version ───────────────────────────────────────────────────────────────

@router.post("/{doc_id}/new-version", response_model=DocumentRead, status_code=201,
             dependencies=[Depends(require_permission("documents", "create"))])
async def create_new_version(
    doc_id: uuid.UUID,
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create the next version of an existing document.
    The previous document is marked is_latest=False.
    The new document inherits title/category from the parent unless overridden.
    """
    prev = await db.get(Document, doc_id)
    if not prev:
        raise HTTPException(404, "Parent document not found")
    ensure_document_action_allowed(current_user, prev, "new_version")

    # Mark old version as superseded
    prev.is_latest = False

    data = body.model_dump(exclude_none=True)
    data.setdefault("title", prev.title)
    data.setdefault("category", prev.category)
    data["version"] = prev.version + 1
    data["previous_version_id"] = prev.id
    data["owner_user_id"] = data.get("owner_user_id") or current_user.id
    data["created_by_id"] = current_user.id
    data["updated_by_id"] = current_user.id
    data["is_latest"] = True
    data["status"] = DocumentStatus.DRAFT

    new_doc = Document(**data)
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc


# ── Stats / summary ───────────────────────────────────────────────────────────

class DocumentStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    expiring_soon_count: int     # approved docs with expiry_date within 30 days
    expired_count: int           # approved docs past expiry_date
    latest_only_count: int


@router.get("/stats/summary", response_model=DocumentStats,
            dependencies=[Depends(require_permission("documents", "view"))])
async def document_stats(db: AsyncSession = Depends(get_db)):
    from datetime import date, timedelta
    today = date.today()
    soon = today + timedelta(days=30)

    total = (await db.execute(select(func.count(Document.id)))).scalar_one()
    latest = (await db.execute(
        select(func.count(Document.id)).where(Document.is_latest == True)
    )).scalar_one()

    status_rows = (await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )).all()
    by_status = {r[0].value: r[1] for r in status_rows}

    cat_rows = (await db.execute(
        select(Document.category, func.count(Document.id)).group_by(Document.category)
    )).all()
    by_category = {r[0].value: r[1] for r in cat_rows}

    expiring = (await db.execute(
        select(func.count(Document.id)).where(
            Document.status == DocumentStatus.APPROVED,
            Document.expiry_date.isnot(None),
            Document.expiry_date >= today,
            Document.expiry_date <= soon,
        )
    )).scalar_one()

    expired = (await db.execute(
        select(func.count(Document.id)).where(
            Document.status == DocumentStatus.APPROVED,
            Document.expiry_date.isnot(None),
            Document.expiry_date < today,
        )
    )).scalar_one()

    return DocumentStats(
        total=total,
        by_status=by_status,
        by_category=by_category,
        expiring_soon_count=expiring,
        expired_count=expired,
        latest_only_count=latest,
    )


# ── Version history ───────────────────────────────────────────────────────────

@router.get("/{doc_id}/versions", response_model=List[DocumentVersionHistory],
            dependencies=[Depends(require_permission("documents", "view"))])
async def get_version_history(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Walk the previous_version chain to return all versions of a document.
    Returns newest first.
    """
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Collect lineage by title + category (same document series)
    result = await db.execute(
        select(Document)
        .where(
            Document.title == doc.title,
            Document.category == doc.category,
        )
        .order_by(Document.version.desc())
    )
    return result.scalars().all()


# ── Expiry tracking ───────────────────────────────────────────────────────────

@router.get("/expiring/list",
            dependencies=[Depends(require_permission("documents", "view"))])
async def list_expiring_documents(
    days: int = Query(30, ge=1, le=365),
    include_expired: bool = Query(True),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List documents expiring within the next N days (plus already expired if requested)."""
    from datetime import date, timedelta
    today = date.today()
    cutoff = today + timedelta(days=days)

    conditions = [
        Document.status == DocumentStatus.APPROVED,
        Document.expiry_date.isnot(None),
        Document.is_latest == True,
    ]
    if include_expired:
        conditions.append(Document.expiry_date <= cutoff)
    else:
        conditions.append(Document.expiry_date >= today)
        conditions.append(Document.expiry_date <= cutoff)

    result = await db.execute(
        select(Document).where(*conditions).order_by(Document.expiry_date.asc()).limit(limit)
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "category": d.category,
            "version": d.version,
            "expiry_date": str(d.expiry_date) if d.expiry_date else None,
            "status": d.status,
            "days_until_expiry": (d.expiry_date - today).days if d.expiry_date else None,
            "expired": d.expiry_date < today if d.expiry_date else False,
            "file_name": d.file_name,
            "related_entity_type": d.related_entity_type,
            "related_entity_id": d.related_entity_id,
        }
        for d in docs
    ]


# ── Tagging ───────────────────────────────────────────────────────────────────

class TagIn(BaseModel):
    tags: List[str]


@router.post("/{doc_id}/tags", status_code=201,
             dependencies=[Depends(require_permission("documents", "edit"))])
async def add_tags(
    doc_id: uuid.UUID,
    body: TagIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add tags to a document. Ignores duplicates."""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    existing_r = await db.execute(
        select(DocumentTag.tag).where(DocumentTag.document_id == doc_id)
    )
    existing = {r[0] for r in existing_r.all()}

    added = []
    for tag in body.tags:
        tag = tag.strip().lower()
        if tag and tag not in existing:
            dt = DocumentTag(
                document_id=doc_id,
                tag=tag,
                created_by=getattr(current_user, "username", None) or str(current_user.id),
            )
            db.add(dt)
            added.append(tag)

    await db.commit()
    return {"added": added, "doc_id": str(doc_id)}


@router.delete("/{doc_id}/tags/{tag}",
               dependencies=[Depends(require_permission("documents", "edit"))])
async def remove_tag(
    doc_id: uuid.UUID,
    tag: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a tag from a document."""
    result = await db.execute(
        select(DocumentTag).where(
            DocumentTag.document_id == doc_id,
            DocumentTag.tag == tag.strip().lower(),
        )
    )
    dt = result.scalar_one_or_none()
    if not dt:
        raise HTTPException(404, "Tag not found")
    await db.delete(dt)
    await db.commit()
    return {"removed": tag, "doc_id": str(doc_id)}


@router.get("/{doc_id}/tags",
            dependencies=[Depends(require_permission("documents", "view"))])
async def list_tags(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all tags for a document."""
    result = await db.execute(
        select(DocumentTag).where(DocumentTag.document_id == doc_id).order_by(DocumentTag.tag)
    )
    return [{"tag": t.tag, "created_by": t.created_by, "created_at": t.created_at.isoformat() if t.created_at else ""} for t in result.scalars().all()]


@router.get("/tags/search",
            dependencies=[Depends(require_permission("documents", "view"))])
async def search_by_tag(
    tag: str = Query(...),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return documents that have a given tag."""
    result = await db.execute(
        select(Document)
        .join(DocumentTag, Document.id == DocumentTag.document_id)
        .where(DocumentTag.tag == tag.strip().lower(), Document.is_latest == True)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "category": d.category,
            "version": d.version,
            "status": d.status,
            "expiry_date": str(d.expiry_date) if d.expiry_date else None,
        }
        for d in docs
    ]
