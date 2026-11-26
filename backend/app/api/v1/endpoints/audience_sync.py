"""Audience lifecycle on ad platforms (M49.S01.T011). Prefix /api/v1/audience-sync.

segment -> preview -> approve (second person, bound to the membership diff) -> sync -> status / reconcile ->
consent withdrawal (removed everywhere + suppression list) -> delete. See services/audience_sync_service.py."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.ads import APPROVE, WRITE, _refused
from app.core.access_control import has_any_permission, require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.models.crm import AdAccount, MarketingAudience
from app.models.m49_audiences import AudienceSuppression, AudienceSync, AudienceSyncMember
from app.services import ads_service as svc
from app.services import audience_sync_adapters as ad
from app.services import audience_sync_service as sv
from app.services.ads_adapters import AdsError

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
ERRS = (svc.Refused, AdsError, EgressBlocked)


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


async def _get(db: AsyncSession, sid: uuid.UUID, user, write: bool = True) -> AudienceSync:
    if write:
        _w(user)
    s = await db.get(AudienceSync, sid)
    if s is None:
        raise HTTPException(404, "Audience sync not found")
    try:
        svc.require_member(user, await svc.control(db, await db.get(AdAccount, s.account_id)))
    except svc.Refused as e:
        _refused(e)
    return s


async def _full(db: AsyncSession, s: AudienceSync, user) -> dict:
    counts = dict((await db.execute(select(AudienceSyncMember.state, func.count()).where(
        AudienceSyncMember.sync_id == s.id).group_by(AudienceSyncMember.state))).all())
    acct = await db.get(AdAccount, s.account_id)
    g = sv.gate(acct, await svc.control(db, acct))
    aud = await db.get(MarketingAudience, s.audience_id)
    return {**sv.out(s), "audience_name": aud.name if aud else None, "account_name": acct.name, "members": counts,
            "gate": {"mode": g["mode"], "transport": g["transport"], "reasons": g["reasons"]},
            "can_approve": bool(user.is_superuser or has_any_permission(user, APPROVE)) and user.username not in (s.requested_by, s.created_by)}


@router.get("/capabilities")
async def capabilities():
    return {"export_enabled": settings.AUDIENCE_EXPORT_ENABLED,
            "providers": [{"provider": p, "operations": ad.CAPS[p], "minimum": ad.MINIMUMS[p][0], "minimum_blocking": ad.MINIMUMS[p][1],
                           "minimum_note": ad.MINIMUMS[p][2], "note": ad.NOTES.get(p)} for p in ad.CAPS]}


@router.get("")
async def list_syncs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Every ad account with whether this user may act on it (refusals are shown, not hidden), and the syncs on the
    accounts they may act on."""
    accounts, syncs = [], []
    for a in (await db.execute(select(AdAccount).order_by(AdAccount.provider, AdAccount.name))).scalars():
        try:
            svc.require_member(user, await svc.control(db, a))
            member, why = True, None
        except svc.Refused as e:
            member, why = False, str(e)
        accounts.append({"id": str(a.id), "provider": a.provider, "name": a.name, "currency": a.currency, "member": member, "refusal": why})
        if member:
            for s in (await db.execute(select(AudienceSync).where(AudienceSync.account_id == a.id).order_by(AudienceSync.created_at.desc()))).scalars():
                syncs.append(await _full(db, s, user))
    return {"accounts": accounts, "syncs": syncs}


class CreateIn(BaseModel):
    audience_id: uuid.UUID
    account_id: uuid.UUID


