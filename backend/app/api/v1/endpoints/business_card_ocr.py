"""Business-card text recognition with review and consent (M50.S01.T010). Prefix /api/v1/crm/card-ocr.
Scan (crm.edit): a JPEG/PNG upload is read in memory; only text and suggested fields are kept as the caller's DRAFT.
Confirm (the draft's owner): reviewed fields + explicit consent create a CRM contact. Discard removes the draft."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m50_data_sso import OcrCardDraft
from app.services import card_ocr_service as ocr
from app.services import pat_service as pats

router = APIRouter()
EDIT = Depends(require_any_permission(("crm.edit", "crm.edit_all", "crm.edit_own_scope")))


def _out(d: OcrCardDraft) -> dict:
    return {"id": str(d.id), "status": d.status, "text": d.text, "fields": d.fields, "engine": d.engine,
            "consent_at": d.consent_at.isoformat() if d.consent_at else None, "contact_id": str(d.contact_id) if d.contact_id else None}


async def _mine(db, did: uuid.UUID, user) -> OcrCardDraft:
    d = await db.get(OcrCardDraft, did)
    if d is None or (d.created_by != user.username and not user.is_superuser):
        raise HTTPException(404, "Card not found")
    return d


@router.get("/status", dependencies=[EDIT])
async def engine_status():
    return ocr.status()


@router.post("/scan", status_code=201, dependencies=[EDIT])
async def scan(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    data = await file.read(ocr.MAX_IMAGE_BYTES + 1)
    try:
        d = await ocr.create_draft(db, current_user, data)
    except ocr.OcrError as e:
        raise HTTPException(e.status, str(e))
    pats.audit(db, current_user, "CARD_OCR_SCANNED", "card_ocr", str(d.id), {"lines": d.text.count("\n") + 1})
    await db.commit()
    return _out(d)


@router.get("/drafts", dependencies=[EDIT])
async def drafts(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(OcrCardDraft).where(OcrCardDraft.created_by == current_user.username, OcrCardDraft.status == "DRAFT")
                             .order_by(OcrCardDraft.created_at.desc()).limit(50))).scalars().all()
    return [_out(d) for d in rows]


class ConfirmIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=150)
    company: Optional[str] = Field(None, max_length=200)
    consent: bool = False


@router.post("/{did}/confirm", dependencies=[EDIT])
async def confirm(did: uuid.UUID, body: ConfirmIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    d = await _mine(db, did, current_user)
    try:
        c = await ocr.confirm(db, d, current_user, body.model_dump(exclude={"consent"}), body.consent)
    except ocr.OcrError as e:
        await db.rollback()
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {**_out(d), "contact": {"id": str(c.id), "full_name": c.full_name}}


@router.post("/{did}/discard", dependencies=[EDIT])
async def discard(did: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    d = await _mine(db, did, current_user)
    if d.status != "DRAFT":
        raise HTTPException(409, f"This card is already {d.status.lower()}.")
    d.status, d.text, d.fields = "DISCARDED", "", {}                  # the recognised text is erased with the discard
    pats.audit(db, current_user, "CARD_OCR_DISCARDED", "card_ocr", str(d.id), {})
    await db.commit()
    return _out(d)
