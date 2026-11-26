"""M48.S01.T009 public e-signature provider callbacks. Prefix /api/v1/public/esign (no login; allow-listed in
PUBLIC_ROUTES and skipped by the input sanitizer because the raw body is what DocuSign signs).

- POST /docusign: DocuSign Connect JSON, X-DocuSign-Signature-N = base64 HMAC-SHA256 of the raw body (constant-time
  check), replay-protected by (envelopeId, event, generatedDateTime) and a 7-day age window.
- GET/POST /adobe-sign: Acrobat Sign verification of intent and notifications; X-AdobeSign-ClientId must be our
  application id and is echoed back; replay-protected by webhookNotificationId.
Both only trigger a status read-back from the provider API with our credentials; payload statuses are never trusted.
"""
from __future__ import annotations

import hmac
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services import esign_provider_service as esp

router = APIRouter()


@router.post("/docusign")
async def docusign_connect(request: Request, db: AsyncSession = Depends(get_db)):
    code, out = await esp.docusign_connect(db, await request.body(), request.headers)
    return JSONResponse(out, code)


@router.get("/adobe-sign")
async def adobe_sign_verify(db: AsyncSession = Depends(get_db), x_adobesign_clientid: Optional[str] = Header(None)):
    ours = await esp.adobe_client_id(db)
    if not ours or not x_adobesign_clientid or not hmac.compare_digest(x_adobesign_clientid.encode(), ours.encode()):
        return JSONResponse({"detail": "Unknown client id."}, 401)
    return JSONResponse({"xAdobeSignClientId": ours}, 200, headers={"X-AdobeSign-ClientId": ours})


@router.post("/adobe-sign")
async def adobe_sign_notify(request: Request, db: AsyncSession = Depends(get_db),
                            x_adobesign_clientid: Optional[str] = Header(None)):
    code, out = await esp.adobe_webhook(db, await request.body(), x_adobesign_clientid)
    if code != 200:
        return JSONResponse(out, code)
    return JSONResponse({**out, "xAdobeSignClientId": x_adobesign_clientid}, 200,
                        headers={"X-AdobeSign-ClientId": x_adobesign_clientid})
