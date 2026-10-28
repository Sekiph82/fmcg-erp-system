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
    AdvancedBOM, AdvancedBOMLine, BOMSubstituteGroup, BOMSubstitute,
    ComponentType, BasisType,
)
from app.schemas.bom import ExplosionNode, ExplosionResult


_D = lambda v: Decimal(str(v))
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


def _scale_qty(line: AdvancedBOMLine, base_qty: Decimal, target_qty: Decimal) -> Decimal:
    """Scale required_qty based on basis_type and scale factor."""
    if line.fixed_consumption:
        return _D(line.required_qty)
    if line.basis_type == BasisType.FIXED:
        return _D(line.required_qty)
    if line.basis_type == BasisType.PERCENTAGE:
        return target_qty * _D(line.required_qty) / _D("100")
    if line.basis_type == BasisType.PER_BATCH:
        scale = target_qty / base_qty if base_qty > 0 else _D("1")
        return _D(line.required_qty) * scale
    if line.basis_type == BasisType.PER_UNIT:
        return _D(line.required_qty) * target_qty
    if line.basis_type == BasisType.PER_100KG:
        return _D(line.required_qty) * (target_qty / _D("100"))
    if line.basis_type == BasisType.PER_1000L:
        return _D(line.required_qty) * (target_qty / _D("1000"))
    # default: proportional
    scale = target_qty / base_qty if base_qty > 0 else _D("1")
    return _D(line.required_qty) * scale


def _adjusted_qty(scaled: Decimal, wastage_pct: Decimal, process_loss_pct: Decimal) -> Decimal:
    """Gross up quantity for waste and process loss."""
    factor = _D("1") + (wastage_pct + process_loss_pct) / _D("100")
    return (scaled * factor).quantize(Decimal("0.0001"))


async def _explode_node(
    db: AsyncSession,
    bom: AdvancedBOM,
    parent_item_name: str,
    target_qty: Decimal,
    level: int,
    flat: Dict[tuple[str, str, str, str, str], dict],
    path: tuple[UUID, ...],
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
                db, child_bom, line.item_name or "?", adj, level + 1, flat, current_path
            )
            node.children = children
            # Don't add to flat requirements — its children will be added
        else:
            # leaf node — aggregate into flat requirements
            item_type = _enum_code(line.item_type)
            component_type = _enum_code(line.component_type)
            item_id = str(line.item_id) if line.item_id is not None else ""
            item_code = str(line.item_code or "").strip().upper()
            item_name = str(line.item_name or "").strip()
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
                    "item_name": line.item_name or "Unknown",
                    "item_code": line.item_code,
                    "item_type": item_type,
                    "component_type": line.component_type.value,
                    "required_uom": line.required_uom,
                    "total_qty": Decimal("0"),
                    "total_adjusted_qty": Decimal("0"),
                    "allergen_flag": False,
                    "critical_component": False,
                }
            flat[key]["total_qty"] += scaled
            flat[key]["total_adjusted_qty"] += adj
            flat[key]["allergen_flag"] = flat[key]["allergen_flag"] or line.allergen_flag
            flat[key]["critical_component"] = flat[key]["critical_component"] or line.critical_component

        nodes.append(node)

    return nodes


async def explode_bom(db: AsyncSession, bom_id: UUID, target_qty: Optional[Decimal] = None) -> ExplosionResult:
    bom = await _load_bom_with_lines(db, bom_id)
    if not bom:
        raise ValueError("BOM not found")

    if target_qty is None:
        target_qty = _D(bom.base_qty)
    else:
        target_qty = _D(target_qty)
    if not target_qty.is_finite() or target_qty <= 0:
        raise BOMExplosionError("BOM explosion target quantity must be positive and finite")

    flat: Dict[tuple[str, str, str, str, str], dict] = {}
    nodes = await _explode_node(db, bom, bom.bom_name, target_qty, 1, flat, ())

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
