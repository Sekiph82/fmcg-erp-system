"""
Utility Transaction Service
────────────────────────────
Central service for creating, enriching, and exposing UtilityTransaction records.

A UtilityTransaction is the unified backbone record for every utility
consumption/production/cost event regardless of origin:

  MANUAL        — operator enters directly in the UI
  READING       — derived from a UtilityReading (meter measurement)
  BILL          — allocated from a supplier utility bill
  CALCULATION   — computed (e.g. sub-metered share, formula-based allocation)
  IOT / API     — pushed by an external system
  IMPORT        — loaded via CSV bulk import
  *_RECORD      — derived from a specialized operational log
                  (boiler, compressor, solar, treatment, wastewater)

The service also handles:
  • Auto-numbered transaction_no (format: TX-{YYYYMMDD}-{seq5})
  • Cost computation when tariff / cost_rate is provided
  • Variance calculation vs standard consumption
  • Enrichment helpers for read responses
"""
from __future__ import annotations

import logging
import time
import random
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import utility_management as crud
from app.models.utility_management import (
    DataQuality,
    SourceMethod,
    TxReferenceType,
    UtilityReading,
    UtilityType,
)
from app.schemas.utility_management import (
    UtilityTransactionCreate,
    UtilityTransactionRead,
    UtilityTransactionSummary,
    UtilityTransactionSummaryRow,
)

logger = logging.getLogger(__name__)

TX_NO_PREFIX = "TX"


# ── Transaction number ────────────────────────────────────────────────────────

def _generate_tx_no(tx_date: date) -> str:
    date_str = tx_date.strftime("%Y%m%d")
    seq = f"{random.randint(10000, 99999)}"
    return f"{TX_NO_PREFIX}-{date_str}-{seq}"


# ── Enrichment ────────────────────────────────────────────────────────────────

def enrich_transaction(obj) -> UtilityTransactionRead:
    """Convert ORM object → UtilityTransactionRead, filling denormalised fields."""
    return UtilityTransactionRead(
        id=obj.id,
        transaction_no=obj.transaction_no,
        utility_type=obj.utility_type,
        transaction_date=obj.transaction_date,
        transaction_time=obj.transaction_time,
        period_start=obj.period_start,
        period_end=obj.period_end,
        source_meter_id=obj.device_id,
        source_asset_id=obj.asset_id,
        device_code=obj.device.device_code if obj.device else None,
        device_name=obj.device.name if obj.device else None,
        asset_no=obj.asset.asset_no if obj.asset else None,
        asset_name=obj.asset.name if obj.asset else None,
        reference_type=obj.reference_type,
        reference_id=obj.reference_id,
        department=obj.department,
        building_area=obj.building_area,
        line_id=obj.production_line,
        machine_id=obj.machine_ref,
        shift_id=obj.shift_ref,
        production_order_id=obj.production_order_id,
        batch_id=obj.batch_no,
        product_id=obj.product_id,
        quantity=obj.quantity,
        uom=obj.unit_of_measure,
        tariff_id=obj.tariff_id,
        tariff_code=obj.tariff.tariff_code if obj.tariff else None,
        cost_rate=obj.cost_rate,
        total_cost=obj.total_cost,
        currency_code=obj.currency_code,
        variance_from_standard=obj.variance_from_standard,
        source_method=obj.source_method,
        quality=obj.quality,
        estimated_or_actual=obj.is_estimated,
        anomaly_flag=obj.is_anomaly,
        anomaly_note=obj.anomaly_note,
        notes=obj.notes,
        created_at=obj.created_at,
    )


# ── Main creation entry-point ─────────────────────────────────────────────────

