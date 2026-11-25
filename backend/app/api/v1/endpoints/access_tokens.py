"""Personal access tokens and the AI request approval queue (M45.S01.T012/T022). Prefix /api/v1/access-tokens.

- GET/POST /             my tokens / create one (shown once); DELETE /{id} revokes it.
- GET /requests          AI-proposed changes waiting for approval (MCP clients, agents).
- POST /requests/{id}/{approve|reject}  a person other than the requester decides; approving executes it.
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.ai_hub import AIActionRequest, PersonalAccessToken
from app.services import pat_service as pats

router = APIRouter()


class TokenIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[Literal["crm.addin", "mcp.read", "mcp.write"]] = Field(min_length=1)
    days: int = Field(90, ge=1, le=365)


@router.get("")
async def mine(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(PersonalAccessToken).where(PersonalAccessToken.user_id == current_user.id)
                             .order_by(PersonalAccessToken.created_at.desc()))).scalars()
    return {"scopes": pats.SCOPES, "tokens": [pats.out(t) for t in rows]}


@router.post("", status_code=201)
async def create(body: TokenIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    t, token = await pats.create(db, current_user.id, body.name, list(body.scopes), body.days)
    pats.audit(db, current_user, "ACCESS_TOKEN_CREATED", "personal_access_token", str(t.id), {"scopes": t.scopes})
    await db.commit()
    return {**pats.out(t), "token": token}


@router.delete("/{tid}")
async def revoke(tid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    t = await db.get(PersonalAccessToken, tid)
    if t is None or (t.user_id != current_user.id and not current_user.is_superuser):
        raise HTTPException(404, "Token not found")
    if t.revoked_at is None:
        t.revoked_at = pats.now()
        pats.audit(db, current_user, "ACCESS_TOKEN_REVOKED", "personal_access_token", str(t.id), {})
    await db.commit()
    return pats.out(t)


def _out(r: AIActionRequest) -> dict:
    return {"id": str(r.id), "source": r.source, "action": r.action, "summary": r.summary, "arguments": r.arguments,
            "status": r.status, "requested_by": str(r.requested_by) if r.requested_by else None,
            "decided_by": r.decided_by, "result": r.result, "created_at": r.created_at.isoformat()}


@router.get("/requests")
async def requests(status: str = "PENDING", db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    stmt = select(AIActionRequest).where(AIActionRequest.status == status)
    if not (current_user.is_superuser or has_any_permission(current_user, ("crm.edit_all",))):
        stmt = stmt.where(AIActionRequest.requested_by == current_user.id)
    return [_out(r) for r in (await db.execute(stmt.order_by(AIActionRequest.created_at.desc()).limit(200))).scalars()]


@router.post("/requests/{rid}/{action}")
async def decide(rid: uuid.UUID, action: Literal["approve", "reject"], db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, ("crm.edit_all",))):
        raise HTTPException(403, "Only CRM administrators approve AI requests.")
    r = await db.get(AIActionRequest, rid)
    if r is None:
        raise HTTPException(404, "Request not found")
    try:
        await pats.decide(db, r, current_user, action == "approve")
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    await db.commit()
    return _out(r)
