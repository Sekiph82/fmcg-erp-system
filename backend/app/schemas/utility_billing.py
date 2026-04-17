"""
Utility Billing, Tariffs & Cost Allocation — Pydantic v2 Schemas
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator


# ── Tariff schemas ─────────────────────────────────────────────────────────────

class TariffCreate(BaseModel):
    tariff_code:   str
    name:          str
    description:   Optional[str] = None
    utility_type:  str
    tariff_type:   str = "FLAT"
    supplier_id:   Optional[uuid.UUID] = None
    effective_from: date
    effective_to:  Optional[date] = None
    unit:          str
    currency_code: str = "USD"
    base_rate:     Decimal
    peak_rate:     Optional[Decimal] = None
    offpeak_rate:  Optional[Decimal] = None
    demand_rate:   Optional[Decimal] = None
    fixed_charge:  Optional[Decimal] = None
    tax_rate_pct:  Optional[Decimal] = None
    tax_rule:      Optional[str] = None
    is_active:     bool = True
    notes:         Optional[str] = None

    @field_validator("utility_type", "tariff_type", mode="before")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper() if v else v


class TariffUpdate(BaseModel):
    name:          Optional[str] = None
    description:   Optional[str] = None
    tariff_type:   Optional[str] = None
    supplier_id:   Optional[uuid.UUID] = None
    effective_from: Optional[date] = None
    effective_to:  Optional[date] = None
    unit:          Optional[str] = None
    currency_code: Optional[str] = None
    base_rate:     Optional[Decimal] = None
    peak_rate:     Optional[Decimal] = None
    offpeak_rate:  Optional[Decimal] = None
    demand_rate:   Optional[Decimal] = None
    fixed_charge:  Optional[Decimal] = None
    tax_rate_pct:  Optional[Decimal] = None
    tax_rule:      Optional[str] = None
    is_active:     Optional[bool] = None
    notes:         Optional[str] = None


class TariffRead(BaseModel):
    id:            uuid.UUID
    tariff_code:   str
    name:          str
    description:   Optional[str]
    utility_type:  str
    tariff_type:   str
    supplier_id:   Optional[uuid.UUID]
    effective_from: date
    effective_to:  Optional[date]
    unit:          str
    currency_code: str
    base_rate:     Decimal
    peak_rate:     Optional[Decimal]
    offpeak_rate:  Optional[Decimal]
    demand_rate:   Optional[Decimal]
    fixed_charge:  Optional[Decimal]
    tax_rate_pct:  Optional[Decimal]
    tax_rule:      Optional[str]
    is_active:     bool
    notes:         Optional[str]
    created_at:    Optional[str]
    updated_at:    Optional[str]

    model_config = {"from_attributes": True}


# ── Bill schemas ───────────────────────────────────────────────────────────────

class BillCreate(BaseModel):
    utility_type:        str
    provider_name:       Optional[str] = None
    supplier_id:         Optional[uuid.UUID] = None
    tariff_id:           Optional[uuid.UUID] = None
    tariff_code:         Optional[str] = None
    bill_reference:      Optional[str] = None
    billing_period_from: date
    billing_period_to:   date
    invoice_date:        Optional[date] = None
    due_date:            Optional[date] = None
    consumption_quantity: Optional[Decimal] = None
    consumption_unit:    Optional[str] = None
    unit_rate:           Optional[Decimal] = None
    base_charge:         Optional[Decimal] = None
    energy_charge:       Optional[Decimal] = None
    demand_charge:       Optional[Decimal] = None
    fixed_charge:        Optional[Decimal] = None
    surcharge_amount:    Optional[Decimal] = None
    tax_amount:          Optional[Decimal] = None
    total_amount:        Decimal
    currency_code:       str = "USD"
    status:              str = "RECEIVED"
    payment_date:        Optional[date] = None
    document_ref:        Optional[str] = None
    notes:               Optional[str] = None

    @field_validator("utility_type", "status", mode="before")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper() if v else v


class BillUpdate(BaseModel):
    provider_name:       Optional[str] = None
    supplier_id:         Optional[uuid.UUID] = None
    tariff_id:           Optional[uuid.UUID] = None
    tariff_code:         Optional[str] = None
    bill_reference:      Optional[str] = None
    billing_period_from: Optional[date] = None
    billing_period_to:   Optional[date] = None
    invoice_date:        Optional[date] = None
    due_date:            Optional[date] = None
    consumption_quantity: Optional[Decimal] = None
    consumption_unit:    Optional[str] = None
    unit_rate:           Optional[Decimal] = None
    base_charge:         Optional[Decimal] = None
    energy_charge:       Optional[Decimal] = None
    demand_charge:       Optional[Decimal] = None
    fixed_charge:        Optional[Decimal] = None
    surcharge_amount:    Optional[Decimal] = None
    tax_amount:          Optional[Decimal] = None
    total_amount:        Optional[Decimal] = None
    currency_code:       Optional[str] = None
    status:              Optional[str] = None
    payment_date:        Optional[date] = None
    document_ref:        Optional[str] = None
    notes:               Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def upper(cls, v):
        return v.upper() if v else v


class BillRead(BaseModel):
    id:                  uuid.UUID
    bill_no:             str
    utility_type:        str
    provider_name:       Optional[str]
    supplier_id:         Optional[uuid.UUID]
    tariff_id:           Optional[uuid.UUID]
    tariff_code:         Optional[str]
    bill_reference:      Optional[str]
    billing_period_from: date
    billing_period_to:   date
    invoice_date:        Optional[date]
    due_date:            Optional[date]
    consumption_quantity: Optional[Decimal]
    consumption_unit:    Optional[str]
    unit_rate:           Optional[Decimal]
    base_charge:         Optional[Decimal]
    energy_charge:       Optional[Decimal]
    demand_charge:       Optional[Decimal]
    fixed_charge:        Optional[Decimal]
    surcharge_amount:    Optional[Decimal]
    tax_amount:          Optional[Decimal]
    total_amount:        Decimal
    currency_code:       str
    status:              str
    payment_date:        Optional[date]
    document_ref:        Optional[str]
    notes:               Optional[str]
    created_at:          Optional[str]
    updated_at:          Optional[str]

    model_config = {"from_attributes": True}


# ── Allocation schemas ─────────────────────────────────────────────────────────

class AllocationCreate(BaseModel):
    utility_type:        str
    allocation_date:     date
    period_start:        Optional[date] = None
    period_end:          Optional[date] = None
    allocation_method:   str = "METERED"
    target_type:         Optional[str] = None
    target_id:           Optional[str] = None
    target_name:         Optional[str] = None
    department:          Optional[str] = None
    production_line:     Optional[str] = None
    building_area:       Optional[str] = None
    machine_ref:         Optional[str] = None
    production_order_id: Optional[uuid.UUID] = None
    batch_no:            Optional[str] = None
    product_id:          Optional[uuid.UUID] = None
    source_cost:         Optional[Decimal] = None
    allocation_basis:    Optional[Decimal] = None
    allocation_basis_unit: Optional[str] = None
    allocated_quantity:  Optional[Decimal] = None
    quantity_unit:       Optional[str] = None
    production_volume_kg: Optional[Decimal] = None
    total_cost:          Decimal
    allocated_cost:      Decimal
    currency_code:       str = "USD"
    cost_per_unit:       Optional[Decimal] = None
    cost_per_ton:        Optional[Decimal] = None
    bill_id:             Optional[uuid.UUID] = None
    source_method:       str = "CALCULATED"
    notes:               Optional[str] = None

    @field_validator("utility_type", "allocation_method", "source_method", mode="before")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper() if v else v

    @field_validator("target_type", mode="before")
    @classmethod
    def upper_opt(cls, v):
        return v.upper() if v else v

    @model_validator(mode="after")
    def compute_derived(self) -> "AllocationCreate":
        # Auto-compute cost_per_unit if missing
        if self.cost_per_unit is None and self.allocated_quantity and self.allocated_quantity > 0:
            self.cost_per_unit = self.allocated_cost / self.allocated_quantity
        # Auto-compute cost_per_ton if missing
        if self.cost_per_ton is None and self.production_volume_kg and self.production_volume_kg > 0:
            self.cost_per_ton = self.allocated_cost / (self.production_volume_kg / 1000)
        return self


class AllocationUpdate(BaseModel):
    allocation_method:   Optional[str] = None
    target_type:         Optional[str] = None
    target_id:           Optional[str] = None
    target_name:         Optional[str] = None
    department:          Optional[str] = None
    production_line:     Optional[str] = None
    building_area:       Optional[str] = None
    machine_ref:         Optional[str] = None
    production_order_id: Optional[uuid.UUID] = None
    batch_no:            Optional[str] = None
    product_id:          Optional[uuid.UUID] = None
    source_cost:         Optional[Decimal] = None
    allocation_basis:    Optional[Decimal] = None
    allocation_basis_unit: Optional[str] = None
    allocated_quantity:  Optional[Decimal] = None
    quantity_unit:       Optional[str] = None
    production_volume_kg: Optional[Decimal] = None
    total_cost:          Optional[Decimal] = None
    allocated_cost:      Optional[Decimal] = None
    currency_code:       Optional[str] = None
    cost_per_unit:       Optional[Decimal] = None
    cost_per_ton:        Optional[Decimal] = None
    bill_id:             Optional[uuid.UUID] = None
    is_approved:         Optional[bool] = None
    notes:               Optional[str] = None


class AllocationRead(BaseModel):
    id:                  uuid.UUID
    allocation_no:       str
    utility_type:        str
    allocation_date:     date
    period_start:        Optional[date]
    period_end:          Optional[date]
    allocation_method:   str
    target_type:         Optional[str]
    target_id:           Optional[str]
    target_name:         Optional[str]
    department:          Optional[str]
    production_line:     Optional[str]
    building_area:       Optional[str]
    machine_ref:         Optional[str]
    production_order_id: Optional[uuid.UUID]
    batch_no:            Optional[str]
    product_id:          Optional[uuid.UUID]
    source_cost:         Optional[Decimal]
    allocation_basis:    Optional[Decimal]
    allocation_basis_unit: Optional[str]
    allocated_quantity:  Optional[Decimal]
    quantity_unit:       Optional[str]
    production_volume_kg: Optional[Decimal]
    total_cost:          Decimal
    allocated_cost:      Decimal
    currency_code:       str
    cost_per_unit:       Optional[Decimal]
    cost_per_ton:        Optional[Decimal]
    bill_id:             Optional[uuid.UUID]
    source_method:       str
    is_approved:         bool
    notes:               Optional[str]
    created_at:          Optional[str]
    updated_at:          Optional[str]

    model_config = {"from_attributes": True}


# ── KPIs & reports ─────────────────────────────────────────────────────────────

class BillingKPIs(BaseModel):
    date_from:             Optional[str] = None
    date_to:               Optional[str] = None
    utility_type:          Optional[str] = None
    total_bills:           int
    total_billed_amount:   Decimal
    total_tax_amount:      Optional[Decimal]
    total_consumption:     Optional[Decimal]
    consumption_unit:      Optional[str]
    avg_unit_rate:         Optional[Decimal]
    unpaid_amount:         Optional[Decimal]
    overdue_count:         int
    disputed_count:        int
    currency_code:         str = "USD"


class AllocationReportRow(BaseModel):
    target_type:      Optional[str]
    target_id:        Optional[str]
    target_name:      Optional[str]
    utility_type:     Optional[str]
    allocated_cost:   Decimal
    allocated_quantity: Optional[Decimal]
    quantity_unit:    Optional[str]
    cost_per_unit:    Optional[Decimal]
    record_count:     int


class AllocationReport(BaseModel):
    period_start:    Optional[str]
    period_end:      Optional[str]
    utility_type:    Optional[str]
    group_by:        str
    rows:            List[AllocationReportRow]
    grand_total:     Decimal


# ── Allocation engine request ──────────────────────────────────────────────────

class AllocationEngineTarget(BaseModel):
    target_type:     str
    target_id:       str
    target_name:     Optional[str] = None
    basis_value:     Decimal   # e.g. runtime hours, %, m², etc.
    basis_unit:      Optional[str] = None


class AllocationEngineRequest(BaseModel):
    bill_id:           uuid.UUID
    allocation_method: str
    allocation_date:   date
    currency_code:     str = "USD"
    targets:           List[AllocationEngineTarget]

    @field_validator("allocation_method", mode="before")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper() if v else v


class AllocationEngineResult(BaseModel):
    bill_id:           uuid.UUID
    bill_no:           str
    total_cost:        Decimal
    allocation_method: str
    allocations_created: int
    rows:              List[AllocationRead]
