"""
Integration framework models.
Covers: M-Pesa (full), CRM/E-commerce/IoT (placeholders),
barcode labels, and unified integration logging.
"""
from __future__ import annotations

import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class IntegrationProvider(str, enum.Enum):
    MPESA = "MPESA"
    CRM = "CRM"
    SHOPIFY = "SHOPIFY"
    WOOCOMMERCE = "WOOCOMMERCE"
    BARCODE = "BARCODE"
    IOT = "IOT"
    GENERIC = "GENERIC"
    # ── Marketing / AdTech ───────────────────────────────────────────────────
    META_ADS = "META_ADS"               # Meta Ads Manager (Facebook/Instagram)
    GOOGLE_ADS = "GOOGLE_ADS"           # Google Ads + Analytics
    TIKTOK_ADS = "TIKTOK_ADS"          # TikTok for Business
    SOCIAL_ANALYTICS = "SOCIAL_ANALYTICS"  # social listening / analytics tool
    ECOMMERCE_ANALYTICS = "ECOMMERCE_ANALYTICS"  # e-commerce analytics (GA4, etc.)


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    TESTING = "TESTING"


class IntegrationLogStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    RETRYING = "RETRYING"


class MpesaTxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    REVERSED = "REVERSED"


class BarcodeFormat(str, enum.Enum):
    EAN13 = "EAN13"
    CODE128 = "CODE128"
    QR = "QR"


class SyncStatus(str, enum.Enum):
    SYNCED = "SYNCED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    CONFLICT = "CONFLICT"


# ── Integration Config ────────────────────────────────────────────────────────

class IntegrationConfig(Base, TimestampMixin):
    """Stores per-provider integration settings (credentials masked in API responses)."""
    __tablename__ = "integration_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(IntegrationProvider), nullable=False, index=True)
    name = Column(String(100), nullable=False)          # e.g. "M-Pesa Production"
    environment = Column(String(20), nullable=False, default="sandbox")  # sandbox|production
    is_active = Column(Boolean, nullable=False, default=False)
    webhook_url = Column(String(500), nullable=True)    # our inbound callback URL
    settings_json = Column(Text, nullable=True)         # JSON with creds (never expose raw)
    status = Column(Enum(IntegrationStatus), nullable=False, default=IntegrationStatus.INACTIVE)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)


# ── Integration Log ───────────────────────────────────────────────────────────

class IntegrationLog(Base, TimestampMixin):
    """Unified audit log for all external integration calls and callbacks."""
    __tablename__ = "integration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(IntegrationProvider), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)  # PAYMENT|CALLBACK|SYNC|SCAN|WEBHOOK
    endpoint = Column(String(500), nullable=True)
    request_payload = Column(Text, nullable=True)   # JSON string (sanitised)
    response_payload = Column(Text, nullable=True)  # JSON string
    status = Column(Enum(IntegrationLogStatus), nullable=False, default=IntegrationLogStatus.PENDING)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    reference = Column(String(200), nullable=True, index=True)  # order_no, phone, etc.
    idempotency_key = Column(String(200), nullable=True, index=True)  # replay prevention


# ── M-Pesa Transaction (Integration layer) ───────────────────────────────────

