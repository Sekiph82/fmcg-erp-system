"""Marketing asset library (M45.S01.T024 DAM) on top of document management.

Assets are MARKETING_CREATIVE documents: upload, versions, tags, approval and malware scan already exist in
/api/v1/documents. This module adds what e-mail and social need:
- GET /api/v1/marketing-assets            approved, scan-clean images with a public URL (marketing staff);
- GET /api/v1/public/assets/{doc_id}/{sig} the image itself (marketing_assets_public.py), for e-mail clients and social schedulers.
The public URL is signed (HMAC of the document id with SECRET_KEY); archiving or a newer version removes it.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.config import settings
from app.core.deps import get_db
from app.models.documents import Document, DocumentCategory, DocumentStatus

IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view", "marketing.edit", "crm.edit_all")))])


def sign(doc_id: uuid.UUID) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"asset:{doc_id}".encode(), hashlib.sha256).hexdigest()[:32]


def _usable(d: Document | None) -> bool:
    return (d is not None and d.category == DocumentCategory.MARKETING_CREATIVE and d.status == DocumentStatus.APPROVED
            and d.is_latest and d.file_scan_status == "CLEAN" and (d.mime_type or "") in IMAGE_TYPES
            and bool(d.storage_key) and d.storage_provider == "local")


@router.get("")
async def assets(q: str | None = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.category == DocumentCategory.MARKETING_CREATIVE,
                                  Document.status == DocumentStatus.APPROVED, Document.is_latest.is_(True))
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q}%"))
    base = settings.PUBLIC_API_URL.rstrip("/") + "/api/v1/public/assets"
    return [{"id": str(d.id), "title": d.title, "version": d.version, "mime_type": d.mime_type,
             "url": f"{base}/{d.id}/{sign(d.id)}"}
            for d in (await db.execute(stmt.order_by(Document.title).limit(200))).scalars() if _usable(d)]

