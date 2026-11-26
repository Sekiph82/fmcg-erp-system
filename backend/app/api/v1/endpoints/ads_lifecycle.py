"""Unified advertising lifecycle (M49.S01.T006). Prefix /api/v1/ads-lifecycle.

Cross-account tree (account -> campaign -> ad set / ad group -> creative / ad) with status, schedules, edits and per-node
reporting, a wizard description, and approved edits through the M48 mutation ledger. Create / approve / submit / pause /
resume / budget / reconcile stay on /api/v1/ads/campaigns (M48) and are linked from each tree row."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.ads import APPROVE, WRITE, _ctrl, _refused, _tree_out
from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.core.provider_http import EgressBlocked
from app.models.crm import AdAccount
from app.models.m48_ads import AdCampaignNode
from app.models.m49_audiences import AdNodeEdit
from app.services import ads_lifecycle_service as lc
from app.services import ads_service as svc
from app.services.ads_adapters import AdsError

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
ERRS = (svc.Refused, AdsError, EgressBlocked)


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _edit_out(e: AdNodeEdit) -> dict:
    return {"id": str(e.id), "node_id": str(e.node_id), "fields": e.fields, "status": e.status, "mode": e.mode,
            "requested_by": e.requested_by, "decided_by": e.decided_by, "read_back": e.read_back, "last_error": e.last_error,
            "created_at": e.created_at.isoformat() if e.created_at else None}


async def _node(db: AsyncSession, nid: uuid.UUID, user, write: bool = True):
    if write:
        _w(user)
    node = await db.get(AdCampaignNode, nid)
    if node is None:
        raise HTTPException(404, "Ad object not found")
    root = node if node.root_id is None else await db.get(AdCampaignNode, node.root_id)
    acct = await db.get(AdAccount, root.account_id)
    try:
        svc.require_member(user, await svc.control(db, acct))
    except svc.Refused as e:
        _refused(e)
    return node, root, acct


async def _edit(db: AsyncSession, eid: uuid.UUID, user, write: bool = True):
    e = await db.get(AdNodeEdit, eid)
    if e is None:
        raise HTTPException(404, "Edit not found")
    node, root, acct = await _node(db, e.node_id, user, write)
    return e, node, root, acct


@router.get("/wizard")
async def wizard():
    """Supported campaign types and their fields per provider, with what is deliberately not offered and why."""
    return lc.wizard()


@router.get("/tree")
async def tree(days: int = Query(30, ge=1, le=400), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Every ad account with whether this user may act on it (a refusal is shown with its reason), and for the accounts they
    may act on: campaigns -> objects with status, schedule, edits, per-node reporting and the M48 action states."""
    out = []
    for acct in (await db.execute(select(AdAccount).order_by(AdAccount.provider, AdAccount.name))).scalars():
        ctrl = await svc.control(db, acct)
        row = {"account": {"id": str(acct.id), "provider": acct.provider, "name": acct.name, "currency": acct.currency,
                           "status": acct.status, "last_sync_at": acct.last_sync_at.isoformat() if acct.last_sync_at else None},
               "controls": _ctrl(ctrl, acct), "member": True, "refusal": None, "campaigns": []}
        try:
            svc.require_member(user, ctrl)
        except svc.Refused as e:
            row.update(member=False, refusal=str(e))
            out.append(row)
            continue
        for root in (await db.execute(select(AdCampaignNode).where(AdCampaignNode.account_id == acct.id, AdCampaignNode.root_id.is_(None))
                                      .order_by(AdCampaignNode.created_at.desc()).limit(100))).scalars():
            t = await _tree_out(db, root, acct, user)
            nodes = await svc.nodes_of(db, root)
            reports = await lc.node_reports(db, acct, root, nodes, days)
            edits = (await db.execute(select(AdNodeEdit).where(AdNodeEdit.root_id == root.id).order_by(AdNodeEdit.created_at))).scalars().all()
            by_node: dict[str, list] = {}
            for e in edits:
                by_node.setdefault(str(e.node_id), []).append(_edit_out(e))
            editor = user.is_superuser or has_any_permission(user, WRITE)
            for n in t["nodes"]:
                fields = sorted(lc.EDITABLE[acct.provider][n["level"]])
                n.update(report=reports[n["id"]], edits=by_node.get(n["id"], []), editable=fields if n["provider_id"] else [],
                         edit_disabled=(None if n["provider_id"] and fields and editor else
                                        "Needs marketing.edit." if not editor else
                                        "Not on the provider yet: edit the draft in the campaign builder." if not n["provider_id"] else
                                        "No documented updatable fields at this level. " + (lc.NOT_EDITABLE.get(acct.provider) or "")),
                         unverified=[f for f in fields if (acct.provider, n["level"], f) in lc.UNVERIFIED])
            row["campaigns"].append(t)
        out.append(row)
    return {"accounts": out, "can_approve": bool(user.is_superuser or has_any_permission(user, APPROVE))}


class EditIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    start_date: Optional[str] = Field(None, max_length=10)
    end_date: Optional[str] = Field(None, max_length=10)


@router.post("/nodes/{nid}/edits", status_code=201)
async def request_edit(nid: uuid.UUID, body: EditIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    node, root, acct = await _node(db, nid, user)
    try:
        e = await lc.request_edit(db, node, root, acct, user, body.model_dump(exclude_none=True))
        await db.commit()
    except ERRS as ex:
        await db.rollback()
        _refused(ex)
    return _edit_out(e)


class DecideIn(BaseModel):
    ok: bool


@router.post("/edits/{eid}/decide")
async def decide(eid: uuid.UUID, body: DecideIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, APPROVE)):
        raise HTTPException(403, "Approvers only (marketing.approve).")
    e, node, root, acct = await _edit(db, eid, user, write=False)
    try:
        await lc.decide_edit(db, e, node, root, acct, user, body.ok)
    except ERRS as ex:
        await db.commit()
        _refused(ex)
    await db.commit()
    return _edit_out(e)


@router.post("/edits/{eid}/apply")
async def apply(eid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    e, node, root, acct = await _edit(db, eid, user)
    try:
        await lc.apply_edit(db, e, node, root, acct, user)
    except ERRS as ex:
        await db.commit()
        _refused(ex)
    return _edit_out(e)


@router.post("/edits/{eid}/reconcile")
async def reconcile(eid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    e, node, root, acct = await _edit(db, eid, user)
    try:
        await lc.reconcile_edit(db, e, node, root, acct, user)
    except ERRS as ex:
        await db.commit()
        _refused(ex)
    return _edit_out(e)


@router.post("/nodes/{nid}/readback")
async def readback(nid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    node, root, acct = await _node(db, nid, user, write=False)
    try:
        return await lc.readback_node(db, node, root, acct, user)
    except ERRS as ex:
        _refused(ex)
