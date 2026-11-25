"""Lead routing, stage approvals, deal splits and handoffs (M43.S01.T014). Prefix /api/v1/crm-routing.
Rules and approvals: company-wide CRM editors; splits: anyone who may edit the deal; handoffs: CRM viewers."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.crm import (CRMDealSplit, CRMHandoff, CRMRoutingRule, CRMStageApprovalRequest, CRMStageApprovalRule,
                            CRMStatus)
from app.services import crm_routing_service as rt

VIEW = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region")
router = APIRouter(dependencies=[Depends(require_any_permission(VIEW))])


def _need_editor(u) -> None:
    if not (u.is_superuser or has_permission(u, "crm.edit_all")):
        raise HTTPException(403, "Company-wide CRM editors only.")


class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    priority: int = Field(100, ge=0, le=10000)
    active: bool = True
    conditions: dict[str, Any] = Field(default_factory=dict)
    method: Literal["ROUND_ROBIN", "WEIGHTED", "FIXED"] = "ROUND_ROBIN"
    user_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    weights: Optional[dict[str, int]] = None


def _rule_out(r: CRMRoutingRule) -> dict:
    return {"id": str(r.id), "name": r.name, "priority": r.priority, "active": r.active, "conditions": r.conditions,
            "method": r.method, "user_ids": r.user_ids, "weights": r.weights}


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    return [_rule_out(r) for r in (await db.execute(select(CRMRoutingRule).order_by(CRMRoutingRule.priority))).scalars()]


@router.post("/rules", status_code=201)
async def create_rule(body: RuleIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    bad = [k for k in body.conditions if k not in rt.CONDITION_KEYS]
    if bad:
        raise HTTPException(422, f"Unsupported conditions: {', '.join(bad)}")
    r = CRMRoutingRule(name=body.name, priority=body.priority, active=body.active, conditions=body.conditions,
                       method=body.method, user_ids=[str(u) for u in body.user_ids], weights=body.weights, state={})
    db.add(r)
    await db.commit()
    return _rule_out(r)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    await db.execute(delete(CRMRoutingRule).where(CRMRoutingRule.id == rule_id))
    await db.commit()


class ApprovalRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    stage_id: uuid.UUID
    min_expected_revenue: Optional[Decimal] = Field(None, ge=0)
    active: bool = True


@router.get("/approval-rules")
async def list_approval_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CRMStageApprovalRule))).scalars()
    return [{"id": str(r.id), "name": r.name, "stage_id": str(r.stage_id), "active": r.active,
             "min_expected_revenue": float(r.min_expected_revenue) if r.min_expected_revenue is not None else None} for r in rows]


@router.post("/approval-rules", status_code=201)
async def create_approval_rule(body: ApprovalRuleIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    r = CRMStageApprovalRule(**body.model_dump())
    db.add(r)
    await db.commit()
    return {"id": str(r.id)}


@router.get("/approvals")
async def pending_approvals(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = select(CRMStageApprovalRequest).where(CRMStageApprovalRequest.status == "PENDING")
    if not (current_user.is_superuser or has_permission(current_user, "crm.edit_all")):
        q = q.where(CRMStageApprovalRequest.requested_by_id == current_user.id)       # reps see their own requests
    rows = (await db.execute(q.order_by(CRMStageApprovalRequest.requested_at))).scalars()
    return [{"id": str(r.id), "record_id": str(r.crm_record_id), "stage_id": str(r.stage_id),
             "requested_by_id": str(r.requested_by_id) if r.requested_by_id else None,
             "requested_at": r.requested_at.isoformat()} for r in rows]


class DecisionIn(BaseModel):
    approve: bool
    reason: Optional[str] = Field(None, max_length=300)


@router.post("/approvals/{request_id}/decision")
async def decide(request_id: uuid.UUID, body: DecisionIn, db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    _need_editor(current_user)
    req = await db.get(CRMStageApprovalRequest, request_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    await rt.decide(db, req, current_user, body.approve, body.reason)
    db.add(AuditLog(actor_id=current_user.id, event_type="CRM_STAGE_APPROVAL_" + req.status, module="crm",
                    target_type="crm_record", target_id=str(req.crm_record_id), details={"reason": body.reason}))
    await db.commit()
    return {"id": str(req.id), "status": req.status}


class SplitIn(BaseModel):
    user_id: uuid.UUID
    share_pct: Decimal = Field(gt=0, le=100)


@router.get("/records/{record_id}/splits")
async def get_splits(record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    rec = await _scoped_record(db, record_id, current_user, "view")
    rows = (await db.execute(select(CRMDealSplit).where(CRMDealSplit.crm_record_id == rec.id))).scalars()
    return [{"user_id": str(s.user_id), "share_pct": float(s.share_pct)} for s in rows]


@router.put("/records/{record_id}/splits")
async def set_splits(record_id: uuid.UUID, body: list[SplitIn], db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    rec = await _scoped_record(db, record_id, current_user, "edit")
    rt.validate_splits([(str(s.user_id), s.share_pct) for s in body])
    await db.execute(delete(CRMDealSplit).where(CRMDealSplit.crm_record_id == rec.id))
    db.add_all([CRMDealSplit(crm_record_id=rec.id, user_id=s.user_id, share_pct=s.share_pct) for s in body])
    await db.commit()
    return [{"user_id": str(s.user_id), "share_pct": float(s.share_pct)} for s in body]


class CreditIn(BaseModel):
    final_value: Decimal = Field(gt=0)
    sales_order_id: Optional[uuid.UUID] = None


@router.post("/records/{record_id}/splits/credit")
async def credit(record_id: uuid.UUID, body: CreditIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_editor(current_user)
    from app.api.v1.endpoints.crm_pipeline import _scoped_record
    rec = await _scoped_record(db, record_id, current_user, "view")
    if rec.status != CRMStatus.WON:
        raise HTTPException(409, "Only a won deal is credited.")
    out = await rt.credit_splits(db, rec, body.final_value, body.sales_order_id, current_user.id)
    await db.commit()
    return out


@router.get("/handoffs")
async def handoffs(status: Optional[str] = "OPEN", db: AsyncSession = Depends(get_db)):
    q = select(CRMHandoff).order_by(CRMHandoff.created_at.desc()).limit(200)
    if status:
        q = q.where(CRMHandoff.status == status)
    return [{"id": str(h.id), "record_id": str(h.crm_record_id), "brief": h.brief, "status": h.status,
             "created_at": h.created_at.isoformat()} for h in (await db.execute(q)).scalars()]


@router.post("/handoffs/{handoff_id}/acknowledge")
async def acknowledge(handoff_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    h = await db.get(CRMHandoff, handoff_id)
    if h is None:
        raise HTTPException(404, "Handoff not found")
    h.status, h.acknowledged_by_id = "ACKNOWLEDGED", current_user.id
    await db.commit()
    return {"id": str(h.id), "status": h.status}
