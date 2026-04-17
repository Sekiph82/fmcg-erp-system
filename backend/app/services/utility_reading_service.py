"""
Utility Reading Ingestion Service
──────────────────────────────────
Central validation pipeline for all incoming utility readings regardless of source
(manual entry, CSV import, IoT/SCADA push, external API).

Pipeline:
  1. Duplicate detection   — same device + datetime already exists?
  2. Unit inheritance       — fill unit_of_measure from device if not supplied
  3. Range validation       — raw_value within device min/max alarm limits?
  4. Jump detection         — % change vs previous reading too large?
  5. Quality assignment     — GOOD / SUSPECT / ESTIMATED
  6. Interval consumption   — delta from previous for CUMULATIVE devices
  7. Auto-approval          — MANUAL source with no anomalies → AUTO_APPROVED
  8. Persist                — delegate to CRUD layer
"""
from __future__ import annotations

import abc
import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import utility_management as crud
from app.models.utility_management import (
    DataQuality,
    ReadingType,
    ValidatedStatus,
)
from app.schemas.utility_management import UtilityReadingCreate, UtilityReadingRead

logger = logging.getLogger(__name__)

# ── Configuration constants ───────────────────────────────────────────────────

# If raw_value deviates from previous by more than this fraction, flag anomaly
JUMP_THRESHOLD_PCT: float = 300.0   # 300 % change

# Prefix for auto-generated reading numbers
READING_NO_PREFIX = "RDG"


# ── IoT ingestion adapter (abstract) ─────────────────────────────────────────

class IoTIngestionAdapter(abc.ABC):
    """
    Abstract base for IoT/SCADA source adapters.
    Implement to wire a specific IoT broker / SCADA system into the pipeline.

    Usage:
        class MyMQTTAdapter(IoTIngestionAdapter):
            async def fetch_pending(self) -> list[UtilityReadingCreate]:
                ...
    """

    @abc.abstractmethod
    async def fetch_pending(self) -> list[UtilityReadingCreate]:
        """Fetch unprocessed readings from the IoT source."""
        ...

    async def ingest_all(self, db: AsyncSession, user_id: Optional[uuid.UUID] = None) -> int:
        """Convenience method: fetch pending and ingest via service pipeline."""
        payloads = await self.fetch_pending()
        count = 0
        for payload in payloads:
            try:
                await ingest_reading(db, payload, user_id=user_id)
                count += 1
            except Exception as exc:
                logger.warning("IoT ingest failed for device=%s dt=%s: %s",
                               payload.device_id, payload.reading_datetime, exc)
        return count


# ── Auto-generated reading number ────────────────────────────────────────────

def _generate_reading_no() -> str:
    import time
    import random
    ts = int(time.time() * 1000)
    rnd = random.randint(100, 999)
    return f"{READING_NO_PREFIX}-{ts}-{rnd}"


# ── Main ingest function ──────────────────────────────────────────────────────

