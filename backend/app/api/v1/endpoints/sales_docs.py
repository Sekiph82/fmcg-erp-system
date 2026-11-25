"""General sales document library (M45.S01.T013), extending quote share links to catalogues, proposals and sales docs.

Staff (prefix /api/v1/sales-docs, documents.view; sharing needs documents.create or sales.create):
- GET  /                      SALES_DOCUMENT library (latest versions) with share counts
- POST /{doc_id}/share        link (256-bit token, shown once), 1–90 days, optional customer label, pin to this version
- GET  /{doc_id}/links        links with view/download counts; POST /links/{id}/revoke
Public (prefix /api/v1/public/docs):
- GET  /{token}               title, version, file name, size and SHA-256 of the version served
- POST /{token}/view          recorded by the page after it renders (30-minute de-dupe; keyed hash, no IP stored)
- GET  /{token}/file          the file — only APPROVED and malware-scan CLEAN; every download is recorded
Documents still NOT_SCANNED (no ClamAV configured) are never served publicly.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.documents import Document, DocumentCategory, DocumentStatus
from app.models.payments_hub import DocShareEvent, DocShareLink

router = APIRouter(dependencies=[Depends(require_any_permission(("documents.view", "sales.view")))])
public = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


async def _served(db: AsyncSession, link: DocShareLink) -> Optional[Document]:
    """The version a link serves: the pinned one, or the latest APPROVED version of its lineage."""
    d = await db.get(Document, link.document_id)
    if d is None or link.pin_version:
        return d
    lineage = d.lineage_id or d.id
    return (await db.execute(select(Document).where(
        (Document.lineage_id == lineage) | (Document.id == lineage), Document.status == DocumentStatus.APPROVED)
        .order_by(Document.version.desc()))).scalars().first() or d


@router.get("")
async def library(db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(Document).where(Document.category == DocumentCategory.SALES_DOCUMENT, Document.is_latest.is_(True))
                             .order_by(Document.title))).scalars().all()
    counts = dict((await db.execute(select(DocShareLink.document_id, func.count()).group_by(DocShareLink.document_id))).all())
    return [{"id": str(d.id), "title": d.title, "version": d.version, "status": d.status.value, "file_name": d.file_name,
             "scan": d.file_scan_status, "links": counts.get(d.id, 0)} for d in docs]


class ShareIn(BaseModel):
    days: int = Field(14, ge=1, le=90)
    label: Optional[str] = Field(None, max_length=150)
    customer_id: Optional[uuid.UUID] = None
    pin_version: bool = False


@router.post("/{doc_id}/share", status_code=201)
async def share(doc_id: uuid.UUID, body: ShareIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import pat_service as pats
    if not (current_user.is_superuser or has_any_permission(current_user, ("documents.create", "sales.create"))):
        raise HTTPException(403, "You may not share documents.")
    d = await db.get(Document, doc_id)
    if d is None or d.category != DocumentCategory.SALES_DOCUMENT:
        raise HTTPException(404, "Sales document not found")
    if d.status != DocumentStatus.APPROVED:
        raise HTTPException(409, "Only approved documents can be shared.")
    if d.confidentiality_level not in ("PUBLIC", "INTERNAL", "CUSTOMER"):
        raise HTTPException(409, f"A {d.confidentiality_level.lower()} document cannot be shared outside the company.")
    token = secrets.token_urlsafe(32)
    link = DocShareLink(token_hash=_digest(token), document_id=d.id, pin_version=body.pin_version, label=body.label,
                        customer_id=body.customer_id, expires_at=_now() + timedelta(days=body.days), created_by_id=current_user.id)
    db.add(link)
    await db.flush()
    pats.audit(db, current_user, "SALES_DOC_SHARED", "document", str(d.id), {"link": str(link.id), "days": body.days})
    await db.commit()
    return {"id": str(link.id), "url": f"{settings.PUBLIC_APP_URL.rstrip('/')}/docs/{token}", "expires_at": link.expires_at.isoformat()}


@router.get("/{doc_id}/links")
async def links(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DocShareLink).where(DocShareLink.document_id == doc_id).order_by(DocShareLink.created_at.desc()))).scalars().all()
    ev = {(l, k): n for l, k, n in (await db.execute(select(DocShareEvent.link_id, DocShareEvent.kind, func.count())
                                                     .group_by(DocShareEvent.link_id, DocShareEvent.kind))).all()}
    last = dict((await db.execute(select(DocShareEvent.link_id, func.max(DocShareEvent.at)).group_by(DocShareEvent.link_id))).all())
    return [{"id": str(l.id), "label": l.label, "pin_version": l.pin_version, "expires_at": l.expires_at.isoformat(),
             "revoked": l.revoked_at is not None, "views": ev.get((l.id, "VIEW"), 0), "downloads": ev.get((l.id, "DOWNLOAD"), 0),
             "last_activity": last[l.id].isoformat() if l.id in last else None} for l in rows]


@router.post("/links/{lid}/revoke")
async def revoke(lid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, ("documents.create", "sales.create"))):
        raise HTTPException(403, "You may not change shared links.")
    l = await db.get(DocShareLink, lid)
    if l is None:
        raise HTTPException(404, "Link not found")
    l.revoked_at = l.revoked_at or _now()
    await db.commit()
    return {"revoked": True}


async def _resolve(db: AsyncSession, token: str) -> tuple[DocShareLink, Document]:
    link = (await db.execute(select(DocShareLink).where(DocShareLink.token_hash == _digest(token or "")))).scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "This link does not exist.")
    if link.revoked_at is not None or link.expires_at <= _now():
        raise HTTPException(410, "This link has expired or was withdrawn.")
    d = await _served(db, link)
    if d is None or d.status != DocumentStatus.APPROVED:
        raise HTTPException(410, "This document is no longer available.")
    return link, d


def _viewer(link_id, request: Request) -> str:
    raw = f"{link_id}:{request.client.host if request.client else ''}:{request.headers.get('user-agent', '')}"
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()


@public.get("/{token}")
async def meta(token: str, db: AsyncSession = Depends(get_db)):
    link, d = await _resolve(db, token)
    return {"title": d.title, "version": d.version, "file_name": d.file_name, "size_bytes": d.file_size_bytes,
            "sha256": d.file_checksum_sha256, "available": d.file_scan_status == "CLEAN",
            "note": None if d.file_scan_status == "CLEAN" else "The file is being checked for malware and cannot be downloaded yet.",
            "expires_at": link.expires_at.isoformat()}


@public.post("/{token}/view")
async def view(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    link, d = await _resolve(db, token)
    vh = _viewer(link.id, request)
    recent = (await db.execute(select(func.count()).select_from(DocShareEvent).where(
        DocShareEvent.link_id == link.id, DocShareEvent.viewer_hash == vh, DocShareEvent.kind == "VIEW",
        DocShareEvent.at >= _now() - timedelta(minutes=30)))).scalar_one()
    if not recent:
        db.add(DocShareEvent(link_id=link.id, kind="VIEW", viewer_hash=vh, document_id=d.id, at=_now()))
        await db.commit()
    return {"recorded": not recent}


@public.get("/{token}/file")
async def file(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    from app.services.document_storage_service import get_document_storage
    link, d = await _resolve(db, token)
    if d.file_scan_status != "CLEAN" or not d.storage_key or d.storage_provider != "local":
        raise HTTPException(423, "The file is not available: it has not passed the malware scan.")
    path = get_document_storage().path_for(d.storage_key)
    if not path.is_file():
        raise HTTPException(404, "File not found")
    db.add(DocShareEvent(link_id=link.id, kind="DOWNLOAD", viewer_hash=_viewer(link.id, request), document_id=d.id, at=_now()))
    await db.commit()
    return FileResponse(path, media_type=d.mime_type or "application/octet-stream", filename=d.file_name or "document",
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
