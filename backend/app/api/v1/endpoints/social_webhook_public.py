"""Signed Meta webhooks for social listening (M44.S01.T008). Prefix /public/social/meta.
Fail closed: without META_APP_SECRET / META_WEBHOOK_VERIFY_TOKEN nothing is accepted."""
from __future__ import annotations

import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services import social_service as ss

router = APIRouter()


@router.get("")
async def verify(request: Request):
    p = request.query_params
    token = settings.META_WEBHOOK_VERIFY_TOKEN
    if not token or p.get("hub.mode") != "subscribe" or not hmac.compare_digest(p.get("hub.verify_token", ""), token):
        raise HTTPException(403, "Verification failed")
    return Response(p.get("hub.challenge", ""), media_type="text/plain")


@router.post("")
async def receive(request: Request, db: AsyncSession = Depends(get_db)):
    raw = await request.body()
    try:
        ss.verify_meta(raw, request.headers.get("X-Hub-Signature-256", ""))
    except ss.SocialError as e:
        raise HTTPException(503 if str(e) == "not configured" else 403, "Webhook not accepted") from None
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Invalid JSON") from None
    res = await ss.ingest_meta(db, payload)
    await db.commit()
    return res
