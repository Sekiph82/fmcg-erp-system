"""Batch scaling + bulk-to-pack conversion services."""
from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import (
    AdvancedBOM, AdvancedBOMLine, BOMConversionProfile,
    BasisType,
)
from app.models.master import Product
from app.schemas.bom import ScaledLine, ScalingResult, ConversionCalcResult
from app.services.utilities_service import convert_uom


_D = lambda v: Decimal(str(v))

_MASS_UOM_TO_GRAMS = {"G": Decimal("1"), "KG": Decimal("1000")}
_VOLUME_UOM_TO_ML = {"ML": Decimal("1"), "L": Decimal("1000")}


def _uom_code(value: object) -> str:
    return str(getattr(value, "value", value)).strip().upper()


def _convert_standard_bulk_uom(
    quantity: Decimal,
    from_uom: str,
    to_uom: str,
    density_g_per_ml: Optional[Decimal],
) -> Optional[Decimal]:
    """Convert canonical mass/volume units; return None for configured units."""
    source = _uom_code(from_uom)
    target = _uom_code(to_uom)
    if source == target:
        return quantity

    if source in _MASS_UOM_TO_GRAMS and target in _MASS_UOM_TO_GRAMS:
        return quantity * _MASS_UOM_TO_GRAMS[source] / _MASS_UOM_TO_GRAMS[target]
    if source in _VOLUME_UOM_TO_ML and target in _VOLUME_UOM_TO_ML:
        return quantity * _VOLUME_UOM_TO_ML[source] / _VOLUME_UOM_TO_ML[target]

    crosses_mass_and_volume = (
        source in _MASS_UOM_TO_GRAMS and target in _VOLUME_UOM_TO_ML
    ) or (
        source in _VOLUME_UOM_TO_ML and target in _MASS_UOM_TO_GRAMS
    )
    if not crosses_mass_and_volume:
        return None
    if density_g_per_ml is None:
        raise HTTPException(
            status_code=422,
            detail="A positive density_g_per_ml is required for mass/volume conversion",
        )

    density = _D(density_g_per_ml)
    if not density.is_finite() or density <= 0:
        raise HTTPException(
            status_code=422,
            detail="A positive finite density_g_per_ml is required for mass/volume conversion",
        )
    if source in _VOLUME_UOM_TO_ML:
        grams = quantity * _VOLUME_UOM_TO_ML[source] * density
        return grams / _MASS_UOM_TO_GRAMS[target]

    grams = quantity * _MASS_UOM_TO_GRAMS[source]
    millilitres = grams / density
    return millilitres / _VOLUME_UOM_TO_ML[target]


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
    """Calculate yield after normalizing input UOM to the profile's source basis.

    A linked source product supplies the canonical basis UOM. Without one, the
    caller must provide the UOM and that declared UOM is the profile's basis.
    """
    r = await db.execute(select(BOMConversionProfile).where(BOMConversionProfile.id == profile_id))
    profile: BOMConversionProfile = r.scalar_one_or_none()
    if not profile:
        raise ValueError("Conversion profile not found")

    profile_source_uom = None
    if profile.source_product_id is not None:
        product_result = await db.execute(
            select(Product.uom).where(Product.id == profile.source_product_id)
        )
        product_uom = product_result.scalar_one_or_none()
        if product_uom is None:
            raise HTTPException(status_code=404, detail="Source product not found")
        profile_source_uom = _uom_code(product_uom)

    input_uom = _uom_code(source_uom) if source_uom else profile_source_uom
    if not input_uom:
        raise HTTPException(
            status_code=422,
            detail="Source UOM is required when the conversion profile has no source product",
        )
    target_source_uom = profile_source_uom or input_uom

    normalized_qty = _convert_standard_bulk_uom(
        source_qty,
        input_uom,
        target_source_uom,
        profile.density_g_per_ml,
    )
    if normalized_qty is None:
        normalized_qty = await convert_uom(db, source_qty, input_uom, target_source_uom)

    theoretical = normalized_qty * _D(profile.theoretical_conversion_ratio)

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
        f"From {float(source_qty):.2f} {input_uom} of bulk:",
        f"  Normalized source quantity = {normalized_qty} {target_source_uom}",
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
        source_uom=input_uom,
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
