"""Public calendar feed (no login): a personal, revocable token in the URL, used by Google Calendar /
Outlook "subscribe from URL". Allow-listed in PUBLIC_ROUTES (M36.S01.T005)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import meeting_service as svc

router = APIRouter()


@router.get("/{token}.ics")
async def calendar_feed(token: str, db: AsyncSession = Depends(get_db)):
    if not (20 <= len(token) <= 100):
        raise HTTPException(404, "Not found")
    ics = await svc.feed_ics(db, token)
    if ics is None:  # unknown, rotated or revoked link, or an inactive user
        raise HTTPException(404, "Not found")
    return Response(ics, media_type="text/calendar; charset=utf-8",
                    headers={"Cache-Control": "private, max-age=300", "X-Robots-Tag": "noindex"})
