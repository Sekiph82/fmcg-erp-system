"""
Biological / Wastewater Treatment Schemas
─────────────────────────────────────────
KPI aggregation, trend, alarm readiness, and CRUD schemas for the
biological / physico-chemical wastewater treatment plant module.

Data source: wastewater_records table (WastewaterRecord model).

KPIs computed:
  cod_removal_pct       – (influent_cod − effluent_cod) / influent_cod × 100
  bod_removal_pct       – (influent_bod − effluent_bod) / influent_bod × 100
  compliance_pct        – compliant records / total records × 100
  treatment_cost_per_m3 – total utility cost / total effluent volume
  blower_energy_per_m3  – blower_power_kwh / effluent_volume
  chemical_cost_per_m3  – chemical cost / effluent_volume (external cost feed)
  sludge_gen_rate       – sludge_produced_kg / influent_volume
  non_compliance_risk   – flag when recent non-compliance trend detected

Alarm triggers (evaluated per record on create/update):
  pH out of range          effluent_ph < 6.0 or > 9.0
  COD too high             effluent_cod_mgl > threshold
  Low dissolved oxygen     do_mgl < 1.5
  Blower failure           aeration_runtime_hours == 0 and plant active
  Overflow risk            influent_flow_m3h > overflow_threshold
  Non-compliant discharge  compliance_status == NON_COMPLIANT
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# WASTEWATER RECORD CRUD
# ══════════════════════════════════════════════════════════════════════════════

class WastewaterRecordCreate(BaseModel):
    asset_id:        UUID
    record_datetime: datetime
    process_stage:   str        = "SECONDARY"   # WastewaterProcess enum value
    shift_ref:       Optional[str]     = None
    operator_id:     Optional[UUID]    = None    # alias → entered_by_id

    # Flow
    influent_flow_m3h: Optional[Decimal] = None
    effluent_flow_m3h: Optional[Decimal] = None

    # Organic load — COD
    influent_cod_mgl:  Optional[Decimal] = None
    effluent_cod_mgl:  Optional[Decimal] = None

    # Organic load — BOD
    influent_bod_mgl:  Optional[Decimal] = None
    effluent_bod_mgl:  Optional[Decimal] = None

    # Solids — TSS
    influent_tss_mgl:  Optional[Decimal] = None
    effluent_tss_mgl:  Optional[Decimal] = None

    # pH
    influent_ph:       Optional[Decimal] = None
    effluent_ph:       Optional[Decimal] = None

    # Biological process parameters
    do_mgl:            Optional[Decimal] = None   # Dissolved Oxygen
    mlss_mgl:          Optional[Decimal] = None
    mlvss_mgl:         Optional[Decimal] = None
    svi:               Optional[Decimal] = None
    srt_days:          Optional[Decimal] = None

    # Additional process parameters
    conductivity_us_cm: Optional[Decimal] = None
    temperature_c:      Optional[Decimal] = None

    # Energy & aeration
    power_consumed_kwh:     Optional[Decimal] = None
    aeration_runtime_hours: Optional[Decimal] = None   # blower_runtime
    blower_power_kw:        Optional[Decimal] = None   # blower_power

    # Chemical dosing
    nutrient_dose_kg:  Optional[Decimal] = None
    antifoam_dose_kg:  Optional[Decimal] = None

    # Sludge
    sludge_produced_kg:    Optional[Decimal] = None
    sludge_dewatered_pct:  Optional[Decimal] = None
    sludge_volume_m3:      Optional[Decimal] = None
    sludge_disposal_qty_kg: Optional[Decimal] = None

    # Compliance & regulatory
    compliance_status:   str           = "COMPLIANT"
    permit_limit_ref:    Optional[str] = None
    deviation_reason:    Optional[str] = None
    corrective_action:   Optional[str] = None

    source_method: str  = "MANUAL"
    is_anomaly:    bool = False
    anomaly_note:  Optional[str] = None
    notes:         Optional[str] = None

    @field_validator("process_stage")
    @classmethod
    def _chk_stage(cls, v: str) -> str:
        valid = {"PRIMARY", "SECONDARY", "TERTIARY", "SLUDGE_HANDLING"}
        if v.upper() not in valid:
            raise ValueError(f"process_stage must be one of {valid}")
        return v.upper()

    @field_validator("compliance_status")
    @classmethod
    def _chk_compliance(cls, v: str) -> str:
        valid = {"COMPLIANT", "NON_COMPLIANT", "BORDERLINE", "NOT_TESTED"}
        if v.upper() not in valid:
            raise ValueError(f"compliance_status must be one of {valid}")
        return v.upper()


class WastewaterRecordUpdate(BaseModel):
    record_datetime:        Optional[datetime] = None
    process_stage:          Optional[str]      = None
    shift_ref:              Optional[str]      = None
    influent_flow_m3h:      Optional[Decimal]  = None
    effluent_flow_m3h:      Optional[Decimal]  = None
    influent_cod_mgl:       Optional[Decimal]  = None
    effluent_cod_mgl:       Optional[Decimal]  = None
    influent_bod_mgl:       Optional[Decimal]  = None
    effluent_bod_mgl:       Optional[Decimal]  = None
    influent_tss_mgl:       Optional[Decimal]  = None
    effluent_tss_mgl:       Optional[Decimal]  = None
    influent_ph:            Optional[Decimal]  = None
    effluent_ph:            Optional[Decimal]  = None
    do_mgl:                 Optional[Decimal]  = None
    mlss_mgl:               Optional[Decimal]  = None
    mlvss_mgl:              Optional[Decimal]  = None
    svi:                    Optional[Decimal]  = None
    srt_days:               Optional[Decimal]  = None
    conductivity_us_cm:     Optional[Decimal]  = None
    temperature_c:          Optional[Decimal]  = None
    power_consumed_kwh:     Optional[Decimal]  = None
    aeration_runtime_hours: Optional[Decimal]  = None
    blower_power_kw:        Optional[Decimal]  = None
    nutrient_dose_kg:       Optional[Decimal]  = None
    antifoam_dose_kg:       Optional[Decimal]  = None
    sludge_produced_kg:     Optional[Decimal]  = None
    sludge_dewatered_pct:   Optional[Decimal]  = None
    sludge_volume_m3:       Optional[Decimal]  = None
    sludge_disposal_qty_kg: Optional[Decimal]  = None
    compliance_status:      Optional[str]      = None
    permit_limit_ref:       Optional[str]      = None
    deviation_reason:       Optional[str]      = None
    corrective_action:      Optional[str]      = None
    source_method:          Optional[str]      = None
    is_anomaly:             Optional[bool]     = None
    anomaly_note:           Optional[str]      = None
    notes:                  Optional[str]      = None


class WastewaterRecordRead(BaseModel):
    id:        UUID
    record_no: str
    asset_id:  UUID
    asset_name: Optional[str] = None
    asset_no:   Optional[str] = None

    record_datetime:        datetime
    process_stage:          str
    shift_ref:              Optional[str]     = None

    influent_flow_m3h:      Optional[Decimal] = None
    effluent_flow_m3h:      Optional[Decimal] = None

    influent_cod_mgl:       Optional[Decimal] = None
    effluent_cod_mgl:       Optional[Decimal] = None
    influent_bod_mgl:       Optional[Decimal] = None
    effluent_bod_mgl:       Optional[Decimal] = None
    influent_tss_mgl:       Optional[Decimal] = None
    effluent_tss_mgl:       Optional[Decimal] = None
    influent_ph:            Optional[Decimal] = None
    effluent_ph:            Optional[Decimal] = None

    do_mgl:                 Optional[Decimal] = None
    mlss_mgl:               Optional[Decimal] = None
    mlvss_mgl:              Optional[Decimal] = None
    svi:                    Optional[Decimal] = None
    srt_days:               Optional[Decimal] = None

    conductivity_us_cm:     Optional[Decimal] = None
    temperature_c:          Optional[Decimal] = None

    power_consumed_kwh:     Optional[Decimal] = None
    aeration_runtime_hours: Optional[Decimal] = None
    blower_power_kw:        Optional[Decimal] = None

    nutrient_dose_kg:       Optional[Decimal] = None
    antifoam_dose_kg:       Optional[Decimal] = None

    sludge_produced_kg:     Optional[Decimal] = None
    sludge_dewatered_pct:   Optional[Decimal] = None
    sludge_volume_m3:       Optional[Decimal] = None
    sludge_disposal_qty_kg: Optional[Decimal] = None

    compliance_status:      str
    permit_limit_ref:       Optional[str]     = None
    deviation_reason:       Optional[str]     = None
    corrective_action:      Optional[str]     = None

    source_method:          str
    is_anomaly:             bool
    anomaly_note:           Optional[str]     = None
    notes:                  Optional[str]     = None

    operator_id:            Optional[UUID]    = None   # mirrors entered_by_id
    operator_name:          Optional[str]     = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# KPIs & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class WastewaterKPIs(BaseModel):
    """
    Aggregated KPIs for the wastewater treatment plant over a date window.

    Alarm thresholds (default values, configurable per plant):
      effluent_ph < 6.0 or > 9.0     → alarm_ph_out_of_range
      effluent_cod > cod_limit        → alarm_cod_high  (limit = 150 mg/L default)
      do_mgl < 1.5                    → alarm_low_do
      aeration_runtime_hours == 0     → alarm_blower_failure
      influent_flow > flow_limit      → alarm_overflow_risk
      compliance_status NON_COMPLIANT → alarm_non_compliant_discharge
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Volume
    total_influent_m3:     Decimal = Decimal("0")
    total_effluent_m3:     Decimal = Decimal("0")
    avg_influent_flow_m3h: Optional[Decimal] = None
    avg_effluent_flow_m3h: Optional[Decimal] = None

    # Organic load
    avg_influent_cod:      Optional[Decimal] = None
    avg_effluent_cod:      Optional[Decimal] = None
    avg_influent_bod:      Optional[Decimal] = None
    avg_effluent_bod:      Optional[Decimal] = None
    avg_influent_tss:      Optional[Decimal] = None
    avg_effluent_tss:      Optional[Decimal] = None

    # KPI 1 — COD removal efficiency %
    cod_removal_pct:       Optional[Decimal] = None
    # KPI 2 — BOD removal efficiency %
    bod_removal_pct:       Optional[Decimal] = None

    # pH
    avg_influent_ph:       Optional[Decimal] = None
    avg_effluent_ph:       Optional[Decimal] = None

    # Biological process
    avg_do_mgl:            Optional[Decimal] = None
    avg_mlss_mgl:          Optional[Decimal] = None
    avg_svi:               Optional[Decimal] = None

    # Physical/chemical
    avg_conductivity_us_cm: Optional[Decimal] = None
    avg_temperature_c:      Optional[Decimal] = None

    # Energy
    total_power_kwh:           Decimal        = Decimal("0")
    total_aeration_hours:      Optional[Decimal] = None
    total_blower_power_kwh:    Optional[Decimal] = None

    # KPI 5 — blower energy per m³ effluent
    blower_energy_per_m3:  Optional[Decimal] = None

    # Chemical dosing
    total_nutrient_dose_kg: Optional[Decimal] = None
    total_antifoam_dose_kg: Optional[Decimal] = None

    # KPI 6 — chemical cost per m3 (requires cost integration)
    chemical_cost_per_m3:  Optional[Decimal] = None

    # Sludge
    total_sludge_produced_kg:  Decimal = Decimal("0")
    total_sludge_volume_m3:    Optional[Decimal] = None
    total_sludge_disposal_kg:  Optional[Decimal] = None
    # KPI 7 — sludge generation rate (kg / m³ influent)
    sludge_gen_rate:           Optional[Decimal] = None

    # KPI 3 — compliance %
    compliance_pct:            Optional[Decimal] = None
    compliant_count:           int = 0
    non_compliant_count:       int = 0
    borderline_count:          int = 0

    # KPI 4 — treatment cost per m3 (from external cost feed)
    treatment_cost_per_m3:     Optional[Decimal] = None
    treatment_cost_total:      Optional[Decimal] = None

    # Counts
    record_count:  int = 0
    anomaly_count: int = 0

    # KPI 8 — non-compliance risk flag
    non_compliance_risk: bool = False   # True when recent non-compliant trend

    # ── Alarm readiness flags ─────────────────────────────────────────────────
    alarm_ph_out_of_range:          bool = False   # avg effluent pH out of [6, 9]
    alarm_cod_high:                 bool = False   # avg effluent COD > 150 mg/L
    alarm_low_do:                   bool = False   # avg DO < 1.5 mg/L
    alarm_blower_failure:           bool = False   # any record with 0 runtime
    alarm_overflow_risk:            bool = False   # avg influent flow > threshold
    alarm_non_compliant_discharge:  bool = False   # non_compliant_count > 0


