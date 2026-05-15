"""GS1 Barcode + Label Printing System — data models."""
import uuid
import enum
from datetime import date, datetime

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum, Date, DateTime, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class BarcodeType(str, enum.Enum):
    EAN13      = "EAN13"
    GS1_128    = "GS1_128"
    QR_CODE    = "QR_CODE"
    CODE128    = "CODE128"
    GS1_DATAMATRIX = "GS1_DATAMATRIX"


class PackagingLevel(str, enum.Enum):
    UNIT       = "UNIT"
    INNER_PACK = "INNER_PACK"
    CARTON     = "CARTON"
    PALLET     = "PALLET"


class PrintJobStatus(str, enum.Enum):
    PENDING    = "PENDING"
    PRINTING   = "PRINTING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


class SSCCStatus(str, enum.Enum):
    ACTIVE     = "ACTIVE"
    SHIPPED    = "SHIPPED"
    RECEIVED   = "RECEIVED"
    CANCELLED  = "CANCELLED"


class LabelTemplateStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    ACTIVE     = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class PrintTrigger(str, enum.Enum):
    MANUAL               = "MANUAL"
    PRODUCTION_COMPLETE  = "PRODUCTION_COMPLETE"
    PACKAGING_COMPLETE   = "PACKAGING_COMPLETE"
    PALLETIZATION        = "PALLETIZATION"
    SHIPMENT             = "SHIPMENT"
    QC_RELEASE           = "QC_RELEASE"


class GS1AIAgentType(str, enum.Enum):
    LABEL_VALIDATOR      = "LABEL_VALIDATOR"
    PACKAGING_OPTIMIZER  = "PACKAGING_OPTIMIZER"


class GS1AIRecStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    APPLIED  = "APPLIED"


# ── Company GS1 Configuration ─────────────────────────────────────────────────

class GS1CompanyConfig(Base, TimestampMixin):
    __tablename__ = "gs1_company_configs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name          = Column(String(255), nullable=False)
    gs1_company_prefix    = Column(String(12), nullable=False, unique=True)
    country_code          = Column(String(3), nullable=True)
    extension_digit       = Column(Integer, default=0, nullable=False)
    sscc_serial_counter   = Column(Integer, default=0, nullable=False)
    is_active             = Column(Boolean, default=True, nullable=False)
    notes                 = Column(Text, nullable=True)

    product_configs = relationship("ProductGS1Config", back_populates="company_config")
    sscc_pallets    = relationship("SSCCPallet", back_populates="company_config")


# ── Product GS1 Extension ─────────────────────────────────────────────────────

class ProductGS1Config(Base, TimestampMixin):
    __tablename__ = "product_gs1_configs"
    __table_args__ = (UniqueConstraint("product_id", name="uq_product_gs1"),)

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id               = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    company_config_id        = Column(UUID(as_uuid=True), ForeignKey("gs1_company_configs.id", ondelete="RESTRICT"), nullable=True)
    gtin                     = Column(String(14), nullable=True, unique=True, index=True)
    barcode_type             = Column(Enum(BarcodeType), default=BarcodeType.EAN13, nullable=False)
    packaging_level          = Column(Enum(PackagingLevel), default=PackagingLevel.UNIT, nullable=False)
    label_template_id        = Column(UUID(as_uuid=True), ForeignKey("gs1_label_templates.id", ondelete="SET NULL"), nullable=True)
    gs1_company_prefix       = Column(String(12), nullable=True)
    requires_serialization   = Column(Boolean, default=False, nullable=False)
    requires_lot_tracking    = Column(Boolean, default=True, nullable=False)
    requires_expiry_tracking = Column(Boolean, default=True, nullable=False)
    units_per_inner_pack     = Column(Integer, nullable=True)
    inner_packs_per_carton   = Column(Integer, nullable=True)
    cartons_per_pallet       = Column(Integer, nullable=True)
    carton_gtin              = Column(String(14), nullable=True)
    pallet_gtin              = Column(String(14), nullable=True)
    product_sku_code         = Column(String(100), nullable=True)
    net_weight_g             = Column(Numeric(12, 4), nullable=True)
    net_volume_ml            = Column(Numeric(12, 4), nullable=True)
    is_active                = Column(Boolean, default=True, nullable=False)
    notes                    = Column(Text, nullable=True)

    product        = relationship("Product")
    company_config = relationship("GS1CompanyConfig", back_populates="product_configs")
    label_template = relationship("GS1LabelTemplate", foreign_keys=[label_template_id])
    lot_barcodes   = relationship("LotBarcodeRecord", back_populates="product_config")


