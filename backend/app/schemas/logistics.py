from __future__ import annotations

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.models.logistics import (
    ShipmentMode, IntlShipmentStatus, ContainerType, ContainerStatus,
    CustomsDocType, CustomsDocStatus, ClearanceStatus,
    LocalCostType, LocalPaymentMethod, LocalCostStatus,
)


# ── Shipment ───────────────────────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    shipment_no: str
    mode: ShipmentMode = ShipmentMode.SEA
    origin_country: str = "Turkey"
    origin_city: Optional[str] = None
    origin_port: Optional[str] = None
    destination_country: str = "Kenya"
    destination_city: str = "Mombasa"
    destination_port: str = "Port of Mombasa"
    final_destination: Optional[str] = None
    carrier: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    bl_number: Optional[str] = None
    planned_departure: Optional[date] = None
    actual_departure: Optional[date] = None
    eta: Optional[date] = None
    incoterm: Optional[str] = None
    currency: str = "USD"
    freight_cost: Optional[float] = None
    insurance_cost: Optional[float] = None
    total_cbm: Optional[float] = None
    total_weight_kg: Optional[float] = None
    forwarder: Optional[str] = None
    notes: Optional[str] = None


class ShipmentUpdate(BaseModel):
    mode: Optional[ShipmentMode] = None
    carrier: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    bl_number: Optional[str] = None
    origin_port: Optional[str] = None
    origin_city: Optional[str] = None
    final_destination: Optional[str] = None
    planned_departure: Optional[date] = None
    actual_departure: Optional[date] = None
    eta: Optional[date] = None
    ata: Optional[date] = None
    status: Optional[IntlShipmentStatus] = None
    incoterm: Optional[str] = None
    freight_cost: Optional[float] = None
    insurance_cost: Optional[float] = None
    total_cbm: Optional[float] = None
    total_weight_kg: Optional[float] = None
    forwarder: Optional[str] = None
    notes: Optional[str] = None


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_no: str
    mode: ShipmentMode
    origin_country: str
    origin_city: Optional[str]
    origin_port: Optional[str]
    destination_country: str
    destination_city: str
    destination_port: str
    final_destination: Optional[str]
    carrier: Optional[str]
    vessel_name: Optional[str]
    voyage_no: Optional[str]
    bl_number: Optional[str]
    planned_departure: Optional[date]
    actual_departure: Optional[date]
    eta: Optional[date]
    ata: Optional[date]
    status: IntlShipmentStatus
    incoterm: Optional[str]
    currency: str
    freight_cost: Optional[float]
    insurance_cost: Optional[float]
    total_cbm: Optional[float]
    total_weight_kg: Optional[float]
    forwarder: Optional[str]
    notes: Optional[str]
    created_at: datetime
    # computed
    container_count: Optional[int] = None
    po_count: Optional[int] = None
    days_to_eta: Optional[int] = None


# ── Container ──────────────────────────────────────────────────────────────────

class ContainerCreate(BaseModel):
    shipment_id: str
    container_no: str
    seal_no: Optional[str] = None
    container_type: ContainerType = ContainerType.DRY_40FT
    tare_weight_kg: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    cbm: Optional[float] = None
    contents_summary: Optional[str] = None
    demurrage_free_days: Optional[int] = 7
    notes: Optional[str] = None


class ContainerUpdate(BaseModel):
    seal_no: Optional[str] = None
    container_type: Optional[ContainerType] = None
    gross_weight_kg: Optional[float] = None
    cbm: Optional[float] = None
    contents_summary: Optional[str] = None
    status: Optional[ContainerStatus] = None
    customs_release_no: Optional[str] = None
    notes: Optional[str] = None


class ContainerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    shipment_no: Optional[str] = None
    container_no: str
    seal_no: Optional[str]
    container_type: ContainerType
    tare_weight_kg: Optional[float]
    gross_weight_kg: Optional[float]
    cbm: Optional[float]
    contents_summary: Optional[str]
    status: ContainerStatus
    customs_release_no: Optional[str]
    demurrage_free_days: Optional[int]
    notes: Optional[str]
    created_at: datetime


# ── PO Link ────────────────────────────────────────────────────────────────────

class POLinkCreate(BaseModel):
    po_id: str
    notes: Optional[str] = None


class POLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    po_id: str
    po_no: Optional[str] = None
    supplier_name: Optional[str] = None
    po_total: Optional[float] = None
    notes: Optional[str]
    created_at: datetime


# ── Customs Document ───────────────────────────────────────────────────────────

class CustomsDocCreate(BaseModel):
    shipment_id: str
    doc_type: CustomsDocType
    doc_no: str
    doc_date: Optional[date] = None
    issuer: Optional[str] = None
    description: Optional[str] = None
    file_ref: Optional[str] = None


class CustomsDocUpdate(BaseModel):
    doc_no: Optional[str] = None
    doc_date: Optional[date] = None
    issuer: Optional[str] = None
    description: Optional[str] = None
    file_ref: Optional[str] = None
    status: Optional[CustomsDocStatus] = None


class CustomsDocRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    doc_type: CustomsDocType
    doc_no: str
    doc_date: Optional[date]
    issuer: Optional[str]
    description: Optional[str]
    file_ref: Optional[str]
    status: CustomsDocStatus
    created_at: datetime


# ── Customs Clearance ──────────────────────────────────────────────────────────

class ClearanceCreate(BaseModel):
    shipment_id: str
    entry_no: Optional[str] = None
    agent_name: Optional[str] = None
    submission_date: Optional[date] = None
    kra_pin: Optional[str] = None
    notes: Optional[str] = None


class ClearanceUpdate(BaseModel):
    entry_no: Optional[str] = None
    agent_name: Optional[str] = None
    submission_date: Optional[date] = None
    examination_date: Optional[date] = None
    clearance_date: Optional[date] = None
    status: Optional[ClearanceStatus] = None
    cif_value_usd: Optional[float] = None
    import_duty: Optional[float] = None
    vat: Optional[float] = None
    idf_fee: Optional[float] = None
    railway_development_levy: Optional[float] = None
    other_charges: Optional[float] = None
    total_taxes_kes: Optional[float] = None
    kra_pin: Optional[str] = None
    notes: Optional[str] = None


class ClearanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    entry_no: Optional[str]
    agent_name: Optional[str]
    submission_date: Optional[date]
    examination_date: Optional[date]
    clearance_date: Optional[date]
    status: ClearanceStatus
    cif_value_usd: Optional[float]
    import_duty: Optional[float]
    vat: Optional[float]
    idf_fee: Optional[float]
    railway_development_levy: Optional[float]
    other_charges: Optional[float]
    total_taxes_kes: Optional[float]
    kra_pin: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Arrival Notification ───────────────────────────────────────────────────────

class ArrivalCreate(BaseModel):
    shipment_id: str
    eta_original: Optional[date] = None
    eta_revised: Optional[date] = None
    notes: Optional[str] = None


class ArrivalUpdate(BaseModel):
    eta_revised: Optional[date] = None
    ata: Optional[date] = None
    port_discharge_date: Optional[date] = None
    customs_clearance_date: Optional[date] = None
    delivery_date: Optional[date] = None
    grn_id: Optional[str] = None
    eta_alert_sent: Optional[bool] = None
    notes: Optional[str] = None


class ArrivalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    eta_original: Optional[date]
    eta_revised: Optional[date]
    eta_alert_sent: bool
    ata: Optional[date]
    port_discharge_date: Optional[date]
    customs_clearance_date: Optional[date]
    delivery_date: Optional[date]
    grn_id: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Local Logistics Costs ─────────────────────────────────────────────────────

class LocalCostCreate(BaseModel):
    shipment_id: str
    cost_type: LocalCostType
    description: str
    vendor_name: Optional[str] = None
    amount_kes: float
    payment_method: LocalPaymentMethod = LocalPaymentMethod.MPESA
    paid_date: Optional[date] = None
    mpesa_reference: Optional[str] = None
    mpesa_phone: Optional[str] = None
    notes: Optional[str] = None


class LocalCostUpdate(BaseModel):
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    amount_kes: Optional[float] = None
    payment_method: Optional[LocalPaymentMethod] = None
    payment_status: Optional[LocalCostStatus] = None
    paid_date: Optional[date] = None
    mpesa_reference: Optional[str] = None
    mpesa_phone: Optional[str] = None
    notes: Optional[str] = None


class LocalCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipment_id: str
    cost_type: LocalCostType
    description: str
    vendor_name: Optional[str]
    amount_kes: float
    payment_method: LocalPaymentMethod
    payment_status: LocalCostStatus
    paid_date: Optional[date]
    mpesa_reference: Optional[str]
    mpesa_phone: Optional[str]
    notes: Optional[str]
    created_at: datetime


class LocalCostSummary(BaseModel):
    """Aggregated cost summary for a shipment."""
    shipment_id: str
    total_kes: float
    paid_kes: float
    pending_kes: float
    by_type: List["LocalCostRead"]


# ── Dashboard / Report rows ────────────────────────────────────────────────────

class ShipmentDashboardRow(BaseModel):
    """Enriched row for the Turkey→Kenya visibility dashboard."""
    shipment_id: str
    shipment_no: str
    mode: ShipmentMode
    status: IntlShipmentStatus
    carrier: Optional[str]
    vessel_name: Optional[str]
    bl_number: Optional[str]
    origin_port: Optional[str]
    destination_port: str
    planned_departure: Optional[date]
    eta: Optional[date]
    eta_revised: Optional[date]
    ata: Optional[date]
    days_to_eta: Optional[int]
    container_count: int
    po_count: int
    clearance_status: Optional[ClearanceStatus]
    total_taxes_kes: Optional[float]
    has_overdue_docs: bool
