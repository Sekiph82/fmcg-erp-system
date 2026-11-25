"""Public e-mail tracking endpoints (M43.S01.T006). Prefix /api/v1/public/t; allow-listed in PUBLIC_ROUTES.

/o/{token}.gif  open pixel (always the same 1×1 GIF, never an error page)
/c/{token}      click: 302 only to a link stored with that message at send time (no open redirect)
/optout         recipient stops tracking (signed unsubscribe token from the e-mail footer)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_engagement_service as engagement
from app.services import crm_outbound_service as outbound
from app.services.crm_lead_capture_service import ip_hash

router = APIRouter()
NO_STORE = {"Cache-Control": "no-store, private", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}


def _client(request: Request) -> tuple[str, str | None]:
    return (request.headers.get("user-agent", "")[:300], ip_hash(request.client.host if request.client else None))


@router.get("/o/{token}.gif")
async def open_pixel(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    ua, ih = _client(request)
    try:
        await engagement.record(db, token, "OPEN", ua, ih)
        await db.commit()
    except Exception:            # tracking must never break the recipient's mail client
        await db.rollback()
    return Response(engagement.PIXEL, media_type="image/gif", headers=NO_STORE)


@router.get("/c/{token}")
async def click(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    ua, ih = _client(request)
    target = await engagement.record(db, token, "CLICK", ua, ih)
    await db.commit()
    if not target:
        raise HTTPException(404, "This link is not available.")
    return RedirectResponse(target, status_code=302, headers=NO_STORE)


@router.post("/optout")
async def tracking_optout(t: str = Query(..., max_length=600), db: AsyncSession = Depends(get_db)):
    email = outbound.email_from_token(t)
    if not email:
        raise HTTPException(404, "This link is not valid.")
    await engagement.opt_out(db, email)
    await db.commit()
    return {"tracking": "off"}
