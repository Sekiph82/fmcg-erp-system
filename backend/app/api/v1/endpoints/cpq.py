"""Advanced CPQ and contract lifecycle (M45.S01.T014). Prefix /api/v1/cpq. Sales rights; templates and settings:
sales.approve or crm.edit_all."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.cpq import ContractTemplate, QuoteTemplate
from app.services import cpq_service as cpq
from app.services import pat_service as pats

router = APIRouter(dependencies=[Depends(require_any_permission(("sales.view", "sales.create", "sales.edit")))])


def _fail(e: cpq.CPQError):
    raise HTTPException(e.status, str(e))


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("sales.approve", "crm.edit_all"))):
        raise HTTPException(403, "Only sales managers change CPQ settings and templates.")


def _edit(u):
    if not (u.is_superuser or has_any_permission(u, ("sales.edit", "sales.create"))):
        raise HTTPException(403, "You may not change quotations.")


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return {**await cpq.settings_get(db), "signature_providers": cpq.SIGNATURE_PROVIDERS}


@router.put("/settings")
async def put_settings(body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.customer_intel import CISetting
    _admin(current_user)
    clean = {k: v for k, v in body.items() if k in cpq.DEFAULTS}
    for lvl in clean.get("approval_levels", []):
        if not isinstance(lvl.get("above_pct"), (int, float)) or "." not in str(lvl.get("permission", "")):
            raise HTTPException(422, "Each level needs above_pct (number) and a permission like sales.approve.")
    row = await db.get(CISetting, "cpq")
    if row is None:
        db.add(CISetting(key="cpq", value=clean, updated_by=current_user.username))
    else:
        row.value, row.updated_by = {**row.value, **clean}, current_user.username
    pats.audit(db, current_user, "CPQ_SETTINGS_CHANGED", "cpq", "settings", clean)
    await db.commit()
    return await cpq.settings_get(db)


@router.post("/quotes/{qid}/price-book")
async def price_book(qid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    try:
        out = await cpq.apply_price_book(db, qid)
    except cpq.CPQError as e:
        _fail(e)
    await db.commit()
    return {"lines": out}


@router.post("/quotes/{qid}/promotions")
async def promotions(qid: uuid.UUID, apply: bool = False, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if apply:
        _edit(current_user)
    try:
        out = await cpq.evaluate_promotions(db, qid, apply=apply)
    except cpq.CPQError as e:
        _fail(e)
    if apply:
        await db.commit()
    else:
        await db.rollback()
    return out


@router.get("/quotes/{qid}/approvals")
async def approvals(qid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cpq.approval_state(db, await cpq._quote(db, qid))
    except cpq.CPQError as e:
        _fail(e)


@router.post("/quotes/{qid}/approvals")
async def approve(qid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        out = await cpq.approve_level(db, qid, current_user)
    except cpq.CPQError as e:
        _fail(e)
    pats.audit(db, current_user, "QUOTE_LEVEL_APPROVED", "quotation", str(qid), {"discount_pct": out["discount_pct"]})
    await db.commit()
    return out


@router.get("/quotes/{qid}/readiness")
async def readiness(qid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cpq.readiness(db, qid)
    except cpq.CPQError as e:
        _fail(e)


@router.get("/report")
async def report(days: int = 90, db: AsyncSession = Depends(get_db)):
    return await cpq.report(db, days)


class QuoteTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    lines: list[dict] = Field(min_length=1)
    notes: Optional[str] = Field(None, max_length=5000)
    valid_days: int = Field(14, ge=1, le=180)


@router.get("/templates")
async def templates(db: AsyncSession = Depends(get_db)):
    q = (await db.execute(select(QuoteTemplate).order_by(QuoteTemplate.name))).scalars().all()
    c = (await db.execute(select(ContractTemplate).order_by(ContractTemplate.name))).scalars().all()
    return {"quote": [{"id": str(t.id), "name": t.name, "lines": t.lines, "valid_days": t.valid_days} for t in q],
            "contract": [{"id": str(t.id), "name": t.name, "term_months": t.term_months, "auto_renew": t.auto_renew,
                          "clauses": t.clauses} for t in c]}


@router.post("/templates/quote", status_code=201)
async def add_quote_template(body: QuoteTemplateIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    for line in body.lines:
        try:
            uuid.UUID(str(line.get("product_id")))
        except ValueError:
            raise HTTPException(422, "Every template line needs a product_id.")
    t = QuoteTemplate(**body.model_dump(), created_by=current_user.username)
    db.add(t)
    await db.commit()
    return {"id": str(t.id)}


class FromTemplateIn(BaseModel):
    template_id: uuid.UUID
    customer_id: uuid.UUID


@router.post("/quotes/from-template", status_code=201)
async def from_template(body: FromTemplateIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    try:
        q = await cpq.quote_from_template(db, body.template_id, body.customer_id, current_user.id)
    except cpq.CPQError as e:
        _fail(e)
    await db.commit()
    return {"id": str(q.id), "quote_no": q.quote_no, "grand_total": str(q.grand_total)}


class ContractTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contract_type: str = Field("SUPPLY", max_length=50)
    clauses: list[dict] = Field(min_length=1)
    term_months: int = Field(12, ge=1, le=120)
    auto_renew: bool = False
    renewal_notice_days: int = Field(30, ge=1, le=365)


@router.post("/templates/contract", status_code=201)
async def add_contract_template(body: ContractTemplateIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    if any(not c.get("title") or not c.get("text") for c in body.clauses):
        raise HTTPException(422, "Every clause needs a title and text.")
    t = ContractTemplate(**body.model_dump())
    db.add(t)
    await db.commit()
    return {"id": str(t.id)}


class ContractIn(BaseModel):
    template_id: uuid.UUID


@router.post("/quotes/{qid}/contract", status_code=201)
async def contract(qid: uuid.UUID, body: ContractIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _edit(current_user)
    try:
        c = await cpq.contract_from_quote(db, qid, body.template_id, current_user)
    except cpq.CPQError as e:
        _fail(e)
    pats.audit(db, current_user, "CONTRACT_FROM_QUOTE", "contract", str(c.id), {"quote": str(qid)})
    await db.commit()
    return {"id": str(c.id), "contract_code": c.contract_code, "end_date": c.end_date.isoformat(), "status": c.status}


@router.get("/returns/{rid}/credit-check")
async def credit_check(rid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cpq.verify_credit_note(db, rid)
    except cpq.CPQError as e:
        _fail(e)
