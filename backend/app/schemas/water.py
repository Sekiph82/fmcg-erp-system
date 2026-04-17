"""
Water Management & Soft Water Management Schemas
─────────────────────────────────────────────────
KPI, trend, balance and breakdown response schemas for the water analytics
layer.  Also contains full CRUD schemas for SoftWaterRecord.

Water transactions live in utility_transactions with utility_type in:
  WATER           – raw water intake
  PROCESS_WATER   – process / treated water consumption
  WASTEWATER      – reject / drain volumes

Soft water records have their own dedicated table: soft_water_records.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# WATER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

# ── KPI block ─────────────────────────────────────────────────────────────────

class WaterKPIs(BaseModel):
    """
    Plant-wide (or scoped) water KPIs for a given date window.

    water_in_m3        – WATER utility_type transactions (raw intake)
    process_m3         – PROCESS_WATER transactions (consumed by production)
    wastewater_m3      – WASTEWATER transactions (discharged / treated)
    balance_m3         – water_in_m3 − wastewater_m3 (net retained)
    loss_m3            – water_in_m3 − process_m3 − wastewater_m3 (unaccounted)
    loss_pct           – loss_m3 / water_in_m3 × 100
    recovery_pct       – process_m3 / water_in_m3 × 100
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Volume (all in m³)
    water_in_m3:    Decimal = Decimal("0")
    process_m3:     Decimal = Decimal("0")
    wastewater_m3:  Decimal = Decimal("0")
    balance_m3:     Optional[Decimal] = None
    loss_m3:        Optional[Decimal] = None
    loss_pct:       Optional[Decimal] = None
    recovery_pct:   Optional[Decimal] = None

    # Daily averages
    avg_m3_per_day: Optional[Decimal] = None

    # Cost
    total_cost:       Optional[Decimal] = None
    avg_cost_per_day: Optional[Decimal] = None
    avg_cost_per_m3:  Optional[Decimal] = None

    # Counts / quality
    tx_count:        int = 0
    anomaly_count:   int = 0
    estimated_count: int = 0
    estimated_pct:   Optional[Decimal] = None


# ── Trend points ──────────────────────────────────────────────────────────────

class WaterTrendPoint(BaseModel):
    """One row in a daily water trend time-series."""
    date:           date
    water_in_m3:    Decimal = Decimal("0")
    process_m3:     Decimal = Decimal("0")
    wastewater_m3:  Decimal = Decimal("0")
    total_cost:     Optional[Decimal] = None
    anomaly_count:  int = 0
    tx_count:       int = 0


# ── Water balance ─────────────────────────────────────────────────────────────

class WaterBalanceRow(BaseModel):
    """A single row in a period water balance."""
    period_label:  str         # e.g. "2026-04" or "Week 15"
    water_in_m3:   Decimal
    process_m3:    Decimal
    wastewater_m3: Decimal
    balance_m3:    Decimal
    loss_m3:       Decimal
    loss_pct:      Optional[Decimal] = None
    recovery_pct:  Optional[Decimal] = None


# ── Breakdown ─────────────────────────────────────────────────────────────────

class WaterBreakdownRow(BaseModel):
    dimension:    str
    group_key:    Optional[str]
    label:        str
    total_m3:     Decimal
    pct_of_total: Optional[Decimal] = None
    total_cost:   Optional[Decimal] = None
    tx_count:     int = 0
    anomaly_count: int = 0


class WaterBreakdown(BaseModel):
    dimension:      str
    rows:           List[WaterBreakdownRow]
    grand_total_m3: Decimal


# ══════════════════════════════════════════════════════════════════════════════
# SOFT WATER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

# ── SoftWaterRecord CRUD schemas ──────────────────────────────────────────────

class SoftWaterRecordCreate(BaseModel):
    asset_id:   UUID
    record_datetime: datetime

    # Water quality in/out
    feed_water_hardness_ppm:    Optional[Decimal] = None
    product_water_hardness_ppm: Optional[Decimal] = None
    feed_water_tds_ppm:         Optional[Decimal] = None
    product_water_tds_ppm:      Optional[Decimal] = None
    feed_ph:                    Optional[Decimal] = None
    product_ph:                 Optional[Decimal] = None
    conductivity_feed_uscm:     Optional[Decimal] = None
    conductivity_product_uscm:  Optional[Decimal] = None

    # Flow / volume
    flow_rate_lpm:       Optional[Decimal] = None
    volume_treated_m3:   Optional[Decimal] = None
    raw_water_input_m3:  Optional[Decimal] = None

    # Chemical consumption
    salt_consumed_kg:    Optional[Decimal] = None
    resin_volume_litres: Optional[Decimal] = None

    # Regeneration
    regen_start:         Optional[datetime] = None
    regen_end:           Optional[datetime] = None
    regeneration_count:  Optional[int] = None
    service_run_hours:   Optional[Decimal] = None

    # Performance
    efficiency_pct:  Optional[Decimal] = None
    status:          str = "ONLINE"

    # Operational
    downtime_minutes: Optional[int] = None
    maintenance_flag: bool = False
    destination_tag:  Optional[str] = None
    department:       Optional[str] = None

    source_method:  str = "MANUAL"
    is_anomaly:     bool = False
    anomaly_note:   Optional[str] = None
    shift_ref:      Optional[str] = None
    notes:          Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"ONLINE", "REGENERATING", "STANDBY", "FAULT"}
        if v.upper() not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v.upper()


