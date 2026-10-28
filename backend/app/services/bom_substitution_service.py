"""Policy-enforced, batch-specific BOM substitute approval workflow."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import audit as audit_crud
from app.models.bom import (
    AdvancedBOM,
    AdvancedBOMLine,
    BOMSubstitute,
    BOMSubstitutionDecision,
    BOMSubstitutionRequest,
    SubstitutionPolicy,
)
from app.models.master import Material, Product
from app.models.user import User
from app.services.bom_quantity_utils import calculate_substitute_qty


class SubstitutionWorkflowError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


def required_approver_roles(policy: SubstitutionPolicy) -> tuple[str, ...]:
    if policy == SubstitutionPolicy.PLANNER_APPROVAL:
        return ("PLANNER",)
    if policy == SubstitutionPolicy.QA_APPROVAL:
        return ("QUALITY",)
    if policy == SubstitutionPolicy.BOTH_REQUIRED:
        return ("PLANNER", "QUALITY")
    if policy == SubstitutionPolicy.SHORTAGE_ONLY:
        return ("PLANNER",)
    if policy == SubstitutionPolicy.EMERGENCY_ONLY:
        # Emergency use always requires independent planning and quality sign-off.
        return ("PLANNER", "QUALITY")
    return ()


async def verify_substitute_master_item(
    db: AsyncSession,
    substitute: BOMSubstitute,
    *,
    expected_item_type,
    required_uom: str,
):
    """Resolve the candidate to an active master item and reject implicit UOM conversion."""
    item_type = getattr(substitute.item_type, "value", substitute.item_type)
    expected_type = getattr(expected_item_type, "value", expected_item_type)
    if item_type != expected_type:
        raise ValueError("Substitute item type must match the BOM line item type")
    if substitute.item_id is None:
        raise ValueError("Substitute must be linked to an active material or product master item")
    model = Material if item_type == "MATERIAL" else Product
    item = await db.get(model, substitute.item_id)
    if item is None or not item.is_active:
        raise ValueError("Substitute master item is missing or inactive")
    master_code = item.code if item_type == "MATERIAL" else item.sku
    master_uom = getattr(item.uom, "value", item.uom)
    if substitute.item_code and substitute.item_code.strip().casefold() != master_code.strip().casefold():
        raise ValueError("Substitute code does not match the linked master item")
    if str(master_uom).strip().upper() != str(required_uom).strip().upper():
        raise ValueError(
            f"Substitute master UOM {master_uom} does not match BOM line UOM {required_uom}; "
            "an approved conversion is required before substitution"
        )
    return item


async def create_request(db: AsyncSession, body, actor: User) -> BOMSubstitutionRequest:
    line_result = await db.execute(
        select(AdvancedBOMLine)
        .where(AdvancedBOMLine.id == body.bom_line_id)
        .options(selectinload(AdvancedBOMLine.substitute_group), selectinload(AdvancedBOMLine.bom))
    )
    line = line_result.scalar_one_or_none()
    if line is None:
        raise SubstitutionWorkflowError(404, "BOM line not found")
    if line.bom_id != body.bom_id:
        raise SubstitutionWorkflowError(422, "The request BOM must be the BOM that directly owns the selected line")
    if line.child_bom_id is not None:
        raise SubstitutionWorkflowError(422, "Substitution requests are limited to leaf material lines")
    group = line.substitute_group
    if group is None or not group.is_active:
        raise SubstitutionWorkflowError(422, "BOM line must reference an active substitute group")
    if line.substitution_policy != group.policy:
        raise SubstitutionWorkflowError(409, "BOM line and substitute group policies differ; reconcile them before requesting substitution")
    roles = required_approver_roles(group.policy)
    if not roles:
        raise SubstitutionWorkflowError(422, "This BOM line policy does not permit substitutions")

    substitute_result = await db.execute(
        select(BOMSubstitute)
        .where(BOMSubstitute.id == body.substitute_id)
        .options(selectinload(BOMSubstitute.group))
    )
    substitute = substitute_result.scalar_one_or_none()
    if substitute is None or not substitute.is_active:
        raise SubstitutionWorkflowError(404, "Active substitute not found")
    if substitute.group_id != group.id:
        raise SubstitutionWorkflowError(422, "Selected substitute does not belong to the BOM line's group")
    try:
        await verify_substitute_master_item(
            db, substitute, expected_item_type=line.item_type, required_uom=line.required_uom
        )
    except ValueError as exc:
        raise SubstitutionWorkflowError(422, str(exc)) from exc

    if group.policy in (SubstitutionPolicy.SHORTAGE_ONLY, SubstitutionPolicy.EMERGENCY_ONLY):
        if not body.shortage_evidence_reference:
            raise SubstitutionWorkflowError(422, "A traceable shortage evidence reference is required by this policy")
    if group.policy == SubstitutionPolicy.EMERGENCY_ONLY:
        if len(body.reason.strip()) < 5:
            raise SubstitutionWorkflowError(422, "Emergency requests require a written reason")

    request = BOMSubstitutionRequest(
        bom_id=line.bom_id,
        bom_line_id=line.id,
        substitute_id=substitute.id,
        policy=group.policy.value,
        target_qty=body.target_qty,
        substitute_qty=calculate_substitute_qty(
            line, line.bom.base_qty, body.target_qty, substitute.qty_ratio
        ),
        context_reference=body.context_reference,
        reason=body.reason,
        shortage_evidence_reference=body.shortage_evidence_reference,
        requested_by_id=actor.id,
        requester_email=actor.email,
        requester_name=actor.full_name,
        status="PENDING",
        decisions=[],
        substitute=substitute,
    )
    db.add(request)
    await db.flush()
    await db.refresh(request)
    await audit_crud.log_event(
        db,
        event_type="BOM_SUBSTITUTION_REQUESTED",
        actor_id=actor.id,
        actor_email=actor.email,
        actor_name=actor.full_name,
        module="bom",
        target_type="bom_substitution_request",
        target_id=str(request.id),
        target_name=substitute.item_name or substitute.item_code,
        after_value={
            "bom_line_id": str(line.id),
            "substitute_id": str(substitute.id),
            "policy": group.policy.value,
            "target_qty": str(body.target_qty),
            "substitute_qty": str(request.substitute_qty),
            "status": request.status,
        },
        details={
            "context_reference": body.context_reference,
            "shortage_evidence_reference": body.shortage_evidence_reference,
            "required_approver_roles": list(roles),
        },
    )
    return request


async def list_requests(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    limit: int = 100,
) -> list[BOMSubstitutionRequest]:
    query = (
        select(BOMSubstitutionRequest)
        .options(selectinload(BOMSubstitutionRequest.decisions), selectinload(BOMSubstitutionRequest.substitute))
        .order_by(BOMSubstitutionRequest.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(BOMSubstitutionRequest.status == status.upper())
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def list_group_lines(db: AsyncSession, group_id: UUID) -> list[dict]:
    result = await db.execute(
        select(AdvancedBOMLine)
        .where(
            AdvancedBOMLine.substitute_group_id == group_id,
            AdvancedBOMLine.child_bom_id.is_(None),
        )
        .options(selectinload(AdvancedBOMLine.bom))
        .order_by(AdvancedBOMLine.line_no)
    )
    lines = result.scalars().all()
    return [
        {
            "id": line.id,
            "bom_id": line.bom_id,
            "bom_code": line.bom.bom_code,
            "bom_name": line.bom.bom_name,
            "line_no": line.line_no,
            "item_name": line.item_name,
            "item_code": line.item_code,
            "required_qty": line.required_qty,
            "required_uom": line.required_uom,
        }
        for line in lines
    ]


async def decide_request(
    db: AsyncSession,
    request_id: UUID,
    *,
    approver_role: str,
    decision: str,
    reason: str,
    actor: User,
) -> BOMSubstitutionRequest:
    approver_role = approver_role.upper()
    decision = decision.upper()
    if approver_role not in ("PLANNER", "QUALITY") or decision not in ("APPROVED", "REJECTED"):
        raise SubstitutionWorkflowError(422, "Invalid approver role or decision")

    result = await db.execute(
        select(BOMSubstitutionRequest)
        .where(BOMSubstitutionRequest.id == request_id)
        .options(
            selectinload(BOMSubstitutionRequest.decisions),
            selectinload(BOMSubstitutionRequest.bom_line)
            .selectinload(AdvancedBOMLine.substitute_group),
            selectinload(BOMSubstitutionRequest.bom_line).selectinload(AdvancedBOMLine.bom),
            selectinload(BOMSubstitutionRequest.substitute),
        )
        .with_for_update()
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise SubstitutionWorkflowError(404, "Substitution request not found")
    if request.status != "PENDING":
        raise SubstitutionWorkflowError(409, "Only pending substitution requests can receive decisions")
    if request.requested_by_id == actor.id or request.requester_email.casefold() == actor.email.casefold():
        raise SubstitutionWorkflowError(403, "The requester cannot approve or reject their own substitution request")

    group = request.bom_line.substitute_group
    if (
        group is None
        or not group.is_active
        or request.substitute.group_id != group.id
        or group.policy.value != request.policy
        or request.bom_line.substitution_policy != group.policy
    ):
        raise SubstitutionWorkflowError(409, "The BOM substitution policy or group changed; submit a new request")
    current_substitute_qty = calculate_substitute_qty(
        request.bom_line,
        request.bom_line.bom.base_qty,
        request.target_qty,
        request.substitute.qty_ratio,
    )
    if current_substitute_qty != request.substitute_qty:
        raise SubstitutionWorkflowError(
            409, "BOM quantities, loss factors, or substitute ratio changed; submit a new request"
        )
    policy = SubstitutionPolicy(request.policy)
    required_roles = required_approver_roles(policy)
    if approver_role not in required_roles:
        raise SubstitutionWorkflowError(403, f"This policy does not require {approver_role.lower()} approval")
    if any(d.approver_role == approver_role for d in request.decisions):
        raise SubstitutionWorkflowError(409, f"A {approver_role.lower()} decision has already been recorded")
    if any(
        d.actor_id == actor.id or d.actor_email.casefold() == actor.email.casefold()
        for d in request.decisions
    ):
        raise SubstitutionWorkflowError(403, "Planner and quality decisions must be made by different users")

    entry = BOMSubstitutionDecision(
        request_id=request.id,
        approver_role=approver_role,
        decision=decision,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_name=actor.full_name,
        reason=reason.strip(),
    )
    db.add(entry)
    request.decisions.append(entry)
    await db.flush()
    decisions = list(request.decisions)
    if decision == "REJECTED":
        request.status = "REJECTED"
    elif all(any(d.approver_role == role and d.decision == "APPROVED" for d in decisions) for role in required_roles):
        request.status = "APPROVED"
    else:
        request.status = "PENDING"

    await audit_crud.log_event(
        db,
        event_type=f"BOM_SUBSTITUTION_{decision}",
        actor_id=actor.id,
        actor_email=actor.email,
        actor_name=actor.full_name,
        module="bom",
        target_type="bom_substitution_request",
        target_id=str(request.id),
        after_value={
            "status": request.status,
            "approver_role": approver_role,
            "decision": decision,
            "approval_decisions": [
                {"role": d.approver_role, "decision": d.decision, "actor_id": str(d.actor_id)}
                for d in decisions
            ],
        },
        details={"reason": reason.strip(), "policy": policy.value},
    )
    await db.flush()
    return request
