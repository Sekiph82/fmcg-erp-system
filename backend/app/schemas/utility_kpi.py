"""
Utility KPI Center — Pydantic v2 Schemas
All KPI payloads served by the /kpi endpoints.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


# ── Shared ────────────────────────────────────────────────────────────────────

class TopConsumerRow(BaseModel):
    label:       str
    consumption: Decimal
    unit:        str
    cost:        Optional[Decimal] = None
    pct_of_total: Optional[Decimal] = None
    record_count: int = 0


class TopConsumers(BaseModel):
    dimension:    str          # department | production_line | machine_ref
    utility_type: Optional[str] = None
    date_from:    Optional[str] = None
    date_to:      Optional[str] = None
    rows:         List[TopConsumerRow]
    grand_total:  Decimal


class DailyTrendPoint(BaseModel):
    date:             str
    electricity_kwh:  Optional[Decimal] = None
    water_m3:         Optional[Decimal] = None
    gas_nm3:          Optional[Decimal] = None
    steam_ton:        Optional[Decimal] = None
    solar_kwh:        Optional[Decimal] = None
    compressed_air_nm3: Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    is_estimated:     bool = False


# ── Main dashboard ─────────────────────────────────────────────────────────────

class MainDashboardKPIs(BaseModel):
    report_date:   str
    period_label:  str = "Today"

    # Electricity
    electricity_kwh_today:     Optional[Decimal] = None
    electricity_kwh_mtd:       Optional[Decimal] = None
    electricity_kwh_per_ton:   Optional[Decimal] = None
    peak_demand_kw:            Optional[Decimal] = None
    night_base_load_kwh:       Optional[Decimal] = None

    # Water
    water_m3_today:            Optional[Decimal] = None
    water_m3_per_ton:          Optional[Decimal] = None

    # Gas
    gas_nm3_today:             Optional[Decimal] = None
    gas_nm3_per_ton:           Optional[Decimal] = None

    # Steam / Boiler
    steam_ton_today:           Optional[Decimal] = None
    gas_per_ton_steam:         Optional[Decimal] = None
    condensate_recovery_pct:   Optional[Decimal] = None
    blowdown_loss_pct:         Optional[Decimal] = None
    boiler_efficiency_pct:     Optional[Decimal] = None

    # Compressed Air
    air_nm3_today:             Optional[Decimal] = None
    air_kwh_per_nm3:           Optional[Decimal] = None
    leak_estimate_pct:         Optional[Decimal] = None
    compressor_efficiency_pct: Optional[Decimal] = None

    # Soft Water
    soft_water_m3_today:       Optional[Decimal] = None
    soft_water_conversion_pct: Optional[Decimal] = None
    salt_per_m3_soft:          Optional[Decimal] = None

    # Solar
    solar_kwh_today:           Optional[Decimal] = None
    solar_contribution_pct:    Optional[Decimal] = None
    solar_vs_expected_pct:     Optional[Decimal] = None

    # Wastewater
    wastewater_cost_per_m3:    Optional[Decimal] = None
    cod_removal_pct:           Optional[Decimal] = None
    wastewater_compliance:     Optional[str] = None

    # Treatment Chemicals
    chemical_cost_today:       Optional[Decimal] = None

    # Cost
    utility_cost_today:        Optional[Decimal] = None
    utility_cost_mtd:          Optional[Decimal] = None
    utility_cost_per_ton:      Optional[Decimal] = None
    utility_cost_per_batch:    Optional[Decimal] = None
    currency_code:             str = "USD"

    # Machine utility
    machine_standby_pct:       Optional[Decimal] = None
    dept_utility_intensity:    Optional[Decimal] = None   # cost/m² or cost/ton per dept

    # Production reference (supplied externally or derived)
    production_tons_today:     Optional[Decimal] = None

    # Alarms
    critical_alarm_count: int = 0
    warning_alarm_count:  int = 0

    # Data quality flag
    has_estimated_data: bool = False


# ── Per-utility sub-dashboard KPIs ────────────────────────────────────────────

class ElectricityDashboardKPIs(BaseModel):
    date_from:            str
    date_to:              str
    kwh_total:            Optional[Decimal] = None
    kwh_per_ton:          Optional[Decimal] = None
    peak_demand_kw:       Optional[Decimal] = None
    night_base_load_kwh:  Optional[Decimal] = None
    solar_offset_kwh:     Optional[Decimal] = None
    solar_contribution_pct: Optional[Decimal] = None
    total_cost:           Optional[Decimal] = None
    cost_per_kwh:         Optional[Decimal] = None
    estimated_pct:        Optional[Decimal] = None
    anomaly_count:        int = 0


class WaterDashboardKPIs(BaseModel):
    date_from:      str
    date_to:        str
    water_m3_total: Optional[Decimal] = None
    water_m3_per_ton: Optional[Decimal] = None
    process_water_m3: Optional[Decimal] = None
    total_cost:     Optional[Decimal] = None
    cost_per_m3:    Optional[Decimal] = None
    estimated_pct:  Optional[Decimal] = None
    anomaly_count:  int = 0


class BoilerDashboardKPIs(BaseModel):
    date_from:              str
    date_to:                str
    steam_ton_total:        Optional[Decimal] = None
    fuel_consumed_total:    Optional[Decimal] = None
    fuel_unit:              Optional[str] = None
    gas_per_ton_steam:      Optional[Decimal] = None
    boiler_efficiency_pct:  Optional[Decimal] = None
    condensate_recovery_pct: Optional[Decimal] = None
    blowdown_loss_pct:      Optional[Decimal] = None
    feedwater_m3_total:     Optional[Decimal] = None
    burner_runtime_hours:   Optional[Decimal] = None
    avg_boiler_load_pct:    Optional[Decimal] = None
    anomaly_count:          int = 0


class CompressorDashboardKPIs(BaseModel):
    date_from:              str
    date_to:                str
    air_nm3_total:          Optional[Decimal] = None
    electricity_kwh_total:  Optional[Decimal] = None
    air_kwh_per_nm3:        Optional[Decimal] = None
    leak_estimate_pct:      Optional[Decimal] = None
    night_idle_kwh:         Optional[Decimal] = None
    avg_load_pct:           Optional[Decimal] = None
    runtime_hours:          Optional[Decimal] = None
    anomaly_count:          int = 0


class SoftWaterDashboardKPIs(BaseModel):
    date_from:              str
    date_to:                str
    sw_volume_m3:           Optional[Decimal] = None
    raw_input_m3:           Optional[Decimal] = None
    conversion_efficiency_pct: Optional[Decimal] = None
    salt_consumed_kg:       Optional[Decimal] = None
    salt_per_m3:            Optional[Decimal] = None
    avg_product_hardness:   Optional[Decimal] = None
    regen_count:            Optional[int] = None
    anomaly_count:          int = 0


class SolarDashboardKPIs(BaseModel):
    date_from:              str
    date_to:                str
    kwh_generated:          Optional[Decimal] = None
    kwh_self_consumed:      Optional[Decimal] = None
    kwh_exported:           Optional[Decimal] = None
    solar_contribution_pct: Optional[Decimal] = None
    avg_pr_ratio:           Optional[Decimal] = None
    avg_capacity_factor:    Optional[Decimal] = None
    avg_inverter_efficiency: Optional[Decimal] = None
    anomaly_count:          int = 0


class ChemicalDashboardKPIs(BaseModel):
    date_from:          str
    date_to:            str
    total_cost:         Optional[Decimal] = None
    total_consumed_kg:  Optional[Decimal] = None
    cost_per_day:       Optional[Decimal] = None
    distinct_chemicals: int = 0
    boiler_cost:        Optional[Decimal] = None
    cooling_cost:       Optional[Decimal] = None
    wwtp_cost:          Optional[Decimal] = None


class WastewaterDashboardKPIs(BaseModel):
    date_from:          str
    date_to:            str
    cod_removal_pct:    Optional[Decimal] = None
    bod_removal_pct:    Optional[Decimal] = None
    avg_do_mgl:         Optional[Decimal] = None
    avg_effluent_ph:    Optional[Decimal] = None
    sludge_kg_total:    Optional[Decimal] = None
    power_kwh_total:    Optional[Decimal] = None
    power_per_m3:       Optional[Decimal] = None
    compliant_pct:      Optional[Decimal] = None
    non_compliant_count: int = 0
    anomaly_count:      int = 0


class MachineDashboardKPIs(BaseModel):
    date_from:              str
    date_to:                str
    total_consumption:      Optional[Decimal] = None
    consumption_unit:       Optional[str] = None
    electricity_per_runtime_h: Optional[Decimal] = None
    water_per_batch:        Optional[Decimal] = None
    air_per_batch:          Optional[Decimal] = None
    standby_pct:            Optional[Decimal] = None
    cost_per_batch:         Optional[Decimal] = None
    avg_variance_pct:       Optional[Decimal] = None
    anomaly_count:          int = 0
    flag_high_variance:     bool = False
    flag_standby_waste:     bool = False


class UtilityCostDashboardKPIs(BaseModel):
    date_from:          str
    date_to:            str
    total_cost:         Optional[Decimal] = None
    electricity_cost:   Optional[Decimal] = None
    water_cost:         Optional[Decimal] = None
    gas_cost:           Optional[Decimal] = None
    steam_cost:         Optional[Decimal] = None
    other_cost:         Optional[Decimal] = None
    cost_per_ton:       Optional[Decimal] = None
    cost_per_batch:     Optional[Decimal] = None
    total_bills:        int = 0
    unpaid_amount:      Optional[Decimal] = None
    currency_code:      str = "USD"
