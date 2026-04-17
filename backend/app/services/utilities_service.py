"""
Utilities service layer.

Provides:
  - get_next_number(module)   → formatted document number string
  - get_setting(key)         → raw value string (or None)
  - convert_uom(qty, from, to) → converted quantity
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utilities import NumberSeries, SystemConfig, UomConversion
from app.schemas.utilities import NextNumberResponse

logger = logging.getLogger(__name__)


async def get_next_number(db: AsyncSession, module: str) -> NextNumberResponse:
    """
    Atomically increment the sequence for `module` and return the formatted number.
    Uses SELECT FOR UPDATE to prevent race conditions.
    Raises 404 if no active series exists for the module.
    """
    result = await db.execute(
        select(NumberSeries)
        .where(NumberSeries.module == module, NumberSeries.is_active == True)  # noqa: E712
        .with_for_update()
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail=f"No active number series found for module '{module}'")

    series.current_number += 1
    seq = series.current_number
    padded = str(seq).zfill(series.padding)
    formatted = f"{series.prefix}{padded}"
    if series.suffix:
        formatted += series.suffix

    await db.flush()
    return NextNumberResponse(module=module, number=formatted, sequence=seq)


async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """Return the raw value of a system config key, or None if not found."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    cfg = result.scalar_one_or_none()
    return cfg.value if cfg else None


async def convert_uom(db: AsyncSession, quantity: Decimal, from_uom: str, to_uom: str) -> Decimal:
    """
    Convert `quantity` from `from_uom` to `to_uom`.
    Looks for a direct conversion factor first, then tries the inverse.
    Raises 422 if no conversion path exists.
    """
    if from_uom == to_uom:
        return quantity

    # Direct conversion
    result = await db.execute(
        select(UomConversion).where(
            UomConversion.from_uom == from_uom,
            UomConversion.to_uom == to_uom,
            UomConversion.is_active == True,  # noqa: E712
        )
    )
    conversion = result.scalar_one_or_none()
    if conversion:
        return quantity * conversion.factor

    # Try inverse
    result = await db.execute(
        select(UomConversion).where(
            UomConversion.from_uom == to_uom,
            UomConversion.to_uom == from_uom,
            UomConversion.is_active == True,  # noqa: E712
        )
    )
    inverse = result.scalar_one_or_none()
    if inverse and inverse.factor != 0:
        return quantity / inverse.factor

    raise HTTPException(
        status_code=422,
        detail=f"No UOM conversion path found between '{from_uom}' and '{to_uom}'",
    )
