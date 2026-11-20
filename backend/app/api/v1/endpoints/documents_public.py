"""Public shared sales documents (no login): /public/documents/{token}. Allow-listed in PUBLIC_ROUTES.
GET only shows the document (mail scanners pre-fetch links); the page posts /view after it renders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_document_service as docs

router = APIRouter()
GONE = "This link is not available. Ask your POVU contact for a new one."


def _check(token: str) -> None:
    if not (20 <= len(token) <= 64):
        raise HTTPException(404, GONE)


@router.get("/{token}")
async def shared_document(token: str, db: AsyncSession = Depends(get_db)):
    _check(token)
    try:
        link = await docs.resolve(db, token)
        return await docs.public_document(db, link)
    except docs.LinkGone:
        raise HTTPException(404, GONE)


@router.post("/{token}/view")
async def shared_document_viewed(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check(token)
    try:
        link = await docs.resolve(db, token, for_update=True)
    except docs.LinkGone:
        raise HTTPException(404, GONE)
    client = request.client.host if request.client else ""
    counted = await docs.record_view(db, link, docs.viewer_hash(link.id, client, request.headers.get("user-agent", "")))
    await db.commit()
    return {"recorded": counted}
