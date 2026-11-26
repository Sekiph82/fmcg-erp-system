"""Signed TikTok Content Posting webhooks (M48.S01.T005). Prefix /public/social/tiktok (no login; PUBLIC_ROUTES).

TikTok-Signature: t=<unix>,s=HMAC-SHA256(TIKTOK_CLIENT_SECRET, "<t>.<raw body>") — https://developers.tiktok.com/doc/webhooks-verification.
Fail closed without TIKTOK_CLIENT_SECRET; stale timestamps (> 5 min) and replayed deliveries are refused / ignored.
A post.publish.* event never marks a post PUBLISHED by itself: it triggers a status fetch, which decides."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import social_service as ss

router = APIRouter()


@router.post("")
async def receive(request: Request, db: AsyncSession = Depends(get_db)):
    raw = await request.body()
    try:
        sig = ss.verify_tiktok(raw, request.headers.get("TikTok-Signature", ""))
    except ss.SocialError as e:
        raise HTTPException(503 if str(e) == "not configured" else 403, "Webhook not accepted") from None
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Invalid JSON") from None
    res = await ss.ingest_tiktok(db, payload if isinstance(payload, dict) else {}, sig)
    await db.commit()
    return res
