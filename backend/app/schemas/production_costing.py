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


class WIPRow(BaseModel):
    """WIP value for one in-progress production order."""
    order_id:              str
    order_no:              str
    product_name:          Optional[str]   = None
    product_sku:           Optional[str]   = None
    planned_quantity:      float
    actual_quantity:       Optional[float] = None
    uom:                   str
    status:                str
    wip_material_cost:     float
    wip_labor_cost:        float
    wip_machine_cost:      float
    wip_total:             float
    scheduled_start:       Optional[str]   = None
    scheduled_end:         Optional[str]   = None


class VarianceDetailRow(BaseModel):
    """Component-level variance for one production order."""
    order_id:              str
    order_no:              str
    product_name:          Optional[str]   = None
    product_sku:           Optional[str]   = None
    status:                str
    actual_quantity:       Optional[float] = None
    # Material
    std_material_cost:     float
    actual_material_cost:  float
    material_variance:     float            # actual - standard (positive = over)
    # Labor
    std_labor_cost:        float
    actual_labor_cost:     float
    labor_variance:        float
    # Machine
    std_machine_cost:      float
    actual_machine_cost:   float
    machine_variance:      float
    # Total
    total_variance:        float
    variance_pct:          Optional[float]  = None


class WorkCenterUtilRow(BaseModel):
    """Utilization data for one work center over a date range."""
    work_center_id:        str
    work_center_name:      str
    work_center_code:      str
    capacity_hours:        Optional[float]  = None
    actual_hours_used:     float
    utilization_pct:       Optional[float]  = None
    completed_orders:      int
    labor_cost_incurred:   float
    machine_cost_incurred: float
