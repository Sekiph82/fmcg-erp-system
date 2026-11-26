"""Custom objects and associations (M45.S01.T015). Prefix /api/v1/custom-objects."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.custom_objects import CustomObjectAssociation, CustomObjectRecord, CustomObjectType
from app.services import custom_object_service as cos
from app.services import pat_service as pats

router = APIRouter(dependencies=[Depends(require_any_permission(cos.VIEW))])


def _fail(e: cos.COError):
    raise HTTPException(e.status, str(e))


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, cos.ADMIN)):
        raise HTTPException(403, "Only CRM administrators define object types.")


def _type_out(t: CustomObjectType) -> dict:
    return {"id": str(t.id), "key": t.key, "label": t.label, "label_plural": t.label_plural, "fields": t.fields,
            "display_field": t.display_field, "view_roles": t.view_roles, "edit_roles": t.edit_roles}


def _rec_out(r: CustomObjectRecord, rules: Optional[dict] = None) -> dict:
    out = {"id": str(r.id), "display": r.display, "data": r.data, "company_id": str(r.company_id) if r.company_id else None,
            "created_by": r.created_by, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}
    if rules:                                  # M47.S01.T010 hidden fields leave the response
        from app.services import sensitive_service as sens
        out["data"] = dict(out["data"])
        sens.strip_hidden(out, rules)
    return out


async def _rules(db, t: CustomObjectType, u) -> dict:
    from app.services import sensitive_service as sens
    return await sens.field_rules(db, f"co:{t.key}", u)


@router.get("/types")
async def types(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return [_type_out(t) for t in (await db.execute(select(CustomObjectType).order_by(CustomObjectType.label))).scalars()
            if cos.can(current_user, t, False)]


@router.post("/types", status_code=201)
async def create_type(body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        v = cos.validate_type(body)
    except cos.COError as e:
        _fail(e)
    if (await db.execute(select(CustomObjectType.id).where(CustomObjectType.key == v["key"]))).first():
        raise HTTPException(409, "An object type with this key exists.")
    t = CustomObjectType(**v, created_by=current_user.username)
    db.add(t)
    pats.audit(db, current_user, "CUSTOM_OBJECT_TYPE_CREATED", "co_type", v["key"], {"fields": [f["key"] for f in v["fields"]]})
    await db.commit()
    return _type_out(t)


@router.put("/types/{key}")
async def update_type(key: str, body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Change labels, fields and roles. Removing a field keeps old values in records but hides them."""
    _admin(current_user)
    t = (await db.execute(select(CustomObjectType).where(CustomObjectType.key == key))).scalar_one_or_none()
    if t is None:
        raise HTTPException(404, "Object type not found")
    try:
        v = cos.validate_type({**body, "key": key})
    except cos.COError as e:
        _fail(e)
    for k, val in v.items():
        setattr(t, k, val)
    pats.audit(db, current_user, "CUSTOM_OBJECT_TYPE_CHANGED", "co_type", key, {})
    await db.commit()
    return _type_out(t)