# ── Lot Barcode Record ────────────────────────────────────────────────────────

class LotBarcodeRecord(Base, TimestampMixin):
    __tablename__ = "gs1_lot_barcode_records"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_config_id  = Column(UUID(as_uuid=True), ForeignKey("product_gs1_configs.id", ondelete="RESTRICT"), nullable=False, index=True)
    lot_id             = Column(UUID(as_uuid=True), ForeignKey("lots.id", ondelete="RESTRICT"), nullable=True, index=True)
    gtin               = Column(String(14), nullable=False)
    lot_number         = Column(String(100), nullable=False)
    production_date    = Column(Date, nullable=True)
    expiry_date        = Column(Date, nullable=True)
    serial_number      = Column(String(100), nullable=True)
    barcode_type       = Column(Enum(BarcodeType), nullable=False)
    gs1_ai_string      = Column(Text, nullable=False)
    gs1_raw_string     = Column(Text, nullable=True)
    qr_payload         = Column(Text, nullable=True)
    barcode_image_b64  = Column(Text, nullable=True)
    qr_image_b64       = Column(Text, nullable=True)
    is_printed         = Column(Boolean, default=False, nullable=False)
    printed_at         = Column(DateTime, nullable=True)
    quantity           = Column(Numeric(14, 3), nullable=True)
    packaging_level    = Column(Enum(PackagingLevel), nullable=True)

    product_config = relationship("ProductGS1Config", back_populates="lot_barcodes")
    lot            = relationship("Lot")
    sscc_links     = relationship("SSCCPalletLot", back_populates="lot_barcode")
    print_items    = relationship("LabelPrintJobItem", back_populates="lot_barcode")


# ── SSCC Pallet ───────────────────────────────────────────────────────────────

class SSCCPallet(Base, TimestampMixin):
    __tablename__ = "gs1_sscc_pallets"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_config_id   = Column(UUID(as_uuid=True), ForeignKey("gs1_company_configs.id", ondelete="RESTRICT"), nullable=True)
    sscc_code           = Column(String(18), nullable=False, unique=True, index=True)
    extension_digit     = Column(Integer, default=0, nullable=False)
    company_prefix      = Column(String(12), nullable=False)
    serial_reference    = Column(String(9), nullable=False)
    check_digit         = Column(Integer, nullable=False)
    pallet_id           = Column(String(100), nullable=True, index=True)
    status              = Column(Enum(SSCCStatus), default=SSCCStatus.ACTIVE, nullable=False)
    warehouse_location  = Column(String(200), nullable=True)
    shipment_reference  = Column(String(200), nullable=True)
    sscc_image_b64      = Column(Text, nullable=True)
    label_printed       = Column(Boolean, default=False, nullable=False)
    label_printed_at    = Column(DateTime, nullable=True)
    notes               = Column(Text, nullable=True)

    company_config = relationship("GS1CompanyConfig", back_populates="sscc_pallets")
    lots           = relationship("SSCCPalletLot", back_populates="sscc_pallet")
    print_items    = relationship("LabelPrintJobItem", back_populates="sscc_pallet")


