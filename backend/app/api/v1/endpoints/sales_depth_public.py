"""M47.S01.T009 public 1-to-1 video page: /api/v1/public/video. The token is the only credential; it serves only its
own video, stops at expiry or revocation, and every view is recorded (30-minute de-dupe)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services import cms_media_service as media
from app.services import video_message_service as vms

router = APIRouter()


@router.get("/{token}")
async def meta(token: str, db: AsyncSession = Depends(get_db)):
    vm, m = await vms.resolve(db, token)
    return {"title": vm.title, "contact_name": vm.contact_name, "mime": m.mime, "expires_at": vm.expires_at.isoformat()}


class ViewIn(BaseModel):
    seconds: int = Field(0, ge=0, le=86400)


@router.post("/{token}/view")
async def view(token: str, request: Request, body: ViewIn = ViewIn(), db: AsyncSession = Depends(get_db)):
    vm, _ = await vms.resolve(db, token)
    recorded = await vms.record_view(db, vm, request, body.seconds)
    await db.commit()
    return {"recorded": recorded}


@router.get("/{token}/file")
async def file(token: str, db: AsyncSession = Depends(get_db)):
    _, m = await vms.resolve(db, token)
    return FileResponse(media.file_path(m), media_type=m.mime,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