async def create_transaction(
    db: AsyncSession,
    data: UtilityTransactionCreate,
    *,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityTransactionRead:
    """
    Validate, auto-number, optionally compute total_cost, then persist.
    Returns enriched read schema.
    """
    # Auto-number if not supplied
    tx_no = data.transaction_no or _generate_tx_no(data.transaction_date)
    # Uniqueness guard
    if await crud.get_transaction_by_no(db, tx_no):
        tx_no = _generate_tx_no(data.transaction_date)

    # Auto-compute cost when rate + quantity are available but total not given
    if (
        data.cost_rate is not None
        and data.total_cost is None
        and data.quantity is not None
    ):
        data = data.model_copy(
            update={"total_cost": Decimal(str(data.cost_rate)) * Decimal(str(data.quantity))}
        )

    obj = await crud.create_transaction(db, tx_no, data, user_id=user_id)

    logger.info(
        "UtilityTransaction created: no=%s type=%s qty=%s %s cost=%s",
        obj.transaction_no, obj.utility_type.value, obj.quantity,
        obj.unit_of_measure, obj.total_cost,
    )

    obj = await crud.get_transaction(db, obj.id)
    return enrich_transaction(obj)


# ── Factory: create from UtilityReading ───────────────────────────────────────

async def create_from_reading(
    db: AsyncSession,
    reading: UtilityReading,
    *,
    standard_consumption: Optional[Decimal] = None,
    tariff_id: Optional[uuid.UUID] = None,
    cost_rate: Optional[Decimal] = None,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityTransactionRead:
    """
    Derive a UtilityTransaction from a UtilityReading.

    Quantity = interval_consumption (for cumulative meters) or raw_value.
    Variance = actual − standard if standard_consumption provided.
    """
    device = reading.device
    quantity = (
        reading.interval_consumption
        if reading.interval_consumption is not None
        else reading.raw_value
    )
    if quantity is None:
        quantity = reading.raw_value

    variance = None
    if standard_consumption is not None:
        variance = Decimal(str(quantity)) - Decimal(str(standard_consumption))

    total_cost = None
    if cost_rate is not None:
        total_cost = Decimal(str(cost_rate)) * Decimal(str(quantity))

    data = UtilityTransactionCreate(
        utility_type=device.utility_type if device else reading.device_id,  # type: ignore[arg-type]
        transaction_date=reading.reading_datetime.date(),
        transaction_time=reading.reading_datetime,
        source_meter_id=reading.device_id,
        source_asset_id=reading.asset_id,
        reference_type=TxReferenceType.READING,
        reference_id=str(reading.id),
        department=reading.department,
        building_area=reading.building_area,
        shift_id=reading.shift_ref,
        batch_id=reading.batch_id,
        quantity=quantity,
        uom=reading.unit_of_measure,
        tariff_id=tariff_id,
        cost_rate=cost_rate,
        total_cost=total_cost,
        variance_from_standard=variance,
        source_method=SourceMethod(reading.source_method.value),
        quality=DataQuality(reading.quality.value),
        estimated_or_actual=False,
        anomaly_flag=reading.is_anomaly,
        anomaly_note=reading.anomaly_note,
    )

    return await create_transaction(db, data, user_id=user_id)


# ── Factory: create from bill allocation ─────────────────────────────────────

async def create_from_bill(
    db: AsyncSession,
    *,
    utility_type: UtilityType,
    transaction_date: date,
    bill_id: uuid.UUID,
    quantity: Decimal,
    uom: str,
    total_cost: Decimal,
    currency_code: str = "USD",
    department: Optional[str] = None,
    building_area: Optional[str] = None,
    line_id: Optional[str] = None,
    tariff_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityTransactionRead:
    """
    Create a transaction representing a supplier-bill-allocated consumption event.
    """
    cost_rate = (total_cost / quantity) if quantity else None

    data = UtilityTransactionCreate(
        utility_type=utility_type,
        transaction_date=transaction_date,
        reference_type=TxReferenceType.BILL,
        reference_id=str(bill_id),
        department=department,
        building_area=building_area,
        line_id=line_id,
        quantity=quantity,
        uom=uom,
        tariff_id=tariff_id,
        cost_rate=cost_rate,
        total_cost=total_cost,
        currency_code=currency_code,
        source_method=SourceMethod.MANUAL,
        quality=DataQuality.GOOD,
        estimated_or_actual=False,
        anomaly_flag=False,
        notes=notes,
    )
    return await create_transaction(db, data, user_id=user_id)


# ── Summary builder ───────────────────────────────────────────────────────────

async def build_summary(
    db: AsyncSession,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department: Optional[str] = None,
    utility_type: Optional[UtilityType] = None,
) -> UtilityTransactionSummary:
    """Aggregate transactions into summary rows grouped by utility type and department."""
    from app.models.utility_management import UTILITY_TYPE_LABELS_PYTHON  # soft import

    raw = await crud.summarize_transactions(
        db,
        date_from=date_from,
        date_to=date_to,
        department=department,
        utility_type=utility_type,
    )

    _LABELS: dict[str, str] = {
        "ELECTRICITY": "Electricity", "WATER": "Water", "SOFT_WATER": "Soft Water",
        "PROCESS_WATER": "Process Water", "STEAM": "Steam",
        "COMPRESSED_AIR": "Compressed Air", "SOLAR": "Solar",
        "NATURAL_GAS": "Natural Gas", "WASTEWATER": "Wastewater",
        "DIESEL": "Diesel", "CHILLED_WATER": "Chilled Water", "OTHER": "Other",
    }

    by_type: list[UtilityTransactionSummaryRow] = []
    for row in raw["by_type"]:
        by_type.append(UtilityTransactionSummaryRow(
            group_key=row.utility_type.value if hasattr(row.utility_type, "value") else str(row.utility_type),
            label=_LABELS.get(str(row.utility_type).upper().split(".")[-1], str(row.utility_type)),
            tx_count=row.tx_count or 0,
            total_quantity=row.total_quantity or Decimal("0"),
            uom=row.unit_of_measure or "",
            total_cost=row.total_cost,
            anomaly_count=row.anomaly_count or 0,
        ))

    by_dept: list[UtilityTransactionSummaryRow] = []
    for row in raw["by_dept"]:
        dept = row.department or "(no department)"
        by_dept.append(UtilityTransactionSummaryRow(
            group_key=dept,
            label=dept,
            tx_count=row.tx_count or 0,
            total_quantity=row.total_quantity or Decimal("0"),
            uom=row.unit_of_measure or "",
            total_cost=row.total_cost,
            anomaly_count=row.anomaly_count or 0,
        ))

    grand_cost = sum(
        (r.total_cost for r in by_type if r.total_cost is not None),
        Decimal("0"),
    ) or None

    grand_tx = sum(r.tx_count for r in by_type)

    return UtilityTransactionSummary(
        by_utility_type=by_type,
        by_department=by_dept,
        grand_total_cost=grand_cost,
        grand_total_tx=grand_tx,
    )
