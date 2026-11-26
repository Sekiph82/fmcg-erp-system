"""Website analytics reports for staff (M44.S01.T009). Prefix /api/v1/web-analytics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.services import web_analytics_service as wa

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])


@router.get("/summary")
async def summary(days: int = Query(30, ge=1, le=400), db: AsyncSession = Depends(get_db)):
    return await wa.summary(db, days)


@router.get("/funnel")
async def funnel(steps: str = Query(..., max_length=1000), days: int = Query(30, ge=1, le=400),
                 db: AsyncSession = Depends(get_db)):
    parts = [s.strip() for s in steps.split(",") if s.strip()][:8]
    if len(parts) < 2:
        raise HTTPException(422, "Give at least two steps (page paths like /pricing or events like CTA:demo).")
    return await wa.funnel(db, parts, days)


@router.get("/journey")
async def journey(email: str = Query(..., min_length=3, max_length=254), db: AsyncSession = Depends(get_db)):
    return await wa.journey(db, email)


@router.get("/deal-journey/{record_id}")
async def deal_journey(record_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await wa.deal_journey(db, record_id)


@router.post("/purge-expired")
async def purge(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, "Administrators only.")
    n = await wa.purge_expired(db)
    await db.commit()
    return {"deleted_events": n}


# ── M47.S01.T008 custom event definitions ───────────────────────────────────────

class DefinitionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    properties: dict[str, str] = Field(default_factory=dict)
    active: bool = True


def _def_out(d) -> dict:
    return {"id": str(d.id), "name": d.name, "description": d.description, "properties": d.properties,
            "active": d.active, "updated_at": (d.updated_at or d.created_at).isoformat() if (d.updated_at or d.created_at) else None}


def _writer(user) -> None:
    if not (user.is_superuser or has_any_permission(user, WRITE)):
        raise HTTPException(403, "Marketing or CRM editors only.")


@router.get("/event-definitions")
async def list_definitions(db: AsyncSession = Depends(get_db)):
    from app.models.m47_automation import WebEventDefinition
    return [_def_out(d) for d in (await db.execute(select(WebEventDefinition).order_by(WebEventDefinition.name))).scalars()]


async def _save_definition(db: AsyncSession, body: DefinitionIn, user, d=None) -> dict:
    from app.models.audit_log import AuditLog
    from app.models.m47_automation import WebEventDefinition
    _writer(user)
    try:
        name, props = wa.validate_definition(body.name, body.properties)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    if d is None:
        d = WebEventDefinition(name=name, created_by=user.username)
        db.add(d)
    d.name, d.description, d.properties, d.active = name, (body.description or None), props, body.active
    d.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=user.id, actor_email=getattr(user, "email", None), actor_name=getattr(user, "full_name", None),
                    event_type="web_event_definition.saved", module="marketing", target_type="web_event_definition",
                    target_id=name, details={"properties": props, "active": body.active}))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "An event with this name is already defined.") from None
    await db.refresh(d)
    return _def_out(d)


@router.post("/event-definitions", status_code=201)
async def create_definition(body: DefinitionIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _save_definition(db, body, user)


@router.put("/event-definitions/{definition_id}")
async def update_definition(definition_id: uuid.UUID, body: DefinitionIn, db: AsyncSession = Depends(get_db),
                            user=Depends(get_current_user)):
    from app.models.m47_automation import WebEventDefinition
    d = await db.get(WebEventDefinition, definition_id)
    if d is None:
        raise HTTPException(404, "Definition not found")
    return await _save_definition(db, body, user, d)


# ── M47.S01.T011 event tags: CSS selector → defined custom event, applied by povu-analytics.js ────────────────

class TagIn(BaseModel):
    selector: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=100)


@router.get("/tags")
async def tags(db: AsyncSession = Depends(get_db)):
    return await wa.event_tags(db)


@router.put("/tags")
async def save_tags(body: list[TagIn], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, WRITE)):
        raise HTTPException(403, "Editing event tags needs marketing edit rights.")
    try:
        out = await wa.save_event_tags(db, [t.model_dump() for t in body[:100]], user.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    await db.commit()
    return out
