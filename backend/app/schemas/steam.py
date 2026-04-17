"""
Steam & Boiler Management Schemas
──────────────────────────────────
KPI aggregation, trend, breakdown, and CRUD schemas.

Data sources:
  boiler_steam_records  – detailed operational log per boiler per shift/period
  utility_transactions  – STEAM utility_type for cost data & line allocation
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# BOILER RECORD CRUD
# ══════════════════════════════════════════════════════════════════════════════

class BoilerRecordCreate(BaseModel):
    asset_id:        UUID
    record_datetime: datetime
    shift_ref:       Optional[str] = None
    department:      Optional[str] = None
    period_hours:    Optional[Decimal] = None    # hours this record covers

    # Steam parameters (instantaneous / average readings)
    steam_pressure_bar:  Optional[Decimal] = None
    steam_temp_c:        Optional[Decimal] = None
    steam_flow_kgh:      Optional[Decimal] = None   # flow rate kg/h
    steam_quality_pct:   Optional[Decimal] = None

    # Period totals
    steam_generated_kg:    Optional[Decimal] = None  # total kg produced this period
    feedwater_consumed_m3: Optional[Decimal] = None  # total m³ feedwater used
    condensate_returned_m3: Optional[Decimal] = None # m³ condensate returned

    # Feed water quality
    feed_water_temp_c:   Optional[Decimal] = None
    feed_water_flow_lpm: Optional[Decimal] = None
    feed_water_ph:       Optional[Decimal] = None
    feed_water_tds_ppm:  Optional[Decimal] = None

    # Blowdown
    blowdown_pct:           Optional[Decimal] = None   # % continuous blowdown
    blowdown_volume_litres: Optional[Decimal] = None   # total blowdown L

    # Fuel
    fuel_type:        Optional[str]     = None   # NATURAL_GAS, LPG, DIESEL, BIOMASS
    fuel_consumption: Optional[Decimal] = None
    fuel_unit:        Optional[str]     = None   # m3, L, kg

    # Combustion / efficiency
    boiler_efficiency_pct: Optional[Decimal] = None
    flue_gas_temp_c:       Optional[Decimal] = None
    o2_pct:                Optional[Decimal] = None
    co2_pct:               Optional[Decimal] = None
    co_ppm:                Optional[Decimal] = None

    # Boiler water chemistry
    boiler_tds_ppm:      Optional[Decimal] = None
    boiler_ph:           Optional[Decimal] = None
    boiler_hardness_ppm: Optional[Decimal] = None
    conductivity_uscm:   Optional[Decimal] = None

    # Operational
    boiler_load_pct:      Optional[Decimal] = None
    burner_runtime_hours: Optional[Decimal] = None
    start_stop_count:     Optional[int]     = None
    running_hours_cumulative: Optional[Decimal] = None

    # Chemical treatment
    chemical_dosing_amount: Optional[Decimal] = None
    chemical_dosing_unit:   Optional[str]     = None

    # Downtime
    downtime_minutes: Optional[int] = None
    downtime_reason:  Optional[str] = None

    # Flags
    maintenance_flag: bool = False
    status:           str  = "RUNNING"
    source_method:    str  = "MANUAL"
    is_anomaly:       bool = False
    anomaly_note:     Optional[str] = None
    notes:            Optional[str] = None

    @field_validator("status")
    @classmethod
    def _chk_status(cls, v: str) -> str:
        valid = {"RUNNING", "STANDBY", "SHUTDOWN", "FAULT"}
        if v.upper() not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v.upper()


class BoilerRecordUpdate(BaseModel):
    record_datetime:     Optional[datetime] = None
    shift_ref:           Optional[str]  = None
    department:          Optional[str]  = None
    period_hours:        Optional[Decimal] = None
    steam_pressure_bar:  Optional[Decimal] = None
    steam_temp_c:        Optional[Decimal] = None
    steam_flow_kgh:      Optional[Decimal] = None
    steam_quality_pct:   Optional[Decimal] = None
    steam_generated_kg:    Optional[Decimal] = None
    feedwater_consumed_m3: Optional[Decimal] = None
    condensate_returned_m3: Optional[Decimal] = None
    feed_water_temp_c:   Optional[Decimal] = None
    feed_water_flow_lpm: Optional[Decimal] = None
    feed_water_ph:       Optional[Decimal] = None
    feed_water_tds_ppm:  Optional[Decimal] = None
    blowdown_pct:           Optional[Decimal] = None
    blowdown_volume_litres: Optional[Decimal] = None
    fuel_type:        Optional[str]     = None
    fuel_consumption: Optional[Decimal] = None
    fuel_unit:        Optional[str]     = None
    boiler_efficiency_pct: Optional[Decimal] = None
    flue_gas_temp_c:       Optional[Decimal] = None
    o2_pct:  Optional[Decimal] = None
    co2_pct: Optional[Decimal] = None
    co_ppm:  Optional[Decimal] = None
    boiler_tds_ppm:      Optional[Decimal] = None
    boiler_ph:           Optional[Decimal] = None
    boiler_hardness_ppm: Optional[Decimal] = None
    conductivity_uscm:   Optional[Decimal] = None
    boiler_load_pct:      Optional[Decimal] = None
    burner_runtime_hours: Optional[Decimal] = None
    start_stop_count:     Optional[int]     = None
    running_hours_cumulative: Optional[Decimal] = None
    chemical_dosing_amount: Optional[Decimal] = None
    chemical_dosing_unit:   Optional[str]     = None
    downtime_minutes: Optional[int] = None
    downtime_reason:  Optional[str] = None
    maintenance_flag: Optional[bool] = None
    status:           Optional[str]  = None
    source_method:    Optional[str]  = None
    is_anomaly:       Optional[bool] = None
    anomaly_note:     Optional[str]  = None
    notes:            Optional[str]  = None


class BoilerRecordRead(BaseModel):
    id:        UUID
    record_no: str
    asset_id:  UUID
    asset_name: Optional[str] = None
    asset_no:   Optional[str] = None

    record_datetime: datetime
    shift_ref:       Optional[str] = None
    department:      Optional[str] = None
    period_hours:    Optional[Decimal] = None

    steam_pressure_bar:  Optional[Decimal] = None
    steam_temp_c:        Optional[Decimal] = None
    steam_flow_kgh:      Optional[Decimal] = None
    steam_quality_pct:   Optional[Decimal] = None
    steam_generated_kg:    Optional[Decimal] = None
    feedwater_consumed_m3: Optional[Decimal] = None
    condensate_returned_m3: Optional[Decimal] = None

    feed_water_temp_c:   Optional[Decimal] = None
    feed_water_flow_lpm: Optional[Decimal] = None
    feed_water_ph:       Optional[Decimal] = None
    feed_water_tds_ppm:  Optional[Decimal] = None

    blowdown_pct:           Optional[Decimal] = None
    blowdown_volume_litres: Optional[Decimal] = None

    fuel_type:        Optional[str]     = None
    fuel_consumption: Optional[Decimal] = None
    fuel_unit:        Optional[str]     = None

    boiler_efficiency_pct: Optional[Decimal] = None
    flue_gas_temp_c:       Optional[Decimal] = None
    o2_pct:  Optional[Decimal] = None
    co2_pct: Optional[Decimal] = None
    co_ppm:  Optional[Decimal] = None

    boiler_tds_ppm:      Optional[Decimal] = None
    boiler_ph:           Optional[Decimal] = None
    boiler_hardness_ppm: Optional[Decimal] = None
    conductivity_uscm:   Optional[Decimal] = None

    boiler_load_pct:      Optional[Decimal] = None
    burner_runtime_hours: Optional[Decimal] = None
    start_stop_count:     Optional[int]     = None
    running_hours_cumulative: Optional[Decimal] = None

    chemical_dosing_amount: Optional[Decimal] = None
    chemical_dosing_unit:   Optional[str]     = None

    downtime_minutes: Optional[int]  = None
    downtime_reason:  Optional[str]  = None

    maintenance_flag: bool
    status:           str
    source_method:    str
    is_anomaly:       bool
    anomaly_note:     Optional[str] = None
    notes:            Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# KPIs & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class SteamKPIs(BaseModel):
    """
    Aggregated KPIs for a boiler / steam system over a date window.

    Calculated from boiler_steam_records (operational detail) and
    utility_transactions (STEAM type, for cost allocation).

    Anomaly threshold guidance:
      condensate_recovery_pct < 70  → poor return; check steam trap / distribution losses
      blowdown_loss_pct > 5         → excessive TDS blowdown; check water treatment
      gas_per_ton_steam: plant-specific — flag > 20% above rolling average
      efficiency_pct < 80           → significant efficiency decline
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Volume
    total_steam_generated_kg: Decimal = Decimal("0")
    total_steam_generated_tons: Decimal = Decimal("0")
    total_feedwater_m3:       Decimal = Decimal("0")
    total_condensate_m3:      Decimal = Decimal("0")
    total_blowdown_litres:    Decimal = Decimal("0")
    total_fuel_consumed:      Decimal = Decimal("0")
    fuel_unit:                Optional[str] = None

    # Per-ton intensity KPIs
    gas_per_ton_steam:    Optional[Decimal] = None   # fuel_unit / ton
    water_per_ton_steam:  Optional[Decimal] = None   # m³ / ton

    # Recovery & losses
    condensate_recovery_pct: Optional[Decimal] = None  # condensate/steam × 100
    blowdown_loss_pct:       Optional[Decimal] = None   # blowdown/(feedwater+blowdown) × 100

    # Efficiency
    avg_efficiency_pct:  Optional[Decimal] = None
    avg_boiler_load_pct: Optional[Decimal] = None
    avg_flue_temp_c:     Optional[Decimal] = None
    avg_o2_pct:          Optional[Decimal] = None

    # Operational
    total_burner_hours:  Optional[Decimal] = None
    total_downtime_hours: Optional[Decimal] = None
    availability_pct:    Optional[Decimal] = None
    total_start_stops:   int = 0

    # Cost (from utility_transactions STEAM)
    steam_cost_total:    Optional[Decimal] = None
    steam_cost_per_ton:  Optional[Decimal] = None

    # Chemical
    total_chemical_dosing: Optional[Decimal] = None

    # Quality / counts
    record_count:         int = 0
    anomaly_count:        int = 0
    maintenance_count:    int = 0

    # Anomaly flags (True = threshold breached)
    flag_low_condensate:  bool = False   # condensate < 70 %
    flag_high_blowdown:   bool = False   # blowdown > 5 %
    flag_low_efficiency:  bool = False   # efficiency < 80 %


