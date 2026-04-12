import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class ShipmentMode(str, enum.Enum):
    SEA = "SEA"
    AIR = "AIR"
    ROAD = "ROAD"
    RAIL = "RAIL"


class IntlShipmentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    CARGO_LOADED = "CARGO_LOADED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED_PORT = "ARRIVED_PORT"
    CUSTOMS_HOLD = "CUSTOMS_HOLD"
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ContainerType(str, enum.Enum):
    DRY_20FT = "20FT_DRY"
    DRY_40FT = "40FT_DRY"
    HC_40FT = "40FT_HC"
    REEFER_20FT = "20FT_REEFER"
    LCL = "LCL"


class ContainerStatus(str, enum.Enum):
    EMPTY = "EMPTY"
    LOADING = "LOADING"
    LOADED = "LOADED"
    IN_TRANSIT = "IN_TRANSIT"
    AT_PORT = "AT_PORT"
    CUSTOMS_HOLD = "CUSTOMS_HOLD"
    RELEASED = "RELEASED"
    RETURNED = "RETURNED"


class CustomsDocType(str, enum.Enum):
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    BILL_OF_LADING = "BILL_OF_LADING"
    AIRWAY_BILL = "AIRWAY_BILL"
    CERTIFICATE_OF_ORIGIN = "CERTIFICATE_OF_ORIGIN"
    PHYTOSANITARY = "PHYTOSANITARY"
    IMPORT_DECLARATION = "IMPORT_DECLARATION"
    DUTY_RECEIPT = "DUTY_RECEIPT"
    OTHER = "OTHER"


class CustomsDocStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ClearanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOCS_SUBMITTED = "DOCS_SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    EXAM_REQUESTED = "EXAM_REQUESTED"
    DUTY_ASSESSED = "DUTY_ASSESSED"
    DUTY_PAID = "DUTY_PAID"
    CLEARED = "CLEARED"
    HELD = "HELD"


# ── International Shipment ─────────────────────────────────────────────────────

