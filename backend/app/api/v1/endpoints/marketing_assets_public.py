"""Public marketing asset images (M45.S01.T024 DAM): /api/v1/public/assets/{doc_id}/{sig}. Signed URL; only approved,
latest, scan-clean MARKETING_CREATIVE images are served."""
from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.marketing_assets import _usable, sign
from app.core.deps import get_db
from app.models.documents import Document
from app.services.document_storage_service import get_document_storage

router = APIRouter()


@router.get("/{doc_id}/{sig}")
async def public_asset(doc_id: uuid.UUID, sig: str, db: AsyncSession = Depends(get_db)):
    d = await db.get(Document, doc_id)
    if not hmac.compare_digest(sig, sign(doc_id)) or not _usable(d):
        raise HTTPException(404, "Not found")
    path = get_document_storage().path_for(d.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type=d.mime_type,
                        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "default-src 'none'"})
