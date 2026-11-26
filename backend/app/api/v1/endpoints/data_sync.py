"""No-code data sync and data quality (M45.S01.T011). Prefix /api/v1/data-sync; webhook: /api/v1/public/data-sync.
Define/change syncs: crm.edit_all. Run: the target's edit right (customers: sales.edit; contacts: crm.edit)."""
from __future__ import annotations

import hmac
import json
import secrets
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.data_sync import DataQualitySnapshot, SyncDefinition, SyncRun
from app.services import data_sync_service as dss
from app.services import pat_service as pats

router = APIRouter()
public = APIRouter()


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("crm.edit_all",))):
        raise HTTPException(403, "Only CRM administrators define data syncs.")


def _may_run(u, sync: SyncDefinition):
    if not (u.is_superuser or has_any_permission(u, dss.TARGETS[sync.target]["perm"])):
        raise HTTPException(403, f"You may not change {sync.target}.")


def _out(s: SyncDefinition) -> dict:
    return {"id": str(s.id), "name": s.name, "direction": s.direction, "source_kind": s.source_kind, "source_url": s.source_url,
            "target": s.target, "key_field": s.key_field, "mapping": s.mapping, "conflict_rule": s.conflict_rule,
            "delete_mode": s.delete_mode, "version": s.version, "every_minutes": s.every_minutes, "active": s.active,
            "has_secret": bool(s.secret)}


def _run(r: SyncRun) -> dict:
    return {"id": str(r.id), "version": r.version, "dry_run": r.dry_run, "trigger": r.trigger, "status": r.status, "counts": r.counts,
            "diff": r.diff[:50], "errors": r.errors[:50], "attempts": r.attempts, "started_at": r.started_at.isoformat()}


