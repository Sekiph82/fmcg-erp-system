"""Provider callbacks for calendar change notifications (M49.S01.T002). Prefix /api/v1/public/calendar-hooks; no login
(allow-listed in PUBLIC_ROUTES). Trust comes from the secret the ERP chose when it created the channel / subscription
(Google X-Goog-Channel-Token, Graph clientState), compared in constant time; unknown or mismatching callers get no
information beyond a status code. The answer is immediate; the delta sync runs after the response."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import calendar_webhook_service as hooks

router = APIRouter()
MAX_BODY = 256 * 1024


async def _json(request: Request):
    raw = await request.body()
    if len(raw) > MAX_BODY:
        return None
    try:
        import json
        return json.loads(raw or b"{}")
    except ValueError:
        return None


@router.post("/google")
async def google(request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    status, body, actions = await hooks.handle_google(db, {k.lower(): v for k, v in request.headers.items()})
    await db.commit()
    if actions:
        background.add_task(hooks.run_actions, actions)
    return JSONResponse(body, status_code=status, background=background)


@router.post("/microsoft")
async def microsoft(request: Request, background: BackgroundTasks, validationToken: str | None = None,
                    db: AsyncSession = Depends(get_db)):
    if validationToken is not None:                       # subscription handshake: echo the token as plain text
        return PlainTextResponse(validationToken, status_code=200)
    payload = await _json(request)
    if payload is None:
        return JSONResponse({"detail": "bad request"}, status_code=400)
    status, body, actions = await hooks.handle_graph(db, payload)
    await db.commit()
    if actions:
        background.add_task(hooks.run_actions, actions)
    return JSONResponse(body, status_code=status, background=background)


@router.post("/microsoft/lifecycle")
async def microsoft_lifecycle(request: Request, background: BackgroundTasks, validationToken: str | None = None,
                              db: AsyncSession = Depends(get_db)):
    if validationToken is not None:
        return PlainTextResponse(validationToken, status_code=200)
    payload = await _json(request)
    if payload is None:
        return JSONResponse({"detail": "bad request"}, status_code=400)
    status, body, actions = await hooks.handle_lifecycle(db, payload)
    await db.commit()
    if actions:
        background.add_task(hooks.run_actions, actions)
    return JSONResponse(body, status_code=status, background=background)
