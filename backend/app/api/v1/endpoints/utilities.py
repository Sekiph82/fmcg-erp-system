"""
Utilities Module API
────────────────────
/utilities/configs              – System configuration (key-value store)
/utilities/uom-conversions      – Unit-of-measure conversion factors
/utilities/number-series        – Document auto-numbering sequences
/utilities/number-series/{module}/next  – Get next document number
/utilities/currencies           – Currency registry and exchange rates
"""
import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import utilities as crud
from app.services import utilities_service as svc
from app.schemas.utilities import (
    SystemConfigCreate, SystemConfigUpdate, SystemConfigRead,
    UomConversionCreate, UomConversionUpdate, UomConversionRead,
    NumberSeriesCreate, NumberSeriesUpdate, NumberSeriesRead, NextNumberResponse,
    CurrencyCreate, CurrencyUpdate, CurrencyRead,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── System Configuration ───────────────────────────────────────────────────────

@router.get("/configs", response_model=List[SystemConfigRead],
            dependencies=[Depends(require_permission("utilities", "view"))])
async def list_configs(
    category: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_configs(db, category=category, skip=skip, limit=limit)


@router.get("/configs/{config_id}", response_model=SystemConfigRead,
            dependencies=[Depends(require_permission("utilities", "view"))])
async def get_config(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_config(db, config_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Config not found")
    return obj


@router.post("/configs", response_model=SystemConfigRead, status_code=201)
async def create_config(
    data: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    existing = await crud.get_config_by_key(db, data.key)
    if existing:
        raise HTTPException(status_code=409, detail=f"Config key '{data.key}' already exists")
    obj = await crud.create_config(db, data, user_id=current_user.id)
    await db.commit()
    logger.info("SystemConfig created: key=%s by user=%s", data.key, current_user.id)
    return obj


@router.patch("/configs/{config_id}", response_model=SystemConfigRead)
async def update_config(
    config_id: uuid.UUID,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "edit")),
):
    obj = await crud.get_config(db, config_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Config not found")
    if not obj.is_editable:
        raise HTTPException(status_code=409, detail="This configuration is read-only and cannot be edited")
    obj = await crud.update_config(db, obj, data, user_id=current_user.id)
    await db.commit()
    logger.info("SystemConfig updated: key=%s by user=%s", obj.key, current_user.id)
    return obj


@router.delete("/configs/{config_id}", status_code=204)
async def delete_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    obj = await crud.get_config(db, config_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Config not found")
    if not obj.is_editable:
        raise HTTPException(status_code=409, detail="This configuration is read-only and cannot be deleted")
    await crud.delete_config(db, obj)
    await db.commit()
    logger.info("SystemConfig deleted: key=%s by user=%s", obj.key, current_user.id)
    return Response(status_code=204)


# ── UOM Conversions ────────────────────────────────────────────────────────────

@router.get("/uom-conversions", response_model=List[UomConversionRead],
            dependencies=[Depends(require_permission("utilities", "view"))])
async def list_conversions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.list_conversions(db, skip=skip, limit=limit)


@router.get("/uom-conversions/{conversion_id}", response_model=UomConversionRead,
            dependencies=[Depends(require_permission("utilities", "view"))])
async def get_conversion(conversion_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=404, detail="UOM conversion not found")
    return obj


@router.post("/uom-conversions", response_model=UomConversionRead, status_code=201)
async def create_conversion(
    data: UomConversionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "edit")),
):
    existing = await crud.get_conversion_pair(db, data.from_uom, data.to_uom)
    if existing:
        raise HTTPException(status_code=409, detail=f"Conversion from '{data.from_uom}' to '{data.to_uom}' already exists")
    obj = await crud.create_conversion(db, data, user_id=current_user.id)
    await db.commit()
    logger.info("UomConversion created: %s→%s (factor=%s) by user=%s", data.from_uom, data.to_uom, data.factor, current_user.id)
    return obj


@router.patch("/uom-conversions/{conversion_id}", response_model=UomConversionRead)
async def update_conversion(
    conversion_id: uuid.UUID,
    data: UomConversionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "edit")),
):
    obj = await crud.get_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=404, detail="UOM conversion not found")
    obj = await crud.update_conversion(db, obj, data)
    await db.commit()
    return obj


