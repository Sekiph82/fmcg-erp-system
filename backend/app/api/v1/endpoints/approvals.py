"""
Generic Approval Workflow API
──────────────────────────────
Prefix: /api/v1/approvals
"""
from __future__ import annotations

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.models.workflow import ApprovalRequest, ApprovalRule, ApprovalStatus, ApprovalStep
from app.schemas.workflow import (
    ApprovalAction, ApprovalReject, ApprovalRequestRead,
    ApprovalRuleCreate, ApprovalRuleRead, ApprovalRuleUpdate,
    ApprovalStepRead, ApprovalSubmit,
)
from app.services import approval_service as svc

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_step(s: ApprovalStep) -> ApprovalStepRead:
    r = ApprovalStepRead.model_validate(s)
    if s.action_by:
        r.action_by_name = s.action_by.full_name or s.action_by.username
    return r


def _build_request(req: ApprovalRequest) -> ApprovalRequestRead:
    r = ApprovalRequestRead.model_validate(req)
    if req.requested_by:
        r.requested_by_name = req.requested_by.full_name or req.requested_by.username
    r.steps = [_build_step(s) for s in (req.steps or [])]
    return r


# ── My Approval Inbox ─────────────────────────────────────────────────────────

@router.get("/", response_model=List[ApprovalRequestRead])
async def my_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all pending approval requests the current user can act on."""
    requests = await svc.get_pending_for_user(db, current_user.id)
    return [_build_request(r) for r in requests]


@router.get("/all", response_model=List[ApprovalRequestRead],
            dependencies=[Depends(require_permission("admin", "view"))])
async def all_approval_requests(
    status: Optional[str] = None,
    module: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Admin view — all approval requests with optional filters."""
    q = (
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps).selectinload(ApprovalStep.action_by),
                 selectinload(ApprovalRequest.requested_by))
        .order_by(ApprovalRequest.created_at.desc())
        .offset(skip).limit(limit)
    )
    if status:
        q = q.where(ApprovalRequest.status == status)
    if module:
        q = q.where(ApprovalRequest.module == module)
    requests = list((await db.execute(q)).scalars().all())
    return [_build_request(r) for r in requests]


@router.get("/{request_id}", response_model=ApprovalRequestRead)
async def get_approval_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps).selectinload(ApprovalStep.action_by),
                 selectinload(ApprovalRequest.requested_by))
        .where(ApprovalRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Approval request not found")
    return _build_request(req)


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/submit", response_model=ApprovalRequestRead, status_code=201)
async def submit_approval(
    body: ApprovalSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit any ERP object for approval."""
    req = await svc.submit_for_approval(
        db,
        module=body.module,
        object_id=body.object_id,
        object_ref=body.object_ref,
        requested_by_id=current_user.id,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
    )
    await db.commit()
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps).selectinload(ApprovalStep.action_by),
                 selectinload(ApprovalRequest.requested_by))
        .where(ApprovalRequest.id == req.id)
    )
    return _build_request(result.scalar_one())


@router.post("/{request_id}/approve", response_model=ApprovalRequestRead)
async def approve(
    request_id: uuid.UUID,
    body: ApprovalAction = ApprovalAction(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await svc.approve_request(db, request_id, current_user.id, notes=body.notes)
    await db.commit()
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps).selectinload(ApprovalStep.action_by),
                 selectinload(ApprovalRequest.requested_by))
        .where(ApprovalRequest.id == req.id)
    )
    return _build_request(result.scalar_one())


@router.post("/{request_id}/reject", response_model=ApprovalRequestRead)
async def reject(
    request_id: uuid.UUID,
    body: ApprovalReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await svc.reject_request(db, request_id, current_user.id, reason=body.reason)
    await db.commit()
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps).selectinload(ApprovalStep.action_by),
                 selectinload(ApprovalRequest.requested_by))
        .where(ApprovalRequest.id == req.id)
    )
    return _build_request(result.scalar_one())


@router.post("/{request_id}/cancel", response_model=ApprovalRequestRead)
async def cancel(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    req = await svc.cancel_request(db, request_id)
    await db.commit()
    await db.refresh(req)
    return _build_request(req)


@router.post("/admin/escalate-overdue", response_model=dict,
             dependencies=[Depends(require_permission("admin", "manage"))])
async def escalate_overdue(db: AsyncSession = Depends(get_db)):
    count = await svc.escalate_overdue(db)
    await db.commit()
    return {"escalated_count": count}


# ── Approval Rules CRUD ───────────────────────────────────────────────────────

@router.get("/rules/", response_model=List[ApprovalRuleRead],
            dependencies=[Depends(require_permission("admin", "view"))])
async def list_rules(
    module: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ApprovalRule).order_by(ApprovalRule.module, ApprovalRule.level)
    if module:
        q = q.where(ApprovalRule.module == module)
    rules = list((await db.execute(q)).scalars().all())
    return [ApprovalRuleRead.model_validate(r) for r in rules]


@router.post("/rules/", response_model=ApprovalRuleRead, status_code=201,
             dependencies=[Depends(require_permission("admin", "manage"))])
async def create_rule(
    body: ApprovalRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    rule = ApprovalRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ApprovalRuleRead.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=ApprovalRuleRead,
              dependencies=[Depends(require_permission("admin", "manage"))])
async def update_rule(
    rule_id: uuid.UUID,
    body: ApprovalRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(ApprovalRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return ApprovalRuleRead.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204,
               dependencies=[Depends(require_permission("admin", "manage"))])
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(ApprovalRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
