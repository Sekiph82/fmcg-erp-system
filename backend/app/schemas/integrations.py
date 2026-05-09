from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.integrations import (
    IntegrationProvider, IntegrationStatus, IntegrationLogStatus,
    MpesaTxStatus, BarcodeFormat, SyncStatus,
    ConnectorStatus, PluginInstallStatus, PluginLifecycleAction,
)


# ── Integration Config ────────────────────────────────────────────────────────

class IntegrationConfigCreate(BaseModel):
    provider: IntegrationProvider
    name: str
    environment: str = "sandbox"
    webhook_url: Optional[str] = None
    notes: Optional[str] = None


class IntegrationConfigUpdate(BaseModel):
    name: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None
    webhook_url: Optional[str] = None
    status: Optional[IntegrationStatus] = None
    notes: Optional[str] = None


class IntegrationConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: IntegrationProvider
    name: str
    environment: str
    is_active: bool
    webhook_url: Optional[str]
    status: IntegrationStatus
    last_tested_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    # settings_json intentionally excluded from read (contains secrets)


class ProviderStatusRow(BaseModel):
    """Summary row for the integrations dashboard."""
    provider: IntegrationProvider
    name: str
    status: IntegrationStatus
    environment: str
    is_active: bool
    last_tested_at: Optional[datetime]
    recent_success: int
    recent_failures: int


# ── Integration Logs ──────────────────────────────────────────────────────────

class IntegrationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: IntegrationProvider
    integration_type: str
    endpoint: Optional[str]
    status: IntegrationLogStatus
    error_message: Optional[str]
    retry_count: int
    duration_ms: Optional[int]
    reference: Optional[str]
    idempotency_key: Optional[str]
    created_at: datetime
    # payloads available on detail endpoint only
    request_payload: Optional[str] = None
    response_payload: Optional[str] = None


# ── M-Pesa ────────────────────────────────────────────────────────────────────

class MpesaInitiateRequest(BaseModel):
    phone_number: str                       # 07XXXXXXXX or 254XXXXXXXXX
    amount: Decimal
    merchant_reference: str                 # AccountReference (e.g. order_no)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class MpesaTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_number: str
    amount: float
    currency: str
    merchant_reference: str
    checkout_request_id: Optional[str]
    mpesa_receipt_number: Optional[str]
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    status: MpesaTxStatus
    error_message: Optional[str]
    result_code: Optional[int]
    result_description: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime


class MpesaCallbackPayload(BaseModel):
    """Daraja STK Push callback body structure."""
    Body: Dict[str, Any]


class MpesaStatusResponse(BaseModel):
    transaction_id: str
    checkout_request_id: Optional[str]
    status: MpesaTxStatus
    mpesa_receipt_number: Optional[str]
    amount: float
    message: str


# ── Barcode ───────────────────────────────────────────────────────────────────

class BarcodeGenerateRequest(BaseModel):
    entity_type: str           # PRODUCT | LOT | LOCATION | MATERIAL
    entity_id: str             # UUID string
    barcode_format: BarcodeFormat = BarcodeFormat.CODE128
    label_template: str = "standard"


class BarcodeGenerateResponse(BaseModel):
    barcode_value: str
    barcode_format: BarcodeFormat
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    svg_data: str              # inline SVG for rendering
    label_id: str


class BarcodeScanRequest(BaseModel):
    barcode_value: str


class BarcodeScanResult(BaseModel):
    barcode_value: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    details: Dict[str, Any]    # entity-specific data (stock level, location, etc.)


class BarcodeLabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    barcode_value: str
    barcode_format: BarcodeFormat
    label_template: str
    print_count: int
    last_printed_at: Optional[datetime]
    created_at: datetime


class PrintRequest(BaseModel):
    label_id: str
    printer_name: Optional[str] = "default"
    copies: int = 1


