"""Conversation intelligence API (M36.S05.T004). Agents see their own; managers see and review all."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.crm import CRMConversationInsight
from app.services import conversation_intel_service as ci

router = APIRouter()


class ReviewIn(BaseModel):
    status: str = Field(pattern="^(REVIEWED|REJECTED)$")
    coaching_note: Optional[str] = Field(None, max_length=3000)


def _out(r: CRMConversationInsight) -> dict:
    return {"id": str(r.id), "source_type": r.source_type, "source_id": str(r.source_id),
            "agent_id": str(r.agent_id) if r.agent_id else None, "findings": r.findings, "counts": r.counts, "engine": r.engine,
            "status": r.status, "coaching_note": r.coaching_note,
            "analysed_at": r.analysed_at.isoformat() if r.analysed_at else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None}


@router.post("/{source_type}/{source_id}/analyse")
async def analyse(source_type: str, source_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        row = await ci.analyse(db, source_type, source_id, current_user)
    except ci.IntelError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return _out(row)


@router.get("")
async def list_insights(status: Optional[str] = Query(None, pattern="^(PENDING_REVIEW|REVIEWED|REJECTED)$"), limit: int = Query(100, ge=1, le=500),
                        db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = ci.visible(select(CRMConversationInsight), current_user)
    if status:
        q = q.where(CRMConversationInsight.status == status)
    rows = (await db.execute(q.order_by(CRMConversationInsight.analysed_at.desc().nullslast()).limit(limit))).scalars().all()
    themes: dict[str, int] = {}
    for r in rows:
        for f in r.findings or []:
            if f.get("kind") == "objection":
                themes[f.get("label", "other")] = themes.get(f.get("label", "other"), 0) + 1
    return {"items": [_out(r) for r in rows], "objections_by_type": themes}


@router.post("/{insight_id}/review")
async def review(insight_id: uuid.UUID, body: ReviewIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        row = await ci.review(db, insight_id, current_user, body.status, body.coaching_note)
    except ci.IntelError as e:
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return _out(row)