class SSCCPalletLot(Base, TimestampMixin):
    __tablename__ = "gs1_sscc_pallet_lots"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sscc_id          = Column(UUID(as_uuid=True), ForeignKey("gs1_sscc_pallets.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_barcode_id   = Column(UUID(as_uuid=True), ForeignKey("gs1_lot_barcode_records.id", ondelete="RESTRICT"), nullable=False)
    quantity         = Column(Numeric(14, 3), nullable=True)
    packaging_level  = Column(Enum(PackagingLevel), nullable=True)

    sscc_pallet  = relationship("SSCCPallet", back_populates="lots")
    lot_barcode  = relationship("LotBarcodeRecord", back_populates="sscc_links")


# ── Label Template ─────────────────────────────────────────────────────────────

class GS1LabelTemplate(Base, TimestampMixin):
    __tablename__ = "gs1_label_templates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String(255), nullable=False)
    description      = Column(Text, nullable=True)
    packaging_level  = Column(Enum(PackagingLevel), nullable=True)
    template_version = Column(Integer, default=1, nullable=False)
    status           = Column(Enum(LabelTemplateStatus), default=LabelTemplateStatus.DRAFT, nullable=False)
    width_mm         = Column(Numeric(6, 1), nullable=True)
    height_mm        = Column(Numeric(6, 1), nullable=True)
    fields           = Column(JSON, nullable=True)
    html_template    = Column(Text, nullable=True)
    css_styles       = Column(Text, nullable=True)
    is_default       = Column(Boolean, default=False, nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)
    notes            = Column(Text, nullable=True)

    product_configs = relationship(
        "ProductGS1Config",
        foreign_keys="ProductGS1Config.label_template_id",
        back_populates="label_template",
    )
    print_jobs      = relationship("LabelPrintJob", back_populates="template")


# ── Label Print Job ───────────────────────────────────────────────────────────

class LabelPrintJob(Base, TimestampMixin):
    __tablename__ = "gs1_label_print_jobs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_no       = Column(String(50), nullable=False, unique=True, index=True)
    trigger      = Column(Enum(PrintTrigger), default=PrintTrigger.MANUAL, nullable=False)
    template_id  = Column(UUID(as_uuid=True), ForeignKey("gs1_label_templates.id", ondelete="SET NULL"), nullable=True)
    status       = Column(Enum(PrintJobStatus), default=PrintJobStatus.PENDING, nullable=False)
    printed_by   = Column(String(200), nullable=True)
    printed_at   = Column(DateTime, nullable=True)
    quantity     = Column(Integer, default=1, nullable=False)
    printer_name = Column(String(200), nullable=True)
    print_data   = Column(JSON, nullable=True)
    notes        = Column(Text, nullable=True)

    template = relationship("GS1LabelTemplate", back_populates="print_jobs")
    items    = relationship("LabelPrintJobItem", back_populates="job", cascade="all, delete-orphan")


class LabelPrintJobItem(Base, TimestampMixin):
    __tablename__ = "gs1_label_print_job_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id          = Column(UUID(as_uuid=True), ForeignKey("gs1_label_print_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_barcode_id  = Column(UUID(as_uuid=True), ForeignKey("gs1_lot_barcode_records.id", ondelete="SET NULL"), nullable=True)
    sscc_id         = Column(UUID(as_uuid=True), ForeignKey("gs1_sscc_pallets.id", ondelete="SET NULL"), nullable=True)
    copies          = Column(Integer, default=1, nullable=False)
    status          = Column(Enum(PrintJobStatus), default=PrintJobStatus.PENDING, nullable=False)

    job         = relationship("LabelPrintJob", back_populates="items")
    lot_barcode = relationship("LotBarcodeRecord", back_populates="print_items")
    sscc_pallet = relationship("SSCCPallet", back_populates="print_items")


# ── AI Recommendations ────────────────────────────────────────────────────────

class GS1AIRecommendation(Base, TimestampMixin):
    __tablename__ = "gs1_ai_recommendations"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type           = Column(Enum(GS1AIAgentType), nullable=False)
    title                = Column(String(500), nullable=False)
    description          = Column(Text, nullable=False)
    affected_entity_type = Column(String(100), nullable=True)
    affected_entity_id   = Column(String(100), nullable=True)
    recommendation       = Column(Text, nullable=False)
    severity             = Column(String(20), default="MEDIUM", nullable=False)
    status               = Column(Enum(GS1AIRecStatus), default=GS1AIRecStatus.PENDING, nullable=False)
    reviewed_by          = Column(String(200), nullable=True)
    reviewed_at          = Column(DateTime, nullable=True)
    agent_metadata       = Column(JSON, nullable=True)
