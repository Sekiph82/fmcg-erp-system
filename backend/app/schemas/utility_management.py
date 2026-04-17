"""
Pydantic schemas for Utility Management — Asset Categories, Assets, Devices, Readings.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, field_validator, model_validator

from app.models.utility_management import (
    UtilityType,
    UtilityAssetStatus,
    LifecycleStatus,
    CriticalityLevel,
    DeviceType,
    ReadingType,
    ReadingSource,
    ReadingFrequency,
    ValidatedStatus,
    SourceMethod,
    DataQuality,
    TxReferenceType,
)


# ── Utility Asset Category ─────────────────────────────────────────────────────

class UtilityAssetCategoryBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    utility_type: UtilityType
    default_unit: Optional[str] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.strip().upper()


class UtilityAssetCategoryCreate(UtilityAssetCategoryBase):
    pass


class UtilityAssetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    utility_type: Optional[UtilityType] = None
    default_unit: Optional[str] = None
    is_active: Optional[bool] = None


class UtilityAssetCategoryRead(UtilityAssetCategoryBase):
    id: uuid.UUID
    asset_count: int = 0

    model_config = {"from_attributes": True}


# ── Utility Asset ──────────────────────────────────────────────────────────────

class UtilityAssetBase(BaseModel):
    asset_no: str
    name: str
    description: Optional[str] = None
    category_id: uuid.UUID
    utility_type: UtilityType
    subsystem: Optional[str] = None

    # Physical location
    location: Optional[str] = None
    building_area: Optional[str] = None
    department: Optional[str] = None

    # Production linkage
    line_id: Optional[str] = None
    machine_id: Optional[str] = None

    # Hierarchy
    parent_asset_id: Optional[uuid.UUID] = None

    # Equipment detail
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None  # DB column: model
    serial_no: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None

    # Capacity / rating
    rated_capacity: Optional[Decimal] = None
    capacity_unit: Optional[str] = None
    rated_power: Optional[Decimal] = None
    rated_power_unit: Optional[str] = None
    flow_capacity: Optional[Decimal] = None
    pressure_capacity: Optional[Decimal] = None
    temperature_range: Optional[str] = None

    # Status / classification
    status: UtilityAssetStatus = UtilityAssetStatus.ACTIVE
    lifecycle_status: Optional[LifecycleStatus] = None
    criticality_level: Optional[CriticalityLevel] = None
    maintenance_strategy: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None

    @field_validator("asset_no")
    @classmethod
    def asset_no_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def parent_ne_self(self) -> "UtilityAssetBase":
        # Can't validate self-reference without id at creation time;
        # enforced in the CRUD layer instead.
        return self


class UtilityAssetCreate(UtilityAssetBase):
    pass


class UtilityAssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    utility_type: Optional[UtilityType] = None
    subsystem: Optional[str] = None
    location: Optional[str] = None
    building_area: Optional[str] = None
    department: Optional[str] = None
    line_id: Optional[str] = None
    machine_id: Optional[str] = None
    parent_asset_id: Optional[uuid.UUID] = None
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None
    serial_no: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    rated_capacity: Optional[Decimal] = None
    capacity_unit: Optional[str] = None
    rated_power: Optional[Decimal] = None
    rated_power_unit: Optional[str] = None
    flow_capacity: Optional[Decimal] = None
    pressure_capacity: Optional[Decimal] = None
    temperature_range: Optional[str] = None
    status: Optional[UtilityAssetStatus] = None
    lifecycle_status: Optional[LifecycleStatus] = None
    criticality_level: Optional[CriticalityLevel] = None
    maintenance_strategy: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class UtilityAssetRead(UtilityAssetBase):
    id: uuid.UUID
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    parent_asset_no: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Utility Device ─────────────────────────────────────────────────────────────

class UtilityDeviceBase(BaseModel):
    device_code: str
    name: str
    description: Optional[str] = None
    device_type: DeviceType
    utility_type: UtilityType

    # Associated asset (optional)
    asset_id: Optional[uuid.UUID] = None

    # Location
    location: Optional[str] = None
    building_area: Optional[str] = None
    department: Optional[str] = None

    # Production linkage
    related_line_id: Optional[str] = None
    related_machine_id: Optional[str] = None

    # Reading classification
    reading_type: Optional[ReadingType] = None
    reading_source: Optional[ReadingSource] = None
    reading_frequency: Optional[ReadingFrequency] = None

    # Equipment detail
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None  # DB column: model
    serial_no: Optional[str] = None
    install_date: Optional[date] = None

    # Calibration
    last_calibration_date: Optional[date] = None
    next_calibration_date: Optional[date] = None
    calibration_required: bool = False
    calibration_frequency_days: Optional[int] = None

    # Range / engineering
    unit_of_measure: str
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    pulse_factor: Optional[Decimal] = None

    # Alarm limits
    min_alarm_limit: Optional[Decimal] = None
    max_alarm_limit: Optional[Decimal] = None

    is_active: bool = True
    notes: Optional[str] = None

    @field_validator("device_code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.strip().upper()


class UtilityDeviceCreate(UtilityDeviceBase):
    pass


class UtilityDeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_type: Optional[DeviceType] = None
    utility_type: Optional[UtilityType] = None
    asset_id: Optional[uuid.UUID] = None
    location: Optional[str] = None
    building_area: Optional[str] = None
    department: Optional[str] = None
    related_line_id: Optional[str] = None
    related_machine_id: Optional[str] = None
    reading_type: Optional[ReadingType] = None
    reading_source: Optional[ReadingSource] = None
    reading_frequency: Optional[ReadingFrequency] = None
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None
    serial_no: Optional[str] = None
    install_date: Optional[date] = None
    last_calibration_date: Optional[date] = None
    next_calibration_date: Optional[date] = None
    calibration_required: Optional[bool] = None
    calibration_frequency_days: Optional[int] = None
    unit_of_measure: Optional[str] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    pulse_factor: Optional[Decimal] = None
    min_alarm_limit: Optional[Decimal] = None
    max_alarm_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class UtilityDeviceRead(UtilityDeviceBase):
    id: uuid.UUID
    asset_no: Optional[str] = None
    asset_name: Optional[str] = None
    reading_count: int = 0
    calibration_due: bool = False

    model_config = {"from_attributes": True}


# ── Utility Reading ────────────────────────────────────────────────────────────

class UtilityReadingCreate(BaseModel):
    reading_no: Optional[str] = None        # auto-generated if blank
    device_id: uuid.UUID
    asset_id: Optional[uuid.UUID] = None

    reading_datetime: datetime
    raw_value: Decimal
    unit_of_measure: Optional[str] = None   # inherits from device if omitted
    cumulative_value: Optional[Decimal] = None

    source_method: SourceMethod = SourceMethod.MANUAL
    source_reference: Optional[str] = None

    department: Optional[str] = None
    building_area: Optional[str] = None
    shift_ref: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None


class UtilityReadingRead(BaseModel):
    id: uuid.UUID
    reading_no: str
    device_id: uuid.UUID
    device_code: Optional[str] = None
    device_name: Optional[str] = None
    asset_id: Optional[uuid.UUID] = None

    reading_datetime: datetime
    raw_value: Decimal
    adjusted_value: Optional[Decimal] = None
    unit_of_measure: str
    cumulative_value: Optional[Decimal] = None
    interval_consumption: Optional[Decimal] = None

    source_method: SourceMethod
    source_reference: Optional[str] = None
    quality: DataQuality
    is_anomaly: bool
    anomaly_note: Optional[str] = None

    validated_status: ValidatedStatus
    validation_notes: Optional[str] = None

    department: Optional[str] = None
    building_area: Optional[str] = None
    shift_ref: Optional[str] = None
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UtilityReadingValidate(BaseModel):
    validated_status: ValidatedStatus
    validation_notes: Optional[str] = None


# ── Utility Transaction ────────────────────────────────────────────────────────

class UtilityTransactionCreate(BaseModel):
    """
    Create a unified utility transaction.

    DB column mapping (schema name → DB column):
      line_id    → production_line
      machine_id → machine_ref
      batch_id   → batch_no
      shift_id   → shift_ref
      source_meter_id  → device_id
      source_asset_id  → asset_id
      estimated_or_actual (bool True=estimated) → is_estimated
      anomaly_flag → is_anomaly
    """
    # Identity
    transaction_no: Optional[str] = None  # auto-generated if blank

    # Classification
    utility_type: UtilityType

    # Date / time
    transaction_date: date
    transaction_time: Optional[datetime] = None   # full tz-aware datetime for sub-day precision
    period_start: Optional[datetime] = None
    period_end:   Optional[datetime] = None

    # Source device / asset
    source_meter_id: Optional[uuid.UUID] = None   # FK → utility_devices.id
    source_asset_id: Optional[uuid.UUID] = None   # FK → utility_assets.id

    # Reference linkage
    reference_type: Optional[TxReferenceType] = None
    reference_id:   Optional[str] = None

    # Allocation dimensions
    department:    Optional[str] = None
    building_area: Optional[str] = None
    line_id:       Optional[str] = None   # production line code
    machine_id:    Optional[str] = None   # machine / equipment code
    shift_id:      Optional[str] = None   # shift reference code

    # Production linkage
    production_order_id: Optional[uuid.UUID] = None
    batch_id:            Optional[str] = None
    product_id:          Optional[uuid.UUID] = None

    # Consumption
    quantity:        Decimal
    uom:             str   # unit of measure

    # Cost
    tariff_id:     Optional[uuid.UUID] = None
    cost_rate:     Optional[Decimal] = None
    total_cost:    Optional[Decimal] = None
    currency_code: str = "USD"

    # Variance
    variance_from_standard: Optional[Decimal] = None

    # Quality / flags
    source_method:      SourceMethod = SourceMethod.MANUAL
    quality:            DataQuality = DataQuality.GOOD
    estimated_or_actual: bool = False   # True = estimated, False = actual → is_estimated
    anomaly_flag:       bool = False    # → is_anomaly
    anomaly_note:       Optional[str] = None
    notes:              Optional[str] = None


class UtilityTransactionUpdate(BaseModel):
    utility_type:           Optional[UtilityType] = None
    transaction_date:       Optional[date] = None
    transaction_time:       Optional[datetime] = None
    period_start:           Optional[datetime] = None
    period_end:             Optional[datetime] = None
    source_meter_id:        Optional[uuid.UUID] = None
    source_asset_id:        Optional[uuid.UUID] = None
    reference_type:         Optional[TxReferenceType] = None
    reference_id:           Optional[str] = None
    department:             Optional[str] = None
    building_area:          Optional[str] = None
    line_id:                Optional[str] = None
    machine_id:             Optional[str] = None
    shift_id:               Optional[str] = None
    production_order_id:    Optional[uuid.UUID] = None
    batch_id:               Optional[str] = None
    product_id:             Optional[uuid.UUID] = None
    quantity:               Optional[Decimal] = None
    uom:                    Optional[str] = None
    tariff_id:              Optional[uuid.UUID] = None
    cost_rate:              Optional[Decimal] = None
    total_cost:             Optional[Decimal] = None
    currency_code:          Optional[str] = None
    variance_from_standard: Optional[Decimal] = None
    source_method:          Optional[SourceMethod] = None
    quality:                Optional[DataQuality] = None
    estimated_or_actual:    Optional[bool] = None
    anomaly_flag:           Optional[bool] = None
    anomaly_note:           Optional[str] = None
    notes:                  Optional[str] = None


class UtilityTransactionRead(BaseModel):
    id:              uuid.UUID
    transaction_no:  str
    utility_type:    UtilityType

    transaction_date: date
    transaction_time: Optional[datetime] = None
    period_start:     Optional[datetime] = None
    period_end:       Optional[datetime] = None

    source_meter_id:  Optional[uuid.UUID] = None
    source_asset_id:  Optional[uuid.UUID] = None
    device_code:      Optional[str] = None
    device_name:      Optional[str] = None
    asset_no:         Optional[str] = None
    asset_name:       Optional[str] = None

    reference_type: Optional[TxReferenceType] = None
    reference_id:   Optional[str] = None

    department:    Optional[str] = None
    building_area: Optional[str] = None
    line_id:       Optional[str] = None
    machine_id:    Optional[str] = None
    shift_id:      Optional[str] = None

    production_order_id: Optional[uuid.UUID] = None
    batch_id:            Optional[str] = None
    product_id:          Optional[uuid.UUID] = None

    quantity:        Decimal
    uom:             str

    tariff_id:     Optional[uuid.UUID] = None
    tariff_code:   Optional[str] = None
    cost_rate:     Optional[Decimal] = None
    total_cost:    Optional[Decimal] = None
    currency_code: Optional[str] = None

    variance_from_standard: Optional[Decimal] = None

    source_method:       SourceMethod
    quality:             DataQuality
    estimated_or_actual: bool
    anomaly_flag:        bool
    anomaly_note:        Optional[str] = None
    notes:               Optional[str] = None
    created_at:          Optional[datetime] = None

    model_config = {"from_attributes": True}


class UtilityTransactionSummaryRow(BaseModel):
    group_key:     str          # utility_type value or department etc.
    label:         str          # human label
    tx_count:      int
    total_quantity: Decimal
    uom:           str
    total_cost:    Optional[Decimal] = None
    anomaly_count: int = 0


class UtilityTransactionSummary(BaseModel):
    by_utility_type: list[UtilityTransactionSummaryRow]
    by_department:   list[UtilityTransactionSummaryRow]
    grand_total_cost: Optional[Decimal] = None
    grand_total_tx:   int = 0
