"""No-code data sync and data quality (M45.S01.T011), common registry for all ERP objects (M50.S01.T009).
Prefix /api/v1/data-sync; webhook: /api/v1/public/data-sync.
Define/change syncs: crm.edit_all. Run: the target's edit right (customers: sales.edit; contacts: crm.edit); export (OUT):
the target's broad view right. Sales/purchase order rows only become proposals; a different person with the create right
approves them. Stock and invoices are read-only: inbound is refused. Every mutation is audited."""
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
from app.models.m50_data_sso import SyncConflict, SyncProposal
from app.services import data_sync_service as dss
from app.services import m50_sync as m50
from app.services import m50_sync_registry as reg
from app.services import pat_service as pats

router = APIRouter()
public = APIRouter()


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("crm.edit_all",))):
        raise HTTPException(403, "Only CRM administrators define data syncs.")


def _may_run(u, sync: SyncDefinition):
    spec = dss.TARGETS[sync.target]
    if getattr(sync, "direction", "IN") == "OUT":
        if not (u.is_superuser or has_any_permission(u, (*spec.get("view_perm", ()), *spec["perm"]))):
            raise HTTPException(403, f"You may not export {sync.target}.")
    elif spec.get("mode") == "read_only":
        raise HTTPException(409, dss.read_only_reason(spec, sync.target))
    elif not (u.is_superuser or has_any_permission(u, spec["perm"])):
        raise HTTPException(403, f"You may not change {sync.target}.")
    guarded = {m["target"] for m in sync.mapping} & dss.CONTROLLED_FIELDS
    if guarded and not (u.is_superuser or has_any_permission(u, ("crm.edit_all",))):
        raise HTTPException(403, f"This sync changes {', '.join(sorted(guarded))}: only CRM administrators may run it.")


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
    return {"targets": {k: {"key": v["key"], "fields": v["fields"], "required": v["required"], "mode": v.get("mode", "write"),
                            "depends": reg.DEPENDS.get(k, []), "why": v.get("why"), "adapter": v.get("adapter")}
                        for k, v in dss.TARGETS.items()},
            "order": reg.order(list(dss.TARGETS)),
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
    options: dict = Field(default_factory=dict)       # custom_objects: {"custom_type": key}; associations: {"from": "contact"|"custom:<key>"}


@router.post("", status_code=201)
async def create(body: SyncIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        spec = await m50.spec_for(db, body.target, body.options)
        dss.validate_mapping(body.target, body.key_field, body.mapping, spec, body.direction)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    if body.source_kind == "HTTP_JSON" and not body.source_url:
        raise HTTPException(422, "A JSON endpoint sync needs its URL.")
    token = secrets.token_urlsafe(24) if body.source_kind == "WEBHOOK" else None
    s = SyncDefinition(**body.model_dump(exclude={"secret", "options"}), secret=dss.encrypt(token or body.secret),
                       created_by=current_user.username, history=[])
    db.add(s)
    await db.flush()
    if body.options:
        await m50.set_options(db, s.id, body.options)
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
        spec = await m50.spec_for(db, s.target, await m50.options(db, s))
        dss.validate_mapping(s.target, s.key_field, body.mapping, spec, s.direction)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    s.history = [*s.history, {"version": s.version, "mapping": s.mapping, "conflict_rule": s.conflict_rule, "delete_mode": s.delete_mode}]
    s.mapping, s.version = body.mapping, s.version + 1
    s.conflict_rule = body.conflict_rule or s.conflict_rule
    s.delete_mode = body.delete_mode or s.delete_mode
    pats.audit(db, current_user, "DATA_SYNC_MAPPING_CHANGED", "ds_sync", str(s.id), {"version": s.version})
    await db.commit()
    return _out(s)


class RunIn(BaseModel):
    dry_run: bool = True
    data: Optional[str] = Field(None, max_length=10_000_000)
    format: Literal["csv", "json", "parquet"] = "csv"      # parquet: base64 of the file
    full_snapshot: bool = True


@router.post("/{sid}/run")
async def run(sid: uuid.UUID, body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    s = await db.get(SyncDefinition, sid)
    if s is None:
        raise HTTPException(404, "Sync not found")
    _may_run(current_user, s)
    try:
        if s.direction == "OUT":
            r = await dss.run_out(db, s, dry_run=body.dry_run, user=current_user.username, actor=current_user)
        else:
            rows = dss.parse_upload(body.data, body.format) if body.data else await dss.pull(s)
            r = await dss.run_in(db, s, rows, dry_run=body.dry_run, user=current_user.username, full_snapshot=body.full_snapshot,
                                 actor=current_user)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    except ValueError as e:
        raise HTTPException(422, f"Could not read the data: {e}")
    if body.dry_run:
        out = _run(r)
        await db.rollback()           # a dry run never writes, not even its own run record
        return out
    pats.audit(db, current_user, "DATA_SYNC_RUN", "ds_sync", str(s.id), {"target": s.target, "direction": s.direction,
                                                                         "counts": r.counts, "run": str(r.id)})
    await db.commit()
    return _run(r)


@router.post("/runs/{rid}/rollback")
async def rollback(rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    r = await db.get(SyncRun, rid)
    if r is None:
        raise HTTPException(404, "Run not found")
    _may_run(current_user, await db.get(SyncDefinition, r.sync_id))
    try:
        out = await dss.rollback(db, r, current_user.username, actor=current_user)
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
    try:
        nr = await dss.run_in(db, s, r.input, dry_run=False, user=current_user.username, trigger="REPLAY", full_snapshot=False,
                              actor=current_user)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    pats.audit(db, current_user, "DATA_SYNC_REPLAYED", "ds_run", str(rid), {"counts": nr.counts})
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
    if s is None or s.source_kind != "WEBHOOK" or not s.active or not hmac.compare_digest(token.encode(), (dss.decrypt(s.secret) or "x" * 40).encode()):
        raise HTTPException(401, "Invalid sync or token.")
    try:
        body = await request.json()
        rows = dss.parse_upload(json.dumps(body), "json")
    except (ValueError, dss.SyncError):
        raise HTTPException(422, "Send {\"rows\": [...]} as JSON.")
    try:
        r = await dss.run_in(db, s, rows, dry_run=False, user="webhook", trigger="WEBHOOK", full_snapshot=False)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {"run_id": str(r.id), "counts": r.counts, "errors": r.errors[:20]}


# ── M50.S01.T009: plan, proposals, conflicts, reconciliation ────────────────────────────────────────────────────

@router.get("/plan")
async def plan(targets: str = "", current_user=Depends(get_current_user)):
    """Dependency order for a full synchronisation (dependencies first), with what a sync may do to each target."""
    chosen = [t for t in targets.split(",") if t] or list(dss.TARGETS)
    bad = [t for t in chosen if t not in dss.TARGETS]
    if bad:
        raise HTTPException(422, f"Unknown target(s): {', '.join(bad)}")
    return [{"target": t, "mode": dss.TARGETS[t].get("mode", "write"), "depends": reg.DEPENDS.get(t, []),
             "inbound": dss.TARGETS[t].get("mode", "write") != "read_only"} for t in reg.order(chosen)]


def _prop(p) -> dict:
    return {"id": str(p.id), "sync_id": str(p.sync_id), "target": p.target, "key": p.key, "status": p.status, "payload": p.payload,
            "proposed_by": p.proposed_by, "decided_by": p.decided_by, "applied_ref": p.applied_ref, "error": p.error,
            "created_at": p.created_at.isoformat() if p.created_at else None}


def _may_see(u, target: str):
    spec = dss.TARGETS[target]
    if not (u.is_superuser or has_any_permission(u, (*spec["perm"], *spec.get("view_perm", ())))):
        raise HTTPException(403, f"You may not see {target}.")


@router.get("/proposals")
async def proposals(status: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = select(SyncProposal).order_by(SyncProposal.created_at.desc()).limit(200)
    if status:
        q = q.where(SyncProposal.status == status.upper())
    return [_prop(p) for p in (await db.execute(q)).scalars() if current_user.is_superuser or has_any_permission(
        current_user, (*dss.TARGETS[p.target]["perm"], *dss.TARGETS[p.target].get("view_perm", ())))]


async def _decide(pid: uuid.UUID, approve: bool, db, user):
    p = await db.get(SyncProposal, pid, with_for_update=True)
    if p is None:
        raise HTTPException(404, "Proposal not found")
    await m50.decide(db, p, user, approve)
    pats.audit(db, user, "DATA_SYNC_PROPOSAL_" + ("APPROVED" if approve else "REJECTED"), "ds_proposal", str(pid),
               {"target": p.target, "key": p.key, "status": p.status, "applied_ref": p.applied_ref})
    await db.commit()
    return _prop(p)


@router.post("/proposals/{pid}/approve")
async def approve_proposal(pid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await _decide(pid, True, db, current_user)


@router.post("/proposals/{pid}/reject")
async def reject_proposal(pid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await _decide(pid, False, db, current_user)


@router.get("/conflicts")
async def conflicts(open_only: bool = True, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = select(SyncConflict, SyncDefinition.target).join(SyncDefinition, SyncDefinition.id == SyncConflict.sync_id)
    if open_only:
        q = q.where(SyncConflict.resolution.is_(None))
    out = []
    for c, target in (await db.execute(q.order_by(SyncConflict.created_at.desc()).limit(200))).all():
        if current_user.is_superuser or has_any_permission(current_user, dss.TARGETS[target]["perm"]):
            out.append({"id": str(c.id), "sync_id": str(c.sync_id), "target": target, "key": c.key, "field": c.field,
                        "source_value": c.source_value, "erp_value": c.erp_value, "resolution": c.resolution})
    return out


class ResolveIn(BaseModel):
    resolution: Literal["SOURCE", "ERP"]


@router.post("/conflicts/{cid}/resolve")
async def resolve_conflict(cid: uuid.UUID, body: ResolveIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    c = await db.get(SyncConflict, cid)
    if c is None:
        raise HTTPException(404, "Conflict not found")
    s = await db.get(SyncDefinition, c.sync_id)
    _may_run(current_user, s)
    try:
        out = await m50.resolve_conflict(db, c, s, await m50.spec_for(db, s.target, await m50.options(db, s)), body.resolution, current_user)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    pats.audit(db, current_user, "DATA_SYNC_CONFLICT_RESOLVED", "ds_conflict", str(cid), {"field": c.field, "resolution": body.resolution})
    await db.commit()
    return out


@router.post("/{sid}/reconcile")
async def reconcile(sid: uuid.UUID, body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Compare source rows with the ERP without writing anything."""
    s = await db.get(SyncDefinition, sid)
    if s is None:
        raise HTTPException(404, "Sync not found")
    _may_run(current_user, s)
    try:
        rows = dss.parse_upload(body.data, body.format) if body.data else await dss.pull(s)
        out = await m50.reconcile_rows(db, s, await m50.spec_for(db, s.target, await m50.options(db, s)), rows, current_user)
    except dss.SyncError as e:
        raise HTTPException(e.status, str(e))
    await db.rollback()
    return out


@router.get("/reconcile/stock")
async def reconcile_stock(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _may_see(current_user, "stock")
    return await m50.reconcile_stock(db)


@router.get("/reconcile/invoices")
async def reconcile_invoices(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _may_see(current_user, "invoices")
    return await m50.reconcile_invoices(db)


class ParquetIn(BaseModel):
    data: str = Field(max_length=30_000_000)        # base64 of the .parquet file


@router.post("/parquet/preview")
async def parquet_preview(body: ParquetIn, current_user=Depends(get_current_user)):
    """Schema (typed columns) and the first rows of a Parquet file, so a mapping can be built from it. Nothing is stored."""
    import base64
    from app.services import parquet_service as pqs
    _admin(current_user)
    try:
        rows, info = pqs.read(base64.b64decode(body.data, validate=True))
    except (ValueError, pqs.ParquetError) as e:
        raise HTTPException(422, str(e))
    return {**info, "preview": [{k: dss._jsonable(v) for k, v in r.items()} for r in rows[:20]]}
