"""Batch scaling + bulk-to-pack conversion services."""
from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMConversionProfile,
    BasisType,
)
from app.schemas.bom import ScaledLine, ScalingResult, ConversionCalcResult


_D = lambda v: Decimal(str(v))


def _scale_line(line: AdvancedBOMLine, base_qty: Decimal, target_qty: Decimal) -> tuple[Decimal, Decimal, Optional[str]]:
    """Returns (scaled_qty, adjusted_qty, warning)."""
    if line.fixed_consumption or line.basis_type == BasisType.FIXED:
        scaled = _D(line.required_qty)
    elif line.basis_type == BasisType.PERCENTAGE:
        scaled = target_qty * _D(line.required_qty) / _D("100")
    elif line.basis_type == BasisType.PER_BATCH:
        scale_factor = target_qty / base_qty if base_qty > 0 else _D("1")
        scaled = _D(line.required_qty) * scale_factor
    elif line.basis_type == BasisType.PER_UNIT:
        scaled = _D(line.required_qty) * target_qty
    elif line.basis_type == BasisType.PER_100KG:
        scaled = _D(line.required_qty) * (target_qty / _D("100"))
    elif line.basis_type == BasisType.PER_1000L:
        scaled = _D(line.required_qty) * (target_qty / _D("1000"))
    else:
        scale_factor = target_qty / base_qty if base_qty > 0 else _D("1")
        scaled = _D(line.required_qty) * scale_factor

    loss_factor = _D("1") + (_D(line.wastage_pct) + _D(line.process_loss_pct)) / _D("100")
    adjusted = (scaled * loss_factor).quantize(Decimal("0.0001"))
    scaled = scaled.quantize(Decimal("0.0001"))

    # warning: critical component scaled to very small qty
    warning = None
    if line.critical_component and adjusted < _D("0.01"):
        warning = f"Critical component {line.item_name or ''} scales to very small qty — check minimum dosage"

    return scaled, adjusted, warning


async def scale_bom(db: AsyncSession, bom_id: UUID, target_qty: Decimal, target_uom: Optional[str] = None) -> ScalingResult:
    bom_r = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == bom_id))
    bom: AdvancedBOM = bom_r.scalar_one_or_none()
    if not bom:
        raise ValueError("BOM not found")

    lines_r = await db.execute(
        select(AdvancedBOMLine).where(AdvancedBOMLine.bom_id == bom_id).order_by(AdvancedBOMLine.line_no)
    )
    lines = lines_r.scalars().all()

    base_qty = _D(bom.base_qty)
    scale_factor = (target_qty / base_qty).quantize(Decimal("0.000001")) if base_qty > 0 else _D("1")

    scaled_lines: List[ScaledLine] = []
    for line in lines:
        scaled, adjusted, warning = _scale_line(line, base_qty, target_qty)
        scaled_lines.append(ScaledLine(
            line_no=line.line_no,
            item_name=line.item_name,
            item_code=line.item_code,
            component_type=line.component_type.value,
            basis_type=line.basis_type.value,
            original_qty=_D(line.required_qty),
            scaled_qty=scaled,
            adjusted_qty=adjusted,
            required_uom=line.required_uom,
            fixed_consumption=line.fixed_consumption,
            warning=warning,
        ))

    return ScalingResult(
        bom_id=str(bom.id),
        bom_code=bom.bom_code,
        original_base_qty=base_qty,
        target_qty=target_qty,
        scale_factor=scale_factor,
        lines=scaled_lines,
    )


async def calculate_conversion(db: AsyncSession, profile_id: UUID, source_qty: Decimal, source_uom: Optional[str] = None) -> ConversionCalcResult:
    r = await db.execute(select(BOMConversionProfile).where(BOMConversionProfile.id == profile_id))
    profile: BOMConversionProfile = r.scalar_one_or_none()
    if not profile:
        raise ValueError("Conversion profile not found")

    theoretical = source_qty * _D(profile.theoretical_conversion_ratio)

    startup_loss = theoretical * _D(profile.startup_loss_pct) / _D("100")
    shutdown_loss = theoretical * _D(profile.shutdown_loss_pct) / _D("100")
    reject = theoretical * _D(profile.packaging_reject_pct) / _D("100")
    residual = theoretical * _D(profile.residual_bulk_pct) / _D("100")
    purge = theoretical * _D(profile.line_purge_loss_pct) / _D("100")

    total_loss = startup_loss + shutdown_loss + reject + residual + purge
    expected_good = max(_D("0"), theoretical - total_loss)
    total_loss_pct = (total_loss / theoretical * _D("100")).quantize(Decimal("0.01")) if theoretical > 0 else _D("0")

    # Volume-based: if fill_volume set, calculate units
    fill_vol = _D(profile.standard_fill_volume) if profile.standard_fill_volume else None

    notes_parts = [
        f"From {float(source_qty):.2f} {source_uom or 'units'} of bulk:",
        f"  Theoretical yield = {float(theoretical):.1f} units",
        f"  Startup loss = {float(startup_loss):.1f} units ({float(profile.startup_loss_pct)}%)",
        f"  Shutdown loss = {float(shutdown_loss):.1f} units ({float(profile.shutdown_loss_pct)}%)",
        f"  Packaging rejects = {float(reject):.1f} units ({float(profile.packaging_reject_pct)}%)",
        f"  Residual bulk = {float(residual):.1f} units ({float(profile.residual_bulk_pct)}%)",
        f"  Expected good units = {float(expected_good):.0f}",
        f"  Total loss = {float(total_loss_pct):.2f}%",
    ]

    return ConversionCalcResult(
        source_qty=source_qty,
        source_uom=source_uom or bom_source_uom(profile),
        theoretical_units=theoretical.quantize(Decimal("0.01")),
        startup_loss_units=startup_loss.quantize(Decimal("0.01")),
        shutdown_loss_units=shutdown_loss.quantize(Decimal("0.01")),
        reject_units=reject.quantize(Decimal("0.01")),
        residual_units=residual.quantize(Decimal("0.01")),
        expected_good_units=expected_good.quantize(Decimal("0.01")),
        total_loss_pct=total_loss_pct,
        fill_volume_per_unit=fill_vol,
        notes="\n".join(notes_parts),
    )


def bom_source_uom(profile: BOMConversionProfile) -> str:
    return profile.fill_volume_uom or "UNIT"