@router.delete("/types/{key}")
async def delete_type(key: str, force: bool = False, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    t = (await db.execute(select(CustomObjectType).where(CustomObjectType.key == key))).scalar_one_or_none()
    if t is None:
        raise HTTPException(404, "Object type not found")
    n = (await db.execute(select(func.count()).select_from(CustomObjectRecord).where(CustomObjectRecord.type_id == t.id))).scalar_one()
    if n and not force:
        raise HTTPException(409, f"{n} records exist; delete with force=true to remove them and their associations.")
    await db.delete(t)
    pats.audit(db, current_user, "CUSTOM_OBJECT_TYPE_DELETED", "co_type", key, {"records": n})
    await db.commit()
    return {"deleted": True, "records": n}


@router.get("/linked/{target_type}/{target_id}")
async def linked(target_type: str, target_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await cos.records_for(db, target_type, target_id, current_user)


@router.get("/{key}/records")
async def records(key: str, q: Optional[str] = Query(None, max_length=100), limit: int = Query(100, ge=1, le=500),
                  db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user)
    except cos.COError as e:
        _fail(e)
    stmt = select(CustomObjectRecord).where(CustomObjectRecord.type_id == t.id)
    if q:
        stmt = stmt.where(CustomObjectRecord.display.ilike(f"%{q}%"))
    rows = (await db.execute(cos.visible(stmt, current_user).order_by(CustomObjectRecord.display).limit(limit))).scalars()
    rules = await _rules(db, t, current_user)
    return {"type": _type_out(t), "records": [_rec_out(r, rules) for r in rows]}


class RecordIn(BaseModel):
    data: dict
    company_id: Optional[uuid.UUID] = None


@router.post("/{key}/records", status_code=201)
async def create_record(key: str, body: RecordIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
        r = await cos.upsert(db, t, body.data, current_user, company_id=body.company_id)
    except cos.COError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    return _rec_out(r, await _rules(db, t, current_user))


@router.get("/{key}/records/{rid}")
async def get_record(key: str, rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user)
        r = await cos.get_record(db, t, rid, current_user)
    except cos.COError as e:
        _fail(e)
    assoc = (await db.execute(select(CustomObjectAssociation).where(CustomObjectAssociation.record_id == r.id))).scalars()
    return {**_rec_out(r, await _rules(db, t, current_user)), "associations": [{"id": str(a.id), "target_type": a.target_type, "target_id": str(a.target_id),
                                             "label": a.label} for a in assoc]}


@router.put("/{key}/records/{rid}")
async def update_record(key: str, rid: uuid.UUID, body: RecordIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
        r = await cos.get_record(db, t, rid, current_user)
        await cos.upsert(db, t, body.data, current_user, record=r)
    except cos.COError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    await db.refresh(r)
    return _rec_out(r, await _rules(db, t, current_user))


@router.delete("/{key}/records/{rid}")
async def delete_record(key: str, rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
        r = await cos.get_record(db, t, rid, current_user)
    except cos.COError as e:
        _fail(e)
    await db.delete(r)                         # associations go with it (ON DELETE CASCADE)
    pats.audit(db, current_user, "CUSTOM_OBJECT_DELETED", "co_record", str(rid), {"type": key, "display": r.display})
    await db.commit()
    return {"deleted": True}


class AssocIn(BaseModel):
    target_type: str
    target_id: uuid.UUID
    label: str = Field("related", max_length=40)


@router.post("/{key}/records/{rid}/associations", status_code=201)
async def add_assoc(key: str, rid: uuid.UUID, body: AssocIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
        r = await cos.get_record(db, t, rid, current_user)
        await cos.associate(db, r, body.target_type, body.target_id, body.label)
    except cos.COError as e:
        _fail(e)
    await db.commit()
    return {"ok": True}


@router.delete("/{key}/records/{rid}/associations/{aid}")
async def remove_assoc(key: str, rid: uuid.UUID, aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
        r = await cos.get_record(db, t, rid, current_user)
    except cos.COError as e:
        _fail(e)
    a = await db.get(CustomObjectAssociation, aid)
    if a is None or a.record_id != r.id:
        raise HTTPException(404, "Association not found")
    await db.delete(a)
    await db.commit()
    return {"deleted": True}


@router.get("/{key}/export.csv", response_class=PlainTextResponse)
async def export(key: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user)
    except cos.COError as e:
        _fail(e)
    rows = list((await db.execute(cos.visible(select(CustomObjectRecord).where(CustomObjectRecord.type_id == t.id), current_user)
                                  .order_by(CustomObjectRecord.display))).scalars())
    hidden = {k for k, a in (await _rules(db, t, current_user)).items() if a == "HIDDEN"}
    if hidden:                                 # M47.S01.T010: hidden columns are not exported
        from types import SimpleNamespace
        t = SimpleNamespace(fields=[f for f in t.fields if f["key"] not in hidden])
        rows = [SimpleNamespace(id=r.id, data={k: v for k, v in r.data.items() if k not in hidden}) for r in rows]
    return PlainTextResponse(cos.export_csv(t, rows), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{key}.csv"'})


class ImportIn(BaseModel):
    csv: str = Field(min_length=1, max_length=5_000_000)


@router.post("/{key}/import")
async def import_(key: str, body: ImportIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user, write=True)
    except cos.COError as e:
        _fail(e)
    out = await cos.import_csv(db, t, body.csv, current_user)
    await db.commit()
    return out


@router.get("/{key}/report")
async def report(key: str, group_by: str, metric: Optional[str] = None, db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    try:
        t = await cos.get_type(db, key, current_user)
        if (await _rules(db, t, current_user)).get(group_by) == "HIDDEN" or (metric and (await _rules(db, t, current_user)).get(metric) == "HIDDEN"):
            raise HTTPException(403, "This field is hidden for your role.")
        return await cos.report(db, t, current_user, group_by, metric)
    except cos.COError as e:
        _fail(e)