# ── Trend & breakdown ─────────────────────────────────────────────────────────

class WastewaterTrendPoint(BaseModel):
    """Daily aggregation for trend charts."""
    date:              str     = ""
    influent_flow_m3h: Decimal = Decimal("0")
    effluent_flow_m3h: Decimal = Decimal("0")
    avg_cod_influent:  Optional[Decimal] = None
    avg_cod_effluent:  Optional[Decimal] = None
    avg_bod_influent:  Optional[Decimal] = None
    avg_bod_effluent:  Optional[Decimal] = None
    avg_do:            Optional[Decimal] = None
    avg_ph_effluent:   Optional[Decimal] = None
    power_kwh:         Decimal = Decimal("0")
    sludge_kg:         Decimal = Decimal("0")
    non_compliant_cnt: int = 0
    record_count:      int = 0

    model_config = {"from_attributes": True}


class WastewaterStagePoint(BaseModel):
    """Per-treatment-stage aggregation."""
    stage:             Optional[str]
    label:             str
    record_count:      int = 0
    avg_cod_removal:   Optional[Decimal] = None
    avg_bod_removal:   Optional[Decimal] = None
    avg_do:            Optional[Decimal] = None
    non_compliant_cnt: int = 0


class WastewaterComplianceSummary(BaseModel):
    """Compliance breakdown for visual flags."""
    period_label:     str
    total_records:    int
    compliant:        int
    non_compliant:    int
    borderline:       int
    not_tested:       int
    compliance_pct:   Optional[Decimal] = None


# ── Alarm event (lightweight, for header/panel display) ───────────────────────

class WastewaterAlarm(BaseModel):
    """
    Lightweight alarm payload emitted alongside KPIs.
    Maps to UtilityAlarmEvent for persistence; here for UI display only.
    """
    alarm_key:   str            # e.g. "ph_out_of_range"
    severity:    str            # INFO | WARNING | ALERT | CRITICAL
    message:     str
    triggered_value: Optional[Decimal] = None
    threshold_value: Optional[Decimal] = None
    record_id:   Optional[UUID] = None
    triggered_at: Optional[datetime] = None


# ── Asset dropdown ─────────────────────────────────────────────────────────────

class WastewaterAsset(BaseModel):
    id:       UUID
    asset_no: str
    name:     str
