"""BOM cost roll-up engine — raw materials, intermediates, packaging, by-products."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import AdvancedBOM, AdvancedBOMLine, ComponentType
from app.schemas.bom import CostingLine, CostingResult


_D = lambda v: Decimal(str(v))


async def _resolve_unit_cost(db: AsyncSession, line: AdvancedBOMLine) -> Decimal:
    """Look up unit cost from Material.standard_cost or Product.standard_cost."""
    from app.models.bom import ItemLinkType
    if line.unit_cost:
        return _D(line.unit_cost)
    if line.item_id:
        if line.item_type == ItemLinkType.MATERIAL:
            from app.models.master import Material
            r = await db.execute(select(Material).where(Material.id == line.item_id))
            m = r.scalar_one_or_none()
            if m and getattr(m, "standard_cost", None):
                return _D(m.standard_cost)
        else:
            from app.models.master import Product
            r = await db.execute(select(Product).where(Product.id == line.item_id))
            p = r.scalar_one_or_none()
            if p and getattr(p, "standard_cost", None):
                return _D(p.standard_cost)
    return _D("0")


async def compute_bom_cost(db: AsyncSession, bom_id: UUID) -> CostingResult:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom: AdvancedBOM = bom_r.scalar_one_or_none()
    if not bom:
        raise ValueError("BOM not found")

    lines_r = await db.execute(
        select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id).order_by(AdvancedBOMLine.line_no)
    )
    lines = lines_r.scalars().all()

    raw_cost = _D("0")
    intermediate_cost = _D("0")
    packaging_cost = _D("0")
    utility_cost = _D("0")
    by_product_credit = _D("0")

    costing_lines: List[CostingLine] = []

    for line in lines:
        uc = await _resolve_unit_cost(db, line)
        # effective qty including waste
        loss_factor = _D("1") + (_D(line.wastage_pct) + _D(line.process_loss_pct)) / _D("100")
        effective_qty = _D(line.required_qty) * loss_factor
        extended = (effective_qty * uc).quantize(Decimal("0.0001"))

        is_credit = line.component_type in (ComponentType.BY_PRODUCT, ComponentType.CO_PRODUCT)

        costing_lines.append(CostingLine(
            line_no=line.line_no,
            item_name=line.item_name,
            component_type=line.component_type.value,
            qty=effective_qty.quantize(Decimal("0.0001")),
            uom=line.required_uom,
            unit_cost=uc,
            extended_cost=extended,
            is_by_product_credit=is_credit,
        ))

        if is_credit:
            by_product_credit += extended
        elif line.component_type == ComponentType.RAW:
            raw_cost += extended
        elif line.component_type == ComponentType.INTERMEDIATE:
            intermediate_cost += extended
        elif line.component_type == ComponentType.PACKAGING:
            packaging_cost += extended
        elif line.component_type == ComponentType.UTILITY:
            utility_cost += extended

    total_cost = raw_cost + intermediate_cost + packaging_cost + utility_cost - by_product_credit
    base_qty = _D(bom.base_qty) if _D(bom.base_qty) > 0 else _D("1")
    cost_per_uom = (total_cost / base_qty).quantize(Decimal("0.0001"))

    # persist back to BOM header
    bom.standard_batch_cost = total_cost.quantize(Decimal("0.0001"))
    bom.standard_cost_per_uom = cost_per_uom
    bom.total_raw_cost = raw_cost.quantize(Decimal("0.0001"))
    bom.total_packaging_cost = packaging_cost.quantize(Decimal("0.0001"))
    bom.by_product_credit = by_product_credit.quantize(Decimal("0.0001"))
    bom.costing_updated_at = datetime.now(timezone.utc)
    await db.flush()

    return CostingResult(
        bom_id=str(bom.id),
        bom_code=bom.bom_code,
        bom_name=bom.bom_name,
        base_qty=_D(bom.base_qty),
        base_uom=bom.base_uom,
        raw_material_cost=raw_cost.quantize(Decimal("0.0001")),
        intermediate_cost=intermediate_cost.quantize(Decimal("0.0001")),
        packaging_cost=packaging_cost.quantize(Decimal("0.0001")),
        utility_cost=utility_cost.quantize(Decimal("0.0001")),
        by_product_credit=by_product_credit.quantize(Decimal("0.0001")),
        total_batch_cost=total_cost.quantize(Decimal("0.0001")),
        cost_per_uom=cost_per_uom,
        lines=costing_lines,
    )


async def compare_bom_versions(db: AsyncSession, bom_id_a: UUID, bom_id_b: UUID) -> dict:
    """Return diff between two BOM versions."""
    a_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id_a))
    b_r = await db.execute(select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id_b))
    a_lines = {l.item_name: l for l in a_r.scalars().all()}
    b_lines = {l.item_name: l for l in b_r.scalars().all()}

    added = [l for name, l in b_lines.items() if name not in a_lines]
    removed = [l for name, l in a_lines.items() if name not in b_lines]
    changed = []
    allergen_changes = []

    for name in set(a_lines) & set(b_lines):
        la, lb = a_lines[name], b_lines[name]
        diffs = {}
        if la.required_qty != lb.required_qty:
            diffs["required_qty"] = {"from": float(la.required_qty), "to": float(lb.required_qty)}
        if la.wastage_pct != lb.wastage_pct:
            diffs["wastage_pct"] = {"from": float(la.wastage_pct), "to": float(lb.wastage_pct)}
        if la.allergen_flag != lb.allergen_flag:
            diffs["allergen_flag"] = {"from": la.allergen_flag, "to": lb.allergen_flag}
            allergen_changes.append(f"{name}: allergen_flag changed {la.allergen_flag} → {lb.allergen_flag}")
        if la.allergen_types != lb.allergen_types:
            allergen_changes.append(f"{name}: allergen types changed {la.allergen_types} → {lb.allergen_types}")
        if diffs:
            changed.append({"item_name": name, "changes": diffs})

    # cost delta
    bom_a_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_a))
    bom_b_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id_b))
    bom_a = bom_a_r.scalar_one_or_none()
    bom_b = bom_b_r.scalar_one_or_none()
    cost_delta = None
    if bom_a and bom_b and bom_a.standard_batch_cost and bom_b.standard_batch_cost:
        cost_delta = float(bom_b.standard_batch_cost) - float(bom_a.standard_batch_cost)

    return {
        "added_lines": added,
        "removed_lines": removed,
        "changed_lines": changed,
        "allergen_changes": allergen_changes,
        "cost_delta": cost_delta,
    }
