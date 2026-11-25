"""Customer intelligence (M45.S01.T004–T006): intent, churn risk, health, alerts. Prefix /api/v1/customer-intel.

Reps see only customers they own (newest CRM record assigned to them); crm.view_all / crm.edit_all see all.
Settings and model training need crm.edit_all.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.customer_intel import CIAlert, CIModel
from app.models.sales import Customer
from app.services import customer_intel_service as ci

router = APIRouter(dependencies=[Depends(require_any_permission(("crm.view", "crm.view_all", "crm.edit_all")))])


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("crm.edit_all",))):
        raise HTTPException(403, "Only CRM administrators change intelligence settings or train models.")


async def _scope(db, u, cid: uuid.UUID):
    vis = await ci.visible_customer_ids(db, u)
    if (vis is not None and cid not in vis) or await db.get(Customer, cid) is None:
        raise HTTPException(404, "Customer not found")


@router.get("/customers")
async def overview(q: Optional[str] = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200),
                   db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Success workspace: health, churn risk and owner for the customers this user may see."""
    stmt = select(Customer).where(Customer.is_active.is_(True))
    vis = await ci.visible_customer_ids(db, current_user)
    if vis is not None:
        stmt = stmt.where(Customer.id.in_(vis or [uuid.uuid4()]))
    if q:
        stmt = stmt.where(Customer.name.ilike(f"%{q}%"))
    custs = list((await db.execute(stmt.order_by(Customer.name).limit(limit))).scalars())
    ids = [c.id for c in custs]
    hs, cs, own = await ci.health(db, ids), await ci.churn(db, ids), await ci.owners(db, ids)
    return [{"id": str(c.id), "name": c.name, "owner_user_id": str(own[c.id]) if own.get(c.id) else None,
             "health": hs[c.id], "churn": cs[c.id]} for c in custs]


@router.get("/customers/{cid}")
async def detail(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _scope(db, current_user, cid)
    return {"intent": await ci.intent(db, cid), "health": (await ci.health(db, [cid]))[cid],
            "churn": (await ci.churn(db, [cid]))[cid]}


@router.get("/alerts")
async def alerts(open_only: bool = True, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    stmt = select(CIAlert, Customer.name).join(Customer, Customer.id == CIAlert.customer_id)
    if open_only:
        stmt = stmt.where(CIAlert.acknowledged_at.is_(None))
    vis = await ci.visible_customer_ids(db, current_user)
    if vis is not None:
        stmt = stmt.where(CIAlert.customer_id.in_(vis or [uuid.uuid4()]))
    return [{"id": str(a.id), "kind": a.kind, "customer_id": str(a.customer_id), "customer": name, "score": a.score,
             "reasons": a.reasons, "created_at": a.created_at.isoformat(), "acknowledged_by": a.acknowledged_by}
            for a, name in (await db.execute(stmt.order_by(CIAlert.created_at.desc()).limit(200))).all()]


@router.post("/alerts/{aid}/ack")
async def ack(aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    a = await db.get(CIAlert, aid)
    if a is None:
        raise HTTPException(404, "Alert not found")
    await _scope(db, current_user, a.customer_id)
    a.acknowledged_by, a.acknowledged_at = current_user.username, datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.get("/settings/{key}")
async def get_settings(key: Literal["intent", "health", "churn"], db: AsyncSession = Depends(get_db)):
    return await ci.settings_for(db, key)


@router.put("/settings/{key}")
async def put_settings(key: Literal["intent", "health", "churn"], body: dict, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        await ci.save_settings(db, key, body, current_user.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    await db.commit()
    return await ci.settings_for(db, key)


@router.post("/churn/train")
async def train(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    out = await ci.train_churn(db, current_user.username)
    await db.commit()
    return out


@router.get("/churn/model")
async def model(db: AsyncSession = Depends(get_db)):
    m = (await db.execute(select(CIModel).where(CIModel.kind == "CHURN", CIModel.status == "ACTIVE")
                          .order_by(CIModel.trained_at.desc()))).scalars().first()
    return None if m is None else {"id": str(m.id), "trained_at": m.trained_at.isoformat(), "trained_by": m.trained_by,
                                   "metrics": m.metrics, "features": m.params.get("features")}


@router.post("/run-daily")
async def run_daily(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    out = await ci.run_daily(db)
    await db.commit()
    return out