@router.delete("/uom-conversions/{conversion_id}", status_code=204)
async def delete_conversion(
    conversion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    obj = await crud.get_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=404, detail="UOM conversion not found")
    await crud.delete_conversion(db, obj)
    await db.commit()
    return Response(status_code=204)


# ── Number Series ──────────────────────────────────────────────────────────────

@router.get("/number-series", response_model=List[NumberSeriesRead],
            dependencies=[Depends(require_permission("utilities", "view"))])
async def list_series(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.list_series(db, skip=skip, limit=limit)


@router.get("/number-series/{series_id}", response_model=NumberSeriesRead,
            dependencies=[Depends(require_permission("utilities", "view"))])
async def get_series(series_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_series(db, series_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Number series not found")
    return obj


@router.post("/number-series", response_model=NumberSeriesRead, status_code=201)
async def create_series(
    data: NumberSeriesCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    existing = await crud.get_series_by_module(db, data.module)
    if existing:
        raise HTTPException(status_code=409, detail=f"Number series for module '{data.module}' already exists")
    obj = await crud.create_series(db, data)
    await db.commit()
    logger.info("NumberSeries created: module=%s prefix=%s by user=%s", data.module, data.prefix, current_user.id)
    return obj


@router.patch("/number-series/{series_id}", response_model=NumberSeriesRead)
async def update_series(
    series_id: uuid.UUID,
    data: NumberSeriesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    obj = await crud.get_series(db, series_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Number series not found")
    obj = await crud.update_series(db, obj, data)
    await db.commit()
    logger.info("NumberSeries updated: module=%s by user=%s", obj.module, current_user.id)
    return obj


@router.delete("/number-series/{series_id}", status_code=204)
async def delete_series(
    series_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    obj = await crud.get_series(db, series_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Number series not found")
    await crud.delete_series(db, obj)
    await db.commit()
    return Response(status_code=204)


@router.post("/number-series/next/{module}", response_model=NextNumberResponse,
             summary="Get and increment the next document number for a module")
async def get_next_number(
    module: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "view")),
):
    """
    Atomically fetch and increment the sequence number for the given module.
    Returns the formatted number string (e.g. PO-0042).
    """
    result = await svc.get_next_number(db, module)
    await db.commit()
    logger.info("NextNumber issued: module=%s number=%s by user=%s", module, result.number, current_user.id)
    return result


# ── Currencies ─────────────────────────────────────────────────────────────────

@router.get("/currencies", response_model=List[CurrencyRead],
            dependencies=[Depends(require_permission("utilities", "view"))])
async def list_currencies(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.list_currencies(db, skip=skip, limit=limit)


@router.get("/currencies/{currency_id}", response_model=CurrencyRead,
            dependencies=[Depends(require_permission("utilities", "view"))])
async def get_currency(currency_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_currency(db, currency_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Currency not found")
    return obj


@router.post("/currencies", response_model=CurrencyRead, status_code=201)
async def create_currency(
    data: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    existing = await crud.get_currency_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Currency '{data.code}' already exists")
    if data.is_base:
        current_base = await crud.get_base_currency(db)
        if current_base:
            raise HTTPException(status_code=409, detail=f"Base currency is already set to '{current_base.code}'. Unset it first.")
    obj = await crud.create_currency(db, data)
    await db.commit()
    logger.info("Currency created: %s by user=%s", data.code, current_user.id)
    return obj


@router.patch("/currencies/{currency_id}", response_model=CurrencyRead)
async def update_currency(
    currency_id: uuid.UUID,
    data: CurrencyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "edit")),
):
    obj = await crud.get_currency(db, currency_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Currency not found")
    if data.is_base:
        current_base = await crud.get_base_currency(db)
        if current_base and current_base.id != currency_id:
            raise HTTPException(status_code=409, detail=f"Base currency is already set to '{current_base.code}'. Unset it first.")
    obj = await crud.update_currency(db, obj, data)
    await db.commit()
    logger.info("Currency updated: %s by user=%s", obj.code, current_user.id)
    return obj


@router.delete("/currencies/{currency_id}", status_code=204)
async def delete_currency(
    currency_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utilities", "manage")),
):
    obj = await crud.get_currency(db, currency_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Currency not found")
    if obj.is_base:
        raise HTTPException(status_code=409, detail="Cannot delete the base currency")
    await crud.delete_currency(db, obj)
    await db.commit()
    return Response(status_code=204)
