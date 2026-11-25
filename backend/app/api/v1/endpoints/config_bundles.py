"""Configuration sandbox (M45.S01.T018). Prefix /api/v1/config-bundles. Superusers or roles.manage only.
GET /export → bundle JSON; POST /plan → dry-run diff (writes nothing); POST /apply → one transaction."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.services import config_bundle_service as cbs
from app.services import pat_service as pats

router = APIRouter()


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("roles.manage",))):
        raise HTTPException(403, "Only administrators move configuration between environments.")


@router.get("/export")
async def export(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    b = await cbs.export(db)
    pats.audit(db, current_user, "CONFIG_BUNDLE_EXPORTED", "config_bundle", b["sha256"][:16],
               {"counts": {k: len(v) for k, v in b["items"].items()}})
    await db.commit()
    return JSONResponse(b, headers={"Content-Disposition": f'attachment; filename="config-{b["sha256"][:8]}.json"'})


class BundleIn(BaseModel):
    bundle: dict
    mode: Literal["overwrite", "skip_existing"] = "overwrite"


@router.post("/plan")
async def plan(body: BundleIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        steps = await cbs.plan(db, body.bundle, body.mode)
    except cbs.BundleError as e:
        raise HTTPException(e.status, str(e))
    await db.rollback()
    return {"steps": [{k: v for k, v in s.items() if k not in ("row", "graph", "id")} for s in steps],
            "summary": {a: sum(1 for s in steps if s["action"] == a) for a in ("create", "update", "unchanged", "skip", "error")}}


@router.post("/apply")
async def apply(body: BundleIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    try:
        out = await cbs.apply(db, body.bundle, current_user.username, body.mode)
    except cbs.BundleError as e:
        await db.rollback()
        raise HTTPException(e.status, str(e))
    pats.audit(db, current_user, "CONFIG_BUNDLE_APPLIED", "config_bundle", str(body.bundle.get("sha256", ""))[:16], out)
    await db.commit()
    return out