async def ingest_reading(
    db: AsyncSession,
    data: UtilityReadingCreate,
    *,
    user_id: Optional[uuid.UUID] = None,
) -> UtilityReadingRead:
    """
    Validate and persist a single utility reading.

    Raises:
        ValueError — on duplicate reading or critical validation failure.
    Returns:
        UtilityReadingRead schema for the saved record.
    """

    # ── 1. Load device ────────────────────────────────────────────────────────
    device = await crud.get_device(db, data.device_id)
    if not device:
        raise ValueError(f"Device {data.device_id} not found")

    # ── 2. Duplicate check ────────────────────────────────────────────────────
    is_dup = await crud.check_duplicate_reading(db, data.device_id, data.reading_datetime)
    if is_dup:
        raise ValueError(
            f"Duplicate reading: device {device.device_code} already has a reading "
            f"at {data.reading_datetime.isoformat()}"
        )

    # ── 3. Inherit unit from device if not provided ───────────────────────────
    unit = data.unit_of_measure or device.unit_of_measure
    data = data.model_copy(update={"unit_of_measure": unit})

    # ── 4. Range validation ───────────────────────────────────────────────────
    anomaly = False
    anomaly_parts: list[str] = []
    quality = DataQuality.GOOD

    raw = float(data.raw_value)

    if device.min_alarm_limit is not None and raw < float(device.min_alarm_limit):
        anomaly = True
        anomaly_parts.append(
            f"Below min alarm limit ({device.min_alarm_limit} {unit})"
        )
        quality = DataQuality.SUSPECT

    if device.max_alarm_limit is not None and raw > float(device.max_alarm_limit):
        anomaly = True
        anomaly_parts.append(
            f"Exceeds max alarm limit ({device.max_alarm_limit} {unit})"
        )
        quality = DataQuality.SUSPECT

    # ── 5. Abnormal jump detection ────────────────────────────────────────────
    prev = await crud.get_previous_reading(db, data.device_id, data.reading_datetime)
    interval_consumption: Optional[float] = None

    if prev is not None:
        prev_val = float(prev.raw_value)
        if prev_val != 0:
            pct_change = abs(raw - prev_val) / abs(prev_val) * 100
            if pct_change > JUMP_THRESHOLD_PCT:
                anomaly = True
                anomaly_parts.append(
                    f"Abnormal jump: {pct_change:.1f}% change from previous "
                    f"({prev_val} → {raw})"
                )
                quality = DataQuality.SUSPECT

        # ── 6. Interval consumption for cumulative devices ────────────────────
        if device.reading_type == ReadingType.CUMULATIVE:
            delta = raw - prev_val
            interval_consumption = delta if delta >= 0 else None

    anomaly_note = "; ".join(anomaly_parts) if anomaly_parts else None

    # ── 7. Validation status ──────────────────────────────────────────────────
    validated_status = ValidatedStatus.PENDING
    if not anomaly:
        validated_status = ValidatedStatus.AUTO_APPROVED

    # ── 8. Reading number ─────────────────────────────────────────────────────
    reading_no = data.reading_no or _generate_reading_no()
    # Ensure uniqueness
    existing_no = await crud.get_reading_by_no(db, reading_no)
    if existing_no:
        reading_no = _generate_reading_no()

    # ── 9. Persist ────────────────────────────────────────────────────────────
    obj = await crud.create_reading(
        db,
        reading_no=reading_no,
        data=data,
        adjusted_value=None,
        interval_consumption=interval_consumption,
        quality=quality,
        is_anomaly=anomaly,
        anomaly_note=anomaly_note,
        validated_status=validated_status,
        user_id=user_id,
    )

    logger.info(
        "Reading ingested: no=%s device=%s dt=%s anomaly=%s quality=%s",
        obj.reading_no, device.device_code, data.reading_datetime, anomaly, quality.value,
    )

    # ── 10. Build response ────────────────────────────────────────────────────
    # Reload with device relationship for denormalised fields
    obj = await crud.get_reading(db, obj.id)
    return _enrich_reading(obj)


def _enrich_reading(obj) -> UtilityReadingRead:
    from app.schemas.utility_management import UtilityReadingRead
    return UtilityReadingRead(
        id=obj.id,
        reading_no=obj.reading_no,
        device_id=obj.device_id,
        device_code=obj.device.device_code if obj.device else None,
        device_name=obj.device.name if obj.device else None,
        asset_id=obj.asset_id,
        reading_datetime=obj.reading_datetime,
        raw_value=obj.raw_value,
        adjusted_value=obj.adjusted_value,
        unit_of_measure=obj.unit_of_measure,
        cumulative_value=obj.cumulative_value,
        interval_consumption=obj.interval_consumption,
        source_method=obj.source_method,
        source_reference=obj.source_reference,
        quality=obj.quality,
        is_anomaly=obj.is_anomaly,
        anomaly_note=obj.anomaly_note,
        validated_status=obj.validated_status,
        validation_notes=obj.validation_notes,
        department=obj.department,
        building_area=obj.building_area,
        shift_ref=obj.shift_ref,
        batch_id=obj.batch_id,
        notes=obj.notes,
        created_at=obj.created_at,
    )
