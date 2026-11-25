"""Sales teams, record tags and saved views (M43.S01.T016). Prefix /api/v1/crm-teams.

Teams and tags are managed by company-wide CRM editors; anyone with CRM view rights reads them. Saved views belong
to their owner and are visible to members of the team they are shared with; applying a view runs the normal,
scope-checked record listing with whitelisted filters only.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import CRMRecordTag, CRMSavedView, CRMTag, CRMTeam, CRMTeamMember
from app.services import crm_team_service as teams

VIEW = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region")
router = APIRouter(dependencies=[Depends(require_any_permission(VIEW))])


def _editor(u) -> bool:
    return u.is_superuser or has_permission(u, "crm.edit_all")


def _need_editor(u) -> None:
    if not _editor(u):
        raise HTTPException(403, "Only company-wide CRM editors can change teams and tags.")


class TeamIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    parent_id: Optional[uuid.UUID] = None
    manager_user_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    active_flag: bool = True


def _team_out(t: CRMTeam, members=None) -> dict:
    return {"id": str(t.id), "code": t.code, "name": t.name, "parent_id": str(t.parent_id) if t.parent_id else None,
            "manager_user_id": str(t.manager_user_id) if t.manager_user_id else None, "active_flag": t.active_flag,
            "members": members}


@router.get("/teams")
async def list_teams(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CRMTeam).order_by(CRMTeam.name))).scalars().all()
    mem = (await db.execute(select(CRMTeamMember))).scalars().all()
    by_team: dict = {}
    for m in mem:
        by_team.setdefault(m.team_id, []).append({"user_id": str(m.user_id), "role": m.role})
    return [_team_out(t, by_team.get(t.id, [])) for t in rows]


@router.post("/teams", status_code=201)
async def create_team(body: TeamIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    if (await db.execute(select(CRMTeam.id).where(CRMTeam.code == body.code))).first():
        raise HTTPException(409, "A team with this code exists.")
    t = CRMTeam(**body.model_dump())
    db.add(t)
    await db.flush()
    await teams.check_no_cycle(db, t.id, t.parent_id)
    await db.commit()
    return _team_out(t, [])


@router.put("/teams/{team_id}")
async def update_team(team_id: uuid.UUID, body: TeamIn, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    _need_editor(current_user)
    t = await db.get(CRMTeam, team_id)
    if t is None:
        raise HTTPException(404, "Team not found")
    if body.code != t.code:
        raise HTTPException(422, "The team code is stored on records and orders; create a new team instead.")
    await teams.check_no_cycle(db, t.id, body.parent_id)
    t.name, t.parent_id, t.manager_user_id, t.company_id, t.active_flag = (
        body.name, body.parent_id, body.manager_user_id, body.company_id, body.active_flag)
    await db.commit()
    return _team_out(t)


class MemberIn(BaseModel):
    user_id: uuid.UUID
    role: Literal["member", "manager"] = "member"


@router.put("/teams/{team_id}/members")
async def set_member(team_id: uuid.UUID, body: MemberIn, db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    _need_editor(current_user)
    if await db.get(CRMTeam, team_id) is None:
        raise HTTPException(404, "Team not found")
    m = await db.get(CRMTeamMember, (team_id, body.user_id)) or CRMTeamMember(team_id=team_id, user_id=body.user_id)
    m.role = body.role
    db.add(m)
    await db.commit()
    return {"team_id": str(team_id), "user_id": str(body.user_id), "role": m.role}


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
async def remove_member(team_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    _need_editor(current_user)
    await db.execute(delete(CRMTeamMember).where(CRMTeamMember.team_id == team_id, CRMTeamMember.user_id == user_id))
    await db.commit()


@router.get("/teams/{team_id}/rollup")
async def team_rollup(team_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    t = await db.get(CRMTeam, team_id)
    if t is None:
        raise HTTPException(404, "Team not found")
    return {"team": t.code, "includes": await teams.descendant_codes(db, t.code)}


# ── tags ──────────────────────────────────────────────────────────────────────

class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: Optional[str] = Field(None, max_length=20)


@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_db)):
    return [{"id": str(t.id), "name": t.name, "color": t.color}
            for t in (await db.execute(select(CRMTag).order_by(CRMTag.name))).scalars()]


@router.post("/tags", status_code=201)
async def create_tag(body: TagIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    if (await db.execute(select(CRMTag.id).where(CRMTag.name == body.name.strip()))).first():
        raise HTTPException(409, "Tag exists.")
    t = CRMTag(name=body.name.strip(), color=body.color)
    db.add(t)
    await db.commit()
    return {"id": str(t.id), "name": t.name, "color": t.color}


@router.put("/records/{record_id}/tags")
async def set_record_tags(record_id: uuid.UUID, tag_ids: list[uuid.UUID], db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    rec = await _scoped_record(db, record_id, current_user, "edit")
    found = set((await db.execute(select(CRMTag.id).where(CRMTag.id.in_(tag_ids)))).scalars())
    if found != set(tag_ids):
        raise HTTPException(422, "Unknown tag")
    await db.execute(delete(CRMRecordTag).where(CRMRecordTag.crm_record_id == rec.id))
    db.add_all([CRMRecordTag(crm_record_id=rec.id, tag_id=t) for t in found])
    await db.commit()
    return {"record_id": str(rec.id), "tag_ids": [str(t) for t in found]}


# ── saved views ───────────────────────────────────────────────────────────────

class ViewIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    team_id: Optional[uuid.UUID] = None
    view_type: Literal["list", "board", "calendar"] = "list"
    filters: dict[str, Any] = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list, max_length=30)
    calendar_field: Optional[Literal["expected_close_date", "next_action_date"]] = None


async def _my_team_ids(db, user_id) -> set:
    return set((await db.execute(select(CRMTeamMember.team_id).where(CRMTeamMember.user_id == user_id))).scalars())


def _view_out(v: CRMSavedView) -> dict:
    return {"id": str(v.id), "name": v.name, "team_id": str(v.team_id) if v.team_id else None, "view_type": v.view_type,
            "filters": v.filters, "columns": v.columns, "calendar_field": v.calendar_field,
            "owner_user_id": str(v.owner_user_id)}


@router.get("/views")
async def list_views(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    team_ids = await _my_team_ids(db, current_user.id)
    rows = (await db.execute(select(CRMSavedView).where(or_(
        CRMSavedView.owner_user_id == current_user.id, CRMSavedView.team_id.in_(team_ids or {uuid.uuid4()})))
        .order_by(CRMSavedView.name))).scalars()
    return [_view_out(v) for v in rows]


@router.post("/views", status_code=201)
async def save_view(body: ViewIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    bad = [k for k in body.filters if k not in teams.VIEW_FILTERS]
    if bad:
        raise HTTPException(422, f"Unsupported filters: {', '.join(bad)}")
    if body.team_id and body.team_id not in await _my_team_ids(db, current_user.id) and not _editor(current_user):
        raise HTTPException(403, "You can only share a view with your own team.")
    v = CRMSavedView(owner_user_id=current_user.id, **body.model_dump())
    db.add(v)
    await db.commit()
    return _view_out(v)


@router.delete("/views/{view_id}", status_code=204)
async def delete_view(view_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    v = await db.get(CRMSavedView, view_id)
    if v is None or v.owner_user_id != current_user.id:
        raise HTTPException(404, "View not found")
    await db.delete(v)
    await db.commit()


@router.get("/views/{view_id}/records")
async def apply_view(view_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Records matching the view, through the same scope rules as the CRM record list."""
    from app.api.v1.endpoints.crm_pipeline import can_view_record
    from app.services import crm_pipeline_service as svc
    v = await db.get(CRMSavedView, view_id)
    if v is None or (v.owner_user_id != current_user.id and v.team_id not in await _my_team_ids(db, current_user.id)):
        raise HTTPException(404, "View not found")
    f = dict(v.filters or {})
    base = {k: f.pop(k, None) for k in ("record_type", "status", "assigned_rep_id", "stage_id", "temperature")}
    rows = await svc.get_records(db, limit=500, extra=f, **base)
    rows = [r for r in rows if can_view_record(current_user, "crm", r)]
    field = v.calendar_field or "expected_close_date"
    return [{"id": str(r.id), "company_name": r.company_name, "status": getattr(r.status, "value", r.status),
             "stage_id": str(r.stage_id) if r.stage_id else None, "expected_revenue": float(r.expected_revenue or 0),
             "currency": r.currency, "date": (getattr(r, field) or None) and getattr(r, field).isoformat()} for r in rows]
