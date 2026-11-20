"""Public shared sales documents (no login): /public/documents/{token}. Allow-listed in PUBLIC_ROUTES.
GET only shows the document (mail scanners pre-fetch links); the page posts /view after it renders,
and /decision when the customer accepts or declines (M36.S04.T003)."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
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


class DecisionIn(BaseModel):
    decision: Literal["ACCEPTED", "DECLINED"]
    signer_name: str = Field(min_length=2, max_length=150, pattern=r"^[^\r\n<>]+$")
    signer_email: EmailStr
    document_hash: str = Field(pattern=r"^[0-9a-f]{64}$", description="document_hash of the version the customer read")
    agree: bool = Field(description="must be true: the signer confirms the statement shown on the page")
    reason: Optional[str] = Field(None, max_length=1000)


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
                                viewer=docs.viewer_hash(link.id, client, request.headers.get("user-agent", "")))
    except docs.LinkGone:
        raise HTTPException(404, GONE)
    except docs.DecisionRefused as e:
        raise HTTPException(409, str(e))
    await db.commit()
    return {"decision": rec.decision, "decided_at": rec.decided_at.isoformat(), "reference": rec.evidence_hash[:12].upper()}
