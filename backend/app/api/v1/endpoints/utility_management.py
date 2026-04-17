"""
Utility Management API
──────────────────────
/utility-management/asset-categories          – Asset category master
/utility-management/asset-categories/export   – CSV export
/utility-management/assets                    – Asset register
/utility-management/assets/export             – CSV export
/utility-management/devices                   – Meters & sensors register
/utility-management/devices/export            – CSV export
/utility-management/readings                  – Utility readings ledger
/utility-management/readings/export           – CSV export
/utility-management/transactions              – Unified transaction backbone
/utility-management/transactions/export       – CSV export
/utility-management/transactions/summary      – Aggregated summary
"""
from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.db.session import get_db
from app.crud import utility_management as crud
from app.models.utility_management import (
    UtilityAssetStatus,
    LifecycleStatus,
    CriticalityLevel,
    UtilityType,
    DeviceType,
    ReadingType,
    ReadingSource,
    ReadingFrequency,
    ValidatedStatus,
    SourceMethod,
    TxReferenceType,
    DataQuality,
)
from app.schemas.utility_management import (
    UtilityAssetCategoryCreate,
    UtilityAssetCategoryRead,
    UtilityAssetCategoryUpdate,
    UtilityAssetCreate,
    UtilityAssetRead,
    UtilityAssetUpdate,
    UtilityDeviceCreate,
    UtilityDeviceRead,
    UtilityDeviceUpdate,
    UtilityReadingCreate,
    UtilityReadingRead,
    UtilityReadingValidate,
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionUpdate,
    UtilityTransactionSummary,
)
from app.services.utility_reading_service import ingest_reading, _enrich_reading
from app.services.utility_transaction_service import (
    create_transaction as svc_create_transaction,
    enrich_transaction,
    build_summary,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────

def _enrich_category(obj, asset_count: int) -> UtilityAssetCategoryRead:
    data = UtilityAssetCategoryRead.model_validate(obj)
    data.asset_count = asset_count
    return data


def _enrich_asset(obj) -> UtilityAssetRead:
    data = UtilityAssetRead(
        id=obj.id,
        asset_no=obj.asset_no,
        name=obj.name,
        description=obj.description,
        category_id=obj.category_id,
        utility_type=obj.utility_type,
        subsystem=obj.subsystem,
        location=obj.location,
        building_area=obj.building_area,
        department=obj.department,
        line_id=obj.line_id,
        machine_id=obj.machine_id,
        parent_asset_id=obj.parent_asset_id,
        manufacturer=obj.manufacturer,
        equipment_model=obj.model,
        serial_no=obj.serial_no,
        install_date=obj.install_date,
        warranty_expiry=obj.warranty_expiry,
        rated_capacity=obj.rated_capacity,
        capacity_unit=obj.capacity_unit,
        rated_power=obj.rated_power,
        rated_power_unit=obj.rated_power_unit,
        flow_capacity=obj.flow_capacity,
        pressure_capacity=obj.pressure_capacity,
        temperature_range=obj.temperature_range,
        status=obj.status,
        lifecycle_status=obj.lifecycle_status,
        criticality_level=obj.criticality_level,
        maintenance_strategy=obj.maintenance_strategy,
        is_active=obj.is_active,
        notes=obj.notes,
        # Denormalised
        category_code=obj.category.code if obj.category else None,
        category_name=obj.category.name if obj.category else None,
        parent_asset_no=obj.parent_asset.asset_no if obj.parent_asset else None,
    )
    return data


# ── Asset Categories ───────────────────────────────────────────────────────────

@router.get(
    "/asset-categories",
    response_model=List[UtilityAssetCategoryRead],
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def list_categories(
    utility_type: Optional[UtilityType] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    cats = await crud.list_categories(
        db,
        utility_type=utility_type,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    result = []
    for c in cats:
        count = await crud.count_assets_for_category(db, c.id)
        result.append(_enrich_category(c, count))
    return result


@router.get(
    "/asset-categories/export/csv",
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def export_categories_csv(db: AsyncSession = Depends(get_db)):
    cats = await crud.list_categories(db, limit=10000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "name", "utility_type", "default_unit", "description", "is_active"])
    for c in cats:
        w.writerow([c.code, c.name, c.utility_type.value, c.default_unit or "", c.description or "", c.is_active])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=utility_asset_categories.csv"},
    )


@router.get(
    "/asset-categories/{category_id}",
    response_model=UtilityAssetCategoryRead,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Category not found")
    count = await crud.count_assets_for_category(db, obj.id)
    return _enrich_category(obj, count)


@router.post(
    "/asset-categories",
    response_model=UtilityAssetCategoryRead,
    status_code=201,
)
async def create_category(
    data: UtilityAssetCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "create")),
):
    existing = await crud.get_category_by_code(db, data.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Category code '{data.code}' already exists",
        )
    obj = await crud.create_category(db, data, user_id=current_user.id)
    await db.commit()
    logger.info("UtilityAssetCategory created: code=%s by user=%s", obj.code, current_user.id)
    return _enrich_category(obj, 0)


@router.patch(
    "/asset-categories/{category_id}",
    response_model=UtilityAssetCategoryRead,
)
async def update_category(
    category_id: uuid.UUID,
    data: UtilityAssetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "edit")),
):
    obj = await crud.get_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Category not found")
    obj = await crud.update_category(db, obj, data)
    await db.commit()
    logger.info("UtilityAssetCategory updated: code=%s by user=%s", obj.code, current_user.id)
    count = await crud.count_assets_for_category(db, obj.id)
    return _enrich_category(obj, count)


