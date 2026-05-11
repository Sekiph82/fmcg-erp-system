from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import OperationalPostingStatus


# ── Cost Line ─────────────────────────────────────────────────────────────────

class LandedCostLineCreate(BaseModel):
    cost_type: str
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    amount_fc: Decimal = Decimal("0")
    currency_code: str = "USD"
    exchange_rate: Decimal = Decimal("1")
    allocation_method: Optional[str] = None
    is_included_in_valuation: bool = True
    account_code: Optional[str] = None
    remarks: Optional[str] = None


class LandedCostLineOut(LandedCostLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    amount_base: Decimal


# ── GRN Link ──────────────────────────────────────────────────────────────────

class LandedCostGRNLinkCreate(BaseModel):
    grn_id: UUID
    grn_no: Optional[str] = None
    po_no: Optional[str] = None


class LandedCostGRNLinkOut(LandedCostGRNLinkCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    grn_value_base: Optional[Decimal] = None
    grn_total_qty: Optional[Decimal] = None
    grn_total_weight: Optional[Decimal] = None
    grn_total_volume: Optional[Decimal] = None
    allocation_share: Optional[Decimal] = None


# ── Allocation Line ───────────────────────────────────────────────────────────

class LandedCostAllocationLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    lc_line_id: UUID
    grn_id: Optional[UUID] = None
    grn_line_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    material_name: Optional[str] = None
    lot_no: Optional[str] = None
    received_qty: Optional[Decimal] = None
    purchase_value: Optional[Decimal] = None
    allocation_share: Optional[Decimal] = None
    allocated_amount: Decimal
    per_unit_lc_cost: Optional[Decimal] = None
    is_posted: bool
    posting_batch_id: Optional[UUID] = None
    journal_entry_id: Optional[UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None


# ── Inventory Adjustment ──────────────────────────────────────────────────────

class LCInventoryAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: UUID
    material_id: Optional[UUID] = None
    lot_no: Optional[str] = None
    adjustment_amount: Decimal
    per_unit_amount: Optional[Decimal] = None
    old_avg_cost: Optional[Decimal] = None
    new_avg_cost: Optional[Decimal] = None
    posting_batch_id: Optional[UUID] = None
    journal_entry_id: Optional[UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None
    posted_at: Optional[datetime] = None


# ── Header ────────────────────────────────────────────────────────────────────

class LandedCostHeaderCreate(BaseModel):
    reference_type: str = "MANUAL"
    shipment_id: Optional[UUID] = None
    po_id: Optional[UUID] = None
    vendor_name: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    currency_code: str = "USD"
    exchange_rate: Decimal = Decimal("1")
    allocation_method: str = "BY_VALUE"
    notes: Optional[str] = None
    cost_lines: List[LandedCostLineCreate] = []
    grn_links: List[LandedCostGRNLinkCreate] = []


class LandedCostHeaderUpdate(BaseModel):
    vendor_name: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    currency_code: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    allocation_method: Optional[str] = None
    notes: Optional[str] = None


class LandedCostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lc_no: str
    reference_type: str
    vendor_name: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    currency_code: str
    exchange_rate: Decimal
    total_lc_amount_fc: Decimal
    total_lc_amount_base: Decimal
    allocation_method: str
    status: str
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LandedCostOut(LandedCostSummary):
    posted_by: Optional[str] = None
    notes: Optional[str] = None
    cost_lines: List[LandedCostLineOut] = []
    grn_links: List[LandedCostGRNLinkOut] = []
    allocation_lines: List[LandedCostAllocationLineOut] = []


# ── AI Recommendation ─────────────────────────────────────────────────────────

class LCAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    header_id: Optional[UUID] = None
    agent_type: str
    status: str
    title: str
    explanation: Optional[str] = None
    impact_summary: Optional[str] = None
    suggested_action: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    actioned_at: Optional[datetime] = None
    created_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────

class LCDashboard(BaseModel):
    total_documents: int
    draft_count: int
    validated_count: int
    posted_count: int
    cancelled_count: int
    total_lc_cost_mtd: Decimal
    total_lc_cost_ytd: Decimal
    pending_ai_recs: int
    top_cost_types: List[dict] = Field(default_factory=list)
    recent_documents: List[LandedCostSummary] = Field(default_factory=list)


# ── Reports ───────────────────────────────────────────────────────────────────

class LCCostByTypeRow(BaseModel):
    cost_type: str
    total_amount: Decimal
    doc_count: int
    pct_of_total: Decimal


class LCAllocationSummaryRow(BaseModel):
    material_name: Optional[str]
    total_allocated: Decimal
    doc_count: int
    avg_per_unit: Optional[Decimal]
