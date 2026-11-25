"""Sensitive-data classification (M45.S01.T017). Prefix /api/v1/sensitive-data.
Classify: superuser or roles.manage. Reveal: data.view_sensitive (audited)."""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.services import pat_service as pats
from app.services import sensitive_service as sens

router = APIRouter()


@router.get("/policy")
async def policy(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    pol = await sens.policy(db)
    from sqlalchemy import select
    from app.models.customer_data import SensitiveField
    ret = {(r.entity, r.field): r.retention_days for r in (await db.execute(select(SensitiveField))).scalars()}
    return {"can_view": sens.can_view(current_user),
            "fields": [{"entity": e, "field": f, "sensitive": f in pol[e], "retention_days": ret.get((e, f))}
                       for e, fs in sens.CLASSIFIABLE.items() for f in fs]}


class FieldIn(BaseModel):
    entity: Literal["customer", "contact"]
    field: str = Field(max_length=40)
    sensitive: bool
    retention_days: Optional[int] = Field(None, ge=30, le=3650)


@router.put("/policy")
async def set_policy(body: FieldIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, ("roles.manage",))):
        raise HTTPException(403, "Only administrators classify fields.")
    try:
        await sens.set_field(db, body.entity, body.field, body.sensitive, body.retention_days, current_user.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    pats.audit(db, current_user, "SENSITIVE_POLICY_CHANGED", body.entity, body.field, body.model_dump())
    await db.commit()
    return {"ok": True}


class RevealIn(BaseModel):
    entity: Literal["customer", "contact"]
    record_id: uuid.UUID
    field: str = Field(max_length=40)


@router.post("/reveal")
async def reveal(body: RevealIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        v = await sens.reveal(db, current_user, body.entity, body.record_id, body.field)
    except PermissionError as e:
        await db.commit()                      # keep the refused attempt in the audit log
        raise HTTPException(403, str(e))
    except (ValueError, LookupError) as e:
        raise HTTPException(404, str(e))
    await db.commit()
    return {"value": v}
