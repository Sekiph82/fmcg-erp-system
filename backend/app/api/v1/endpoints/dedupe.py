"""Duplicate review and merge for customers and contacts (M45.S01.T010). Prefix /api/v1/dedupe.
View: crm.view_all / crm.edit_all. Merge, dismiss and undo: crm.edit_all."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.customer_data import MergeLog
from app.services import dedupe_service as dd

router = APIRouter(dependencies=[Depends(require_any_permission(("crm.view_all", "crm.edit_all")))])
Entity = Literal["customer", "contact"]


def _edit(u):
    if not (u.is_superuser or has_any_permission(u, ("crm.edit_all",))):
        raise HTTPException(403, "Only CRM administrators merge records.")


@router.get("/candidates")
async def candidates(entity: Entity = "customer", threshold: float = Query(0.7, ge=0.4, le=1.0), db: AsyncSession = Depends(get_db)):
    return await dd.candidates(db, entity, threshold)


class PairIn(BaseModel):
    entity: Entity
    survivor_id: uuid.UUID
    merged_id: uuid.UUID
    reason: str = Field("", max_length=300)


@router.post("/preview")
async def preview(body: PairIn, db: AsyncSession = Depends(get_db)):
    try:
        return await dd.preview(db, body.entity, body.survivor_id, body.merged_id)
    except dd.MergeError as e:
        raise HTTPException(e.status, str(e))


@router.post("/merge")
async def merge(body: PairIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    try:
        log = await dd.merge(db, body.entity, body.survivor_id, body.merged_id, current_user, body.reason)
    except dd.MergeError as e:
        await db.rollback()
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {"merge_id": str(log.id), "moved": log.moved, "changes": log.field_changes,
            "removed_duplicates": len(log.snapshot.get("removed", []))}


@router.post("/dismiss")
async def dismiss(body: PairIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    await dd.dismiss(db, body.entity, body.survivor_id, body.merged_id, current_user.username)
    await db.commit()
    return {"ok": True}


@router.get("/merges")
async def merges(db: AsyncSession = Depends(get_db)):
    return [{"id": str(m.id), "entity": m.entity, "survivor_id": str(m.survivor_id), "merged_id": str(m.merged_id),
             "merged_by": m.merged_by, "merged_at": m.merged_at.isoformat(), "reason": m.reason,
             "moved": [{"table": x["table"], "rows": len(x["ids"])} for x in m.moved], "undone_by": m.undone_by}
            for m in (await db.execute(select(MergeLog).order_by(MergeLog.merged_at.desc()).limit(100))).scalars()]


@router.post("/merges/{mid}/undo")
async def undo(mid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    try:
        await dd.undo(db, mid, current_user)
    except dd.MergeError as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {"ok": True}
