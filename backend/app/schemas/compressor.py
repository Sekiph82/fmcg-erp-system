"""
Compressor & Compressed Air Management Schemas
───────────────────────────────────────────────
KPI aggregation, trend, breakdown, and CRUD schemas.

Data sources:
  compressor_records      – detailed operational log per compressor per shift/period
  utility_transactions    – COMPRESSED_AIR utility_type for cost allocation
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# COMPRESSOR RECORD CRUD
# ══════════════════════════════════════════════════════════════════════════════

class CompressorRecordCreate(BaseModel):
    asset_id:        UUID
    record_datetime: datetime
    shift_ref:       Optional[str]     = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None
    period_hours:    Optional[Decimal] = None

    # Period totals
    air_generated_nm3:    Optional[Decimal] = None
    air_unit:             str               = "Nm3"
    electricity_used_kwh: Optional[Decimal] = None

    # Time breakdown
    runtime_hours:     Optional[Decimal] = None
    load_time_hours:   Optional[Decimal] = None
    unload_time_hours: Optional[Decimal] = None
    idle_time_hours:   Optional[Decimal] = None

    # Pressure readings (instantaneous / average)
    inlet_pressure_bar:         Optional[Decimal] = None
    discharge_pressure_bar:     Optional[Decimal] = None
    system_pressure_bar:        Optional[Decimal] = None
    receiver_tank_pressure_bar: Optional[Decimal] = None
    line_pressure_bar:          Optional[Decimal] = None

    # Flow & power
    flow_rate_m3h:          Optional[Decimal] = None
    power_kw:               Optional[Decimal] = None
    specific_energy_kwh_m3: Optional[Decimal] = None

    # Load & cumulative
    load_pct:                  Optional[Decimal] = None
    running_hours_cumulative:  Optional[Decimal] = None
    loaded_hours_cumulative:   Optional[Decimal] = None

    # Air quality
    air_temperature_c:    Optional[Decimal] = None
    dew_point_c:          Optional[Decimal] = None
    pressure_dew_point_c: Optional[Decimal] = None

    # Dryer
    dryer_status:      Optional[str]     = None   # ON, OFF, FAULT, BYPASS
    dryer_dew_point_c: Optional[Decimal] = None

    # Oil & filter
    oil_pressure_bar: Optional[Decimal] = None
    oil_temp_c:       Optional[Decimal] = None
    filter_dp_bar:    Optional[Decimal] = None
    oil_level:        Optional[str]     = None   # HIGH, NORMAL, LOW

    # Leak testing
    leak_test_done:      bool              = False
    leak_estimation_pct: Optional[Decimal] = None
    leak_volume_nm3:     Optional[Decimal] = None

    # Night / non-production
    night_idle_kwh: Optional[Decimal] = None
    night_idle_nm3: Optional[Decimal] = None

    # Operational
    start_stop_count:  Optional[int]     = None
    downtime_minutes:  Optional[int]     = None
    downtime_reason:   Optional[str]     = None
    maintenance_flag:  bool              = False
    status:            str               = "RUNNING"
    source_method:     str               = "MANUAL"
    is_anomaly:        bool              = False
    anomaly_note:      Optional[str]     = None
    notes:             Optional[str]     = None

    @field_validator("status")
    @classmethod
    def _chk_status(cls, v: str) -> str:
        valid = {"RUNNING", "STANDBY", "FAULT", "MAINTENANCE"}
        if v.upper() not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v.upper()


class CompressorRecordUpdate(BaseModel):
    record_datetime:            Optional[datetime] = None
    shift_ref:                  Optional[str]      = None
    department:                 Optional[str]      = None
    production_line:            Optional[str]      = None
    period_hours:               Optional[Decimal]  = None
    air_generated_nm3:          Optional[Decimal]  = None
    air_unit:                   Optional[str]      = None
    electricity_used_kwh:       Optional[Decimal]  = None
    runtime_hours:              Optional[Decimal]  = None
    load_time_hours:            Optional[Decimal]  = None
    unload_time_hours:          Optional[Decimal]  = None
    idle_time_hours:            Optional[Decimal]  = None
    inlet_pressure_bar:         Optional[Decimal]  = None
    discharge_pressure_bar:     Optional[Decimal]  = None
    system_pressure_bar:        Optional[Decimal]  = None
    receiver_tank_pressure_bar: Optional[Decimal]  = None
    line_pressure_bar:          Optional[Decimal]  = None
    flow_rate_m3h:              Optional[Decimal]  = None
    power_kw:                   Optional[Decimal]  = None
    specific_energy_kwh_m3:     Optional[Decimal]  = None
    load_pct:                   Optional[Decimal]  = None
    running_hours_cumulative:   Optional[Decimal]  = None
    loaded_hours_cumulative:    Optional[Decimal]  = None
    air_temperature_c:          Optional[Decimal]  = None
    dew_point_c:                Optional[Decimal]  = None
    pressure_dew_point_c:       Optional[Decimal]  = None
    dryer_status:               Optional[str]      = None
    dryer_dew_point_c:          Optional[Decimal]  = None
    oil_pressure_bar:           Optional[Decimal]  = None
    oil_temp_c:                 Optional[Decimal]  = None
    filter_dp_bar:              Optional[Decimal]  = None
    oil_level:                  Optional[str]      = None
    leak_test_done:             Optional[bool]     = None
    leak_estimation_pct:        Optional[Decimal]  = None
    leak_volume_nm3:            Optional[Decimal]  = None
    night_idle_kwh:             Optional[Decimal]  = None
    night_idle_nm3:             Optional[Decimal]  = None
    start_stop_count:           Optional[int]      = None
    downtime_minutes:           Optional[int]      = None
    downtime_reason:            Optional[str]      = None
    maintenance_flag:           Optional[bool]     = None
    status:                     Optional[str]      = None
    source_method:              Optional[str]      = None
    is_anomaly:                 Optional[bool]     = None
    anomaly_note:               Optional[str]      = None
    notes:                      Optional[str]      = None


class CompressorRecordRead(BaseModel):
    id:        UUID
    record_no: str
    asset_id:  UUID
    asset_name: Optional[str] = None
    asset_no:   Optional[str] = None

    record_datetime: datetime
    shift_ref:       Optional[str]     = None
    department:      Optional[str]     = None
    production_line: Optional[str]     = None
    period_hours:    Optional[Decimal] = None

    air_generated_nm3:    Optional[Decimal] = None
    air_unit:             Optional[str]     = None
    electricity_used_kwh: Optional[Decimal] = None

    runtime_hours:     Optional[Decimal] = None
    load_time_hours:   Optional[Decimal] = None
    unload_time_hours: Optional[Decimal] = None
    idle_time_hours:   Optional[Decimal] = None

    inlet_pressure_bar:         Optional[Decimal] = None
    discharge_pressure_bar:     Optional[Decimal] = None
    system_pressure_bar:        Optional[Decimal] = None
    receiver_tank_pressure_bar: Optional[Decimal] = None
    line_pressure_bar:          Optional[Decimal] = None

    flow_rate_m3h:          Optional[Decimal] = None
    power_kw:               Optional[Decimal] = None
    specific_energy_kwh_m3: Optional[Decimal] = None

    load_pct:                  Optional[Decimal] = None
    running_hours_cumulative:  Optional[Decimal] = None
    loaded_hours_cumulative:   Optional[Decimal] = None

    air_temperature_c:    Optional[Decimal] = None
    dew_point_c:          Optional[Decimal] = None
    pressure_dew_point_c: Optional[Decimal] = None

    dryer_status:      Optional[str]     = None
    dryer_dew_point_c: Optional[Decimal] = None

    oil_pressure_bar: Optional[Decimal] = None
    oil_temp_c:       Optional[Decimal] = None
    filter_dp_bar:    Optional[Decimal] = None
    oil_level:        Optional[str]     = None

    leak_test_done:      bool
    leak_estimation_pct: Optional[Decimal] = None
    leak_volume_nm3:     Optional[Decimal] = None

    night_idle_kwh: Optional[Decimal] = None
    night_idle_nm3: Optional[Decimal] = None

    start_stop_count:  Optional[int]     = None
    downtime_minutes:  Optional[int]     = None
    downtime_reason:   Optional[str]     = None
    maintenance_flag:  bool
    status:            str
    source_method:     str
    is_anomaly:        bool
    anomaly_note:      Optional[str]     = None
    notes:             Optional[str]     = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# KPIs & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class AirKPIs(BaseModel):
    """
    Aggregated KPIs for a compressor / compressed air system over a date window.

    Anomaly threshold guidance:
      specific_energy_kwh_nm3 > 0.12   → poor efficiency; check unload time / leaks
      idle_run_ratio > 20 %             → high idle; investigate demand profile
      avg_leak_pct > 5 %                → significant leak; schedule leak hunt
      night_pct > 15 %                  → excessive night consumption; check auto-stop
      pressure_drop_bar > 0.3           → excessive line pressure loss
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Volume & energy
    total_air_nm3:          Decimal = Decimal("0")
    total_electricity_kwh:  Decimal = Decimal("0")
    specific_energy_kwh_nm3: Optional[Decimal] = None   # kWh / Nm³

    # Time breakdown (hours)
    total_runtime_hours:     Optional[Decimal] = None
    total_load_hours:        Optional[Decimal] = None
    total_unload_hours:      Optional[Decimal] = None
    total_idle_hours:        Optional[Decimal] = None

    # Utilisation KPIs
    utilization_pct:  Optional[Decimal] = None   # load_hours / runtime × 100
    idle_run_ratio:   Optional[Decimal] = None   # idle_hours / runtime × 100

    # Pressure
    avg_discharge_pressure_bar:     Optional[Decimal] = None
    avg_system_pressure_bar:        Optional[Decimal] = None
    avg_receiver_pressure_bar:      Optional[Decimal] = None
    avg_line_pressure_bar:          Optional[Decimal] = None
    avg_pressure_drop_bar:          Optional[Decimal] = None   # discharge - line

    # Dryer
    avg_dryer_dew_point_c: Optional[Decimal] = None

    # Leak
    leak_test_count:  int             = 0
    avg_leak_pct:     Optional[Decimal] = None
    total_leak_nm3:   Optional[Decimal] = None

    # Night / non-production
    total_night_kwh: Optional[Decimal] = None
    night_pct:       Optional[Decimal] = None   # night_kwh / total_kwh × 100

    # Cost (from utility_transactions COMPRESSED_AIR)
    air_cost_total:   Optional[Decimal] = None
    air_cost_per_nm3: Optional[Decimal] = None

    # Counts
    record_count:      int = 0
    anomaly_count:     int = 0
    maintenance_count: int = 0
    start_stop_total:  int = 0

    # Anomaly flags
    flag_high_idle:        bool = False   # idle_run_ratio > 20 %
    flag_leak_detected:    bool = False   # avg_leak_pct > 5 %
    flag_pressure_drop:    bool = False   # avg_pressure_drop > 0.3 bar
    flag_high_night:       bool = False   # night_pct > 15 %
    flag_poor_efficiency:  bool = False   # specific_energy > 0.12 kWh/Nm³


