"""GS1 Barcode + Label Printing — Pydantic v2 schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ── Shared base ───────────────────────────────────────────────────────────────

class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── GS1 Company Config ────────────────────────────────────────────────────────

class GS1CompanyConfigCreate(_Base):
    company_name: str
    gs1_company_prefix: str
    country_code: Optional[str] = None
    extension_digit: int = 0
    notes: Optional[str] = None


class GS1CompanyConfigOut(_Base):
    id: uuid.UUID
    company_name: str
    gs1_company_prefix: str
    country_code: Optional[str]
    extension_digit: int
    sscc_serial_counter: int
    is_active: bool
    notes: Optional[str]
    created_at: datetime


# ── Product GS1 Config ────────────────────────────────────────────────────────

class ProductGS1ConfigCreate(_Base):
    product_id: uuid.UUID
    company_config_id: Optional[uuid.UUID] = None
    gtin: Optional[str] = None
    barcode_type: str = "EAN13"
    packaging_level: str = "UNIT"
    label_template_id: Optional[uuid.UUID] = None
    gs1_company_prefix: Optional[str] = None
    requires_serialization: bool = False
    requires_lot_tracking: bool = True
    requires_expiry_tracking: bool = True
    units_per_inner_pack: Optional[int] = None
    inner_packs_per_carton: Optional[int] = None
    cartons_per_pallet: Optional[int] = None
    carton_gtin: Optional[str] = None
    pallet_gtin: Optional[str] = None
    notes: Optional[str] = None


class ProductGS1ConfigUpdate(_Base):
    gtin: Optional[str] = None
    barcode_type: Optional[str] = None
    packaging_level: Optional[str] = None
    label_template_id: Optional[uuid.UUID] = None
    requires_serialization: Optional[bool] = None
    requires_lot_tracking: Optional[bool] = None
    requires_expiry_tracking: Optional[bool] = None
    units_per_inner_pack: Optional[int] = None
    inner_packs_per_carton: Optional[int] = None
    cartons_per_pallet: Optional[int] = None
    carton_gtin: Optional[str] = None
    pallet_gtin: Optional[str] = None
    notes: Optional[str] = None


class ProductGS1ConfigOut(_Base):
    id: uuid.UUID
    product_id: uuid.UUID
    company_config_id: Optional[uuid.UUID]
    gtin: Optional[str]
    barcode_type: str
    packaging_level: str
    label_template_id: Optional[uuid.UUID]
    gs1_company_prefix: Optional[str]
    requires_serialization: bool
    requires_lot_tracking: bool
    requires_expiry_tracking: bool
    units_per_inner_pack: Optional[int]
    inner_packs_per_carton: Optional[int]
    cartons_per_pallet: Optional[int]
    carton_gtin: Optional[str]
    pallet_gtin: Optional[str]
    is_active: bool
    notes: Optional[str]
    product_name: Optional[str] = None
    created_at: datetime


# ── Barcode Generation ────────────────────────────────────────────────────────

class BarcodeGenerateRequest(_Base):
    product_id: Optional[uuid.UUID] = None
    gtin: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[date] = None
    production_date: Optional[date] = None
    serial_number: Optional[str] = None
    barcode_type: str = "GS1_128"
    quantity: Optional[Decimal] = None
    lot_id: Optional[uuid.UUID] = None
    packaging_level: Optional[str] = None
    save_record: bool = True


class BarcodeGenerateResponse(_Base):
    gs1_ai_string: str
    gs1_raw_string: str
    qr_payload: str
    barcode_image_b64: Optional[str] = None
    qr_image_b64: Optional[str] = None
    check_digit_valid: bool = True
    record_id: Optional[uuid.UUID] = None
    gtin: str
    lot_number: Optional[str]
    expiry_date: Optional[date]
    production_date: Optional[date]


# ── GS1 String Parsing ────────────────────────────────────────────────────────

class GS1DecodeRequest(_Base):
    gs1_string: str


class GS1DecodeResponse(_Base):
    segments: dict[str, str]
    gtin: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    production_date: Optional[str] = None
    serial_number: Optional[str] = None
    sscc: Optional[str] = None
    is_valid: bool
    validation_errors: List[str] = []
    matched_product: Optional[dict] = None
    matched_lot: Optional[dict] = None


# ── Lot Barcode Record ────────────────────────────────────────────────────────

class LotBarcodeOut(_Base):
    id: uuid.UUID
    product_config_id: uuid.UUID
    lot_id: Optional[uuid.UUID]
    gtin: str
    lot_number: str
    production_date: Optional[date]
    expiry_date: Optional[date]
    serial_number: Optional[str]
    barcode_type: str
    gs1_ai_string: str
    qr_payload: Optional[str]
    barcode_image_b64: Optional[str]
    qr_image_b64: Optional[str]
    is_printed: bool
    printed_at: Optional[datetime]
    quantity: Optional[Decimal]
    packaging_level: Optional[str]
    created_at: datetime


# ── SSCC / Pallet ─────────────────────────────────────────────────────────────

class SSCCGenerateRequest(_Base):
    company_config_id: Optional[uuid.UUID] = None
    pallet_id: Optional[str] = None
    warehouse_location: Optional[str] = None
    notes: Optional[str] = None


class SSCCPalletOut(_Base):
    id: uuid.UUID
    sscc_code: str
    extension_digit: int
    company_prefix: str
    serial_reference: str
    check_digit: int
    pallet_id: Optional[str]
    status: str
    warehouse_location: Optional[str]
    shipment_reference: Optional[str]
    sscc_image_b64: Optional[str]
    label_printed: bool
    label_printed_at: Optional[datetime]
    notes: Optional[str]
    lot_count: int = 0
    created_at: datetime


class SSCCAddLotRequest(_Base):
    lot_barcode_id: uuid.UUID
    quantity: Optional[Decimal] = None
    packaging_level: Optional[str] = None


# ── Label Template ─────────────────────────────────────────────────────────────

class LabelTemplateCreate(_Base):
    name: str
    description: Optional[str] = None
    packaging_level: Optional[str] = None
    width_mm: Optional[Decimal] = None
    height_mm: Optional[Decimal] = None
    fields: Optional[dict] = None
    html_template: Optional[str] = None
    css_styles: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None


class LabelTemplateUpdate(_Base):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    width_mm: Optional[Decimal] = None
    height_mm: Optional[Decimal] = None
    fields: Optional[dict] = None
    html_template: Optional[str] = None
    css_styles: Optional[str] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None


class LabelTemplateOut(_Base):
    id: uuid.UUID
    name: str
    description: Optional[str]
    packaging_level: Optional[str]
    template_version: int
    status: str
    width_mm: Optional[Decimal]
    height_mm: Optional[Decimal]
    fields: Optional[dict]
    html_template: Optional[str]
    css_styles: Optional[str]
    is_default: bool
    is_active: bool
    notes: Optional[str]
    created_at: datetime


# ── Print Job ─────────────────────────────────────────────────────────────────

class PrintJobCreate(_Base):
    trigger: str = "MANUAL"
    template_id: Optional[uuid.UUID] = None
    printer_name: Optional[str] = None
    printed_by: Optional[str] = None
    notes: Optional[str] = None
    items: List[dict] = []


class PrintJobOut(_Base):
    id: uuid.UUID
    job_no: str
    trigger: str
    template_id: Optional[uuid.UUID]
    status: str
    printed_by: Optional[str]
    printed_at: Optional[datetime]
    quantity: int
    printer_name: Optional[str]
    notes: Optional[str]
    item_count: int = 0
    created_at: datetime


# ── AI Recommendations ────────────────────────────────────────────────────────

class GS1AIRecOut(_Base):
    id: uuid.UUID
    agent_type: str
    title: str
    description: str
    affected_entity_type: Optional[str]
    affected_entity_id: Optional[str]
    recommendation: str
    severity: str
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    agent_metadata: Optional[dict]
    created_at: datetime


class GS1AIRecReview(_Base):
    status: str
    reviewed_by: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class GS1DashboardOut(_Base):
    total_products_configured: int
    total_gtins: int
    total_barcodes_generated: int
    total_labels_printed: int
    total_sscc_pallets: int
    active_sscc_pallets: int
    total_print_jobs: int
    pending_print_jobs: int
    total_label_templates: int
    ai_recommendations_pending: int
    recent_barcodes: List[LotBarcodeOut]
    recent_sscc: List[SSCCPalletOut]


# ── Report ────────────────────────────────────────────────────────────────────

class LabelPrintHistoryOut(_Base):
    job_no: str
    trigger: str
    status: str
    printed_by: Optional[str]
    printed_at: Optional[datetime]
    quantity: int
    template_name: Optional[str]
    created_at: datetime


class SSCCTrackingOut(_Base):
    sscc_code: str
    pallet_id: Optional[str]
    status: str
    warehouse_location: Optional[str]
    shipment_reference: Optional[str]
    lot_count: int
    created_at: datetime


class PackagingHierarchyOut(_Base):
    gtin: str
    product_name: str
    packaging_level: str
    units_per_inner_pack: Optional[int]
    inner_packs_per_carton: Optional[int]
    cartons_per_pallet: Optional[int]
    total_units_per_pallet: Optional[int]
