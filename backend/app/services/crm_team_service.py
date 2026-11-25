"""Sales teams with hierarchy, record tags, required fields per stage and saved views (M43.S01.T016).

Teams keep their historic string key (`code`) because sales_team_id on CRM records, sales orders and access scopes
already stores it; the migration turned every distinct existing value into a team, so nothing is relinked. A
manager's roll-up covers the team and all its descendants (cycle-safe).
Required fields: a stage lists CRM record fields that must be filled to ENTER it; checked with the values of the
same request, so a rep can fill and move in one step.
Saved views: per user, optionally shared with one team; filters are a whitelisted dict, never raw SQL.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMPipelineStage, CRMRecord, CRMTeam

REQUIRABLE = ("contact_person_name", "contact_email", "contact_phone", "expected_revenue", "expected_close_date",
              "assigned_rep_id", "industry_segment", "assigned_customer_id", "territory_id", "next_action_date",
              "sales_team_id", "expected_margin")
VIEW_FILTERS = ("record_type", "status", "assigned_rep_id", "stage_id", "pipeline_id", "temperature", "tag",
                "sales_team_id", "forecast_category")


async def descendant_codes(db: AsyncSession, code: str) -> list[str]:
    teams = (await db.execute(select(CRMTeam.id, CRMTeam.code, CRMTeam.parent_id))).all()
    by_code = {c: i for i, c, _ in teams}
    children: dict = {}
    for i, c, p in teams:
        children.setdefault(p, []).append((i, c))
    root = by_code.get(code)
    if root is None:
        return [code]
    out, stack, seen = [code], [root], {root}
    while stack:
        for i, c in children.get(stack.pop(), []):
            if i not in seen:
                seen.add(i)
                out.append(c)
                stack.append(i)
    return out


async def check_no_cycle(db: AsyncSession, team_id, parent_id) -> None:
    cur, hops = parent_id, 0
    while cur is not None and hops < 100:
        if cur == team_id:
            raise HTTPException(422, "A team cannot sit under itself.")
        cur = (await db.execute(select(CRMTeam.parent_id).where(CRMTeam.id == cur))).scalar_one_or_none()
        hops += 1


def _empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


async def check_stage_entry(db: AsyncSession, rec: CRMRecord, new_stage_id, pending: Optional[dict] = None) -> None:
    if new_stage_id is None or str(new_stage_id) == str(rec.stage_id):
        return
    st = await db.get(CRMPipelineStage, new_stage_id)
    missing = [f for f in (st.required_fields or []) if f in REQUIRABLE
               and _empty((pending or {}).get(f, getattr(rec, f, None)))] if st else []
    if missing:
        raise HTTPException(409, {"code": "required_fields", "message": f"Fill {', '.join(missing)} before moving to "
                                  f"'{st.stage_name}'.", "fields": missing})