# ── Trend & breakdown ─────────────────────────────────────────────────────────

class AirTrendPoint(BaseModel):
    """Daily aggregation for trend charts."""
    date:                str = ""
    air_nm3:             Decimal = Decimal("0")
    electricity_kwh:     Decimal = Decimal("0")
    load_hours:          Decimal = Decimal("0")
    idle_hours:          Decimal = Decimal("0")
    night_kwh:           Decimal = Decimal("0")
    avg_discharge_bar:   Optional[Decimal] = None
    avg_line_bar:        Optional[Decimal] = None
    avg_specific_energy: Optional[Decimal] = None
    anomaly_count:       int = 0
    record_count:        int = 0

    # fix string → date for actual use
    model_config = {"from_attributes": True}


class AirShiftPoint(BaseModel):
    shift_id:        Optional[str]
    label:           str
    air_nm3:         Decimal = Decimal("0")
    electricity_kwh: Decimal = Decimal("0")
    avg_specific_energy: Optional[Decimal] = None
    record_count:    int = 0
    anomaly_count:   int = 0


class AirBreakdownRow(BaseModel):
    """One row in a dimension breakdown (from utility_transactions COMPRESSED_AIR)."""
    dimension:    str
    group_key:    Optional[str]
    label:        str
    total_nm3:    Decimal = Decimal("0")
    total_cost:   Optional[Decimal] = None
    pct_of_total: Optional[Decimal] = None
    tx_count:     int = 0


class AirBreakdown(BaseModel):
    dimension:       str
    rows:            List[AirBreakdownRow]
    grand_total_nm3: Decimal


# ── Asset dropdown ─────────────────────────────────────────────────────────────

class CompressorAsset(BaseModel):
    id:       UUID
    asset_no: str
    name:     str
