from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class _Base(BaseModel):
    model_config = {"from_attributes": True}


# ── Forecast schemas ──────────────────────────────────────────────────────────

class ForecastGenerateRequest(BaseModel):
    product_id:     UUID
    warehouse_id:   Optional[UUID]   = None
    forecast_model: str              = "EXPONENTIAL_SMOOTHING"
    period_type:    str              = "MONTHLY"
    periods_ahead:  int              = Field(6, ge=1, le=24)
    history_periods: int             = Field(12, ge=3, le=36)
    model_params:   Optional[dict]   = None


class ForecastLineOut(_Base):
    id:           UUID
    period_date:  date
    forecast_qty: Decimal
    adjusted_qty: Optional[Decimal]
    actual_qty:   Optional[Decimal]
    error_pct:    Optional[Decimal]
    is_spike:     bool
    is_outlier:   bool
    notes:        Optional[str]


class ForecastLineOverride(BaseModel):
    adjusted_qty: Optional[Decimal]
    notes:        Optional[str]


class ForecastOut(_Base):
    id:             UUID
    product_id:     UUID
    product_sku:    Optional[str]   = None
    product_name:   Optional[str]   = None
    warehouse_id:   Optional[UUID]
    forecast_model: str
    period_type:    str
    start_date:     date
    end_date:       date
    status:         str
    is_approved:    bool
    mape:           Optional[Decimal]
    notes:          Optional[str]
    created_at:     Optional[datetime]
    lines:          list[ForecastLineOut] = []


class ForecastSummary(_Base):
    id:             UUID
    product_id:     UUID
    product_sku:    Optional[str]   = None
    product_name:   Optional[str]   = None
    forecast_model: str
    period_type:    str
    start_date:     date
    end_date:       date
    status:         str
    mape:           Optional[Decimal]
    created_at:     Optional[datetime]


class ForecastAccuracyRow(BaseModel):
    product_id:   UUID
    product_sku:  Optional[str]
    product_name: Optional[str]
    periods:      int
    avg_mape:     Optional[Decimal]
    min_mape:     Optional[Decimal]
    max_mape:     Optional[Decimal]


# ── MRP Run schemas ───────────────────────────────────────────────────────────

class MRPRunCreate(BaseModel):
    planning_horizon_days: int            = Field(90, ge=7, le=365)
    include_forecast:      bool           = True
    include_safety_stock:  bool           = True
    warehouse_id:          Optional[UUID] = None
    notes:                 Optional[str]  = None


class MRPRunOut(_Base):
    id:                    UUID
    run_no:                str
    run_date:              date
    planning_horizon_days: int
    status:                str
    trigger:               str
    include_forecast:      bool
    include_safety_stock:  bool
    warehouse_id:          Optional[UUID]
    error_message:         Optional[str]
    product_count:         Optional[int]
    shortage_count:        Optional[int]
    suggestion_count:      Optional[int]
    started_at:            Optional[datetime]
    completed_at:          Optional[datetime]
    notes:                 Optional[str]
    created_at:            Optional[datetime]


# ── MRP Result schemas ────────────────────────────────────────────────────────

class MRPResultOut(_Base):
    id:                       UUID
    run_id:                   UUID
    product_id:               UUID
    product_sku:              Optional[str]     = None
    product_name:             Optional[str]     = None
    so_demand_qty:            Decimal
    forecast_demand_qty:      Decimal
    safety_stock_qty:         Decimal
    gross_demand_qty:         Decimal
    stock_on_hand_qty:        Decimal
    incoming_po_qty:          Decimal
    incoming_prod_qty:        Decimal
    total_supply_qty:         Decimal
    net_requirement_qty:      Decimal
    shortage_flag:            bool
    suggested_production_qty:  Optional[Decimal]
    suggested_procurement_qty: Optional[Decimal]


# ── Suggestion schemas ────────────────────────────────────────────────────────

class SuggestionOut(_Base):
    id:               UUID
    run_id:           UUID
    suggestion_type:  str
    status:           str
    product_id:       Optional[UUID]
    product_sku:      Optional[str]   = None
    product_name:     Optional[str]   = None
    material_id:      Optional[UUID]
    material_code:    Optional[str]   = None
    material_name:    Optional[str]   = None
    suggested_qty:    Decimal
    uom:              Optional[str]
    required_date:    date
    planned_start_date: Optional[date]
    driver_product_id:  Optional[UUID]
    net_requirement_qty: Optional[Decimal]
    moq:              Optional[Decimal]
    preferred_supplier_id: Optional[UUID]
    preferred_supplier_name: Optional[str] = None
    estimated_cost:   Optional[Decimal]
    rejection_reason: Optional[str]
    notes:            Optional[str]
    created_at:       Optional[datetime]


class SuggestionApprove(BaseModel):
    notes: Optional[str] = None


class SuggestionReject(BaseModel):
    rejection_reason: str


class SuggestionConvertResult(BaseModel):
    suggestion_id: UUID
    converted_to:  str           # "purchase_requisition" | "production_order"
    reference_no:  str
    reference_id:  UUID


# ── Dashboard summary ─────────────────────────────────────────────────────────

class MRPDashboard(BaseModel):
    last_run:               Optional[MRPRunOut]
    total_runs:             int
    open_suggestions:       int
    shortage_products:      int
    pending_approval:       int
    active_forecasts:       int
    recent_runs:            list[MRPRunOut]


class ShortageAlert(BaseModel):
    product_id:        UUID
    product_sku:       Optional[str]
    product_name:      Optional[str]
    net_requirement:   Decimal
    suggested_qty:     Optional[Decimal]
    required_date:     Optional[date]
    run_no:            str