@router.delete("/asset-categories/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "delete")),
):
    obj = await crud.get_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Category not found")
    count = await crud.count_assets_for_category(db, obj.id)
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete category — {count} asset(s) are assigned to it. "
                   "Reassign or delete those assets first.",
        )
    await crud.delete_category(db, obj)
    await db.commit()
    logger.info("UtilityAssetCategory deleted: code=%s by user=%s", obj.code, current_user.id)
    return Response(status_code=204)


# ── Utility Assets ─────────────────────────────────────────────────────────────

@router.get(
    "/assets",
    response_model=List[UtilityAssetRead],
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def list_assets(
    utility_type: Optional[UtilityType] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    department: Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id: Optional[str] = Query(None),
    machine_id: Optional[str] = Query(None),
    status: Optional[UtilityAssetStatus] = Query(None),
    lifecycle_status: Optional[LifecycleStatus] = Query(None),
    criticality_level: Optional[CriticalityLevel] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    assets = await crud.list_assets(
        db,
        utility_type=utility_type,
        category_id=category_id,
        department=department,
        building_area=building_area,
        line_id=line_id,
        machine_id=machine_id,
        status=status,
        lifecycle_status=lifecycle_status,
        criticality_level=criticality_level,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    return [_enrich_asset(a) for a in assets]


@router.get(
    "/assets/export/csv",
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def export_assets_csv(db: AsyncSession = Depends(get_db)):
    assets = await crud.list_assets(db, limit=10000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "asset_no", "name", "category_code", "utility_type", "status",
        "lifecycle_status", "criticality_level", "department", "building_area",
        "subsystem", "line_id", "machine_id", "location",
        "manufacturer", "equipment_model", "serial_no",
        "install_date", "warranty_expiry",
        "rated_capacity", "capacity_unit", "rated_power", "rated_power_unit",
        "flow_capacity", "pressure_capacity", "temperature_range",
        "maintenance_strategy", "is_active", "notes",
    ])
    for a in assets:
        w.writerow([
            a.asset_no, a.name,
            a.category.code if a.category else "",
            a.utility_type.value,
            a.status.value,
            a.lifecycle_status.value if a.lifecycle_status else "",
            a.criticality_level.value if a.criticality_level else "",
            a.department or "", a.building_area or "",
            a.subsystem or "", a.line_id or "", a.machine_id or "",
            a.location or "",
            a.manufacturer or "", a.model or "", a.serial_no or "",
            a.install_date.isoformat() if a.install_date else "",
            a.warranty_expiry.isoformat() if a.warranty_expiry else "",
            a.rated_capacity or "", a.capacity_unit or "",
            a.rated_power or "", a.rated_power_unit or "",
            a.flow_capacity or "", a.pressure_capacity or "",
            a.temperature_range or "",
            a.maintenance_strategy or "",
            a.is_active, a.notes or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=utility_assets.csv"},
    )


@router.get(
    "/assets/{asset_id}",
    response_model=UtilityAssetRead,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_asset(db, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _enrich_asset(obj)


@router.post(
    "/assets",
    response_model=UtilityAssetRead,
    status_code=201,
)
async def create_asset(
    data: UtilityAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "create")),
):
    # Unique code check
    existing = await crud.get_asset_by_no(db, data.asset_no)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Asset code '{data.asset_no}' already exists",
        )
    # Category must exist
    cat = await crud.get_category(db, data.category_id)
    if not cat:
        raise HTTPException(status_code=400, detail="Category not found")
    # Self-reference guard
    if data.parent_asset_id:
        parent = await crud.get_asset(db, data.parent_asset_id)
        if not parent:
            raise HTTPException(status_code=400, detail="Parent asset not found")

    obj = await crud.create_asset(db, data, user_id=current_user.id)
    await db.commit()
    # Reload with relationships
    obj = await crud.get_asset(db, obj.id)
    logger.info("UtilityAsset created: asset_no=%s by user=%s", obj.asset_no, current_user.id)
    return _enrich_asset(obj)


@router.patch(
    "/assets/{asset_id}",
    response_model=UtilityAssetRead,
)
async def update_asset(
    asset_id: uuid.UUID,
    data: UtilityAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "edit")),
):
    obj = await crud.get_asset(db, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Asset not found")
    if data.category_id:
        cat = await crud.get_category(db, data.category_id)
        if not cat:
            raise HTTPException(status_code=400, detail="Category not found")
    if data.parent_asset_id is not None:
        if data.parent_asset_id == asset_id:
            raise HTTPException(status_code=400, detail="Asset cannot be its own parent")
        parent = await crud.get_asset(db, data.parent_asset_id)
        if not parent:
            raise HTTPException(status_code=400, detail="Parent asset not found")

    obj = await crud.update_asset(db, obj, data)
    await db.commit()
    obj = await crud.get_asset(db, obj.id)
    logger.info("UtilityAsset updated: asset_no=%s by user=%s", obj.asset_no, current_user.id)
    return _enrich_asset(obj)


@router.delete("/assets/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "delete")),
):
    obj = await crud.get_asset(db, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Asset not found")
    await crud.delete_asset(db, obj)
    await db.commit()
    logger.info("UtilityAsset deleted: asset_no=%s by user=%s", obj.asset_no, current_user.id)
    return Response(status_code=204)


# ── Utility Devices ────────────────────────────────────────────────────────────

def _enrich_device(obj, reading_count: int = 0) -> UtilityDeviceRead:
    today = date.today()
    calibration_due = (
        obj.calibration_required
        and obj.next_calibration_date is not None
        and obj.next_calibration_date <= today
    )
    return UtilityDeviceRead(
        id=obj.id,
        device_code=obj.device_code,
        name=obj.name,
        description=obj.description,
        device_type=obj.device_type,
        utility_type=obj.utility_type,
        asset_id=obj.asset_id,
        location=obj.location,
        building_area=obj.building_area,
        department=obj.department,
        related_line_id=obj.related_line_id,
        related_machine_id=obj.related_machine_id,
        reading_type=obj.reading_type,
        reading_source=obj.reading_source,
        reading_frequency=obj.reading_frequency,
        manufacturer=obj.manufacturer,
        equipment_model=obj.model,
        serial_no=obj.serial_no,
        install_date=obj.install_date,
        last_calibration_date=obj.last_calibration_date,
        next_calibration_date=obj.next_calibration_date,
        calibration_required=obj.calibration_required,
        calibration_frequency_days=obj.calibration_frequency_days,
        unit_of_measure=obj.unit_of_measure,
        min_value=obj.min_value,
        max_value=obj.max_value,
        pulse_factor=obj.pulse_factor,
        min_alarm_limit=obj.min_alarm_limit,
        max_alarm_limit=obj.max_alarm_limit,
        is_active=obj.is_active,
        notes=obj.notes,
        asset_no=obj.asset.asset_no if obj.asset else None,
        asset_name=obj.asset.name if obj.asset else None,
        reading_count=reading_count,
        calibration_due=calibration_due,
    )


@router.get(
    "/devices",
    response_model=List[UtilityDeviceRead],
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def list_devices(
    utility_type: Optional[UtilityType] = Query(None),
    device_type: Optional[DeviceType] = Query(None),
    asset_id: Optional[uuid.UUID] = Query(None),
    department: Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    related_line_id: Optional[str] = Query(None),
    related_machine_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    calibration_due_before: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    devices = await crud.list_devices(
        db,
        utility_type=utility_type,
        device_type=device_type,
        asset_id=asset_id,
        department=department,
        building_area=building_area,
        related_line_id=related_line_id,
        related_machine_id=related_machine_id,
        is_active=is_active,
        calibration_due_before=calibration_due_before,
        search=search,
        skip=skip,
        limit=limit,
    )
    result = []
    for d in devices:
        count = await crud.count_readings_for_device(db, d.id)
        result.append(_enrich_device(d, count))
    return result


@router.get(
    "/devices/export/csv",
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def export_devices_csv(db: AsyncSession = Depends(get_db)):
    devices = await crud.list_devices(db, limit=10000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "device_code", "name", "device_type", "utility_type",
        "reading_type", "reading_source", "reading_frequency",
        "asset_no", "department", "building_area", "location",
        "related_line_id", "related_machine_id",
        "unit_of_measure", "min_value", "max_value",
        "min_alarm_limit", "max_alarm_limit",
        "calibration_required", "calibration_frequency_days",
        "last_calibration_date", "next_calibration_date",
        "manufacturer", "equipment_model", "serial_no", "install_date",
        "is_active", "notes",
    ])
    for d in devices:
        w.writerow([
            d.device_code, d.name,
            d.device_type.value, d.utility_type.value,
            d.reading_type.value if d.reading_type else "",
            d.reading_source.value if d.reading_source else "",
            d.reading_frequency.value if d.reading_frequency else "",
            d.asset.asset_no if d.asset else "",
            d.department or "", d.building_area or "", d.location or "",
            d.related_line_id or "", d.related_machine_id or "",
            d.unit_of_measure,
            d.min_value or "", d.max_value or "",
            d.min_alarm_limit or "", d.max_alarm_limit or "",
            d.calibration_required,
            d.calibration_frequency_days or "",
            d.last_calibration_date.isoformat() if d.last_calibration_date else "",
            d.next_calibration_date.isoformat() if d.next_calibration_date else "",
            d.manufacturer or "", d.model or "", d.serial_no or "",
            d.install_date.isoformat() if d.install_date else "",
            d.is_active, d.notes or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=utility_devices.csv"},
    )


@router.get(
    "/devices/{device_id}",
    response_model=UtilityDeviceRead,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_device(db, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    count = await crud.count_readings_for_device(db, obj.id)
    return _enrich_device(obj, count)


@router.post("/devices", response_model=UtilityDeviceRead, status_code=201)
async def create_device(
    data: UtilityDeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "create")),
):
    existing = await crud.get_device_by_code(db, data.device_code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Device code '{data.device_code}' already exists",
        )
    if data.asset_id:
        asset = await crud.get_asset(db, data.asset_id)
        if not asset:
            raise HTTPException(status_code=400, detail="Asset not found")
    obj = await crud.create_device(db, data, user_id=current_user.id)
    await db.commit()
    obj = await crud.get_device(db, obj.id)
    logger.info("UtilityDevice created: code=%s by user=%s", obj.device_code, current_user.id)
    return _enrich_device(obj, 0)


@router.patch("/devices/{device_id}", response_model=UtilityDeviceRead)
async def update_device(
    device_id: uuid.UUID,
    data: UtilityDeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "edit")),
):
    obj = await crud.get_device(db, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    if data.asset_id is not None:
        asset = await crud.get_asset(db, data.asset_id)
        if not asset:
            raise HTTPException(status_code=400, detail="Asset not found")
    obj = await crud.update_device(db, obj, data)
    await db.commit()
    obj = await crud.get_device(db, obj.id)
    count = await crud.count_readings_for_device(db, obj.id)
    logger.info("UtilityDevice updated: code=%s by user=%s", obj.device_code, current_user.id)
    return _enrich_device(obj, count)


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "delete")),
):
    obj = await crud.get_device(db, device_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    count = await crud.count_readings_for_device(db, obj.id)
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete device — {count} reading(s) exist. Delete readings first.",
        )
    await crud.delete_device(db, obj)
    await db.commit()
    logger.info("UtilityDevice deleted: code=%s by user=%s", obj.device_code, current_user.id)
    return Response(status_code=204)


# ── Utility Readings ───────────────────────────────────────────────────────────

@router.get(
    "/readings",
    response_model=List[UtilityReadingRead],
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def list_readings(
    device_id: Optional[uuid.UUID] = Query(None),
    asset_id: Optional[uuid.UUID] = Query(None),
    department: Optional[str] = Query(None),
    source_method: Optional[SourceMethod] = Query(None),
    validated_status: Optional[ValidatedStatus] = Query(None),
    is_anomaly: Optional[bool] = Query(None),
    batch_id: Optional[str] = Query(None),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    readings = await crud.list_readings(
        db,
        device_id=device_id,
        asset_id=asset_id,
        department=department,
        source_method=source_method,
        validated_status=validated_status,
        is_anomaly=is_anomaly,
        batch_id=batch_id,
        from_dt=from_dt,
        to_dt=to_dt,
        skip=skip,
        limit=limit,
    )
    return [_enrich_reading(r) for r in readings]


@router.get(
    "/readings/export/csv",
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def export_readings_csv(
    device_id: Optional[uuid.UUID] = Query(None),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    readings = await crud.list_readings(db, device_id=device_id, from_dt=from_dt, to_dt=to_dt, limit=50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "reading_no", "device_code", "reading_datetime",
        "raw_value", "adjusted_value", "unit_of_measure",
        "cumulative_value", "interval_consumption",
        "source_method", "source_reference",
        "quality", "is_anomaly", "anomaly_note",
        "validated_status", "department", "shift_ref", "batch_id", "notes",
    ])
    for r in readings:
        w.writerow([
            r.reading_no,
            r.device.device_code if r.device else "",
            r.reading_datetime.isoformat(),
            r.raw_value,
            r.adjusted_value or "",
            r.unit_of_measure,
            r.cumulative_value or "",
            r.interval_consumption or "",
            r.source_method.value,
            r.source_reference or "",
            r.quality.value,
            r.is_anomaly,
            r.anomaly_note or "",
            r.validated_status.value,
            r.department or "",
            r.shift_ref or "",
            r.batch_id or "",
            r.notes or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=utility_readings.csv"},
    )


@router.get(
    "/readings/{reading_id}",
    response_model=UtilityReadingRead,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_reading(reading_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_reading(db, reading_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reading not found")
    return _enrich_reading(obj)


@router.post("/readings", response_model=UtilityReadingRead, status_code=201)
async def create_reading(
    data: UtilityReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "create")),
):
    try:
        result = await ingest_reading(db, data, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    logger.info(
        "UtilityReading created: no=%s device=%s by user=%s",
        result.reading_no, result.device_code, current_user.id,
    )
    return result


@router.patch(
    "/readings/{reading_id}/validate",
    response_model=UtilityReadingRead,
)
async def validate_reading(
    reading_id: uuid.UUID,
    data: UtilityReadingValidate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "edit")),
):
    obj = await crud.get_reading(db, reading_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reading not found")
    obj = await crud.validate_reading(db, obj, data)
    await db.commit()
    obj = await crud.get_reading(db, obj.id)
    logger.info(
        "UtilityReading validated: no=%s status=%s by user=%s",
        obj.reading_no, data.validated_status, current_user.id,
    )
    return _enrich_reading(obj)


@router.delete("/readings/{reading_id}", status_code=204)
async def delete_reading(
    reading_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "delete")),
):
    obj = await crud.get_reading(db, reading_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reading not found")
    await crud.delete_reading(db, obj)
    await db.commit()
    logger.info("UtilityReading deleted: no=%s by user=%s", obj.reading_no, current_user.id)
    return Response(status_code=204)


# ── Utility Transactions ───────────────────────────────────────────────────────

@router.get(
    "/transactions/summary",
    response_model=UtilityTransactionSummary,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_transaction_summary(
    utility_type: Optional[UtilityType] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await build_summary(
        db,
        utility_type=utility_type,
        department=department,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/transactions",
    response_model=List[UtilityTransactionRead],
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def list_transactions(
    utility_type: Optional[UtilityType] = Query(None),
    reference_type: Optional[TxReferenceType] = Query(None),
    department: Optional[str] = Query(None),
    building_area: Optional[str] = Query(None),
    line_id: Optional[str] = Query(None),
    machine_id: Optional[str] = Query(None),
    shift_id: Optional[str] = Query(None),
    source_meter_id: Optional[uuid.UUID] = Query(None),
    source_asset_id: Optional[uuid.UUID] = Query(None),
    production_order_id: Optional[uuid.UUID] = Query(None),
    batch_id: Optional[str] = Query(None),
    source_method: Optional[SourceMethod] = Query(None),
    is_anomaly: Optional[bool] = Query(None),
    is_estimated: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    txs = await crud.list_transactions(
        db,
        utility_type=utility_type,
        reference_type=reference_type,
        department=department,
        building_area=building_area,
        line_id=line_id,
        machine_id=machine_id,
        shift_id=shift_id,
        source_meter_id=source_meter_id,
        source_asset_id=source_asset_id,
        production_order_id=production_order_id,
        batch_id=batch_id,
        source_method=source_method,
        is_anomaly=is_anomaly,
        is_estimated=is_estimated,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=limit,
    )
    return [enrich_transaction(t) for t in txs]


@router.get(
    "/transactions/export/csv",
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def export_transactions_csv(
    utility_type: Optional[UtilityType] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    txs = await crud.list_transactions(
        db,
        utility_type=utility_type,
        department=department,
        date_from=date_from,
        date_to=date_to,
        limit=100_000,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "transaction_no", "utility_type", "transaction_date",
        "device_code", "asset_no", "department", "building_area",
        "line_id", "machine_id", "shift_id",
        "production_order_id", "batch_id",
        "quantity", "uom", "cost_rate", "total_cost", "currency_code",
        "variance_from_standard",
        "source_method", "quality", "estimated", "anomaly",
        "reference_type", "reference_id", "notes",
    ])
    for t in txs:
        w.writerow([
            t.transaction_no,
            t.utility_type.value,
            t.transaction_date.isoformat(),
            t.device.device_code if t.device else "",
            t.asset.asset_no if t.asset else "",
            t.department or "",
            t.building_area or "",
            t.production_line or "",
            t.machine_ref or "",
            t.shift_ref or "",
            str(t.production_order_id) if t.production_order_id else "",
            t.batch_no or "",
            t.quantity,
            t.unit_of_measure,
            t.cost_rate or "",
            t.total_cost or "",
            t.currency_code or "",
            t.variance_from_standard or "",
            t.source_method.value,
            t.quality.value,
            t.is_estimated,
            t.is_anomaly,
            t.reference_type.value if t.reference_type else "",
            t.reference_id or "",
            t.notes or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=utility_transactions.csv"},
    )


@router.get(
    "/transactions/{tx_id}",
    response_model=UtilityTransactionRead,
    dependencies=[Depends(require_permission("utility_management", "view"))],
)
async def get_transaction(tx_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_transaction(db, tx_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return enrich_transaction(obj)


@router.post("/transactions", response_model=UtilityTransactionRead, status_code=201)
async def create_transaction(
    data: UtilityTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "create")),
):
    try:
        result = await svc_create_transaction(db, data, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    logger.info(
        "UtilityTransaction created: no=%s type=%s by user=%s",
        result.transaction_no, result.utility_type, current_user.id,
    )
    return result


@router.patch("/transactions/{tx_id}", response_model=UtilityTransactionRead)
async def update_transaction(
    tx_id: uuid.UUID,
    data: UtilityTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "edit")),
):
    obj = await crud.get_transaction(db, tx_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    obj = await crud.update_transaction(db, obj, data)
    await db.commit()
    obj = await crud.get_transaction(db, obj.id)
    logger.info(
        "UtilityTransaction updated: no=%s by user=%s",
        obj.transaction_no, current_user.id,
    )
    return enrich_transaction(obj)


@router.delete("/transactions/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("utility_management", "delete")),
):
    obj = await crud.get_transaction(db, tx_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await crud.delete_transaction(db, obj)
    await db.commit()
    logger.info(
        "UtilityTransaction deleted: no=%s by user=%s",
        obj.transaction_no, current_user.id,
    )
    return Response(status_code=204)
