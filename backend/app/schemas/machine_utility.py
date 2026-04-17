"""
Machine Utility Consumption Mapping Schemas
────────────────────────────────────────────
Two-layer design:

  MachineUtilityMapping  — master config: which meter serves which machine,
                            rated consumption, allocation share.
  MachineConsumptionRecord — operational log: actual consumption per machine
                              per date/shift, linked to production order/batch.

KPIs (computed in service):
  electricity_per_runtime_h    kWh / runtime_hour
  water_per_batch              m³  / batch
  air_per_batch                Nm³ / batch
  standby_consumption          sum of is_standby records per utility
  cost_per_batch               total_cost / distinct batch count
  cost_per_unit_produced       total_cost / produced quantity (where order linked)
  variance_pct                 (actual − expected) / expected × 100
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# MACHINE UTILITY MAPPING (master config)
# ══════════════════════════════════════════════════════════════════════════════

class MachineUtilityMappingCreate(BaseModel):
    machine_ref:     str
    machine_name:    str
    work_center_id:  Optional[UUID]    = None   # FK → work_centers.id
    department:      Optional[str]     = None
    production_line: Optional[str]     = None
    building_area:   Optional[str]     = None
    utility_type:    str               = "ELECTRICITY"
    device_id:       Optional[UUID]    = None   # FK → utility_devices.id (source meter)
    asset_id:        Optional[UUID]    = None   # FK → utility_assets.id
    allocation_pct:  Optional[Decimal] = None   # % share of shared meter
    rated_consumption: Optional[Decimal] = None # nameplate rate
    rated_unit:      Optional[str]     = None   # e.g. kW, m³/h, kg/h
    is_active:       bool              = True
    notes:           Optional[str]     = None

    @field_validator("utility_type")
    @classmethod
    def _chk_type(cls, v: str) -> str:
        valid = {
            "ELECTRICITY", "WATER", "SOFT_WATER", "PROCESS_WATER",
            "STEAM", "COMPRESSED_AIR", "SOLAR", "NATURAL_GAS",
            "WASTEWATER", "DIESEL", "CHILLED_WATER", "OTHER",
        }
        if v.upper() not in valid:
            raise ValueError(f"utility_type must be one of {valid}")
        return v.upper()


class MachineUtilityMappingUpdate(BaseModel):
    machine_name:    Optional[str]     = None
    work_center_id:  Optional[UUID]    = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None
    building_area:   Optional[str]     = None
    device_id:       Optional[UUID]    = None
    asset_id:        Optional[UUID]    = None
    allocation_pct:  Optional[Decimal] = None
    rated_consumption: Optional[Decimal] = None
    rated_unit:      Optional[str]     = None
    is_active:       Optional[bool]    = None
    notes:           Optional[str]     = None


class MachineUtilityMappingRead(BaseModel):
    id:              UUID
    machine_ref:     str
    machine_name:    str
    work_center_id:  Optional[UUID]    = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None
    building_area:   Optional[str]     = None
    utility_type:    str
    device_id:       Optional[UUID]    = None
    device_name:     Optional[str]     = None   # denormalized
    asset_id:        Optional[UUID]    = None
    allocation_pct:  Optional[Decimal] = None
    rated_consumption: Optional[Decimal] = None
    rated_unit:      Optional[str]     = None
    is_active:       bool
    notes:           Optional[str]     = None
    created_at:      Optional[datetime] = None
    updated_at:      Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# MACHINE CONSUMPTION RECORD (operational log)
# ══════════════════════════════════════════════════════════════════════════════

class MachineConsumptionRecordCreate(BaseModel):
    work_center_id:  UUID              # FK → work_centers.id (REQUIRED)
    record_date:     date
    utility_type:    str               = "ELECTRICITY"
    mapping_id:      Optional[UUID]    = None   # FK → machine_utility_mappings.id
    device_id:       Optional[UUID]    = None   # source meter FK
    shift_ref:       Optional[str]     = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None

    source_method:   str               = "MANUAL"
    is_estimated:    bool              = False
    is_standby:      bool              = False

    runtime_hours:   Optional[Decimal] = None

    nominal_rate:    Optional[Decimal] = None
    nominal_unit:    Optional[str]     = None

    actual_consumption: Optional[Decimal] = None
    actual_unit:     Optional[str]     = None

    production_order_id: Optional[UUID] = None
    batch_no:        Optional[str]     = None
    batch_lot_id:    Optional[UUID]    = None

    cost_rate:       Optional[Decimal] = None
    total_cost:      Optional[Decimal] = None
    currency_code:   Optional[str]     = "USD"

    is_anomaly:      bool              = False
    anomaly_note:    Optional[str]     = None
    notes:           Optional[str]     = None

    @field_validator("utility_type")
    @classmethod
    def _chk_type(cls, v: str) -> str:
        valid = {
            "ELECTRICITY", "WATER", "SOFT_WATER", "PROCESS_WATER",
            "STEAM", "COMPRESSED_AIR", "SOLAR", "NATURAL_GAS",
            "WASTEWATER", "DIESEL", "CHILLED_WATER", "OTHER",
        }
        if v.upper() not in valid:
            raise ValueError(f"utility_type must be one of {valid}")
        return v.upper()


class MachineConsumptionRecordUpdate(BaseModel):
    record_date:        Optional[date]     = None
    shift_ref:          Optional[str]      = None
    department:         Optional[str]      = None
    production_line:    Optional[str]      = None
    device_id:          Optional[UUID]     = None
    source_method:      Optional[str]      = None
    is_estimated:       Optional[bool]     = None
    is_standby:         Optional[bool]     = None
    runtime_hours:      Optional[Decimal]  = None
    nominal_rate:       Optional[Decimal]  = None
    nominal_unit:       Optional[str]      = None
    actual_consumption: Optional[Decimal]  = None
    actual_unit:        Optional[str]      = None
    variance_pct:       Optional[Decimal]  = None
    production_order_id: Optional[UUID]   = None
    batch_no:           Optional[str]      = None
    batch_lot_id:       Optional[UUID]     = None
    cost_rate:          Optional[Decimal]  = None
    total_cost:         Optional[Decimal]  = None
    currency_code:      Optional[str]      = None
    is_anomaly:         Optional[bool]     = None
    anomaly_note:       Optional[str]      = None
    notes:              Optional[str]      = None


class MachineConsumptionRecordRead(BaseModel):
    id:              UUID
    record_no:       str
    mapping_id:      Optional[UUID]    = None
    work_center_id:  UUID
    machine_ref:     str
    machine_name:    Optional[str]     = None
    utility_type:    str
    device_id:       Optional[UUID]    = None
    device_name:     Optional[str]     = None

    record_date:     date
    shift_ref:       Optional[str]     = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None

    source_method:   str
    is_estimated:    bool
    is_standby:      bool

    runtime_hours:   Optional[Decimal] = None

    nominal_rate:    Optional[Decimal] = None
    nominal_unit:    Optional[str]     = None

    actual_consumption: Optional[Decimal] = None
    actual_unit:     Optional[str]     = None
    variance_pct:    Optional[Decimal] = None

    production_order_id: Optional[UUID] = None
    production_order_no: Optional[str]  = None   # denormalized
    batch_no:        Optional[str]      = None
    batch_lot_id:    Optional[UUID]     = None

    cost_rate:       Optional[Decimal]  = None
    total_cost:      Optional[Decimal]  = None
    currency_code:   Optional[str]      = None

    is_anomaly:      bool
    anomaly_note:    Optional[str]      = None
    notes:           Optional[str]      = None

    entered_by_id:   Optional[UUID]     = None
    entered_by_name: Optional[str]      = None

    created_at:      Optional[datetime] = None
    updated_at:      Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# KPIs & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class MachineUtilityKPIs(BaseModel):
    """
    Aggregated machine utility KPIs over a date window.

    Reporting readiness flags:
      flag_high_variance   avg_variance_pct > 15 %
      flag_standby_waste   standby_pct > 20 % of total consumption
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    machine_ref:  Optional[str] = None
    utility_type: Optional[str] = None

    # Volume totals
    total_consumption:    Decimal = Decimal("0")
    total_runtime_hours:  Optional[Decimal] = None
    total_standby_consumption: Optional[Decimal] = None
    consumption_unit:     Optional[str] = None

    # KPI 1 — electricity per runtime hour
    electricity_per_runtime_h: Optional[Decimal] = None   # kWh / h

    # KPI 2 — water per batch
    water_per_batch:      Optional[Decimal] = None   # m³ / batch

    # KPI 3 — compressed air per batch
    air_per_batch:        Optional[Decimal] = None   # Nm³ / batch

    # KPI 4 — standby consumption share
    standby_pct:          Optional[Decimal] = None   # %

    # KPI 5 — cost per batch
    cost_per_batch:       Optional[Decimal] = None

    # KPI 6 — cost per unit produced (if order linked)
    cost_per_unit:        Optional[Decimal] = None

    # General cost
    total_cost:           Optional[Decimal] = None
    avg_cost_rate:        Optional[Decimal] = None

    # Variance vs standard
    avg_variance_pct:     Optional[Decimal] = None   # deviation from nominal rate

    # Counts
    record_count:         int = 0
    batch_count:          int = 0
    order_count:          int = 0
    anomaly_count:        int = 0

    # Anomaly flags
    flag_high_variance:   bool = False   # avg_variance_pct > 15 %
    flag_standby_waste:   bool = False   # standby_pct > 20 %


