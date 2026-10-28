"""Shared BOM quantity scaling helpers for planning, explosion, and substitution."""
from __future__ import annotations

from decimal import Decimal

from app.models.bom import AdvancedBOMLine, BasisType


def decimal_value(value) -> Decimal:
    return Decimal(str(value))


def scale_bom_line_qty(line: AdvancedBOMLine, base_qty: Decimal, target_qty: Decimal) -> Decimal:
    """Scale required_qty according to the line basis and batch target."""
    if line.fixed_consumption or line.basis_type == BasisType.FIXED:
        return decimal_value(line.required_qty)
    if line.basis_type == BasisType.PERCENTAGE:
        return target_qty * decimal_value(line.required_qty) / decimal_value("100")
    if line.basis_type == BasisType.PER_BATCH:
        scale = target_qty / base_qty if base_qty > 0 else decimal_value("1")
        return decimal_value(line.required_qty) * scale
    if line.basis_type == BasisType.PER_UNIT:
        return decimal_value(line.required_qty) * target_qty
    if line.basis_type == BasisType.PER_100KG:
        return decimal_value(line.required_qty) * (target_qty / decimal_value("100"))
    if line.basis_type == BasisType.PER_1000L:
        return decimal_value(line.required_qty) * (target_qty / decimal_value("1000"))
    scale = target_qty / base_qty if base_qty > 0 else decimal_value("1")
    return decimal_value(line.required_qty) * scale


def adjusted_bom_line_qty(scaled: Decimal, wastage_pct: Decimal, process_loss_pct: Decimal) -> Decimal:
    factor = decimal_value("1") + (wastage_pct + process_loss_pct) / decimal_value("100")
    return (scaled * factor).quantize(decimal_value("0.0001"))


def calculate_substitute_qty(line: AdvancedBOMLine, base_qty: Decimal, target_qty: Decimal, qty_ratio) -> Decimal:
    """Derive the approved substitute quantity from the current BOM inputs."""
    adjusted = adjusted_bom_line_qty(
        scale_bom_line_qty(line, decimal_value(base_qty), decimal_value(target_qty)),
        decimal_value(line.wastage_pct),
        decimal_value(line.process_loss_pct),
    )
    return (adjusted * decimal_value(qty_ratio)).quantize(decimal_value("0.0001"))
