from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from uuid import UUID as _UUID  # noqa: F401 - re-export for consistency

from app.models.tax_regulatory import (
    TaxType, TaxAppliesTo, RegulatoryFlagType,
    ComplianceStatus, TxTaxStatus, ETimsStatus, VATReturnStatus,
)
from datetime import datetime


# ── Country Tax Config ─────────────────────────────────────────────────────────

class CountryTaxConfigCreate(BaseModel):
    country_code: str
    country_name: str
    currency: str
    standard_vat_rate: Optional[Decimal] = None
    reduced_vat_rate: Optional[Decimal] = None
    zero_rated_vat: bool = False
    standard_wht_rate: Optional[Decimal] = None
    corporate_tax_rate: Optional[Decimal] = None
    import_duty_default_rate: Optional[Decimal] = None
    fiscal_year_start_month: int = 1
    tax_authority: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class CountryTaxConfigUpdate(BaseModel):
    country_name: Optional[str] = None
    currency: Optional[str] = None
    standard_vat_rate: Optional[Decimal] = None
    reduced_vat_rate: Optional[Decimal] = None
    zero_rated_vat: Optional[bool] = None
    standard_wht_rate: Optional[Decimal] = None
    corporate_tax_rate: Optional[Decimal] = None
    import_duty_default_rate: Optional[Decimal] = None
    fiscal_year_start_month: Optional[int] = None
    tax_authority: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CountryTaxConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    country_code: str
    country_name: str
    currency: str
    standard_vat_rate: Optional[Decimal]
    reduced_vat_rate: Optional[Decimal]
    zero_rated_vat: bool
    standard_wht_rate: Optional[Decimal]
    corporate_tax_rate: Optional[Decimal]
    import_duty_default_rate: Optional[Decimal]
    fiscal_year_start_month: int
    tax_authority: Optional[str]
    notes: Optional[str]
    is_active: bool


# ── Tax Category ───────────────────────────────────────────────────────────────

class TaxCategoryCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class TaxCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TaxCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


# ── Tax Rule ───────────────────────────────────────────────────────────────────

class TaxRuleCreate(BaseModel):
    country_code: str
    tax_category_id: UUID
    tax_type: TaxType
    applies_to: TaxAppliesTo = TaxAppliesTo.ALL
    rate: Decimal
    is_compound: bool = False
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    description: Optional[str] = None
    is_active: bool = True


class TaxRuleUpdate(BaseModel):
    rate: Optional[Decimal] = None
    applies_to: Optional[TaxAppliesTo] = None
    is_compound: Optional[bool] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TaxRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    country_code: str
    tax_category_id: UUID
    tax_type: TaxType
    applies_to: TaxAppliesTo
    rate: Decimal
    is_compound: bool
    effective_from: Optional[date]
    effective_to: Optional[date]
    description: Optional[str]
    is_active: bool
    category: Optional[TaxCategoryRead] = None


# ── Product Tax Mapping ────────────────────────────────────────────────────────

class ProductTaxMappingCreate(BaseModel):
    country_code: str
    tax_category_id: UUID
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    hs_code: Optional[str] = None
    is_zero_rated: bool = False
    is_exempt: bool = False
    notes: Optional[str] = None


class ProductTaxMappingUpdate(BaseModel):
    tax_category_id: Optional[UUID] = None
    hs_code: Optional[str] = None
    is_zero_rated: Optional[bool] = None
    is_exempt: Optional[bool] = None
    notes: Optional[str] = None


class ProductTaxMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    country_code: str
    tax_category_id: UUID
    product_id: Optional[UUID]
    material_id: Optional[UUID]
    hs_code: Optional[str]
    is_zero_rated: bool
    is_exempt: bool
    notes: Optional[str]
    category: Optional[TaxCategoryRead] = None


# ── Regulatory Flag ────────────────────────────────────────────────────────────

class RegulatoryFlagCreate(BaseModel):
    country_code: str
    flag_type: RegulatoryFlagType
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    hs_code: Optional[str] = None
    status: ComplianceStatus = ComplianceStatus.PENDING
    authority: Optional[str] = None
    license_no: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    document_ref: Optional[str] = None
    restriction_details: Optional[str] = None
    notes: Optional[str] = None


class RegulatoryFlagUpdate(BaseModel):
    status: Optional[ComplianceStatus] = None
    authority: Optional[str] = None
    license_no: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    document_ref: Optional[str] = None
    restriction_details: Optional[str] = None
    notes: Optional[str] = None


class RegulatoryFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    country_code: str
    flag_type: RegulatoryFlagType
    product_id: Optional[UUID]
    material_id: Optional[UUID]
    hs_code: Optional[str]
    status: ComplianceStatus
    authority: Optional[str]
    license_no: Optional[str]
    issue_date: Optional[date]
    expiry_date: Optional[date]
    document_ref: Optional[str]
    restriction_details: Optional[str]
    notes: Optional[str]


# ── Transaction Tax ────────────────────────────────────────────────────────────

class TransactionTaxCreate(BaseModel):
    entity_type: str
    entity_id: UUID
    country_code: str
    tax_rule_id: Optional[UUID] = None
    tax_type: TaxType
    tax_category_code: Optional[str] = None
    description: Optional[str] = None
    taxable_amount: Decimal
    rate: Decimal
    tax_amount: Decimal
    currency: str = "KES"
    status: TxTaxStatus = TxTaxStatus.DRAFT
    notes: Optional[str] = None


class TransactionTaxUpdate(BaseModel):
    status: Optional[TxTaxStatus] = None
    notes: Optional[str] = None


class TransactionTaxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entity_type: str
    entity_id: UUID
    country_code: str
    tax_rule_id: Optional[UUID]
    tax_type: TaxType
    tax_category_code: Optional[str]
    description: Optional[str]
    taxable_amount: Decimal
    rate: Decimal
    tax_amount: Decimal
    currency: str
    status: TxTaxStatus
    notes: Optional[str]


# ── Reporting ──────────────────────────────────────────────────────────────────

class TaxSummaryRow(BaseModel):
    country_code: str
    tax_type: str
    currency: str
    total_taxable_amount: Decimal
    total_tax_amount: Decimal
    transaction_count: int


class RegulatoryStatusRow(BaseModel):
    country_code: str
    flag_type: str
    status: str
    count: int
    expiring_soon: int   # expiry within 30 days


class ApplyTaxRequest(BaseModel):
    """Apply applicable tax rules to an entity and return computed lines."""
    entity_type: str
    entity_id: UUID
    country_code: str
    applies_to: TaxAppliesTo
    taxable_amount: Decimal
    currency: str = "KES"
    hs_code: Optional[str] = None
    product_id: Optional[UUID] = None
    material_id: Optional[UUID] = None


# ── eTIMS / KRA ───────────────────────────────────────────────────────────────

class ETimsSubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_id: UUID
    status: ETimsStatus
    control_unit_invoice_no: Optional[str]
    signed_invoice_hash: Optional[str]
    invoice_qr_data: Optional[str]
    transmitted_at: Optional[datetime]
    kra_response_code: Optional[str]
    kra_response_message: Optional[str]
    error_message: Optional[str]
    retry_count: int
    # Provider/integrator tracking fields (TASK-005.1A)
    provider_name: Optional[str] = None
    provider_reference: Optional[str] = None
    environment: Optional[str] = None
    request_payload: Optional[dict] = None
    response_payload: Optional[dict] = None
    accepted_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    attempt_count: int = 0
    error_code: Optional[str] = None
    created_at: datetime


class ETimsCancelRequest(BaseModel):
    reason: str
    allow_cancel_accepted: bool = False


class VATReturnCreate(BaseModel):
    period_ym: str
    notes: Optional[str] = None


class VATReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    period_ym: str
    status: VATReturnStatus
    standard_rated_sales: Decimal
    zero_rated_sales: Decimal
    exempt_sales: Decimal
    output_vat: Decimal
    standard_rated_purchases: Decimal
    input_vat: Decimal
    net_vat_payable: Decimal
    filed_at: Optional[datetime]
    acknowledgement_ref: Optional[str]
    notes: Optional[str]
    created_at: datetime


class WithholdingTaxCreate(BaseModel):
    direction: str     # DEDUCTED | SUFFERED
    entity_type: str   # SUPPLIER | CUSTOMER
    entity_id: UUID
    invoice_id: Optional[UUID] = None
    payment_date: date
    gross_amount: Decimal
    wht_rate: Decimal
    period_ym: str
    certificate_no: Optional[str] = None
    notes: Optional[str] = None


class WithholdingTaxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    direction: str
    entity_type: str
    entity_id: UUID
    invoice_id: Optional[UUID]
    payment_date: date
    gross_amount: Decimal
    wht_rate: Decimal
    wht_amount: Decimal
    net_amount: Decimal
    certificate_no: Optional[str]
    period_ym: str
    notes: Optional[str]
    created_at: datetime
