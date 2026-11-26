"""Dynamic audiences (M44.S01.T010). Prefix /api/v1/audiences."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.crm import MarketingAudience
from app.services import audience_service as aus

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "marketing.create", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])


class AudienceIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    rules: dict[str, Any]
    require_consent: bool = True


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _rules(r: dict) -> dict:
    try:
        return aus.validate(r)
    except aus.AudienceError as e:
        raise HTTPException(422, str(e)) from None


def _out(a: MarketingAudience) -> dict:
    return {"id": str(a.id), "name": a.name, "rules": a.rules, "require_consent": a.require_consent,
            "member_count": a.member_count, "blocked_count": a.blocked_count,
            "computed_at": a.computed_at.isoformat() if a.computed_at else None}


async def _get(db, aid: uuid.UUID) -> MarketingAudience:
    a = await db.get(MarketingAudience, aid)
    if a is None:
        raise HTTPException(404, "Audience not found")
    return a


@router.get("")
async def list_audiences(db: AsyncSession = Depends(get_db)):
    return [_out(a) for a in (await db.execute(select(MarketingAudience).order_by(MarketingAudience.name))).scalars()]




@router.post("/preview")
async def preview_count(body: AudienceIn, db: AsyncSession = Depends(get_db)):
    res = await aus.evaluate(db, _rules(body.rules), body.require_consent)
    return {"members": len(res["members"]), "blocked": res["blocked"],
            "sample": [c.name for c, _ in res["members"][:10]]}


@router.post("", status_code=201)
async def create(body: AudienceIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    if (await db.execute(select(MarketingAudience).where(MarketingAudience.name == body.name))).scalar_one_or_none():
        raise HTTPException(409, "An audience with this name exists.")
    a = MarketingAudience(name=body.name, rules=_rules(body.rules), require_consent=body.require_consent,
                          created_by_id=current_user.id)
    db.add(a)
    await db.flush()
    await aus.recompute(db, a)
    await db.commit()
    return _out(a)


@router.put("/{aid}")
async def update(aid: uuid.UUID, body: AudienceIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    a = await _get(db, aid)
    a.name, a.rules, a.require_consent = body.name, _rules(body.rules), body.require_consent
    await aus.recompute(db, a)
    await db.commit()
    return _out(a)


@router.post("/{aid}/recompute")
async def recompute(aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    a = await aus.recompute(db, await _get(db, aid))
    await db.commit()
    return _out(a)


@router.delete("/{aid}", status_code=204)
async def remove(aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    await db.delete(await _get(db, aid))
    await db.commit()


@router.get("/{aid}/similar")
async def similar(aid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await aus.similar(db, await _get(db, aid))


@router.get("/{aid}/export.csv", response_class=PlainTextResponse)
async def export(aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    if not settings.AUDIENCE_EXPORT_ENABLED:
        raise HTTPException(403, "Audience export is switched off (AUDIENCE_EXPORT_ENABLED). Turn it on only with a "
                                 "lawful basis to share hashed customer lists with an ad platform.")
    a = await _get(db, aid)
    return PlainTextResponse(await aus.hashed_export(db, a), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="audience-{a.id}.csv"'})


@router.post("/{aid}/upload/{provider}")
async def upload(aid: uuid.UUID, provider: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """M47.S01.T010 Meta Custom Audience / Google Customer Match upload of the consented members, SHA-256 hashed.
    Without a connected ad account (or with export switched off) the answer is NOT_CONFIGURED; nothing is sent.
    (Parameter order kept as before: aid, provider, current_user.)"""
    from app.services import ads_adapters as ads
    from app.services import pat_service as pats
    _w(current_user)
    if provider not in ("meta", "google"):
        raise HTTPException(422, "Provider must be meta or google.")
    if not settings.AUDIENCE_EXPORT_ENABLED:
        return {"status": "NOT_CONFIGURED", "message": "Audience sharing is switched off (AUDIENCE_EXPORT_ENABLED)."}
    a = await _get(db, aid)
    try:
        out = await ads.upload_audience(db, a, provider, current_user)
    except ads.AdsError as e:
        if e.kind == "NOT_CONFIGURED":
            await db.rollback()
            return {"status": "NOT_CONFIGURED", "message": str(e)}
        await db.commit()                     # keep the FAILED upload row
        raise HTTPException(502 if e.kind == "PROVIDER" else 409, str(e)) from None
    pats.audit(db, current_user, "AUDIENCE_UPLOADED", "mkt_audience", str(a.id), {"provider": provider, "sent": out["sent"]})
    await db.commit()
    return out


@router.post("/conversion-uploads/{provider}")
async def upload_conversions(provider: str, days: int = 7, db: AsyncSession = Depends(get_db),
                             current_user=Depends(get_current_user)):
    """M47.S01.T010 Meta CAPI / Google offline conversions from won deals and paid invoices of the last `days`
    (consented e-mails only, hashed). Each source is uploaded once per provider."""
    from datetime import datetime, timedelta, timezone
    from app.services import ads_adapters as ads
    _w(current_user)
    if not settings.AUDIENCE_EXPORT_ENABLED:
        return {"status": "NOT_CONFIGURED", "message": "Audience sharing is switched off (AUDIENCE_EXPORT_ENABLED)."}
    try:
        out = await ads.upload_conversions(db, provider, datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90))))
    except ads.AdsError as e:
        await db.rollback()
        if e.kind == "NOT_CONFIGURED":
            return {"status": "NOT_CONFIGURED", "message": str(e)}
        raise HTTPException(422, str(e)) from None
    await db.commit()
    return out