class IntegrationMpesaTransaction(Base, TimestampMixin):
    """
    Full M-Pesa Daraja transaction record for the integration module.
    More complete than the sales-linked MpesaTransaction; can link to any entity.
    """
    __tablename__ = "integration_mpesa_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), nullable=False, index=True)
    amount = Column(Numeric(16, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    merchant_reference = Column(String(200), nullable=False)   # AccountReference in STK Push
    checkout_request_id = Column(String(200), nullable=True, index=True, unique=True)
    merchant_request_id = Column(String(200), nullable=True)
    mpesa_receipt_number = Column(String(100), nullable=True, index=True)  # on success

    # Generic entity link (e.g. so_id, invoice_id, local_cost_id)
    related_entity_type = Column(String(50), nullable=True)    # "sales_order" | "invoice" | "local_cost"
    related_entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(Enum(MpesaTxStatus), nullable=False, default=MpesaTxStatus.PENDING)

    # Raw Daraja payloads (stored for full traceability)
    request_payload = Column(Text, nullable=True)   # STK Push request body
    response_payload = Column(Text, nullable=True)  # STK Push API response
    callback_payload = Column(Text, nullable=True)  # Daraja callback body

    error_message = Column(Text, nullable=True)
    result_code = Column(Integer, nullable=True)
    result_description = Column(Text, nullable=True)

    retry_count = Column(Integer, nullable=False, default=0)
    initiated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    initiated_by = relationship("User")


# ── CRM Customer Mapping ──────────────────────────────────────────────────────

class CrmCustomerMapping(Base, TimestampMixin):
    """Maps internal Customer to external CRM contact/lead records."""
    __tablename__ = "crm_customer_mappings"
    __table_args__ = (UniqueConstraint("customer_id", "crm_provider", name="uq_crm_customer_provider"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    crm_provider = Column(String(100), nullable=False)   # "salesforce" | "hubspot" | "zoho"
    external_crm_id = Column(String(200), nullable=False)
    sync_status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    sync_direction = Column(String(20), nullable=False, default="BIDIRECTIONAL")  # PUSH|PULL|BIDIRECTIONAL
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=True)          # extra CRM-specific fields (JSON)

    customer = relationship("Customer")


# ── E-commerce Mappings ───────────────────────────────────────────────────────

class EcommerceOrderMapping(Base, TimestampMixin):
    """Maps external platform orders to internal SalesOrders."""
    __tablename__ = "ecommerce_order_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(String(50), nullable=False, index=True)  # SHOPIFY|WOOCOMMERCE|etc.
    external_order_id = Column(String(200), nullable=False)
    external_order_no = Column(String(200), nullable=True)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    sync_status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    raw_payload = Column(Text, nullable=True)            # original order JSON from platform
    error_message = Column(Text, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    so = relationship("SalesOrder")


class EcommerceProductMapping(Base, TimestampMixin):
    """Maps external platform products to internal Products."""
    __tablename__ = "ecommerce_product_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(String(50), nullable=False, index=True)
    external_product_id = Column(String(200), nullable=False)
    external_sku = Column(String(200), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    sync_status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    product = relationship("Product")


# ── Machine / IoT Events ──────────────────────────────────────────────────────

class MachineEvent(Base, TimestampMixin):
    """Incoming event from a production machine or IoT sensor."""
    __tablename__ = "machine_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(String(100), nullable=False, index=True)   # device identifier
    machine_name = Column(String(255), nullable=True)
    event_type = Column(String(50), nullable=False)  # COUNTER|STATUS|ALARM|SPEED|TEMPERATURE|CUSTOM
    value_str = Column(String(200), nullable=True)   # raw string value
    value_numeric = Column(Numeric(18, 4), nullable=True)
    unit = Column(String(20), nullable=True)         # pcs, rpm, °C, %
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=True)   # timestamp from device
    raw_payload = Column(Text, nullable=True)         # original JSON/string from device

    production_order = relationship("ProductionOrder")


# ── Barcode Labels ────────────────────────────────────────────────────────────

class BarcodeLabel(Base, TimestampMixin):
    """Generated barcode record for products, lots, or warehouse locations."""
    __tablename__ = "barcode_labels"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_barcode_entity"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)      # PRODUCT | LOT | LOCATION | MATERIAL
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    entity_name = Column(String(255), nullable=True)       # denormalized for label printing
    barcode_value = Column(String(200), nullable=False, unique=True, index=True)
    barcode_format = Column(Enum(BarcodeFormat), nullable=False, default=BarcodeFormat.CODE128)
    label_template = Column(String(100), nullable=True, default="standard")
    print_count = Column(Integer, nullable=False, default=0)
    last_printed_at = Column(DateTime(timezone=True), nullable=True)
