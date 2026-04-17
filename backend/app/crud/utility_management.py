"""
CRUD operations for Utility Management: Categories, Assets, Devices, Readings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import (
    UtilityAsset,
    UtilityAssetCategory,
    UtilityAssetStatus,
    LifecycleStatus,
    CriticalityLevel,
    UtilityType,
    UtilityDevice,
    DeviceType,
    ReadingType,
    ReadingSource,
    ReadingFrequency,
    UtilityReading,
    SourceMethod,
    DataQuality,
    ValidatedStatus,
    UtilityTransaction,
    TxReferenceType,
)
from app.schemas.utility_management import (
    UtilityAssetCategoryCreate,
    UtilityAssetCategoryUpdate,
    UtilityAssetCreate,
    UtilityAssetUpdate,
    UtilityDeviceCreate,
    UtilityDeviceUpdate,
    UtilityReadingCreate,
    UtilityReadingValidate,
    UtilityTransactionCreate,
    UtilityTransactionUpdate,
)


# ── Utility Asset Category ─────────────────────────────────────────────────────

async def list_categories(
    db: AsyncSession,
    *,
    utility_type: Optional[UtilityType] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[UtilityAssetCategory]:
    q = select(UtilityAssetCategory)
    if utility_type:
        q = q.where(UtilityAssetCategory.utility_type == utility_type)
    if is_active is not None:
        q = q.where(UtilityAssetCategory.is_active == is_active)
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            (func.lower(UtilityAssetCategory.code).like(term)) |
            (func.lower(UtilityAssetCategory.name).like(term))
        )
    result = await db.execute(
        q.order_by(UtilityAssetCategory.utility_type, UtilityAssetCategory.code)
         .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_category(
    db: AsyncSession, category_id: uuid.UUID
) -> Optional[UtilityAssetCategory]:
    result = await db.execute(
        select(UtilityAssetCategory).where(UtilityAssetCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_category_by_code(
    db: AsyncSession, code: str
) -> Optional[UtilityAssetCategory]:
    result = await db.execute(
        select(UtilityAssetCategory).where(
            UtilityAssetCategory.code == code.upper()
        )
    )
    return result.scalar_one_or_none()


async def create_category(
    db: AsyncSession,
    data: UtilityAssetCategoryCreate,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityAssetCategory:
    obj = UtilityAssetCategory(**data.model_dump(), created_by_id=user_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_category(
    db: AsyncSession,
    obj: UtilityAssetCategory,
    data: UtilityAssetCategoryUpdate,
) -> UtilityAssetCategory:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_category(db: AsyncSession, obj: UtilityAssetCategory) -> None:
    await db.delete(obj)
    await db.flush()


async def count_assets_for_category(
    db: AsyncSession, category_id: uuid.UUID
) -> int:
    result = await db.execute(
        select(func.count()).where(UtilityAsset.category_id == category_id)
    )
    return result.scalar_one()


# ── Utility Asset ──────────────────────────────────────────────────────────────

def _asset_query_base():
    return (
        select(UtilityAsset)
        .options(
            selectinload(UtilityAsset.category),
            selectinload(UtilityAsset.parent_asset),
        )
    )


async def list_assets(
    db: AsyncSession,
    *,
    utility_type: Optional[UtilityType] = None,
    category_id: Optional[uuid.UUID] = None,
    department: Optional[str] = None,
    building_area: Optional[str] = None,
    line_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    status: Optional[UtilityAssetStatus] = None,
    lifecycle_status: Optional[LifecycleStatus] = None,
    criticality_level: Optional[CriticalityLevel] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[UtilityAsset]:
    q = _asset_query_base()
    if utility_type:
        q = q.where(UtilityAsset.utility_type == utility_type)
    if category_id:
        q = q.where(UtilityAsset.category_id == category_id)
    if department:
        q = q.where(UtilityAsset.department == department)
    if building_area:
        q = q.where(UtilityAsset.building_area == building_area)
    if line_id:
        q = q.where(UtilityAsset.line_id == line_id)
    if machine_id:
        q = q.where(UtilityAsset.machine_id == machine_id)
    if status:
        q = q.where(UtilityAsset.status == status)
    if lifecycle_status:
        q = q.where(UtilityAsset.lifecycle_status == lifecycle_status)
    if criticality_level:
        q = q.where(UtilityAsset.criticality_level == criticality_level)
    if is_active is not None:
        q = q.where(UtilityAsset.is_active == is_active)
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            (func.lower(UtilityAsset.asset_no).like(term)) |
            (func.lower(UtilityAsset.name).like(term))
        )
    result = await db.execute(
        q.order_by(UtilityAsset.utility_type, UtilityAsset.asset_no)
         .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_asset(
    db: AsyncSession, asset_id: uuid.UUID
) -> Optional[UtilityAsset]:
    result = await db.execute(
        _asset_query_base().where(UtilityAsset.id == asset_id)
    )
    return result.scalar_one_or_none()


async def get_asset_by_no(
    db: AsyncSession, asset_no: str
) -> Optional[UtilityAsset]:
    result = await db.execute(
        select(UtilityAsset).where(UtilityAsset.asset_no == asset_no.upper())
    )
    return result.scalar_one_or_none()


def _build_asset_kwargs(data_dict: dict) -> dict:
    """Map schema field names to model column names."""
    kwargs = {}
    for k, v in data_dict.items():
        if k == "equipment_model":
            kwargs["model"] = v
        else:
            kwargs[k] = v
    return kwargs


async def create_asset(
    db: AsyncSession,
    data: UtilityAssetCreate,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityAsset:
    kwargs = _build_asset_kwargs(data.model_dump())
    kwargs["created_by_id"] = user_id
    obj = UtilityAsset(**kwargs)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_asset(
    db: AsyncSession,
    obj: UtilityAsset,
    data: UtilityAssetUpdate,
) -> UtilityAsset:
    for k, v in _build_asset_kwargs(data.model_dump(exclude_unset=True)).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_asset(db: AsyncSession, obj: UtilityAsset) -> None:
    await db.delete(obj)
    await db.flush()


# ── Utility Device ─────────────────────────────────────────────────────────────

def _device_query_base():
    return (
        select(UtilityDevice)
        .options(selectinload(UtilityDevice.asset))
    )


def _build_device_kwargs(data_dict: dict) -> dict:
    kwargs = {}
    for k, v in data_dict.items():
        if k == "equipment_model":
            kwargs["model"] = v
        else:
            kwargs[k] = v
    return kwargs


async def list_devices(
    db: AsyncSession,
    *,
    utility_type: Optional[UtilityType] = None,
    device_type: Optional[DeviceType] = None,
    asset_id: Optional[uuid.UUID] = None,
    department: Optional[str] = None,
    building_area: Optional[str] = None,
    related_line_id: Optional[str] = None,
    related_machine_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    calibration_due_before: Optional[str] = None,  # ISO date string
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[UtilityDevice]:
    q = _device_query_base()
    if utility_type:
        q = q.where(UtilityDevice.utility_type == utility_type)
    if device_type:
        q = q.where(UtilityDevice.device_type == device_type)
    if asset_id:
        q = q.where(UtilityDevice.asset_id == asset_id)
    if department:
        q = q.where(UtilityDevice.department == department)
    if building_area:
        q = q.where(UtilityDevice.building_area == building_area)
    if related_line_id:
        q = q.where(UtilityDevice.related_line_id == related_line_id)
    if related_machine_id:
        q = q.where(UtilityDevice.related_machine_id == related_machine_id)
    if is_active is not None:
        q = q.where(UtilityDevice.is_active == is_active)
    if calibration_due_before:
        from datetime import date as _date
        q = q.where(UtilityDevice.next_calibration_date <= _date.fromisoformat(calibration_due_before))
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            (func.lower(UtilityDevice.device_code).like(term)) |
            (func.lower(UtilityDevice.name).like(term))
        )
    result = await db.execute(
        q.order_by(UtilityDevice.utility_type, UtilityDevice.device_code)
         .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_device(
    db: AsyncSession, device_id: uuid.UUID
) -> Optional[UtilityDevice]:
    result = await db.execute(
        _device_query_base().where(UtilityDevice.id == device_id)
    )
    return result.scalar_one_or_none()


async def get_device_by_code(
    db: AsyncSession, code: str
) -> Optional[UtilityDevice]:
    result = await db.execute(
        select(UtilityDevice).where(UtilityDevice.device_code == code.upper())
    )
    return result.scalar_one_or_none()


async def count_readings_for_device(
    db: AsyncSession, device_id: uuid.UUID
) -> int:
    result = await db.execute(
        select(func.count()).where(UtilityReading.device_id == device_id)
    )
    return result.scalar_one()


async def create_device(
    db: AsyncSession,
    data: UtilityDeviceCreate,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityDevice:
    kwargs = _build_device_kwargs(data.model_dump())
    kwargs["created_by_id"] = user_id
    obj = UtilityDevice(**kwargs)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_device(
    db: AsyncSession,
    obj: UtilityDevice,
    data: UtilityDeviceUpdate,
) -> UtilityDevice:
    for k, v in _build_device_kwargs(data.model_dump(exclude_unset=True)).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_device(db: AsyncSession, obj: UtilityDevice) -> None:
    await db.delete(obj)
    await db.flush()


# ── Utility Reading ────────────────────────────────────────────────────────────

def _reading_query_base():
    return (
        select(UtilityReading)
        .options(selectinload(UtilityReading.device))
    )


async def list_readings(
    db: AsyncSession,
    *,
    device_id: Optional[uuid.UUID] = None,
    asset_id: Optional[uuid.UUID] = None,
    department: Optional[str] = None,
    source_method: Optional[SourceMethod] = None,
    validated_status: Optional[ValidatedStatus] = None,
    is_anomaly: Optional[bool] = None,
    batch_id: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[UtilityReading]:
    q = _reading_query_base()
    if device_id:
        q = q.where(UtilityReading.device_id == device_id)
    if asset_id:
        q = q.where(UtilityReading.asset_id == asset_id)
    if department:
        q = q.where(UtilityReading.department == department)
    if source_method:
        q = q.where(UtilityReading.source_method == source_method)
    if validated_status:
        q = q.where(UtilityReading.validated_status == validated_status)
    if is_anomaly is not None:
        q = q.where(UtilityReading.is_anomaly == is_anomaly)
    if batch_id:
        q = q.where(UtilityReading.batch_id == batch_id)
    if from_dt:
        q = q.where(UtilityReading.reading_datetime >= from_dt)
    if to_dt:
        q = q.where(UtilityReading.reading_datetime <= to_dt)
    result = await db.execute(
        q.order_by(UtilityReading.reading_datetime.desc())
         .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_reading(
    db: AsyncSession, reading_id: uuid.UUID
) -> Optional[UtilityReading]:
    result = await db.execute(
        _reading_query_base().where(UtilityReading.id == reading_id)
    )
    return result.scalar_one_or_none()


async def get_reading_by_no(
    db: AsyncSession, reading_no: str
) -> Optional[UtilityReading]:
    result = await db.execute(
        select(UtilityReading).where(UtilityReading.reading_no == reading_no)
    )
    return result.scalar_one_or_none()


async def get_previous_reading(
    db: AsyncSession,
    device_id: uuid.UUID,
    before_dt: datetime,
) -> Optional[UtilityReading]:
    """Return the most recent reading for a device strictly before `before_dt`."""
    result = await db.execute(
        select(UtilityReading)
        .where(
            UtilityReading.device_id == device_id,
            UtilityReading.reading_datetime < before_dt,
        )
        .order_by(UtilityReading.reading_datetime.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def check_duplicate_reading(
    db: AsyncSession,
    device_id: uuid.UUID,
    reading_datetime: datetime,
) -> bool:
    """Return True if a reading already exists for device+datetime."""
    result = await db.execute(
        select(func.count()).where(
            UtilityReading.device_id == device_id,
            UtilityReading.reading_datetime == reading_datetime,
        )
    )
    return result.scalar_one() > 0


async def create_reading(
    db: AsyncSession,
    reading_no: str,
    data: UtilityReadingCreate,
    adjusted_value: Optional[float] = None,
    interval_consumption: Optional[float] = None,
    quality: DataQuality = DataQuality.GOOD,
    is_anomaly: bool = False,
    anomaly_note: Optional[str] = None,
    validated_status: ValidatedStatus = ValidatedStatus.PENDING,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityReading:
    obj = UtilityReading(
        reading_no=reading_no,
        device_id=data.device_id,
        asset_id=data.asset_id,
        reading_datetime=data.reading_datetime,
        raw_value=data.raw_value,
        adjusted_value=adjusted_value,
        unit_of_measure=data.unit_of_measure or "",
        cumulative_value=data.cumulative_value,
        interval_consumption=interval_consumption,
        source_method=data.source_method,
        source_reference=data.source_reference,
        quality=quality,
        is_anomaly=is_anomaly,
        anomaly_note=anomaly_note,
        validated_status=validated_status,
        department=data.department,
        building_area=data.building_area,
        shift_ref=data.shift_ref,
        batch_id=data.batch_id,
        notes=data.notes,
        entered_by_id=user_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def validate_reading(
    db: AsyncSession,
    obj: UtilityReading,
    data: UtilityReadingValidate,
) -> UtilityReading:
    obj.validated_status = data.validated_status
    if data.validation_notes is not None:
        obj.validation_notes = data.validation_notes
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_reading(db: AsyncSession, obj: UtilityReading) -> None:
    await db.delete(obj)
    await db.flush()


# ── Utility Transaction ────────────────────────────────────────────────────────

def _tx_query_base():
    return (
        select(UtilityTransaction)
        .options(
            selectinload(UtilityTransaction.device),
            selectinload(UtilityTransaction.asset),
            selectinload(UtilityTransaction.tariff),
        )
    )


def _build_tx_kwargs(data_dict: dict) -> dict:
    """Map schema field names → DB column names for UtilityTransaction."""
    mapping = {
        "source_meter_id":   "device_id",
        "source_asset_id":   "asset_id",
        "line_id":           "production_line",
        "machine_id":        "machine_ref",
        "shift_id":          "shift_ref",
        "batch_id":          "batch_no",
        "uom":               "unit_of_measure",
        "estimated_or_actual": "is_estimated",
        "anomaly_flag":      "is_anomaly",
    }
    result = {}
    for k, v in data_dict.items():
        result[mapping.get(k, k)] = v
    return result


async def list_transactions(
    db: AsyncSession,
    *,
    utility_type: Optional[UtilityType] = None,
    reference_type: Optional[TxReferenceType] = None,
    department: Optional[str] = None,
    building_area: Optional[str] = None,
    line_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    shift_id: Optional[str] = None,
    source_meter_id: Optional[uuid.UUID] = None,
    source_asset_id: Optional[uuid.UUID] = None,
    production_order_id: Optional[uuid.UUID] = None,
    batch_id: Optional[str] = None,
    source_method: Optional[SourceMethod] = None,
    is_anomaly: Optional[bool] = None,
    is_estimated: Optional[bool] = None,
    date_from: Optional["date_type"] = None,
    date_to: Optional["date_type"] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[UtilityTransaction]:
    from datetime import date as date_type
    q = _tx_query_base()
    if utility_type:
        q = q.where(UtilityTransaction.utility_type == utility_type)
    if reference_type:
        q = q.where(UtilityTransaction.reference_type == reference_type)
    if department:
        q = q.where(UtilityTransaction.department == department)
    if building_area:
        q = q.where(UtilityTransaction.building_area == building_area)
    if line_id:
        q = q.where(UtilityTransaction.production_line == line_id)
    if machine_id:
        q = q.where(UtilityTransaction.machine_ref == machine_id)
    if shift_id:
        q = q.where(UtilityTransaction.shift_ref == shift_id)
    if source_meter_id:
        q = q.where(UtilityTransaction.device_id == source_meter_id)
    if source_asset_id:
        q = q.where(UtilityTransaction.asset_id == source_asset_id)
    if production_order_id:
        q = q.where(UtilityTransaction.production_order_id == production_order_id)
    if batch_id:
        q = q.where(UtilityTransaction.batch_no == batch_id)
    if source_method:
        q = q.where(UtilityTransaction.source_method == source_method)
    if is_anomaly is not None:
        q = q.where(UtilityTransaction.is_anomaly == is_anomaly)
    if is_estimated is not None:
        q = q.where(UtilityTransaction.is_estimated == is_estimated)
    if date_from:
        q = q.where(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        q = q.where(UtilityTransaction.transaction_date <= date_to)
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            (func.lower(UtilityTransaction.transaction_no).like(term)) |
            (func.lower(UtilityTransaction.department).like(term)) |
            (func.lower(UtilityTransaction.batch_no).like(term))
        )
    result = await db.execute(
        q.order_by(UtilityTransaction.transaction_date.desc(), UtilityTransaction.transaction_no)
         .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_transaction(
    db: AsyncSession, tx_id: uuid.UUID
) -> Optional[UtilityTransaction]:
    result = await db.execute(
        _tx_query_base().where(UtilityTransaction.id == tx_id)
    )
    return result.scalar_one_or_none()


async def get_transaction_by_no(
    db: AsyncSession, tx_no: str
) -> Optional[UtilityTransaction]:
    result = await db.execute(
        select(UtilityTransaction).where(UtilityTransaction.transaction_no == tx_no)
    )
    return result.scalar_one_or_none()


async def create_transaction(
    db: AsyncSession,
    transaction_no: str,
    data: UtilityTransactionCreate,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityTransaction:
    kwargs = _build_tx_kwargs(data.model_dump())
    kwargs["transaction_no"] = transaction_no
    kwargs["created_by_id"]  = user_id
    obj = UtilityTransaction(**{k: v for k, v in kwargs.items() if v is not None or k == "is_estimated" or k == "is_anomaly"})
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_transaction(
    db: AsyncSession,
    obj: UtilityTransaction,
    data: UtilityTransactionUpdate,
) -> UtilityTransaction:
    for k, v in _build_tx_kwargs(data.model_dump(exclude_unset=True)).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_transaction(db: AsyncSession, obj: UtilityTransaction) -> None:
    await db.delete(obj)
    await db.flush()


async def summarize_transactions(
    db: AsyncSession,
    *,
    date_from: Optional["date_type"] = None,
    date_to: Optional["date_type"] = None,
    department: Optional[str] = None,
    utility_type: Optional[UtilityType] = None,
) -> dict:
    from datetime import date as date_type
    from sqlalchemy import case, cast, Float

    base_where = []
    if date_from:
        base_where.append(UtilityTransaction.transaction_date >= date_from)
    if date_to:
        base_where.append(UtilityTransaction.transaction_date <= date_to)
    if department:
        base_where.append(UtilityTransaction.department == department)
    if utility_type:
        base_where.append(UtilityTransaction.utility_type == utility_type)

    # By utility type
    by_type_q = (
        select(
            UtilityTransaction.utility_type,
            UtilityTransaction.unit_of_measure,
            func.count().label("tx_count"),
            func.sum(UtilityTransaction.quantity).label("total_quantity"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.sum(
                func.cast(UtilityTransaction.is_anomaly, Integer)
            ).label("anomaly_count"),
        )
        .where(*base_where)
        .group_by(UtilityTransaction.utility_type, UtilityTransaction.unit_of_measure)
        .order_by(UtilityTransaction.utility_type)
    )
    by_type_rows = list((await db.execute(by_type_q)).all())

    # By department
    by_dept_q = (
        select(
            UtilityTransaction.department,
            UtilityTransaction.unit_of_measure,
            func.count().label("tx_count"),
            func.sum(UtilityTransaction.quantity).label("total_quantity"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.sum(
                func.cast(UtilityTransaction.is_anomaly, Integer)
            ).label("anomaly_count"),
        )
        .where(*base_where)
        .group_by(UtilityTransaction.department, UtilityTransaction.unit_of_measure)
        .order_by(UtilityTransaction.department)
    )
    by_dept_rows = list((await db.execute(by_dept_q)).all())

    return {"by_type": by_type_rows, "by_dept": by_dept_rows}