class PrintResponse(BaseModel):
    job_id: str
    label_id: str
    printer_name: str
    copies: int
    status: str          # "queued" | "printing" | "done" (placeholder)
    message: str


# ── CRM ───────────────────────────────────────────────────────────────────────

class CrmSyncRequest(BaseModel):
    direction: str = "PUSH"      # PUSH | PULL | BIDIRECTIONAL
    customer_ids: Optional[List[str]] = None   # None = sync all


class CrmSyncResult(BaseModel):
    total: int
    synced: int
    failed: int
    errors: List[str]


class CrmMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    crm_provider: str
    external_crm_id: str
    sync_status: SyncStatus
    sync_direction: str
    last_sync_at: Optional[datetime]
    created_at: datetime


# ── E-commerce ────────────────────────────────────────────────────────────────

class EcommerceImportRequest(BaseModel):
    platform: str              # SHOPIFY | WOOCOMMERCE
    since_date: Optional[str] = None
    limit: int = 50


class EcommerceImportResult(BaseModel):
    platform: str
    imported: int
    mapped: int
    failed: int
    errors: List[str]


class EcommerceOrderMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_platform: str
    external_order_id: str
    external_order_no: Optional[str]
    so_id: Optional[str]
    sync_status: SyncStatus
    error_message: Optional[str]
    last_sync_at: Optional[datetime]
    created_at: datetime


class InventorySyncResult(BaseModel):
    platform: str
    products_synced: int
    failed: int
    errors: List[str]


# ── IoT / Machine ─────────────────────────────────────────────────────────────

class MachineEventCreate(BaseModel):
    machine_id: str
    machine_name: Optional[str] = None
    event_type: str
    value_str: Optional[str] = None
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    production_order_id: Optional[str] = None
    received_at: Optional[datetime] = None
    raw_payload: Optional[str] = None


class MachineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    machine_id: str
    machine_name: Optional[str]
    event_type: str
    value_str: Optional[str]
    value_numeric: Optional[float]
    unit: Optional[str]
    production_order_id: Optional[str]
    received_at: Optional[datetime]
    created_at: datetime


class MachineStatusRow(BaseModel):
    machine_id: str
    machine_name: Optional[str]
    last_event_type: Optional[str]
    last_value: Optional[str]
    last_seen: Optional[datetime]
    event_count_24h: int


# Marketplace / plugin architecture

class MarketplaceConnectorRead(BaseModel):
    connector_id: str
    connector_code: str
    name: str
    category: str
    description: Optional[str] = None
    icon_emoji: Optional[str] = None
    auth_type: Optional[str] = None
    status: ConnectorStatus
    is_configured: bool
    config_guide: Optional[str] = None
    docs_url: Optional[str] = None
    current_version: str
    module_key: Optional[str] = None
    dependency_codes: List[str] = []
    required_permissions: List[str] = []
    supports_tenant_config: bool = True
    is_core: bool = False
    installation_status: Optional[PluginInstallStatus] = None
    installed_version: Optional[str] = None
    tenant_key: Optional[str] = None


class PluginInstallRequest(BaseModel):
    tenant_key: str = "default"
    environment: str = "sandbox"
    config: Dict[str, Any] = {}
    notes: Optional[str] = None


class PluginConfigUpdate(BaseModel):
    tenant_key: str = "default"
    environment: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class PluginInstallationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    connector_id: Optional[str]
    connector_code: str
    tenant_key: str
    installed_version: str
    status: PluginInstallStatus
    environment: str
    config_json: Optional[str]
    installed_by_id: Optional[str]
    installed_at: Optional[datetime]
    disabled_at: Optional[datetime]
    last_updated_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class PluginLifecycleEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installation_id: Optional[str]
    connector_code: str
    tenant_key: str
    action: PluginLifecycleAction
    previous_status: Optional[str]
    new_status: Optional[str]
    actor_id: Optional[str]
    message: Optional[str]
    metadata_json: Optional[str]
    created_at: datetime