# ── Trend & breakdown ─────────────────────────────────────────────────────────

class SteamTrendPoint(BaseModel):
    """Daily aggregation for trend charts."""
    date:                 date
    steam_generated_kg:   Decimal = Decimal("0")
    fuel_consumed:        Decimal = Decimal("0")
    feedwater_m3:         Decimal = Decimal("0")
    condensate_m3:        Decimal = Decimal("0")
    blowdown_litres:      Decimal = Decimal("0")
    avg_efficiency_pct:   Optional[Decimal] = None
    avg_boiler_load_pct:  Optional[Decimal] = None
    downtime_minutes:     int = 0
    anomaly_count:        int = 0
    record_count:         int = 0


class SteamShiftPoint(BaseModel):
    """Per-shift aggregation."""
    shift_id:          Optional[str]
    label:             str
    steam_generated_kg: Decimal = Decimal("0")
    fuel_consumed:     Decimal = Decimal("0")
    avg_efficiency_pct: Optional[Decimal] = None
    record_count:      int = 0
    anomaly_count:     int = 0


class SteamBreakdownRow(BaseModel):
    """One row in a dimension breakdown (from utility_transactions STEAM)."""
    dimension:    str
    group_key:    Optional[str]
    label:        str
    total_kg:     Decimal = Decimal("0")
    total_cost:   Optional[Decimal] = None
    pct_of_total: Optional[Decimal] = None
    tx_count:     int = 0


class SteamBreakdown(BaseModel):
    dimension:       str
    rows:            List[SteamBreakdownRow]
    grand_total_kg:  Decimal


# ── Asset dropdown ─────────────────────────────────────────────────────────────

class BoilerAsset(BaseModel):
    id:       UUID
    asset_no: str
    name:     str
