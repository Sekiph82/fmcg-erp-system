"""Customer data hub (M45.S01.T001–T003): sources, prospecting, research, enrichment, business cards.
Prefix /api/v1/customer-data. View: crm.view; import/apply: crm.edit_all; outreach proposals: crm.edit."""
from __future__ import annotations

import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.customer_data import DataSource, ProspectRun
from app.services import customer_data_service as cds
from app.services import pat_service as pats

router = APIRouter(dependencies=[Depends(require_any_permission(("crm.view", "crm.view_all", "crm.edit_all")))])


def _can(u, *perms):
    if not (u.is_superuser or has_any_permission(u, perms)):
        raise HTTPException(403, f"Needs {' or '.join(perms)}.")


def _fail(e: cds.DataError):
    raise HTTPException(e.status, str(e))


@router.get("/provider")
async def provider():
    return cds.provider_status()


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    license_note: str = Field(min_length=3, max_length=500)
    mapping: dict[str, str]
    rows: Optional[list[dict]] = None
    csv: Optional[str] = Field(None, max_length=5_000_000)
    retention_days: int = Field(365, ge=1, le=1825)


@router.post("/sources", status_code=201)
async def import_source(body: SourceIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    rows = body.rows or (list(csv.DictReader(io.StringIO(body.csv))) if body.csv else [])
    if not rows:
        raise HTTPException(422, "No rows: send rows or csv.")
    try:
        out = await cds.import_source(db, name=body.name, license_note=body.license_note, rows=rows, mapping=body.mapping,
                                      retention_days=body.retention_days, user=current_user.username)
    except cds.DataError as e:
        _fail(e)
    pats.audit(db, current_user, "DATA_SOURCE_IMPORTED", "cd_source", out["source_id"], {"rows": out["stored"], "name": body.name})
    await db.commit()
    return out


@router.get("/sources")
async def sources(db: AsyncSession = Depends(get_db)):
    return [{"id": str(s.id), "name": s.name, "kind": s.kind, "license_note": s.license_note, "rows": s.rows,
             "imported_by": s.imported_by, "imported_at": s.imported_at.isoformat(), "expires_at": s.expires_at.isoformat()}
            for s in (await db.execute(select(DataSource).order_by(DataSource.imported_at.desc()))).scalars()]


@router.delete("/sources/{sid}")
async def delete_source(sid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    s = await db.get(DataSource, sid)
    if s is None:
        raise HTTPException(404, "Source not found")
    await db.delete(s)      # its rows and proposals go with it (cascade)
    pats.audit(db, current_user, "DATA_SOURCE_DELETED", "cd_source", str(sid), {"name": s.name})
    await db.commit()
    return {"deleted": True}


class ProspectIn(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    channel: Optional[str] = None
    segment: Optional[str] = None
    size_bands: Optional[list[str]] = None
    keywords: Optional[list[str]] = Field(None, max_length=10)
    exclude_customers: bool = True


@router.post("/prospect")
async def prospect(body: ProspectIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    crit = body.model_dump(exclude_none=True)
    if not any(k in crit for k in cds.CRITERIA):
        raise HTTPException(422, "Give at least one criterion.")
    run = await cds.prospect(db, crit, current_user.username)
    await db.commit()
    return {"run_id": str(run.id), "results": run.results, "provider": cds.provider_status()}


class OutreachIn(BaseModel):
    result_id: str
    subject: Optional[str] = Field(None, max_length=300)
    body: Optional[str] = Field(None, max_length=10000)


@router.post("/prospect/runs/{rid}/draft")
async def outreach_draft(rid: uuid.UUID, body: OutreachIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    run = await db.get(ProspectRun, rid)
    res = next((r for r in (run.results if run else []) if r["id"] == body.result_id), None)
    if res is None:
        raise HTTPException(404, "Result not found")
    return await cds.draft(db, res, current_user.full_name or current_user.username)


@router.post("/prospect/runs/{rid}/outreach", status_code=201)
async def outreach(rid: uuid.UUID, body: OutreachIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Never sends: creates an AI request that a different person approves; the outbox applies suppression."""
    _can(current_user, "crm.edit", "crm.edit_all")
    run = await db.get(ProspectRun, rid)
    res = next((r for r in (run.results if run else []) if r["id"] == body.result_id), None)
    if res is None:
        raise HTTPException(404, "Result not found")
    if not res["can_email"]:
        raise HTTPException(409, "No valid e-mail for this prospect; call or visit instead.")
    d = await cds.draft(db, res, current_user.full_name or current_user.username)
    req = await pats.propose(db, source="PROSPECT", source_ref=f"{rid}:{res['id']}", user=current_user, action="send_email",
                             arguments={"to_email": res["email"], "subject": body.subject or d["subject"], "body": body.body or d["body"]},
                             summary=f"First contact: {res['company_name']}")
    await db.commit()
    return {"approval_request_id": str(req.id), "status": "PENDING"}


@router.post("/research/{cid}")
async def research(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        out = await cds.research(db, cid)
    except cds.DataError as e:
        _fail(e)
    await db.commit()
    return out


class ApplyIn(BaseModel):
    overwrite: bool = False


@router.post("/facts/{fid}/apply")
async def apply_fact(fid: uuid.UUID, body: ApplyIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        out = await cds.apply_fact(db, fid, current_user, body.overwrite)
    except cds.DataError as e:
        _fail(e)
    await db.commit()
    return out


@router.post("/facts/{fid}/reject")
async def reject_fact(fid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        await cds.reject_fact(db, fid, current_user)
    except cds.DataError as e:
        _fail(e)
    await db.commit()
    return {"ok": True}


class VerifyIn(BaseModel):
    verified: bool


@router.put("/customers/{cid}/verified/{field}")
async def verify(cid: uuid.UUID, field: str, body: VerifyIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        await cds.set_verified(db, cid, field, current_user, body.verified)
    except cds.DataError as e:
        _fail(e)
    pats.audit(db, current_user, "FIELD_VERIFIED" if body.verified else "FIELD_UNVERIFIED", "customer", str(cid), {"field": field})
    await db.commit()
    return {"ok": True}


class CardIn(BaseModel):
    text: str = Field(min_length=3, max_length=3000)


@router.post("/business-card/parse")
async def card_parse(body: CardIn):
    return cds.parse_card(body.text)


class CardSave(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=50)
    job_title: Optional[str] = Field(None, max_length=150)
    company: Optional[str] = Field(None, max_length=200)
    confirmed: bool = False


@router.post("/business-card/save", status_code=201)
async def card_save(body: CardSave, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    if not body.confirmed:
        raise HTTPException(422, "Check and confirm every field first.")
    from app.models.crm import CRMContact
    from app.services import crm_contact_service as cs
    email = cds.norm_email(body.email)
    if email and (dup := await cs.find_by_email(db, email)) is not None:
        raise HTTPException(409, {"message": "A contact with this e-mail exists.", "existing_id": str(dup.id)})
    c = CRMContact(full_name=body.full_name.strip(), email=email, phone=cds.norm_phone(body.phone) or body.phone,
                   job_title=body.job_title, notes=f"Company on card: {body.company}" if body.company else None,
                   owner_user_id=current_user.id, source="business card")
    db.add(c)
    await db.flush()
    await cs.set_lifecycle(db, c, "LEAD", "business-card", current_user.id)
    await db.commit()
    return {"id": str(c.id)}
