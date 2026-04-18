"""
Utilities Reports — Pydantic v2 Schemas
All response shapes for the 21 utility report types.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


# ── Shared primitives ──────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str
    value: Optional[Decimal] = None
    value2: Optional[Decimal] = None   # second series (e.g. cost alongside consumption)
    label: Optional[str] = None


class DistributionSlice(BaseModel):
    label: str
    value: Optional[Decimal] = None
    pct: Optional[Decimal] = None


# ── 1. Daily Consumption Reports ───────────────────────────────────────────────

class DailyConsumptionRow(BaseModel):
    date: str
    utility_type: str
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    total_cost: Optional[Decimal] = None
    currency: Optional[str] = None
    department: Optional[str] = None
    shift_ref: Optional[str] = None
    tx_count: Optional[int] = None


class DailyConsumptionReport(BaseModel):
    date_from: str
    date_to: str
    utility_type: Optional[str] = None
    total_quantity: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    unit: Optional[str] = None
    rows: List[DailyConsumptionRow] = []
    trend: List[TrendPoint] = []


# ── 2. Daily Utility Summary ───────────────────────────────────────────────────

class UtilityTypeSummaryRow(BaseModel):
    utility_type: str
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    total_cost: Optional[Decimal] = None
    tx_count: Optional[int] = None
    avg_daily: Optional[Decimal] = None


class DailySummaryReport(BaseModel):
    date_from: str
    date_to: str
    total_cost: Optional[Decimal] = None
    rows: List[UtilityTypeSummaryRow] = []
    trend: List[TrendPoint] = []


# ── 3. Boiler Efficiency Report ────────────────────────────────────────────────

class BoilerEfficiencyRow(BaseModel):
    record_no: str
    asset_no: Optional[str] = None
    record_datetime: str
    shift_ref: Optional[str] = None
    department: Optional[str] = None
    period_hours: Optional[Decimal] = None
    steam_generated_kg: Optional[Decimal] = None
    fuel_type: Optional[str] = None
    fuel_consumption: Optional[Decimal] = None
    fuel_unit: Optional[str] = None
    boiler_efficiency_pct: Optional[Decimal] = None
    boiler_load_pct: Optional[Decimal] = None
    blowdown_pct: Optional[Decimal] = None
    feedwater_consumed_m3: Optional[Decimal] = None
    condensate_returned_m3: Optional[Decimal] = None
    steam_pressure_bar: Optional[Decimal] = None
    steam_temp_c: Optional[Decimal] = None
    status: Optional[str] = None
    is_anomaly: Optional[bool] = None


class BoilerEfficiencyReport(BaseModel):
    date_from: str
    date_to: str
    avg_efficiency_pct: Optional[Decimal] = None
    total_steam_kg: Optional[Decimal] = None
    total_fuel: Optional[Decimal] = None
    avg_load_pct: Optional[Decimal] = None
    condensate_recovery_pct: Optional[Decimal] = None
    rows: List[BoilerEfficiencyRow] = []
    trend: List[TrendPoint] = []


# ── 4. Steam Generation Report ─────────────────────────────────────────────────

class SteamGenerationRow(BaseModel):
    date: str
    asset_no: Optional[str] = None
    steam_generated_kg: Optional[Decimal] = None
    steam_pressure_bar: Optional[Decimal] = None
    steam_temp_c: Optional[Decimal] = None
    steam_flow_kgh: Optional[Decimal] = None
    steam_quality_pct: Optional[Decimal] = None
    feedwater_m3: Optional[Decimal] = None
    blowdown_litres: Optional[Decimal] = None


class SteamGenerationReport(BaseModel):
    date_from: str
    date_to: str
    total_steam_kg: Optional[Decimal] = None
    avg_pressure_bar: Optional[Decimal] = None
    avg_temp_c: Optional[Decimal] = None
    avg_quality_pct: Optional[Decimal] = None
    rows: List[SteamGenerationRow] = []
    trend: List[TrendPoint] = []


# ── 5. Compressor Performance & Leak Report ────────────────────────────────────

class CompressorPerformanceRow(BaseModel):
    record_no: str
    asset_no: Optional[str] = None
    record_datetime: str
    shift_ref: Optional[str] = None
    department: Optional[str] = None
    period_hours: Optional[Decimal] = None
    air_generated_nm3: Optional[Decimal] = None
    electricity_used_kwh: Optional[Decimal] = None
    specific_energy_kwh_m3: Optional[Decimal] = None
    load_pct: Optional[Decimal] = None
    discharge_pressure_bar: Optional[Decimal] = None
    leak_test_done: Optional[bool] = None
    leak_estimation_pct: Optional[Decimal] = None
    leak_volume_nm3: Optional[Decimal] = None
    night_idle_kwh: Optional[Decimal] = None
    status: Optional[str] = None
    is_anomaly: Optional[bool] = None


class CompressorPerformanceReport(BaseModel):
    date_from: str
    date_to: str
    total_air_nm3: Optional[Decimal] = None
    total_kwh: Optional[Decimal] = None
    avg_specific_energy: Optional[Decimal] = None
    avg_load_pct: Optional[Decimal] = None
    avg_leak_pct: Optional[Decimal] = None
    total_leak_nm3: Optional[Decimal] = None
    rows: List[CompressorPerformanceRow] = []
    trend: List[TrendPoint] = []


# ── 6. Soft Water Production & Salt Report ─────────────────────────────────────

class SoftWaterProductionRow(BaseModel):
    record_no: str
    asset_no: Optional[str] = None
    record_datetime: str
    shift_ref: Optional[str] = None
    department: Optional[str] = None
    volume_treated_m3: Optional[Decimal] = None
    raw_water_input_m3: Optional[Decimal] = None
    salt_consumed_kg: Optional[Decimal] = None
    salt_per_m3: Optional[Decimal] = None
    efficiency_pct: Optional[Decimal] = None
    feed_water_hardness_ppm: Optional[Decimal] = None
    product_water_hardness_ppm: Optional[Decimal] = None
    regeneration_count: Optional[int] = None
    destination_tag: Optional[str] = None


class SoftWaterProductionReport(BaseModel):
    date_from: str
    date_to: str
    total_volume_treated_m3: Optional[Decimal] = None
    total_raw_water_m3: Optional[Decimal] = None
    total_salt_kg: Optional[Decimal] = None
    avg_salt_per_m3: Optional[Decimal] = None
    avg_efficiency_pct: Optional[Decimal] = None
    conversion_pct: Optional[Decimal] = None
    rows: List[SoftWaterProductionRow] = []
    trend: List[TrendPoint] = []


# ── 7. Water Treatment Chemical Report ────────────────────────────────────────

class ChemicalTreatmentRow(BaseModel):
    record_no: str
    asset_no: Optional[str] = None
    record_datetime: str
    treatment_type: Optional[str] = None
    chemical_name: Optional[str] = None
    chemical_category: Optional[str] = None
    treatment_area: Optional[str] = None
    quantity_dosed: Optional[Decimal] = None
    unit: Optional[str] = None
    target_dose_ppm: Optional[Decimal] = None
    actual_dose_ppm: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    overdose_flag: Optional[bool] = None
    underdose_flag: Optional[bool] = None
    feed_ph: Optional[Decimal] = None
    product_ph: Optional[Decimal] = None
    residual_chlorine_ppm: Optional[Decimal] = None


class ChemicalTreatmentReport(BaseModel):
    date_from: str
    date_to: str
    total_dosed: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    overdose_count: Optional[int] = None
    underdose_count: Optional[int] = None
    rows: List[ChemicalTreatmentRow] = []
    by_chemical: List[DistributionSlice] = []
    by_area: List[DistributionSlice] = []


# ── 8. Solar Generation vs Consumption Report ──────────────────────────────────

class SolarGenerationRow(BaseModel):
    date: str
    asset_no: Optional[str] = None
    energy_generated_kwh: Optional[Decimal] = None
    self_consumption_kwh: Optional[Decimal] = None
    grid_export_kwh: Optional[Decimal] = None
    irradiance_wm2: Optional[Decimal] = None
    pr_ratio: Optional[Decimal] = None
    inverter_efficiency_pct: Optional[Decimal] = None
    availability_pct: Optional[Decimal] = None
    capacity_factor_pct: Optional[Decimal] = None
    total_elec_consumption_kwh: Optional[Decimal] = None
    solar_contribution_pct: Optional[Decimal] = None


class SolarGenerationReport(BaseModel):
    date_from: str
    date_to: str
    total_generated_kwh: Optional[Decimal] = None
    total_self_consumption_kwh: Optional[Decimal] = None
    total_grid_export_kwh: Optional[Decimal] = None
    avg_pr_ratio: Optional[Decimal] = None
    avg_contribution_pct: Optional[Decimal] = None
    rows: List[SolarGenerationRow] = []
    trend: List[TrendPoint] = []


# ── 9. Wastewater Compliance Report ───────────────────────────────────────────

class WastewaterComplianceRow(BaseModel):
    record_no: str
    asset_no: Optional[str] = None
    record_datetime: str
    process_stage: Optional[str] = None
    shift_ref: Optional[str] = None
    influent_cod_mgl: Optional[Decimal] = None
    effluent_cod_mgl: Optional[Decimal] = None
    cod_removal_pct: Optional[Decimal] = None
    influent_bod_mgl: Optional[Decimal] = None
    effluent_bod_mgl: Optional[Decimal] = None
    influent_tss_mgl: Optional[Decimal] = None
    effluent_tss_mgl: Optional[Decimal] = None
    effluent_ph: Optional[Decimal] = None
    do_mgl: Optional[Decimal] = None
    compliance_status: Optional[str] = None
    permit_limit_ref: Optional[str] = None
    deviation_reason: Optional[str] = None
    power_consumed_kwh: Optional[Decimal] = None
    sludge_produced_kg: Optional[Decimal] = None


class WastewaterComplianceReport(BaseModel):
    date_from: str
    date_to: str
    compliant_count: Optional[int] = None
    non_compliant_count: Optional[int] = None
    borderline_count: Optional[int] = None
    compliance_rate_pct: Optional[Decimal] = None
    avg_cod_removal_pct: Optional[Decimal] = None
    rows: List[WastewaterComplianceRow] = []
    trend: List[TrendPoint] = []


# ── 10. Cost Allocation Reports ────────────────────────────────────────────────

class CostAllocationRow(BaseModel):
    dimension: str           # dept name / line / machine / product / batch
    utility_type: Optional[str] = None
    allocated_cost: Optional[Decimal] = None
    allocated_quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    cost_per_unit: Optional[Decimal] = None
    cost_per_ton: Optional[Decimal] = None
    production_volume_kg: Optional[Decimal] = None
    allocation_count: Optional[int] = None
    pct_of_total: Optional[Decimal] = None


class CostAllocationReport(BaseModel):
    date_from: str
    date_to: str
    group_by: str   # department | production_line | machine_ref | product | batch
    utility_type: Optional[str] = None
    total_cost: Optional[Decimal] = None
    rows: List[CostAllocationRow] = []
    by_utility: List[DistributionSlice] = []


# ── 11. Base Load Analysis ─────────────────────────────────────────────────────

class BaseLoadRow(BaseModel):
    utility_type: str
    unit: Optional[str] = None
    min_daily: Optional[Decimal] = None
    p10_daily: Optional[Decimal] = None
    p25_daily: Optional[Decimal] = None
    median_daily: Optional[Decimal] = None
    mean_daily: Optional[Decimal] = None
    p75_daily: Optional[Decimal] = None
    p90_daily: Optional[Decimal] = None
    max_daily: Optional[Decimal] = None
    base_load_est: Optional[Decimal] = None
    base_load_pct: Optional[Decimal] = None
    cost_base_load: Optional[Decimal] = None


class BaseLoadAnalysis(BaseModel):
    date_from: str
    date_to: str
    rows: List[BaseLoadRow] = []
    trend: List[TrendPoint] = []


# ── 12. Peak Demand Analysis ───────────────────────────────────────────────────

class PeakDemandRow(BaseModel):
    date: str
    utility_type: str
    department: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    total_cost: Optional[Decimal] = None
    is_anomaly: Optional[bool] = None


class PeakDemandAnalysis(BaseModel):
    date_from: str
    date_to: str
    utility_type: Optional[str] = None
    peak_date: Optional[str] = None
    peak_value: Optional[Decimal] = None
    peak_unit: Optional[str] = None
    top_days: List[PeakDemandRow] = []
    trend: List[TrendPoint] = []


# ── 13. Alarm Trend Report ────────────────────────────────────────────────────

class AlarmTrendRow(BaseModel):
    date: str
    critical: Optional[int] = None
    alert: Optional[int] = None
    warning: Optional[int] = None
    info: Optional[int] = None
    total: Optional[int] = None


class AlarmDetailRow(BaseModel):
    event_no: str
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None
    utility_type: Optional[str] = None
    asset_no: Optional[str] = None
    device_code: Optional[str] = None
    severity: Optional[str] = None
    triggered_at: str
    status: Optional[str] = None
    triggered_value: Optional[Decimal] = None
    threshold_value: Optional[Decimal] = None
    parameter: Optional[str] = None


class AlarmTrendReport(BaseModel):
    date_from: str
    date_to: str
    total_events: Optional[int] = None
    critical_count: Optional[int] = None
    unresolved_count: Optional[int] = None
    trend: List[AlarmTrendRow] = []
    top_rules: List[DistributionSlice] = []
    recent: List[AlarmDetailRow] = []


# ── 14. Abnormal Consumption Report ───────────────────────────────────────────

class AbnormalConsumptionRow(BaseModel):
    date: str
    utility_type: str
    department: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    mean_baseline: Optional[Decimal] = None
    deviation_pct: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    is_anomaly: Optional[bool] = None
    anomaly_note: Optional[str] = None


class AbnormalConsumptionReport(BaseModel):
    date_from: str
    date_to: str
    utility_type: Optional[str] = None
    anomaly_count: Optional[int] = None
    high_deviation_count: Optional[int] = None
    rows: List[AbnormalConsumptionRow] = []


# ── 15. Sustainability Summary ─────────────────────────────────────────────────

class SustainabilityMetric(BaseModel):
    label: str
    value: Optional[Decimal] = None
    unit: Optional[str] = None
    benchmark: Optional[Decimal] = None
    trend: Optional[str] = None   # "up" | "down" | "stable"


class SustainabilityReport(BaseModel):
    date_from: str
    date_to: str
    # Energy
    total_electricity_kwh: Optional[Decimal] = None
    solar_kwh: Optional[Decimal] = None
    solar_pct: Optional[Decimal] = None
    # Water
    total_water_m3: Optional[Decimal] = None
    process_water_m3: Optional[Decimal] = None
    # Waste
    wastewater_treated_m3: Optional[Decimal] = None
    compliance_rate_pct: Optional[Decimal] = None
    # Cost
    total_utility_cost: Optional[Decimal] = None
    # Carbon estimate (kgCO2e using standard grid factor 0.7 kgCO2e/kWh)
    estimated_co2e_kg: Optional[Decimal] = None
    metrics: List[SustainabilityMetric] = []
    trend: List[TrendPoint] = []
