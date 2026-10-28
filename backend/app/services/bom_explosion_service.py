"""
Multi-Level BOM Explosion Engine.

Recursive algorithm:
  1. Load BOM header + lines
  2. For each line, if it has a child_bom_id → recurse into child BOM
  3. Adjust quantities by scale factor + waste/loss at each level
  4. Build tree of ExplosionNode + flat leaf-level requirements
  5. Aggregate leaf requirements across phantom/intermediate levels
"""
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMSubstituteGroup, BOMSubstitute, BOMSubstitutionRequest,
    ComponentType, BasisType, SubstitutionPolicy,
)
from app.schemas.bom import ExplosionNode, ExplosionResult
from app.services.bom_substitution_service import required_approver_roles, verify_substitute_master_item
from app.services.bom_quantity_utils import (
    decimal_value as _D,
    scale_bom_line_qty as _scale_qty,
    adjusted_bom_line_qty as _adjusted_qty,
    calculate_substitute_qty,
)


_MAX_DEPTH = 10


class BOMExplosionError(ValueError):
    """Raised when a nested BOM cannot be exploded without losing requirements."""


def _enum_code(value) -> str:
    return str(getattr(value, "value", value) or "").strip().upper()


async def _load_bom_with_lines(db: AsyncSession, bom_id: UUID) -> Optional[AdvancedBOM]:
    r = await db.execute(
        select(AdvancedBOM)
        .where(AdvancedBOM.id == bom_id)
        .options(
            selectinload(AdvancedBOM.lines)
            .selectinload(AdvancedBOMLine.substitute_group)
            .selectinload(BOMSubstituteGroup.substitutes)
        )
    )
    return r.scalar_one_or_none()