@router.get("")
async def overview(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    syncs = (await db.execute(select(SyncDefinition).order_by(SyncDefinition.name))).scalars().all()
    runs = (await db.execute(select(SyncRun).order_by(SyncRun.started_at.desc()).limit(30))).scalars().all()
    return {"targets": {k: {"key": v["key"], "fields": v["fields"], "required": v["required"]} for k, v in dss.TARGETS.items()},
            "transforms": sorted(dss.TRANSFORMS), "syncs": [_out(s) for s in syncs], "runs": [_run(r) for r in runs]}


class SyncIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    direction: Literal["IN", "OUT"] = "IN"
    source_kind: Literal["UPLOAD", "HTTP_JSON", "WEBHOOK"]
    source_url: Optional[str] = Field(None, pattern=r"^https?://\S+$", max_length=500)
    secret: Optional[str] = Field(None, max_length=500)
    target: str
    key_field: str
    mapping: list[dict]
    conflict_rule: Literal["source_wins", "target_wins", "skip"] = "source_wins"
    delete_mode: Literal["ignore", "deactivate"] = "ignore"
    every_minutes: Optional[int] = Field(None, ge=15, le=10080)


@router.post("", status_code=201)
async def create(body: SyncIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        dss.validate_mapping(body.target, body.key_field, body.mapping)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    if body.source_kind == "HTTP_JSON" and not body.source_url:
        raise HTTPException(422, "A JSON endpoint sync needs its URL.")
    token = secrets.token_urlsafe(24) if body.source_kind == "WEBHOOK" else None
    s = SyncDefinition(**body.model_dump(exclude={"secret"}), secret=dss.encrypt(token or body.secret), created_by=current_user.username,
                       history=[])
    db.add(s)
    pats.audit(db, current_user, "DATA_SYNC_CREATED", "ds_sync", body.name, {"target": body.target, "direction": body.direction})
    await db.commit()
    return {**_out(s), **({"webhook_token": token, "webhook_url": f"/api/v1/public/data-sync/{s.id}"} if token else {})}


class MappingIn(BaseModel):
    mapping: list[dict]
    conflict_rule: Optional[Literal["source_wins", "target_wins", "skip"]] = None
    delete_mode: Optional[Literal["ignore", "deactivate"]] = None


@router.put("/{sid}/mapping")
async def new_version(sid: uuid.UUID, body: MappingIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    s = await db.get(SyncDefinition, sid)
    if s is None:
        raise HTTPException(404, "Sync not found")
    try:
        dss.validate_mapping(s.target, s.key_field, body.mapping)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    s.history = [*s.history, {"version": s.version, "mapping": s.mapping, "conflict_rule": s.conflict_rule, "delete_mode": s.delete_mode}]
    s.mapping, s.version = body.mapping, s.version + 1
    s.conflict_rule = body.conflict_rule or s.conflict_rule
    s.delete_mode = body.delete_mode or s.delete_mode
    await db.commit()
    return _out(s)


class RunIn(BaseModel):
    dry_run: bool = True
    data: Optional[str] = Field(None, max_length=10_000_000)
    format: Literal["csv", "json"] = "csv"
    full_snapshot: bool = True


@router.post("/{sid}/run")
async def run(sid: uuid.UUID, body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    s = await db.get(SyncDefinition, sid)
    if s is None:
        raise HTTPException(404, "Sync not found")
    _may_run(current_user, s)
    try:
        if s.direction == "OUT":
            r = await dss.run_out(db, s, dry_run=body.dry_run, user=current_user.username)
        else:
            rows = dss.parse_upload(body.data, body.format) if body.data else await dss.pull(s)
            r = await dss.run_in(db, s, rows, dry_run=body.dry_run, user=current_user.username, full_snapshot=body.full_snapshot)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    except ValueError as e:
        raise HTTPException(422, f"Could not read the data: {e}")
    if body.dry_run:
        out = _run(r)
        await db.rollback()           # a dry run never writes, not even its own run record
        return out
    await db.commit()
    return _run(r)


@router.post("/runs/{rid}/rollback")
async def rollback(rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    r = await db.get(SyncRun, rid)
    if r is None:
        raise HTTPException(404, "Run not found")
    _may_run(current_user, await db.get(SyncDefinition, r.sync_id))
    try:
        out = await dss.rollback(db, r, current_user.username)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    pats.audit(db, current_user, "DATA_SYNC_ROLLED_BACK", "ds_run", str(rid), out)
    await db.commit()
    return out


@router.post("/runs/{rid}/replay")
async def replay(rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    r = await db.get(SyncRun, rid)
    if r is None or not r.input:
        raise HTTPException(404, "Nothing to replay")
    s = await db.get(SyncDefinition, r.sync_id)
    _may_run(current_user, s)
    nr = await dss.run_in(db, s, r.input, dry_run=False, user=current_user.username, trigger="REPLAY", full_snapshot=False)
    await db.commit()
    return _run(nr)


@router.get("/quality")
async def quality(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    trend = (await db.execute(select(DataQualitySnapshot).order_by(DataQualitySnapshot.day.desc()).limit(60))).scalars().all()
    return {"now": await dss.quality(db),
            "trend": [{"day": t.day.isoformat(), "entity": t.entity, "score": t.metrics.get("score")} for t in reversed(trend)]}


@public.post("/{sid}")
async def webhook(sid: uuid.UUID, request: Request, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    s = await db.get(SyncDefinition, sid)
    token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    if s is None or s.source_kind != "WEBHOOK" or not s.active or not hmac.compare_digest(token, dss.decrypt(s.secret) or "x" * 40):
        raise HTTPException(401, "Invalid sync or token.")
    try:
        body = await request.json()
        rows = dss.parse_upload(json.dumps(body), "json")
    except (ValueError, dss.SyncError):
        raise HTTPException(422, "Send {\"rows\": [...]} as JSON.")
    r = await dss.run_in(db, s, rows, dry_run=False, user="webhook", trigger="WEBHOOK", full_snapshot=False)
    await db.commit()
    return {"run_id": str(r.id), "counts": r.counts, "errors": r.errors[:20]}
