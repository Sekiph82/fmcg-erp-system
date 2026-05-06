"""
Generic Approval Workflow Engine
─────────────────────────────────
Any ERP module can submit an object for approval. The engine:
  1. Looks up matching ApprovalRules for the module + amount
  2. Creates an ApprovalRequest with one step per level
  3. Routes approve/reject actions through the step chain
  4. Fires APPROVAL_REQUIRED notifications at each step
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    ApprovalModule, ApprovalRequest, ApprovalRule,
    ApprovalStatus, ApprovalStep,
)
from app.models.user import User


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


async def _matching_rules(
    db: AsyncSession,
    module: ApprovalModule,
    amount: Optional[Decimal],
) -> List[ApprovalRule]:
    """Return active rules for module + amount, sorted by level."""
    q = select(ApprovalRule).where(
        ApprovalRule.module == module,
        ApprovalRule.is_active.is_(True),
    )
    if amount is not None:
        q = q.where(ApprovalRule.amount_min <= amount)
        q = q.where(
            (ApprovalRule.amount_max.is_(None)) | (ApprovalRule.amount_max >= amount)
        )
    q = q.order_by(ApprovalRule.level.asc())
    return list((await db.execute(q)).scalars().all())


async def _notify_step(db: AsyncSession, step: ApprovalStep, request: ApprovalRequest) -> None:
    """Fire an in-app APPROVAL_REQUIRED notification to all users with required_role."""
    from app.models.notifications import Notification, NotificationType, NotificationPriority, NotificationChannel, NotificationStatus
    from sqlalchemy import select as sa_select
    from app.models.role import Role

    role_q = sa_select(Role).where(Role.name == step.required_role)
    role = (await db.execute(role_q)).scalar_one_or_none()
    if not role:
        return

    from app.models.user import user_role
    users_q = sa_select(User).join(user_role, user_role.c.user_id == User.id).where(
        user_role.c.role_id == role.id, User.is_active.is_(True)
    )
    users = list((await db.execute(users_q)).scalars().all())

    for user in users:
        notif = Notification(
            user_id=str(user.id),
            user_name=user.full_name or user.username,
            title=f"Approval Required: {request.object_ref}",
            message=f"{request.module.value} {request.object_ref} requires your approval (Level {step.level})."
                    + (f" Amount: KES {float(request.amount):,.2f}" if request.amount else ""),
            notification_type=NotificationType.APPROVAL_REQUIRED,
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.PENDING,
            reference_type=request.module.value,
            reference_id=str(request.object_id),
            module="approvals",
        )
        db.add(notif)


async def submit_for_approval(
    db: AsyncSession,
    *,
    module: ApprovalModule,
    object_id: uuid.UUID,
    object_ref: str,
    requested_by_id: Optional[uuid.UUID],
    amount: Optional[Decimal] = None,
    currency: str = "KES",
    description: Optional[str] = None,
) -> ApprovalRequest:
    """
    Submit an ERP object for approval. Creates the request and first step.
    Returns the created ApprovalRequest.
    """
    rules = await _matching_rules(db, module, amount)
    max_level = max((r.level for r in rules), default=1) if rules else 1

    request = ApprovalRequest(
        module=module,
        object_id=object_id,
        object_ref=object_ref,
        amount=amount,
        currency=currency,
        status=ApprovalStatus.PENDING,
        current_level=1,
        max_level=max_level,
        description=description,
        requested_by_id=requested_by_id,
    )
    db.add(request)
    await db.flush()

    # Create step for level 1
    level1_rules = [r for r in rules if r.level == 1]
    required_role = level1_rules[0].required_role if level1_rules else "admin"
    sla_hours = level1_rules[0].sla_hours if level1_rules else 24

    step = ApprovalStep(
        request_id=request.id,
        level=1,
        required_role=required_role,
        status=ApprovalStatus.PENDING,
        sla_deadline=_now() + timedelta(hours=sla_hours),
    )
    db.add(step)
    await db.flush()

    await _notify_step(db, step, request)
    return request


async def approve_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    approver_id: uuid.UUID,
    notes: Optional[str] = None,
) -> ApprovalRequest:
    """Approve the current pending step. Advances to next level or marks fully approved."""
    request = await db.get(ApprovalRequest, request_id, options=[selectinload(ApprovalRequest.steps)])
    if not request:
        raise HTTPException(404, "Approval request not found")
    if request.status != ApprovalStatus.PENDING:
        raise HTTPException(422, f"Request is {request.status.value}, cannot approve")

    current_step = next(
        (s for s in request.steps if s.level == request.current_level and s.status == ApprovalStatus.PENDING),
        None,
    )
    if not current_step:
        raise HTTPException(422, "No pending step found at current level")

    current_step.status = ApprovalStatus.APPROVED
    current_step.action_at = _now()
    current_step.action_by_id = approver_id
    current_step.notes = notes

    next_level = request.current_level + 1

    if next_level > request.max_level:
        # All levels approved
        request.status = ApprovalStatus.APPROVED
        request.final_action_at = _now()
        request.final_action_by_id = approver_id
    else:
        # Advance to next level
        request.current_level = next_level
        rules = await _matching_rules(db, request.module, request.amount)
        next_rules = [r for r in rules if r.level == next_level]
        required_role = next_rules[0].required_role if next_rules else "admin"
        sla_hours = next_rules[0].sla_hours if next_rules else 24

        next_step = ApprovalStep(
            request_id=request.id,
            level=next_level,
            required_role=required_role,
            status=ApprovalStatus.PENDING,
            sla_deadline=_now() + timedelta(hours=sla_hours),
        )
        db.add(next_step)
        await db.flush()
        await _notify_step(db, next_step, request)

    await db.flush()
    return request


async def reject_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    rejector_id: uuid.UUID,
    reason: str,
) -> ApprovalRequest:
    """Reject the request at the current level. Terminates the chain."""
    request = await db.get(ApprovalRequest, request_id, options=[selectinload(ApprovalRequest.steps)])
    if not request:
        raise HTTPException(404, "Approval request not found")
    if request.status != ApprovalStatus.PENDING:
        raise HTTPException(422, f"Request is {request.status.value}, cannot reject")

    current_step = next(
        (s for s in request.steps if s.level == request.current_level and s.status == ApprovalStatus.PENDING),
        None,
    )
    if current_step:
        current_step.status = ApprovalStatus.REJECTED
        current_step.action_at = _now()
        current_step.action_by_id = rejector_id
        current_step.rejection_reason = reason

    request.status = ApprovalStatus.REJECTED
    request.final_action_at = _now()
    request.final_action_by_id = rejector_id
    await db.flush()
    return request


async def cancel_request(
    db: AsyncSession,
    request_id: uuid.UUID,
) -> ApprovalRequest:
    """Cancel a pending approval request (e.g. the source document was deleted)."""
    request = await db.get(ApprovalRequest, request_id)
    if not request:
        raise HTTPException(404, "Approval request not found")
    if request.status not in (ApprovalStatus.PENDING, ApprovalStatus.ESCALATED):
        raise HTTPException(422, "Only PENDING or ESCALATED requests can be cancelled")
    request.status = ApprovalStatus.CANCELLED
    await db.flush()
    return request


async def escalate_overdue(db: AsyncSession) -> int:
    """
    Find pending steps past their SLA deadline and escalate to ESCALATED status.
    Returns count of escalated requests.
    """
    now = _now()
    q = select(ApprovalStep).where(
        ApprovalStep.status == ApprovalStatus.PENDING,
        ApprovalStep.sla_deadline < now,
    )
    overdue_steps = list((await db.execute(q)).scalars().all())
    escalated = 0
    for step in overdue_steps:
        step.status = ApprovalStatus.ESCALATED
        request = await db.get(ApprovalRequest, step.request_id)
        if request and request.status == ApprovalStatus.PENDING:
            request.status = ApprovalStatus.ESCALATED
            escalated += 1
    await db.flush()
    return escalated


async def get_pending_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[ApprovalRequest]:
    """Return all PENDING/ESCALATED requests where user's roles match any step's required_role."""
    from app.models.role import Role
    from app.models.user import user_role

    # Get user's role names
    roles_q = (
        select(Role.name)
        .join(user_role, user_role.c.role_id == Role.id)
        .where(user_role.c.user_id == user_id)
    )
    user_roles = set((await db.execute(roles_q)).scalars().all())

    if not user_roles:
        return []

    # Find pending steps for these roles
    steps_q = select(ApprovalStep.request_id).where(
        ApprovalStep.status.in_([ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]),
        ApprovalStep.required_role.in_(user_roles),
    ).distinct()
    request_ids = list((await db.execute(steps_q)).scalars().all())

    if not request_ids:
        return []

    q = (
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps), selectinload(ApprovalRequest.requested_by))
        .where(
            ApprovalRequest.id.in_(request_ids),
            ApprovalRequest.status.in_([ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]),
        )
        .order_by(ApprovalRequest.created_at.desc())
    )
    return list((await db.execute(q)).scalars().all())