async def _explode_node(
    db: AsyncSession,
    bom: AdvancedBOM,
    parent_item_name: str,
    target_qty: Decimal,
    level: int,
    flat: Dict[tuple[str, str, str, str, str], dict],
    path: tuple[UUID, ...],
    substitution_requests: dict[str, BOMSubstitutionRequest],
    applied_request_ids: set[str],
) -> List[ExplosionNode]:
    path_codes = " -> ".join(str(item_id) for item_id in (*path, bom.id))
    if level > _MAX_DEPTH:
        raise BOMExplosionError(f"BOM nesting exceeds maximum depth {_MAX_DEPTH}: {path_codes}")
    if bom.id in path:
        raise BOMExplosionError(f"BOM cycle detected: {path_codes}")
    current_path = (*path, bom.id)
    base_qty = _D(bom.base_qty)
    if not base_qty.is_finite() or base_qty <= 0:
        raise BOMExplosionError(
            f"BOM {bom.bom_code} must have a positive finite base quantity"
        )

    nodes: List[ExplosionNode] = []

    for line in bom.lines:
        scaled = _scale_qty(line, base_qty, target_qty)
        adj = _adjusted_qty(scaled, _D(line.wastage_pct), _D(line.process_loss_pct))
        substitution = substitution_requests.get(str(line.id))
        if substitution is not None and substitution.bom_id != bom.id:
            raise BOMExplosionError(
                "Approved substitution request BOM does not directly own the matched BOM line"
            )
        if substitution is not None and line.child_bom_id is not None:
            raise BOMExplosionError("Approved substitutions cannot replace intermediate BOM lines")
        if substitution is not None and (
            line.substitute_group_id is None
            or substitution.substitute.group_id != line.substitute_group_id
            or not line.substitute_group
            or not line.substitute_group.is_active
            or _enum_code(line.substitute_group.policy) != substitution.policy
            or _enum_code(line.substitution_policy) != substitution.policy
        ):
            raise BOMExplosionError("Approved substitution no longer matches the BOM line's active group")
        verified_substitute = None
        if substitution is not None:
            current_substitute_qty = calculate_substitute_qty(
                line, base_qty, target_qty, substitution.substitute.qty_ratio
            )
            if current_substitute_qty != _D(substitution.substitute_qty):
                raise BOMExplosionError(
                    "BOM quantities, loss factors, or substitute ratio changed after the request; submit a new request"
                )
            request_id = str(substitution.id)
            if request_id in applied_request_ids:
                raise BOMExplosionError("A substitution request cannot be reused for repeated nested BOM occurrences")
            try:
                verified_substitute = await verify_substitute_master_item(
                    db,
                    substitution.substitute,
                    expected_item_type=line.item_type,
                    required_uom=line.required_uom,
                )
            except ValueError as exc:
                raise BOMExplosionError(str(exc)) from exc

        # substitute options
        subs: List[str] = []
        if line.substitute_group and line.substitute_group.substitutes:
            subs = [s.item_name or "unknown" for s in line.substitute_group.substitutes if s.is_active]

        node = ExplosionNode(
            level=level,
            line_id=str(line.id),
            bom_id=str(bom.id),
            bom_code=bom.bom_code,
            parent_item_name=parent_item_name,
            item_name=line.item_name or "Unknown",
            item_code=line.item_code,
            component_type=line.component_type.value,
            required_qty=scaled.quantize(Decimal("0.0001")),
            adjusted_qty=adj,
            required_uom=line.required_uom,
            wastage_pct=_D(line.wastage_pct),
            process_loss_pct=_D(line.process_loss_pct),
            basis_type=line.basis_type.value,
            consumption_stage=line.consumption_stage,
            allergen_flag=line.allergen_flag,
            critical_component=line.critical_component,
            substitutes=subs,
            applied_substitute=(
                verified_substitute.name or substitution.substitute.item_code
                if substitution is not None else None
            ),
            applied_substitute_qty=(
                _D(substitution.substitute_qty).quantize(Decimal("0.0001"))
                if substitution is not None else None
            ),
            substitution_request_id=str(substitution.id) if substitution is not None else None,
        )

        # Recurse if has child BOM (intermediate / multi-level)
        if line.child_bom_id:
            child_bom = await _load_bom_with_lines(db, line.child_bom_id)
            if child_bom is None:
                raise BOMExplosionError(
                    f"Child BOM {line.child_bom_id} referenced by line {line.id} is missing or unavailable"
                )
            if _enum_code(line.required_uom) != _enum_code(child_bom.base_uom):
                raise BOMExplosionError(
                    f"Child BOM UOM {child_bom.base_uom} does not match line UOM {line.required_uom} "
                    f"for line {line.id}"
                )
            children = await _explode_node(
                db, child_bom, line.item_name or "?", adj, level + 1, flat, current_path,
                substitution_requests, applied_request_ids,
            )
            node.children = children
            # Don't add to flat requirements — its children will be added
        else:
            # leaf node — aggregate into flat requirements
            source_item = verified_substitute if substitution is not None else line
            item_type = _enum_code(substitution.substitute.item_type if substitution is not None else line.item_type)
            component_type = _enum_code(line.component_type)
            if substitution is not None:
                item_id = str(source_item.id)
                item_code = str(source_item.code if item_type == "MATERIAL" else source_item.sku or "").strip().upper()
                item_name = str(source_item.name or "").strip()
            else:
                item_id = str(source_item.item_id) if source_item.item_id is not None else ""
                item_code = str(source_item.item_code or "").strip().upper()
                item_name = str(source_item.item_name or "").strip()
            if item_id:
                identity_kind, identity_value = "ID", item_id
            elif item_code:
                identity_kind, identity_value = "CODE", item_code
            elif item_name:
                identity_kind, identity_value = "NAME", " ".join(item_name.casefold().split())
            else:
                raise BOMExplosionError(
                    f"Leaf BOM line {line.id} has no item ID, code, or name"
                )
            key = (
                item_type,
                component_type,
                identity_kind,
                identity_value,
                _enum_code(line.required_uom),
            )
            if key not in flat:
                flat[key] = {
                    "item_name": item_name or "Unknown",
                    "item_code": item_code or None,
                    "item_type": item_type,
                    "component_type": line.component_type.value,
                    "required_uom": line.required_uom,
                    "total_qty": Decimal("0"),
                    "total_adjusted_qty": Decimal("0"),
                    "allergen_flag": False,
                    "critical_component": False,
                }
            if substitution is not None:
                flat[key]["total_qty"] += _D(substitution.substitute_qty)
                flat[key]["total_adjusted_qty"] += _D(substitution.substitute_qty)
                applied_request_ids.add(str(substitution.id))
            else:
                flat[key]["total_qty"] += scaled
                flat[key]["total_adjusted_qty"] += adj
            flat[key]["allergen_flag"] = flat[key]["allergen_flag"] or line.allergen_flag
            flat[key]["critical_component"] = flat[key]["critical_component"] or line.critical_component

        nodes.append(node)

    return nodes


