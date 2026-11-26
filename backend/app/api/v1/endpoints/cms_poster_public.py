"""M47.S01.T007 public poster frame of a CMS video. Prefix /api/v1/public/cms (no login; allow-listed in PUBLIC_ROUTES).
Same access as the video itself: public media for everyone, gated media for portal members on its list (401/403)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.api.v1.endpoints.cms_public import _media
from app.services import cms_media_service as media

router = APIRouter()


@router.get("/media/{media_id}/poster")
async def poster(media_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    m, _ = await _media(db, media_id, request)
    return FileResponse(media.poster_file(m), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=300" if m.public else "private, no-store", "X-Content-Type-Options": "nosniff"})
