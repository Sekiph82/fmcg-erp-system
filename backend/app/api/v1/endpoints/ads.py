"""Ad platforms (M44.S01.T002–T005). Prefix /api/v1/ads. Reporting, account list, drafts with guardrail and approval,
validate-only checks. Live publishing is refused."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.models.crm import AdAccount, AdDraft
from app.services import ads_service as svc
from app.services.ads_adapters import ADAPTERS, AdsError

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
PROVIDER = Field(pattern=r"^(meta|google|linkedin|tiktok)$")
HTTP = {"NOT_CONFIGURED": 503, "AUTH": 502, "PERMISSION": 502, "RATE_LIMIT": 429, "VALIDATION": 422, "VERSION": 502,
        "PROVIDER": 502}


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _fail(e: Exception):
    if isinstance(e, EgressBlocked):
        raise HTTPException(503, str(e)) from None
    headers = {"Retry-After": str(e.retry_after)} if getattr(e, "retry_after", None) else None
    raise HTTPException(HTTP.get(e.kind, 502), {"kind": e.kind, "detail": str(e)}, headers=headers) from None


def _acct(a: AdAccount) -> dict:
    return {"id": str(a.id), "provider": a.provider, "external_id": a.external_id, "name": a.name, "currency": a.currency,
            "time_zone": a.time_zone, "status": a.status, "last_error": a.last_error,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None}


def _draft(d: AdDraft) -> dict:
    return {"id": str(d.id), "account_id": str(d.account_id), "name": d.name, "objective": d.objective,
            "daily_budget": float(d.daily_budget), "start_date": d.start_date.isoformat() if d.start_date else None,
            "end_date": d.end_date.isoformat() if d.end_date else None, "status": d.status,
            "requested_by": d.requested_by, "approved_by": d.approved_by, "validation": d.validation, "created_by": d.created_by}


@router.get("/providers")
async def providers():
    return [{"provider": p, "configured": a.configured(), "validate_only": a.supports_validate_only,
             "live_publishing": False} for p, a in ADAPTERS.items()]


@router.get("/providers/{provider}/accounts")
async def discover(provider: str):
    if provider not in ADAPTERS:
        raise HTTPException(404, "Unknown provider")
    try:
        return await ADAPTERS[provider].accounts()
    except (AdsError, EgressBlocked) as e:
        _fail(e)


class AccountIn(BaseModel):
    provider: str = PROVIDER
    external_id: str = Field(min_length=1, max_length=40, pattern=r"^[0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    time_zone: Optional[str] = Field(None, max_length=64)


@router.get("/accounts")
async def accounts(db: AsyncSession = Depends(get_db)):
    return [_acct(a) for a in (await db.execute(select(AdAccount).order_by(AdAccount.provider, AdAccount.name))).scalars()]


@router.post("/accounts", status_code=201)
async def add_account(body: AccountIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    a = AdAccount(**body.model_dump())
    db.add(a)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(409, "This account is already added.") from None
    return _acct(a)


@router.post("/accounts/{aid}/sync")
async def sync(aid: uuid.UUID, days: int = Query(7, ge=1, le=90), db: AsyncSession = Depends(get_db),
               current_user=Depends(get_current_user)):
    _w(current_user)
    a = await db.get(AdAccount, aid)
    if a is None:
        raise HTTPException(404, "Account not found")
    until = date.today() - timedelta(days=1)
    try:
        res = await svc.sync(db, a, until - timedelta(days=days - 1), until)
    except (AdsError, EgressBlocked) as e:
        await db.commit()                     # keep the account status / error
        _fail(e)
    await db.commit()
    return res


@router.get("/performance")
async def performance(days: int = Query(30, ge=1, le=400), db: AsyncSession = Depends(get_db)):
    return await svc.performance(db, days)


class DraftIn(BaseModel):
    account_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z_]+$")
    daily_budget: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.get("/drafts")
async def drafts(db: AsyncSession = Depends(get_db)):
    return [_draft(d) for d in (await db.execute(select(AdDraft).order_by(AdDraft.created_at.desc()))).scalars()]


@router.post("/drafts", status_code=201)
async def create_draft(body: DraftIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    old = (await db.execute(select(AdDraft).where(AdDraft.idempotency_key == body.idempotency_key))).scalar_one_or_none()
    if old is not None:
        return _draft(old)                    # same key → same draft, never a duplicate
    if await db.get(AdAccount, body.account_id) is None:
        raise HTTPException(404, "Account not found")
    try:
        svc.check_guardrail(body.daily_budget)
    except AdsError as e:
        _fail(e)
    d = AdDraft(**body.model_dump(), created_by=current_user.username)
    db.add(d)
    try:
        await db.commit()
    except IntegrityError:                    # a parallel request with the same key won the race
        await db.rollback()
        return _draft((await db.execute(select(AdDraft).where(AdDraft.idempotency_key == body.idempotency_key))).scalar_one())
    return _draft(d)


@router.post("/drafts/{did}/{action}")
async def draft_action(did: uuid.UUID, action: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    d = await db.get(AdDraft, did)
    if d is None:
        raise HTTPException(404, "Draft not found")
    if action == "request":
        if d.status not in ("DRAFT", "REJECTED"):
            raise HTTPException(409, "Already sent for approval.")
        d.status, d.requested_by, d.approved_by = "PENDING", current_user.username, None
    elif action in ("approve", "reject"):
        if d.status != "PENDING":
            raise HTTPException(409, "Nothing waiting for approval.")
        if current_user.username in (d.requested_by, d.created_by):
            raise HTTPException(403, "A second editor must approve.")
        d.status, d.approved_by = ("APPROVED" if action == "approve" else "REJECTED"), current_user.username
    elif action == "validate":
        try:
            await svc.validate_draft(db, d)
        except (AdsError, EgressBlocked) as e:
            _fail(e)
    elif action == "publish":
        raise HTTPException(403, "Live publishing is disabled. Ad accounts are activated only with owner authorization (M47); "
                                 "use the validated draft to create the campaign in the platform until then.")
    else:
        raise HTTPException(404, "Unknown action")
    await db.commit()
    return _draft(d)