@router.post("", status_code=201)
async def create(body: CreateIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _w(user)
    audience, acct = await db.get(MarketingAudience, body.audience_id), await db.get(AdAccount, body.account_id)
    if audience is None or acct is None:
        raise HTTPException(404, "Audience or ad account not found")
    try:
        s = await sv.create_sync(db, audience, acct, user)
        await db.commit()
    except ERRS as e:
        _refused(e)
    return await _full(db, s, user)


class LookalikeIn(BaseModel):
    origin_sync_id: uuid.UUID
    ratio: float = Field(0.01, ge=0.01, le=0.20)


@router.post("/lookalike", status_code=201)
async def lookalike(body: LookalikeIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Provider lookalike (Meta only, from a customer-list seed on the same account). Others are refused with the reason."""
    origin = await _get(db, body.origin_sync_id, user)
    try:
        s = await sv.create_sync(db, await db.get(MarketingAudience, origin.audience_id), await db.get(AdAccount, origin.account_id),
                                 user, kind="LOOKALIKE", origin=origin, ratio=body.ratio)
        await db.commit()
    except ERRS as e:
        await db.rollback()
        _refused(e)
    return await _full(db, s, user)


@router.get("/{sid}")
async def one(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _full(db, await _get(db, sid, user, write=False), user)


@router.get("/{sid}/preview")
async def preview(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await sv.preview(db, await _get(db, sid, user, write=False))


@router.post("/{sid}/approvals")
async def request_approval(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await _get(db, sid, user)
    try:
        await sv.request_approval(db, s, user)
        await db.commit()
    except ERRS as e:
        await db.rollback()
        _refused(e)
    return await _full(db, s, user)


class DecideIn(BaseModel):
    ok: bool


@router.post("/{sid}/decide")
async def decide(sid: uuid.UUID, body: DecideIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, APPROVE)):
        raise HTTPException(403, "Approvers only (marketing.approve).")
    s = await _get(db, sid, user, write=False)
    try:
        await sv.decide(db, s, user, body.ok)
    except ERRS as e:
        await db.commit()                    # keep a stale request reset
        _refused(e)
    await db.commit()
    return await _full(db, s, user)


async def _act(db: AsyncSession, s: AudienceSync, user, fn):
    try:
        res = await fn()
    except ERRS as e:
        await db.commit()
        _refused(e)
    await db.commit()
    return {**(res if isinstance(res, dict) else {}), "sync": await _full(db, s, user)}


@router.post("/{sid}/sync")
async def run(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await _get(db, sid, user)
    return await _act(db, s, user, lambda: sv.run_sync(db, s, user))


@router.post("/{sid}/poll")
async def poll(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await _get(db, sid, user)
    return await _act(db, s, user, lambda: sv.poll(db, s))


@router.post("/{sid}/reconcile")
async def reconcile(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await _get(db, sid, user)
    return await _act(db, s, user, lambda: sv.reconcile(db, s, user))


@router.delete("/{sid}")
async def remove(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await _get(db, sid, user)
    return await _act(db, s, user, lambda: sv.delete_sync(db, s, user))


class WithdrawIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


@router.post("/consent-withdrawal")
async def consent_withdrawal(body: WithdrawIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Consent withdrawn: unsubscribe, add to the suppression list, remove from every platform list, recompute local
    audiences. Allowed for any marketing editor whatever the ad account (data protection is not account-scoped)."""
    _w(user)
    try:
        out = await sv.withdraw_consent(db, user, body.email)
    except ERRS as e:
        await db.rollback()
        _refused(e)
    await db.commit()
    return out


@router.get("/suppression/count")
async def suppression_count(db: AsyncSession = Depends(get_db)):
    return {"suppressed": (await db.execute(select(func.count()).select_from(AudienceSuppression))).scalar_one()}


@router.get("/conversions/overview")
async def conversions(db: AsyncSession = Depends(get_db)):
    """Conversion uploads per provider (upload itself: POST /api/v1/audiences/conversion-uploads/{provider}; Meta and
    Google only; consented, hashed, once per source)."""
    return {"export_enabled": settings.AUDIENCE_EXPORT_ENABLED, "rows": await sv.conversions_overview(db),
            "providers": {p: ad.CAPS[p]["conversions"] for p in ad.CAPS}}