class InternationalShipment(Base, TimestampMixin):
    """Header for a Turkey → Kenya (or any cross-border) shipment."""
    __tablename__ = "intl_shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_no = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(Enum(ShipmentMode), nullable=False, default=ShipmentMode.SEA)

    # Origin (Turkey)
    origin_country = Column(String(100), nullable=False, default="Turkey")
    origin_city = Column(String(100), nullable=True)
    origin_port = Column(String(200), nullable=True)     # e.g. Port of Istanbul / Izmir Port

    # Destination (Kenya)
    destination_country = Column(String(100), nullable=False, default="Kenya")
    destination_city = Column(String(100), nullable=False, default="Mombasa")
    destination_port = Column(String(200), nullable=False, default="Port of Mombasa")
    final_destination = Column(String(255), nullable=True)  # inland delivery address / warehouse

    # Carrier
    carrier = Column(String(255), nullable=True)
    vessel_name = Column(String(255), nullable=True)
    voyage_no = Column(String(100), nullable=True)
    bl_number = Column(String(100), nullable=True, index=True)

    # Dates
    planned_departure = Column(Date, nullable=True)
    actual_departure = Column(Date, nullable=True)
    eta = Column(Date, nullable=True, index=True)
    ata = Column(Date, nullable=True)

    status = Column(Enum(IntlShipmentStatus), nullable=False, default=IntlShipmentStatus.DRAFT)

    # Commercial
    incoterm = Column(String(20), nullable=True)          # FOB, CIF, CFR, EXW, DAP
    currency = Column(String(10), nullable=False, default="USD")
    freight_cost = Column(Numeric(14, 2), nullable=True)
    insurance_cost = Column(Numeric(14, 2), nullable=True)
    total_cbm = Column(Numeric(10, 3), nullable=True)
    total_weight_kg = Column(Numeric(14, 3), nullable=True)

    forwarder = Column(String(255), nullable=True)       # freight forwarder name
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User")
    containers = relationship("ShipmentContainer", back_populates="shipment", cascade="all, delete-orphan")
    po_links = relationship("ShipmentPOLink", back_populates="shipment", cascade="all, delete-orphan")
    customs_docs = relationship("CustomsDocument", back_populates="shipment", cascade="all, delete-orphan")
    clearance = relationship("CustomsClearance", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    arrival = relationship("ArrivalNotification", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    local_costs = relationship("LocalLogisticsCost", back_populates="shipment", cascade="all, delete-orphan", order_by="LocalLogisticsCost.created_at")


# ── Container ──────────────────────────────────────────────────────────────────

class ShipmentContainer(Base, TimestampMixin):
    __tablename__ = "shipment_containers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    container_no = Column(String(50), nullable=False, index=True)  # e.g. MSCU1234567
    seal_no = Column(String(100), nullable=True)
    container_type = Column(Enum(ContainerType), nullable=False, default=ContainerType.DRY_40FT)
    tare_weight_kg = Column(Numeric(10, 3), nullable=True)
    gross_weight_kg = Column(Numeric(10, 3), nullable=True)
    cbm = Column(Numeric(10, 3), nullable=True)
    contents_summary = Column(Text, nullable=True)       # free-text description of contents
    status = Column(Enum(ContainerStatus), nullable=False, default=ContainerStatus.LOADING)
    customs_release_no = Column(String(100), nullable=True)
    demurrage_free_days = Column(Integer, nullable=True, default=7)
    notes = Column(Text, nullable=True)

    shipment = relationship("InternationalShipment", back_populates="containers")


# ── Shipment ↔ PO link (many-to-many) ─────────────────────────────────────────

class ShipmentPOLink(Base, TimestampMixin):
    __tablename__ = "shipment_po_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    notes = Column(String(500), nullable=True)

    shipment = relationship("InternationalShipment", back_populates="po_links")
    po = relationship("PurchaseOrder")


# ── Customs Documents ──────────────────────────────────────────────────────────

class CustomsDocument(Base, TimestampMixin):
    __tablename__ = "customs_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(Enum(CustomsDocType), nullable=False)
    doc_no = Column(String(200), nullable=False)         # invoice no / BL no / AWB no
    doc_date = Column(Date, nullable=True)
    issuer = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    file_ref = Column(String(500), nullable=True)        # placeholder — path / S3 key
    status = Column(Enum(CustomsDocStatus), nullable=False, default=CustomsDocStatus.DRAFT)

    shipment = relationship("InternationalShipment", back_populates="customs_docs")


# ── Customs Clearance ──────────────────────────────────────────────────────────

class CustomsClearance(Base, TimestampMixin):
    """KRA / Port of Mombasa customs clearance record."""
    __tablename__ = "customs_clearances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, unique=True)
    entry_no = Column(String(100), nullable=True)         # customs entry / IDF number
    agent_name = Column(String(255), nullable=True)
    submission_date = Column(Date, nullable=True)
    examination_date = Column(Date, nullable=True)
    clearance_date = Column(Date, nullable=True)
    status = Column(Enum(ClearanceStatus), nullable=False, default=ClearanceStatus.PENDING)

    # Landed cost components (KES)
    cif_value_usd = Column(Numeric(14, 2), nullable=True)
    import_duty = Column(Numeric(14, 2), nullable=True)
    vat = Column(Numeric(14, 2), nullable=True)
    idf_fee = Column(Numeric(14, 2), nullable=True)       # Import Declaration Form fee
    railway_development_levy = Column(Numeric(14, 2), nullable=True)
    other_charges = Column(Numeric(14, 2), nullable=True)
    total_taxes_kes = Column(Numeric(14, 2), nullable=True)

    kra_pin = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    shipment = relationship("InternationalShipment", back_populates="clearance")


# ── Arrival Notification ───────────────────────────────────────────────────────

class LocalCostType(str, enum.Enum):
    TRANSPORT = "TRANSPORT"                   # Road/truck from port to warehouse
    CLEARING_FEE = "CLEARING_FEE"             # Agent service fee (not govt duties)
    PORT_HANDLING = "PORT_HANDLING"           # Port storage, crane fees
    WAREHOUSE_HANDLING = "WAREHOUSE_HANDLING" # Receiving/unloading at warehouse
    FUMIGATION = "FUMIGATION"
    INSPECTION_FEE = "INSPECTION_FEE"
    OTHER = "OTHER"


class LocalPaymentMethod(str, enum.Enum):
    MPESA = "MPESA"
    BANK = "BANK"
    CASH = "CASH"


class LocalCostStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


class ArrivalNotification(Base, TimestampMixin):
    """Tracks ETA revisions, actual arrival, port events and GRN linkage."""
    __tablename__ = "arrival_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, unique=True)
    eta_original = Column(Date, nullable=True)
    eta_revised = Column(Date, nullable=True)
    eta_alert_sent = Column(Boolean, nullable=False, default=False)

    ata = Column(Date, nullable=True)                    # actual time of arrival at port
    port_discharge_date = Column(Date, nullable=True)
    customs_clearance_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)          # delivered to warehouse

    # Link to GRN when goods are received into inventory
    grn_id = Column(UUID(as_uuid=True), ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True)

    notes = Column(Text, nullable=True)

    shipment = relationship("InternationalShipment", back_populates="arrival")
    grn = relationship("GoodsReceipt")


# ── Local Logistics Costs (Kenya-side) ────────────────────────────────────────

class LocalLogisticsCost(Base, TimestampMixin):
    """
    Kenya-side local logistics costs after port arrival:
    transport, clearing agent fees, port handling, warehouse handling, etc.
    Supports M-Pesa payment references for local service provider payments.
    """
    __tablename__ = "local_logistics_costs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("intl_shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    cost_type = Column(Enum(LocalCostType), nullable=False)
    description = Column(String(255), nullable=False)
    vendor_name = Column(String(255), nullable=True)          # transporter / agent name
    amount_kes = Column(Numeric(14, 2), nullable=False)
    payment_method = Column(Enum(LocalPaymentMethod), nullable=False, default=LocalPaymentMethod.MPESA)
    payment_status = Column(Enum(LocalCostStatus), nullable=False, default=LocalCostStatus.PENDING)
    paid_date = Column(Date, nullable=True)
    mpesa_reference = Column(String(100), nullable=True, index=True)  # M-Pesa receipt no
    mpesa_phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    shipment = relationship("InternationalShipment", back_populates="local_costs")
    recorded_by = relationship("User")
