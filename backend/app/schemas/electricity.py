"""
Electricity Management Schemas
───────────────────────────────
KPI aggregation, trend, and breakdown response schemas for the
electricity-specific analytics layer.

All source data lives in utility_transactions where utility_type = ELECTRICITY.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


# ── KPI block ──────────────────────────────────────────────────────────────────

class ElectricityKPIs(BaseModel):
    """
    Plant-wide (or scoped) electricity KPIs for a given date window.

    base_load_kwh  — average of the bottom 20th-percentile of daily totals
                     (proxy for floor / always-on consumption)
    peak_demand_kwh — maximum single-transaction quantity in the window
                      (proxy for peak draw; accurate only if transactions
                       represent interval readings rather than shift totals)
    idle_kwh       — consumption with no production_line / machine / batch linkage
    solar_offset_kwh — SOLAR transactions in the same window & scope
    net_kwh        — total_kwh − solar_offset_kwh (when solar data present)
    """
    date_from: Optional[date] = None
    date_to:   Optional[date] = None

    # Volume
    total_kwh:        Decimal
    avg_kwh_per_day:  Optional[Decimal] = None
    peak_demand_kwh:  Optional[Decimal] = None
    base_load_kwh:    Optional[Decimal] = None
    idle_kwh:         Optional[Decimal] = None
    solar_offset_kwh: Optional[Decimal] = None
    net_kwh:          Optional[Decimal] = None

    # Cost
    total_cost:       Optional[Decimal] = None
    avg_cost_per_day: Optional[Decimal] = None
    avg_cost_per_kwh: Optional[Decimal] = None

    # Counts / quality
    tx_count:        int = 0
    anomaly_count:   int = 0
    estimated_count: int = 0
    estimated_pct:   Optional[Decimal] = None
    has_tariff_data: bool = False


# ── Trend points ───────────────────────────────────────────────────────────────

class ElectricityTrendPoint(BaseModel):
    """One row in a daily trend time-series."""
    date:          date
    total_kwh:     Decimal
    peak_kwh:      Optional[Decimal] = None   # max single record on that day
    total_cost:    Optional[Decimal] = None
    anomaly_count: int = 0
    tx_count:      int = 0


class ElectricityShiftPoint(BaseModel):
    """Aggregation per shift label."""
    shift_id:      Optional[str]
    label:         str
    total_kwh:     Decimal
    total_cost:    Optional[Decimal] = None
    tx_count:      int = 0
    anomaly_count: int = 0


# ── Breakdown ─────────────────────────────────────────────────────────────────

class ElectricityBreakdownRow(BaseModel):
    dimension:    str            # department | line | machine | building_area | shift
    group_key:    Optional[str]  # actual DB value (None = unassigned)
    label:        str            # display label
    total_kwh:    Decimal
    pct_of_total: Optional[Decimal] = None
    total_cost:   Optional[Decimal] = None
    tx_count:     int = 0
    anomaly_count: int = 0


class ElectricityBreakdown(BaseModel):
    dimension:       str
    rows:            List[ElectricityBreakdownRow]
    grand_total_kwh: Decimal


# ── Tariff summary (light read for the UI dropdown) ───────────────────────────

class ElectricityTariffRead(BaseModel):
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
