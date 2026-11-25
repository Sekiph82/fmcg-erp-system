"""Customer view of a shared deal plan (M43.S01.T010). Prefix /api/v1/public/deal-plans; allow-listed.
The customer sees the plan title and steps only (no deal value, notes or internal fields) and may tick steps that
are theirs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import crm_playbook_service as pbs

router = APIRouter()


class TickIn(BaseModel):
    step_id: str
    done: bool


@router.get("/{token}")
async def view_plan(token: str, db: AsyncSession = Depends(get_db)):
    plan = await pbs.plan_by_token(db, token[:100])
    if plan is None:
        raise HTTPException(404, "This plan link is not valid.")
    return {"title": plan.title, "steps": plan.steps}


@router.post("/{token}/steps")
async def tick(token: str, body: TickIn, db: AsyncSession = Depends(get_db)):
    plan = await pbs.plan_by_token(db, token[:100])
    if plan is None:
        raise HTTPException(404, "This plan link is not valid.")
    steps = [dict(s) for s in plan.steps]
    step = next((s for s in steps if s["id"] == body.step_id), None)
    if step is None or step["owner"] != "customer":
        raise HTTPException(403, "Only your own steps can be ticked.")
    step["done"] = body.done
    plan.steps = steps
    await db.commit()
    return {"title": plan.title, "steps": plan.steps}
