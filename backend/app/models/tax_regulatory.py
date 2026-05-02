import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class TaxType(str, enum.Enum):
    VAT = "VAT"
    EXCISE = "EXCISE"
    CUSTOMS_DUTY = "CUSTOMS_DUTY"
    WITHHOLDING_TAX = "WITHHOLDING_TAX"
    RAILWAY_DEV_LEVY = "RAILWAY_DEV_LEVY"
    IDF_FEE = "IDF_FEE"
    STAMP_DUTY = "STAMP_DUTY"
    CORPORATE_TAX = "CORPORATE_TAX"
    OTHER = "OTHER"


class TaxAppliesTo(str, enum.Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    ALL = "ALL"


class RegulatoryFlagType(str, enum.Enum):
    CHEMICAL_COMPLIANCE = "CHEMICAL_COMPLIANCE"
    RESTRICTED_GOODS = "RESTRICTED_GOODS"
    IMPORT_LICENSE = "IMPORT_LICENSE"
    EXPORT_LICENSE = "EXPORT_LICENSE"
    PHYTOSANITARY = "PHYTOSANITARY"
    HALAL_CERTIFICATION = "HALAL_CERTIFICATION"
    KEBS_STANDARD = "KEBS_STANDARD"       # Kenya Bureau of Standards
    KEPHIS = "KEPHIS"                      # Kenya Plant Health Inspectorate
    REACH_COMPLIANCE = "REACH_COMPLIANCE"  # EU/Turkey chemicals
    OTHER = "OTHER"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TxTaxStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


# ── Country Tax Configuration ──────────────────────────────────────────────────

class CountryTaxConfig(Base, TimestampMixin):
    """One record per country — top-level tax parameters."""
    __tablename__ = "country_tax_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(10), unique=True, nullable=False, index=True)  # e.g. KE, TR
    country_name = Column(String(100), nullable=False)
    currency = Column(String(10), nullable=False)
    standard_vat_rate = Column(Numeric(8, 4), nullable=True)       # e.g. 16.00 for Kenya
    reduced_vat_rate = Column(Numeric(8, 4), nullable=True)
    zero_rated_vat = Column(Boolean, nullable=False, default=False)
    standard_wht_rate = Column(Numeric(8, 4), nullable=True)       # withholding tax
    corporate_tax_rate = Column(Numeric(8, 4), nullable=True)
    import_duty_default_rate = Column(Numeric(8, 4), nullable=True)
    fiscal_year_start_month = Column(Integer, nullable=False, default=1)  # 1=Jan
    tax_authority = Column(String(255), nullable=True)              # e.g. KRA, GİB
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    rules = relationship("TaxRule", back_populates="country_config", cascade="all, delete-orphan")


# ── Tax Categories ─────────────────────────────────────────────────────────────

class TaxCategory(Base, TimestampMixin):
    """Reusable named tax category — VAT Standard, VAT Zero-Rated, Excise 25%, etc."""
    __tablename__ = "tax_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    rules = relationship("TaxRule", back_populates="category")
    product_mappings = relationship("ProductTaxMapping", back_populates="category")


# ── Tax Rules ──────────────────────────────────────────────────────────────────

class TaxRule(Base, TimestampMixin):
    """A specific tax rate for a country × category × transaction type combination."""
    __tablename__ = "tax_rules"
    __table_args__ = (
        UniqueConstraint("country_code", "tax_category_id", "tax_type", "applies_to", name="uq_tax_rule"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(10), ForeignKey("country_tax_configs.country_code", ondelete="CASCADE"), nullable=False, index=True)
    tax_category_id = Column(UUID(as_uuid=True), ForeignKey("tax_categories.id", ondelete="CASCADE"), nullable=False)
    tax_type = Column(Enum(TaxType), nullable=False)
    applies_to = Column(Enum(TaxAppliesTo), nullable=False, default=TaxAppliesTo.ALL)
    rate = Column(Numeric(8, 4), nullable=False)                   # percentage e.g. 16.0000
    is_compound = Column(Boolean, nullable=False, default=False)   # compounded on previous taxes
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    country_config = relationship("CountryTaxConfig", back_populates="rules")
    category = relationship("TaxCategory", back_populates="rules")


# ── Product Tax Mapping ────────────────────────────────────────────────────────

class ProductTaxMapping(Base, TimestampMixin):
    """Maps a product / material to tax categories per country."""
    __tablename__ = "product_tax_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(10), ForeignKey("country_tax_configs.country_code", ondelete="CASCADE"), nullable=False, index=True)
    tax_category_id = Column(UUID(as_uuid=True), ForeignKey("tax_categories.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=True, index=True)
    hs_code = Column(String(20), nullable=True, index=True)        # Harmonized System code
    is_zero_rated = Column(Boolean, nullable=False, default=False)
    is_exempt = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    country_config = relationship("CountryTaxConfig")
    category = relationship("TaxCategory", back_populates="product_mappings")
    product = relationship("Product")
    material = relationship("Material")


# ── Regulatory Flags ───────────────────────────────────────────────────────────

class RegulatoryFlag(Base, TimestampMixin):
    """Compliance and regulatory flag per product/material/country."""
    __tablename__ = "regulatory_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(10), nullable=False, index=True)
    flag_type = Column(Enum(RegulatoryFlagType), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=True, index=True)
    hs_code = Column(String(20), nullable=True)
    status = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.PENDING)
    authority = Column(String(255), nullable=True)                 # KRA, KEBS, KEPHIS, etc.
    license_no = Column(String(200), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)
    document_ref = Column(String(500), nullable=True)              # file path placeholder
    restriction_details = Column(Text, nullable=True)              # notes on restrictions
    notes = Column(Text, nullable=True)

    product = relationship("Product")
    material = relationship("Material")


# ── Transaction Tax ────────────────────────────────────────────────────────────

class TransactionTax(Base, TimestampMixin):
    """Applied tax line on any entity (PO, SO, Invoice, Logistics shipment)."""
    __tablename__ = "transaction_taxes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Polymorphic entity reference — no FK to keep this module decoupled
    entity_type = Column(String(50), nullable=False, index=True)   # PURCHASE_ORDER, SALES_ORDER, INVOICE, INTL_SHIPMENT
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    country_code = Column(String(10), nullable=False, index=True)
    tax_rule_id = Column(UUID(as_uuid=True), ForeignKey("tax_rules.id", ondelete="RESTRICT"), nullable=True)
    tax_type = Column(Enum(TaxType), nullable=False)
    tax_category_code = Column(String(50), nullable=True)           # denormalised for reporting
    description = Column(String(500), nullable=True)
    taxable_amount = Column(Numeric(16, 4), nullable=False)
    rate = Column(Numeric(8, 4), nullable=False)                    # rate applied (snapshot)
    tax_amount = Column(Numeric(16, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    status = Column(Enum(TxTaxStatus), nullable=False, default=TxTaxStatus.DRAFT)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    tax_rule = relationship("TaxRule")
    created_by = relationship("User")


# ── eTIMS / KRA e-Invoice ──────────────────────────────────────────────────────

class ETimsStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ETimsSubmission(Base, TimestampMixin):
    """
    Tracks KRA eTIMS submission status per invoice.
    One-to-one with Invoice. Simulation-ready: set ETIMS_API_URL in config to enable live calls.
    """
    __tablename__ = "etims_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    status = Column(Enum(ETimsStatus), nullable=False, default=ETimsStatus.PENDING)
    control_unit_invoice_no = Column(String(100), nullable=True)   # TIMS serial number from KRA
    signed_invoice_hash = Column(String(500), nullable=True)       # SHA-256 of signed invoice
    invoice_qr_data = Column(Text, nullable=True)                  # QR code string
    transmitted_at = Column(DateTime(timezone=True), nullable=True)
    kra_response_code = Column(String(20), nullable=True)
    kra_response_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    submitted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    invoice = relationship("Invoice")
    submitted_by = relationship("User")


class VATReturnStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class VATReturn(Base, TimestampMixin):
    """
    Monthly VAT3 return aggregate for KRA filing.
    Auto-generated from sales invoices and purchase invoices.
    """
    __tablename__ = "vat_returns"
    __table_args__ = (UniqueConstraint("period_ym", name="uq_vat_return_period"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_ym = Column(String(7), nullable=False, index=True)   # "2026-04"
    status = Column(Enum(VATReturnStatus), nullable=False, default=VATReturnStatus.DRAFT)

    # Sales (Output VAT)
    standard_rated_sales = Column(Numeric(18, 4), nullable=False, default=0)
    zero_rated_sales = Column(Numeric(18, 4), nullable=False, default=0)
    exempt_sales = Column(Numeric(18, 4), nullable=False, default=0)
    output_vat = Column(Numeric(18, 4), nullable=False, default=0)

    # Purchases (Input VAT)
    standard_rated_purchases = Column(Numeric(18, 4), nullable=False, default=0)
    input_vat = Column(Numeric(18, 4), nullable=False, default=0)

    # Net
    net_vat_payable = Column(Numeric(18, 4), nullable=False, default=0)

    filed_at = Column(DateTime(timezone=True), nullable=True)
    filed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledgement_ref = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    filed_by = relationship("User")


class WithholdingTaxRecord(Base, TimestampMixin):
    """WHT deducted from payments to suppliers or received from customers."""
    __tablename__ = "withholding_tax_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    direction = Column(String(20), nullable=False)               # DEDUCTED | SUFFERED
    entity_type = Column(String(30), nullable=False)             # SUPPLIER | CUSTOMER
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)       # polymorphic, not FK
    payment_date = Column(Date, nullable=False)
    gross_amount = Column(Numeric(16, 4), nullable=False)
    wht_rate = Column(Numeric(8, 4), nullable=False)
    wht_amount = Column(Numeric(16, 4), nullable=False)
    net_amount = Column(Numeric(16, 4), nullable=False)
    certificate_no = Column(String(100), nullable=True)
    period_ym = Column(String(7), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User")
