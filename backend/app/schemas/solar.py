"""
Solar Energy Management Schemas
────────────────────────────────
KPI aggregation, trend, breakdown, and CRUD schemas.

Data sources:
  utility_transactions  – SOLAR utility_type for generation volume & cost
  solar_records         – operational log (irradiance, DC/AC, PR ratio, grid export)
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ══════════════════════════════════════════════════════════════════════════════
# SOLAR RECORD CRUD
# ══════════════════════════════════════════════════════════════════════════════

class SolarRecordCreate(BaseModel):
    asset_id:        UUID
    record_datetime: datetime

    # Environmental
    irradiance_wm2:  Optional[Decimal] = None
    panel_temp_c:    Optional[Decimal] = None
    ambient_temp_c:  Optional[Decimal] = None

    # DC side
    dc_voltage_v:  Optional[Decimal] = None
    dc_current_a:  Optional[Decimal] = None
    dc_power_kw:   Optional[Decimal] = None

    # AC / inverter output
    ac_power_kw:            Optional[Decimal] = None
    energy_generated_kwh:   Optional[Decimal] = None
    grid_export_kwh:        Optional[Decimal] = None
    self_consumption_kwh:   Optional[Decimal] = None

    # Performance
    inverter_efficiency_pct: Optional[Decimal] = None
    pr_ratio:                Optional[Decimal] = None
    availability_pct:        Optional[Decimal] = None
    capacity_factor_pct:     Optional[Decimal] = None

    source_method: str = "IOT"
    is_anomaly:    bool = False
    anomaly_note:  Optional[str] = None
    notes:         Optional[str] = None


class SolarRecordUpdate(BaseModel):
    record_datetime: Optional[datetime] = None

    irradiance_wm2:  Optional[Decimal] = None
    panel_temp_c:    Optional[Decimal] = None
    ambient_temp_c:  Optional[Decimal] = None

    dc_voltage_v:  Optional[Decimal] = None
    dc_current_a:  Optional[Decimal] = None
    dc_power_kw:   Optional[Decimal] = None

    ac_power_kw:            Optional[Decimal] = None
    energy_generated_kwh:   Optional[Decimal] = None
    grid_export_kwh:        Optional[Decimal] = None
    self_consumption_kwh:   Optional[Decimal] = None

    inverter_efficiency_pct: Optional[Decimal] = None
    pr_ratio:                Optional[Decimal] = None
    availability_pct:        Optional[Decimal] = None
    capacity_factor_pct:     Optional[Decimal] = None

    source_method: Optional[str] = None
    is_anomaly:    Optional[bool] = None
    anomaly_note:  Optional[str] = None
    notes:         Optional[str] = None


class SolarRecordRead(BaseModel):
    id:        UUID
    record_no: str
    asset_id:  UUID
    asset_name: Optional[str] = None
    asset_no:   Optional[str] = None

    record_datetime: datetime

    irradiance_wm2:  Optional[Decimal] = None
    panel_temp_c:    Optional[Decimal] = None
    ambient_temp_c:  Optional[Decimal] = None

    dc_voltage_v:  Optional[Decimal] = None
    dc_current_a:  Optional[Decimal] = None
    dc_power_kw:   Optional[Decimal] = None

    ac_power_kw:            Optional[Decimal] = None
    energy_generated_kwh:   Optional[Decimal] = None
    grid_export_kwh:        Optional[Decimal] = None
    self_consumption_kwh:   Optional[Decimal] = None

    inverter_efficiency_pct: Optional[Decimal] = None
    pr_ratio:                Optional[Decimal] = None
    availability_pct:        Optional[Decimal] = None
    capacity_factor_pct:     Optional[Decimal] = None

    source_method: str
    is_anomaly:    bool
    anomaly_note:  Optional[str] = None
    notes:         Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS — KPIs
# ══════════════════════════════════════════════════════════════════════════════

class SolarKPIs(BaseModel):
    """
    Plant-wide (or asset-scoped) solar KPIs for a given date window.

    Sources:
      - utility_transactions (utility_type = SOLAR) for generation volume & cost
      - solar_records for self-consumption, grid export, PR ratio, inverter efficiency
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Generation volume (from utility_transactions)
    total_generated_kwh:       Decimal
    avg_generated_kwh_per_day: Optional[Decimal] = None
    peak_generation_kwh:       Optional[Decimal] = None

    # Self-consumption & export (from solar_records)
    total_self_consumption_kwh: Optional[Decimal] = None
    total_grid_export_kwh:      Optional[Decimal] = None
    self_consumption_ratio:     Optional[Decimal] = None  # self_consumed / generated
    solar_contribution_pct:     Optional[Decimal] = None  # generated vs expected

    # Performance (from solar_records)
    avg_pr_ratio:                Optional[Decimal] = None
    avg_inverter_efficiency_pct: Optional[Decimal] = None
    avg_capacity_factor_pct:     Optional[Decimal] = None

    # Cost / savings
    total_cost_offset:    Optional[Decimal] = None   # avoided grid cost (from transactions)
    avg_cost_per_kwh:     Optional[Decimal] = None

    # Counts / quality
    tx_count:      int = 0
    record_count:  int = 0
    anomaly_count: int = 0


# ── Trend points ───────────────────────────────────────────────────────────────

class SolarTrendPoint(BaseModel):
    date:                 date
    total_generated_kwh:  Decimal
    grid_export_kwh:      Optional[Decimal] = None
    self_consumption_kwh: Optional[Decimal] = None
    avg_pr_ratio:         Optional[Decimal] = None
    total_cost:           Optional[Decimal] = None
    anomaly_count:        int = 0
    tx_count:             int = 0


# ── Breakdown ─────────────────────────────────────────────────────────────────

class SolarBreakdownRow(BaseModel):
    dimension:            str
    group_key:            Optional[str]
    label:                str
    total_generated_kwh:  Decimal
    pct_of_total:         Optional[Decimal] = None
    total_cost:           Optional[Decimal] = None
    tx_count:             int = 0
    anomaly_count:        int = 0


class SolarBreakdown(BaseModel):
    dimension:                 str
    rows:                      List[SolarBreakdownRow]
    grand_total_generated_kwh: Decimal


# ── Tariff summary ─────────────────────────────────────────────────────────────

class SolarTariffRead(BaseModel):
    id:           str
    tariff_code:  str
    name:         str
    tariff_type:  str
    base_rate:    Decimal
    unit:         str
    currency_code: str
    effective_from: date
    effective_to:   Optional[date] = None
    is_active:    bool

    model_config = {"from_attributes": True}