async def explode_bom(
    db: AsyncSession,
    bom_id: UUID,
    target_qty: Optional[Decimal] = None,
    substitution_request_ids: Optional[List[UUID]] = None,
    context_reference: Optional[str] = None,
) -> ExplosionResult:
    bom = await _load_bom_with_lines(db, bom_id)
    if not bom:
        raise ValueError("BOM not found")

    if target_qty is None:
        target_qty = _D(bom.base_qty)
    else:
        target_qty = _D(target_qty)
    if not target_qty.is_finite() or target_qty <= 0:
        raise BOMExplosionError("BOM explosion target quantity must be positive and finite")

    substitution_requests: dict[str, BOMSubstitutionRequest] = {}
    if substitution_request_ids:
        if not context_reference or not context_reference.strip():
            raise BOMExplosionError("An approved substitution must be applied with its exact production/order context reference")
        if len(set(substitution_request_ids)) != len(substitution_request_ids):
            raise BOMExplosionError("A substitution request may only be supplied once")
        request_result = await db.execute(
            select(BOMSubstitutionRequest)
            .where(BOMSubstitutionRequest.id.in_(substitution_request_ids))
            .options(selectinload(BOMSubstitutionRequest.substitute).selectinload(BOMSubstitute.group))
            .options(selectinload(BOMSubstitutionRequest.decisions))
        )
        requests = list(request_result.scalars().unique().all())
        if len(requests) != len(substitution_request_ids):
            raise BOMExplosionError("One or more substitution requests do not exist")
        for request in requests:
            if request.status != "APPROVED":
                raise BOMExplosionError("Only fully approved substitution requests may be applied")
            if request.bom_id != bom.id:
                raise BOMExplosionError("Approved substitution request belongs to a different BOM")
            if _D(request.target_qty) != target_qty:
                raise BOMExplosionError("Approved substitution request is for a different BOM target quantity")
            if request.context_reference != context_reference.strip():
                raise BOMExplosionError("Approved substitution request belongs to a different production/order context")
            try:
                required_roles = required_approver_roles(SubstitutionPolicy(request.policy))
            except ValueError as exc:
                raise BOMExplosionError("Approved substitution request has an unknown policy") from exc
            decisions = {decision.approver_role: decision for decision in request.decisions}
            if not required_roles or any(
                role not in decisions or decisions[role].decision != "APPROVED"
                for role in required_roles
            ):
                raise BOMExplosionError("Substitution request status does not have its required approval evidence")
            approvers = [decisions[role] for role in required_roles]
            identities = [decision.actor_email.casefold() for decision in approvers]
            if len(set(identities)) != len(identities) or any(
                decision.actor_id == request.requested_by_id
                or decision.actor_email.casefold() == request.requester_email.casefold()
                for decision in approvers
            ):
                raise BOMExplosionError("Substitution approval evidence violates independent-review requirements")
            if not request.substitute.is_active or not request.substitute.group.is_active:
                raise BOMExplosionError("Approved substitute or substitute group is no longer active")
            line_id = str(request.bom_line_id)
            if line_id in substitution_requests:
                raise BOMExplosionError("Only one substitution request may target a BOM line per explosion")
            substitution_requests[line_id] = request

    flat: Dict[tuple[str, str, str, str, str], dict] = {}
    applied_request_ids: set[str] = set()
    nodes = await _explode_node(
        db, bom, bom.bom_name, target_qty, 1, flat, (), substitution_requests, applied_request_ids
    )
    if applied_request_ids != {str(request.id) for request in substitution_requests.values()}:
        raise BOMExplosionError("A substitution request does not target a line in this BOM explosion")

    def _depth(n: ExplosionNode) -> int:
        if not n.children:
            return 1
        return 1 + max(_depth(c) for c in n.children)

    total_levels = max((_depth(n) for n in nodes), default=1)

    flat_list = [
        {**v, "total_qty": float(v["total_qty"].quantize(Decimal("0.0001"))),
         "total_adjusted_qty": float(v["total_adjusted_qty"].quantize(Decimal("0.0001")))}
        for v in flat.values()
    ]

    return ExplosionResult(
        bom_id=str(bom.id),
        bom_code=bom.bom_code,
        bom_name=bom.bom_name,
        target_qty=target_qty,
        target_uom=bom.base_uom,
        total_levels=total_levels,
        nodes=nodes,
        flat_requirements=flat_list,
    )
