from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.finance import OperationalPostingStatus
from app.models.landed_cost import LandedCostType


AllocationMethodInput = Literal[
    "BY_QUANTITY", "BY_WEIGHT", "BY_VOLUME", "BY_VALUE", "EQUAL_SPLIT"
]


# ── Cost Line ─────────────────────────────────────────────────────────────────

class LandedCostLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_type: LandedCostType
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    amount_fc: Decimal = Decimal("0")
    estimated_amount_fc: Optional[Decimal] = None
    currency_code: str = "KES"
    allocation_method: Optional[AllocationMethodInput] = None
    is_included_in_valuation: bool = True
    account_code: Optional[str] = None
    remarks: Optional[str] = None

    @field_validator("amount_fc")
    @classmethod
    def validate_legacy_amount_range(cls, value: Decimal) -> Decimal:
        return _validate_cost_amount(value)

    @field_validator("estimated_amount_fc")
    @classmethod
    def validate_estimate_range(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return _validate_cost_amount(value) if value is not None else value

    @field_validator("currency_code")
    @classmethod
    def normalize_currency_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized):
            raise ValueError("Currency must be a three-letter ISO code")
        return normalized



class LandedCostLineOut(LandedCostLineCreate):
    model_config = ConfigDict(from_attributes=True)
    # Historical documents may contain custom cost labels entered before the
    # supported input catalogue was enforced; keep those readable on output.
    cost_type: str
    allocation_method: Optional[str] = None
    id: UUID
    header_id: UUID
    amount_base: Decimal
    exchange_rate: Decimal
    exchange_rate_id: Optional[UUID] = None
    exchange_rate_date: Optional[date] = None
    exchange_rate_source: Optional[str] = None
    actual_record: Optional["LandedCostLineActualOut"] = None

    @computed_field
    @property
    def variance_fc(self) -> Optional[Decimal]:
        if self.actual_record is None or self.estimated_amount_fc is None:
            return None
        return self.actual_record.amount_fc - self.estimated_amount_fc

    @computed_field
    @property
    def variance_base(self) -> Optional[Decimal]:
        variance = self.variance_fc
        if variance is None:
            return None
        return variance * self.exchange_rate


class LandedCostLineActualCreate(BaseModel):
    amount_fc: Decimal
    source_reference: str = Field(min_length=1, max_length=200)

    @field_validator("amount_fc")
    @classmethod
    def validate_actual_range(cls, value: Decimal) -> Decimal:
        return _validate_cost_amount(value)

    @field_validator("source_reference")
    @classmethod
    def normalize_source_reference(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A source reference is required")
        return value


class LandedCostLineActualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lc_line_id: UUID
    amount_fc: Decimal
    source_reference: str
    recorded_by_id: Optional[UUID] = None
    recorded_at: datetime
    actual_amount_base: Optional[Decimal] = None
    variance_amount_base: Optional[Decimal] = None
    variance_status: Optional[str] = None
    posting_error: Optional[str] = None
    posted_at: Optional[datetime] = None
    variance_postings: List["LandedCostActualVariancePostingOut"] = Field(default_factory=list)


class LandedCostActualVariancePostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actual_id: UUID
    allocation_line_id: UUID
    variance_amount_base: Decimal
    posting_batch_id: Optional[UUID] = None
    journal_entry_id: Optional[UUID] = None
    accounting_status: Optional[OperationalPostingStatus] = None
    posting_error: Optional[str] = None
    posted_at: Optional[datetime] = None


LandedCostLineOut.model_rebuild()


def _validate_cost_amount(value: Decimal) -> Decimal:
    if not value.is_finite() or abs(value) >= Decimal("10000000000"):
        raise ValueError("Cost amount must fit NUMERIC(14,4)")
    try:
        rounded = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Cost amount must fit NUMERIC(14,4)") from exc
    if abs(rounded) >= Decimal("10000000000"):
        raise ValueError("Cost amount must fit NUMERIC(14,4)")
    return value


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
    received_weight: Optional[Decimal] = None
    received_volume: Optional[Decimal] = None
    purchase_value: Optional[Decimal] = None
    allocation_basis: Optional[Decimal] = None
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
    model_config = ConfigDict(extra="forbid")

    reference_type: str = "MANUAL"
    shipment_id: Optional[UUID] = None
    po_id: Optional[UUID] = None
    vendor_name: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    currency_code: str = "KES"
    allocation_method: AllocationMethodInput = "BY_VALUE"
    notes: Optional[str] = None
    cost_lines: List[LandedCostLineCreate] = []
    grn_links: List[LandedCostGRNLinkCreate] = []

    @field_validator("currency_code")
    @classmethod
    def normalize_currency_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized):
            raise ValueError("Currency must be a three-letter ISO code")
        return normalized



class LandedCostHeaderUpdate(BaseModel):
    vendor_name: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    currency_code: Optional[str] = None
    allocation_method: Optional[AllocationMethodInput] = None
    notes: Optional[str] = None

    @field_validator("currency_code")
    @classmethod
    def normalize_currency_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized):
            raise ValueError("Currency must be a three-letter ISO code")
        return normalized


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
    exchange_rate_id: Optional[UUID] = None
    exchange_rate_date: Optional[date] = None
    exchange_rate_source: Optional[str] = None
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


class LandedCostReconciliationCheck(BaseModel):
    check_id: str
    status: Literal["PASS", "FAIL", "PENDING", "NOT_APPLICABLE"]
    detail: str
    allocation_line_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    journal_entry_id: Optional[UUID] = None
    posting_batch_id: Optional[UUID] = None


class LandedCostAuditEntry(BaseModel):
    entry_id: str
    entry_type: str
    occurred_at: datetime
    status: str
    description: str
    source_reference: Optional[str] = None
    amount_base: Optional[Decimal] = None
    currency: Optional[str] = None
    actor_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    journal_entry_id: Optional[UUID] = None
    posting_batch_id: Optional[UUID] = None


class LandedCostReconciliationOut(BaseModel):
    header_id: UUID
    generated_at: datetime
    status: Literal["RECONCILED", "EXCEPTIONS", "PENDING"]
    checks: List[LandedCostReconciliationCheck] = Field(default_factory=list)
    audit_entries: List[LandedCostAuditEntry] = Field(default_factory=list)


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
