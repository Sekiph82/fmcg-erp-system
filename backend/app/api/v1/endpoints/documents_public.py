"""Public shared sales documents (no login): /public/documents/{token}. Allow-listed in PUBLIC_ROUTES.
GET only shows the document (mail scanners pre-fetch links); the page posts /view after it renders,
and /decision when the customer accepts or declines (M36.S04.T003)."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
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
        d = await docs.decision_for(db, link.quotation_id)
        # once answered, the signer can always re-open their confirmation (also after a decline)
        doc = await docs.public_document(db, link, any_status=d is not None)
        if d is not None:  # already answered: say so (name only, no e-mail)
            doc["decision"] = {"decision": d.decision, "signer_name": d.signer_name, "decided_at": d.decided_at.isoformat(),
                               "reference": d.evidence_hash[:12].upper()}
            doc["can_decide"] = False
        return doc
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


class SignerCodeIn(BaseModel):
    signer_email: EmailStr


@router.post("/{token}/signer-code")
async def send_signer_code(token: str, body: SignerCodeIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """E-mail a one-time code to the signer — only to an address on file for the quoted customer. The answer (and its
    timing: the e-mail goes out after the response) is the same whether or not the address is on file."""
    import logging

    from app.core.config import settings
    from app.services.email_sender import send_email

    _check(token)
    if not settings.SMTP_HOST and not settings.OTP_DEV_DELIVERY_MODE:
        raise HTTPException(503, "E-mail is not set up yet. Please contact your POVU representative.")
    try:
        link = await docs.resolve(db, token, for_update=True)
        code = await docs.request_signer_code(db, link, str(body.signer_email))
    except docs.LinkGone:
        raise HTTPException(404, GONE)
    except docs.DecisionRefused as e:
        raise HTTPException(429, str(e))
    await db.commit()   # the code exists before it is sent
    if code:
        to = str(body.signer_email)
        if settings.SMTP_HOST:
            def _send() -> None:
                try:
                    send_email(to, "Your code to sign the POVU quotation",
                               f"Your code is {code}. It works for 15 minutes on the quotation page.\n"
                               "If you did not ask for it, you can ignore this e-mail.")
                except Exception:
                    logging.getLogger(__name__).exception("signer code e-mail failed")
            background.add_task(_send)
        else:
            logging.getLogger(__name__).info("[DEV SIGNER CODE] To=%s code=%s (dev mode, not sent)", to, code)
    return {"message": "If this e-mail is on file for your company, a code is on its way. It works for 15 minutes."}


class DecisionIn(BaseModel):
    decision: Literal["ACCEPTED", "DECLINED"]
    signer_name: str = Field(min_length=2, max_length=150, pattern=r"^[^\r\n<>]+$")
    signer_email: EmailStr
    document_hash: str = Field(pattern=r"^[0-9a-f]{64}$", description="document_hash of the version the customer read")
    agree: bool = Field(description="must be true: the signer confirms the statement shown on the page")
    reason: Optional[str] = Field(None, max_length=1000)
    code: str = Field(default="", max_length=6, description="one-time code e-mailed to signer_email (M41.S01.T002)")


@router.post("/{token}/decision")
async def shared_document_decision(token: str, body: DecisionIn, request: Request, db: AsyncSession = Depends(get_db)):
    """The customer accepts or declines with their typed name and e-mail (electronic signature)."""
    _check(token)
    if not body.agree:
        raise HTTPException(422, "Please tick the box to confirm.")
    try:
        link = await docs.resolve(db, token, for_update=True)
        client = request.client.host if request.client else ""
        rec = await docs.decide(db, link, decision=body.decision, signer_name=body.signer_name.strip(),
                                signer_email=str(body.signer_email), seen_hash=body.document_hash, reason=body.reason,
                                code=body.code,
                                viewer=docs.viewer_hash(link.id, client, request.headers.get("user-agent", "")))
    except docs.LinkGone:
        raise HTTPException(404, GONE)
    except docs.DecisionRefused as e:
        raise HTTPException(409, str(e))
    await db.commit()
    return {"decision": rec.decision, "decided_at": rec.decided_at.isoformat(), "reference": rec.evidence_hash[:12].upper()}
