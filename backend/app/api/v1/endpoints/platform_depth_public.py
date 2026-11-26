"""M47.S01.T010 Slack interactivity endpoint (no login; Slack signs every request). Prefix /api/v1/public/slack.

POST /interactions  Slack posts application/x-www-form-urlencoded `payload=<json>` with X-Slack-Request-Timestamp and
X-Slack-Signature (v0 HMAC-SHA256 with the app's signing secret over "v0:{timestamp}:{raw body}", 5-minute window).
Without SLACK_SIGNING_SECRET the endpoint answers 503 NOT_CONFIGURED and does nothing.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import messaging_service as ms

router = APIRouter()


@router.post("/interactions")
async def interactions(request: Request, db: AsyncSession = Depends(get_db)):
    raw = await request.body()
    if len(raw) > 100_000:
        raise HTTPException(413, "Too large")
    try:
        ok = ms.verify_slack(raw, request.headers.get("x-slack-request-timestamp", ""), request.headers.get("x-slack-signature", ""))
    except ms.MessagingError as e:
        raise HTTPException(e.status, str(e)) from None
    if not ok:
        raise HTTPException(401, "Bad signature")
    try:
        payload = json.loads((parse_qs(raw.decode())).get("payload", ["{}"])[0])
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Bad payload") from None
    if payload.get("type") != "block_actions":
        return {"text": "Ignored."}
    text = await ms.slack_interaction(db, payload)
    await db.commit()
    return {"response_type": "ephemeral", "replace_original": False, "text": text}