class MachineUtilityTrendPoint(BaseModel):
    """Daily aggregation per machine per utility type."""
    date:              str     = ""
    machine_ref:       Optional[str] = None
    utility_type:      Optional[str] = None
    total_consumption: Decimal = Decimal("0")
    standby:           Decimal = Decimal("0")
    runtime_hours:     Decimal = Decimal("0")
    total_cost:        Optional[Decimal] = None
    batch_count:       int = 0
    record_count:      int = 0

    model_config = {"from_attributes": True}


class MachineUtilityBreakdownRow(BaseModel):
    """One row in a breakdown — by machine, utility type, shift, line, etc."""
    group_key:         Optional[str]
    label:             str
    total_consumption: Decimal = Decimal("0")
    total_cost:        Optional[Decimal] = None
    pct_of_total:      Optional[Decimal] = None
    runtime_hours:     Optional[Decimal] = None
    record_count:      int = 0


class MachineUtilityBreakdown(BaseModel):
    dimension:            str
    rows:                 List[MachineUtilityBreakdownRow]
    grand_total:          Decimal


# ── Dropdown helpers ───────────────────────────────────────────────────────────

class WorkCenterDropdown(BaseModel):
    id:             UUID
    work_center_id: str
    name:           str
    department:     Optional[str] = None
    type:           str

    model_config = {"from_attributes": True}


class MappingDropdown(BaseModel):
    id:           UUID
    machine_ref:  str
    machine_name: str
    utility_type: str
    rated_consumption: Optional[Decimal] = None
    rated_unit:   Optional[str] = None

    model_config = {"from_attributes": True}
