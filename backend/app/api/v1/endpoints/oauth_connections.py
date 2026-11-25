"""Connected accounts (delegated OAuth) — M43.S00.T004. Prefix /api/v1/integrations/oauth.

Each signed-in user connects their own Google or Microsoft mailbox/calendar; nobody sees another user's tokens.
  GET    /providers                       which providers are configured (setup state, no secrets)
  GET    /connections                     the caller's own connections
  POST   /{provider}/{purpose}/start      consent URL (409 NOT_CONFIGURED without a client id/secret)
  GET    /callback                        provider redirect (public; the single-use state is the credential)
  DELETE /connections/{id}                disconnect (revoke at Google, wipe tokens locally)
"""
from __future__ import annotations

import uuid
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.oauth_connection import OAuthConnection
from app.models.user import User
from app.services import oauth_service as oauth

router = APIRouter()


def _fail(e: oauth.OAuthError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail={"code": e.code, "message": str(e)})


@router.get("/providers")
async def providers(current_user: User = Depends(get_current_user)):
    return [{"provider": p, "purposes": sorted({pu for (pp, pu) in oauth.SCOPES if pp == p}),
             "configured": oauth.is_configured(p), "redirect_uri": oauth.redirect_uri()}
            for p in ("google", "microsoft")]


@router.get("/connections")
async def my_connections(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(OAuthConnection).where(OAuthConnection.user_id == current_user.id)
                             .order_by(OAuthConnection.provider, OAuthConnection.purpose))).scalars()
    return [oauth.public_view(c) for c in rows]


@router.post("/{provider}/{purpose}/start")
async def start(provider: str, purpose: str, db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    try:
        url = await oauth.start(db, current_user.id, provider, purpose)
    except oauth.OAuthError as e:
        raise _fail(e) from None
    await db.commit()
    return {"authorize_url": url}


@router.get("/callback")
async def callback(state: str = Query("", max_length=128), code: Optional[str] = Query(None, max_length=4096),
                   error: Optional[str] = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    # mail connections return to the mailbox screen, calendar connections to meetings (both show ConnectedAccounts)
    pages = {"mail": "/dashboard/email", "calendar": "/dashboard/meetings"}
    target = settings.PUBLIC_APP_URL.rstrip("/") + "/dashboard/email"
    try:
        conn = await oauth.complete(db, state=state, code=code, error=error)
        if conn.purpose == "mail":
            from app.services.mail_api_adapters import ensure_mail_account
            await ensure_mail_account(db, conn)
        await db.commit()
        target = settings.PUBLIC_APP_URL.rstrip("/") + pages.get(conn.purpose, "/dashboard/email")
        q = {"oauth": "connected", "provider": conn.provider, "purpose": conn.purpose}
    except oauth.OAuthError as e:
        await db.commit()          # the consumed state stays consumed (no replay)
        q = {"oauth": "error", "reason": e.code}
    return RedirectResponse(f"{target}?{urlencode(q)}", status_code=303)


@router.delete("/connections/{connection_id}", status_code=204)
async def disconnect(connection_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    conn = await db.get(OAuthConnection, connection_id)
    if conn is None or (conn.user_id != current_user.id and not current_user.is_superuser):
        raise HTTPException(404, "Connection not found")
    await oauth.disconnect(db, conn, current_user.id)
    await db.commit()
