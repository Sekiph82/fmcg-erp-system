"""
Production Costing Schemas
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class OrderCostBreakdown(BaseModel):
    """Detailed cost breakdown for a single production order."""
    model_config = ConfigDict(from_attributes=True)

    order_id:                str
    order_no:                str
    product_name:            Optional[str]   = None
    product_sku:             Optional[str]   = None
    status:                  str
    actual_quantity:         Optional[float] = None
    uom:                     str

    total_material_cost:     Optional[float] = None
    total_labor_cost:        Optional[float] = None
    total_machine_cost:      Optional[float] = None
    total_energy_cost:       Optional[float] = None
    total_cost:              Optional[float] = None
    cost_per_unit:           Optional[float] = None
    standard_cost_per_unit:  Optional[float] = None
    cost_variance_pct:       Optional[float] = None
    costing_finalized_at:    Optional[str]   = None

    # live-computed extras (not stored)
    material_row_count:      Optional[int]   = None
    labor_row_count:         Optional[int]   = None


class CostReportRow(BaseModel):
    """Aggregated cost row per product for the report."""
    product_id:              str
    sku:                     str
    product_name:            str
    standard_cost_per_unit:  float
    order_count:             int
    total_qty:               float
    total_material_cost:     float
    total_labor_cost:        float
    total_machine_cost:      float
    total_energy_cost:       float
    total_cost:              float
    avg_cost_per_unit:       float
    avg_variance_pct:        float
    material_pct:            float
    labor_pct:               float
    machine_pct:             float
    energy_pct:              float


class CostTrendPoint(BaseModel):
    """One day of cost trend data."""
    date:              str
    material_cost:     float
    labor_cost:        float
    machine_cost:      float
    energy_cost:       float
    total_cost:        float
    total_qty:         float
    avg_cost_per_unit: float
    order_count:       int


class CostKPIs(BaseModel):
    """Top-level cost KPIs for the dashboard."""
    order_count:           int
    total_qty:             float
    total_material_cost:   float
    total_labor_cost:      float
    total_machine_cost:    float
    total_energy_cost:     float
    total_cost:            float
    avg_cost_per_unit:     float
    avg_variance_pct:      float
    over_budget_count:     int
    material_pct:          float
    labor_pct:             float
    machine_pct:           float
    energy_pct:            float
    flag_high_variance:    bool
    flag_high_material:    bool