class SoftWaterRecordUpdate(BaseModel):
    record_datetime: Optional[datetime] = None

    feed_water_hardness_ppm:    Optional[Decimal] = None
    product_water_hardness_ppm: Optional[Decimal] = None
    feed_water_tds_ppm:         Optional[Decimal] = None
    product_water_tds_ppm:      Optional[Decimal] = None
    feed_ph:                    Optional[Decimal] = None
    product_ph:                 Optional[Decimal] = None
    conductivity_feed_uscm:     Optional[Decimal] = None
    conductivity_product_uscm:  Optional[Decimal] = None

    flow_rate_lpm:       Optional[Decimal] = None
    volume_treated_m3:   Optional[Decimal] = None
    raw_water_input_m3:  Optional[Decimal] = None

    salt_consumed_kg:    Optional[Decimal] = None
    resin_volume_litres: Optional[Decimal] = None

    regen_start:        Optional[datetime] = None
    regen_end:          Optional[datetime] = None
    regeneration_count: Optional[int] = None
    service_run_hours:  Optional[Decimal] = None

    efficiency_pct:  Optional[Decimal] = None
    status:          Optional[str] = None

    downtime_minutes: Optional[int] = None
    maintenance_flag: Optional[bool] = None
    destination_tag:  Optional[str] = None
    department:       Optional[str] = None

    source_method: Optional[str] = None
    is_anomaly:    Optional[bool] = None
    anomaly_note:  Optional[str] = None
    shift_ref:     Optional[str] = None
    notes:         Optional[str] = None


class SoftWaterRecordRead(BaseModel):
    id:        UUID
    record_no: str
    asset_id:  UUID

    record_datetime: datetime

    feed_water_hardness_ppm:    Optional[Decimal] = None
    product_water_hardness_ppm: Optional[Decimal] = None
    feed_water_tds_ppm:         Optional[Decimal] = None
    product_water_tds_ppm:      Optional[Decimal] = None
    feed_ph:                    Optional[Decimal] = None
    product_ph:                 Optional[Decimal] = None
    conductivity_feed_uscm:     Optional[Decimal] = None
    conductivity_product_uscm:  Optional[Decimal] = None

    flow_rate_lpm:       Optional[Decimal] = None
    volume_treated_m3:   Optional[Decimal] = None
    raw_water_input_m3:  Optional[Decimal] = None

    salt_consumed_kg:    Optional[Decimal] = None
    resin_volume_litres: Optional[Decimal] = None

    regen_start:        Optional[datetime] = None
    regen_end:          Optional[datetime] = None
    regeneration_count: Optional[int] = None
    service_run_hours:  Optional[Decimal] = None

    efficiency_pct:  Optional[Decimal] = None
    status:          str

    downtime_minutes: Optional[int] = None
    maintenance_flag: bool
    destination_tag:  Optional[str] = None
    department:       Optional[str] = None

    source_method: str
    is_anomaly:    bool
    anomaly_note:  Optional[str] = None
    shift_ref:     Optional[str] = None
    notes:         Optional[str] = None

    # Asset name (joined)
    asset_name: Optional[str] = None
    asset_no:   Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Soft Water KPIs ───────────────────────────────────────────────────────────

class SoftWaterKPIs(BaseModel):
    """
    Aggregated KPIs for a soft water / ion exchange system.

    conversion_eff_pct  – avg(efficiency_pct) across records
    salt_per_m3         – total_salt_kg / total_volume_m3
    regen_count         – sum of regeneration_count
    regen_frequency     – avg regenerations per day
    hardness_removal_pct – (1 − avg_product_hardness / avg_feed_hardness) × 100
    loss_ratio          – (raw_input − treated_output) / raw_input × 100
    compliance_pct      – % of records where product_water_hardness ≤ 50 ppm (WHO guideline)
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    total_volume_m3:    Decimal = Decimal("0")
    total_raw_input_m3: Decimal = Decimal("0")
    total_salt_kg:      Decimal = Decimal("0")

    conversion_eff_pct:  Optional[Decimal] = None
    salt_per_m3:         Optional[Decimal] = None
    regen_count:         int = 0
    regen_frequency:     Optional[Decimal] = None    # regens/day
    hardness_removal_pct: Optional[Decimal] = None
    loss_ratio:          Optional[Decimal] = None
    compliance_pct:      Optional[Decimal] = None    # product_hardness ≤ 50 ppm

    record_count:       int = 0
    anomaly_count:      int = 0
    maintenance_count:  int = 0
    avg_downtime_min:   Optional[Decimal] = None


# ── Soft Water trend point ─────────────────────────────────────────────────────

class SoftWaterTrendPoint(BaseModel):
    """One day's aggregation for the soft water trend chart."""
    date:             date
    volume_treated_m3: Decimal = Decimal("0")
    salt_consumed_kg:  Decimal = Decimal("0")
    avg_efficiency_pct: Optional[Decimal] = None
    regen_count:       int = 0
    anomaly_count:     int = 0
    maintenance_count: int = 0
    record_count:      int = 0
