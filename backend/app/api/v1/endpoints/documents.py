"""Document Management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
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
from app.services.document_storage_service import get_document_storage, scan_document

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.post("/{doc_id}/file", response_model=DocumentRead, status_code=201,
             dependencies=[Depends(require_permission("documents", "edit"))])
async def upload_document_file(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "edit")
    if doc.status != DocumentStatus.DRAFT or not doc.is_latest:
        raise HTTPException(409, "Files can only be attached to the latest draft document version")
    if doc.storage_key or doc.file_name or doc.file_size_bytes:
        raise HTTPException(409, "Document files are immutable; create a new document version to replace a file")

    storage = get_document_storage()
    stored = await storage.store_upload(file)
    try:
        scan_result = await scan_document(storage.path_for(stored.storage_key))
        # The file is stored/scanned before taking the row lock. Re-read and
        # validate under a lock so concurrent approval or uploads cannot attach
        # a file to an approved version or replace another uploaded binary.
        locked_doc = (await db.execute(
            select(Document)
            .where(Document.id == doc_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )).scalar_one_or_none()
        if not locked_doc:
            raise HTTPException(404, "Document not found")
        ensure_document_action_allowed(current_user, locked_doc, "edit")
        if locked_doc.status != DocumentStatus.DRAFT or not locked_doc.is_latest:
            raise HTTPException(409, "Files can only be attached to the latest draft document version")
        if locked_doc.storage_key or locked_doc.file_name or locked_doc.file_size_bytes:
            raise HTTPException(409, "Document files are immutable; create a new document version to replace a file")

        locked_doc.file_url = None
        locked_doc.file_name = stored.file_name
        locked_doc.file_size_bytes = stored.file_size_bytes
        locked_doc.mime_type = stored.mime_type
        locked_doc.storage_provider = "local"
        locked_doc.storage_key = stored.storage_key
        locked_doc.file_checksum_sha256 = stored.sha256
        locked_doc.file_scan_status = scan_result.status
        locked_doc.file_scan_result = scan_result.result
        locked_doc.updated_by_id = current_user.id
        await db.commit()
    except Exception:
        await db.rollback()
        # A failed commit can have an ambiguous outcome if the connection was
        # lost. Remove the blob only after confirming no row points to it.
        try:
            persisted_key = (await db.execute(
                select(Document.storage_key).where(Document.id == doc_id)
            )).scalar_one_or_none()
            if persisted_key != stored.storage_key:
                storage.delete(stored.storage_key)
        except Exception as cleanup_error:
            logger.warning(
                "Could not confirm document upload cleanup for document %s; preserving storage object %s: %s",
                doc_id,
                stored.storage_key,
                cleanup_error,
            )
        raise
    await db.refresh(locked_doc)
    return locked_doc


@router.post("/{doc_id}/scan", response_model=DocumentRead,
             dependencies=[Depends(require_permission("documents", "edit"))])
async def scan_document_file(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = (await db.execute(
        select(Document)
        .where(Document.id == doc_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "edit")
    if not doc.storage_key or doc.storage_provider != "local":
        raise HTTPException(409, "Document has no locally stored file to scan")
    storage = get_document_storage()
    path = storage.path_for(doc.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Stored document file not found")
    storage_key = doc.storage_key
    doc.file_scan_status = "SCANNING"
    doc.file_scan_result = "Malware scan is in progress; download and approval remain blocked."
    doc.updated_by_id = current_user.id
    await db.commit()

    try:
        result = await scan_document(path)
    except Exception:
        logger.exception("Document malware scan failed for document %s", doc_id)
        result_status = "SCAN_ERROR"
        result_detail = "The malware scan failed; the file remains quarantined."
    else:
        result_status = result.status
        result_detail = result.result

    locked_doc = (await db.execute(
        select(Document)
        .where(Document.id == doc_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not locked_doc:
        raise HTTPException(404, "Document not found")
    if locked_doc.storage_key != storage_key:
        raise HTTPException(409, "The document file changed during scanning; scan the current file again")
    locked_doc.file_scan_status = result_status
    locked_doc.file_scan_result = result_detail
    locked_doc.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(locked_doc)
    return locked_doc


@router.get("/{doc_id}/file", dependencies=[Depends(require_permission("documents", "view"))])
async def download_document_file(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "view")
    if not doc.storage_key or doc.storage_provider != "local":
        raise HTTPException(404, "Stored document file not found")
    if doc.file_scan_status != "CLEAN":
        raise HTTPException(423, "The document is quarantined until a malware scan reports CLEAN")
    path = get_document_storage().path_for(doc.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Stored document file not found")
    return FileResponse(
        path,
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.file_name or "document",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


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
    doc = (await db.execute(
        select(Document)
        .where(Document.id == doc_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    ensure_document_action_allowed(current_user, doc, "approve")
    if doc.status != DocumentStatus.DRAFT:
        raise HTTPException(400, f"Document is already {doc.status.value}")
    if doc.storage_key and doc.file_scan_status != "CLEAN":
        raise HTTPException(409, "A document with an unscanned or infected file cannot be approved")
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
