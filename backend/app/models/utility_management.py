"""
Utility Management Module — Database Models

Covers all factory utility and infrastructure systems:
electricity, water, soft water, steam/boilers, compressed air,
solar, chemical water treatment, biological wastewater treatment,
utility chemical consumption, utility bills, cost allocation,
alarms/anomaly detection, and machine-level consumption mapping.
"""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum as SAEnum, DateTime, Date, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enumerations ───────────────────────────────────────────────────────────────

class UtilityType(str, enum.Enum):
    ELECTRICITY    = "ELECTRICITY"
    WATER          = "WATER"
    SOFT_WATER     = "SOFT_WATER"
    PROCESS_WATER  = "PROCESS_WATER"
    STEAM          = "STEAM"
    COMPRESSED_AIR = "COMPRESSED_AIR"
    SOLAR          = "SOLAR"
    NATURAL_GAS    = "NATURAL_GAS"
    WASTEWATER     = "WASTEWATER"
    DIESEL         = "DIESEL"
    CHILLED_WATER  = "CHILLED_WATER"
    OTHER          = "OTHER"


class SourceMethod(str, enum.Enum):
    """How a reading or record value was obtained."""
    MANUAL     = "MANUAL"      # Typed in by an operator
    IMPORTED   = "IMPORTED"    # Loaded via CSV/Excel import
    API        = "API"         # Received from an external API
    IOT        = "IOT"         # Pushed by an IoT device / SCADA
    CALCULATED = "CALCULATED"  # Derived by system logic
    ESTIMATED  = "ESTIMATED"   # Estimated / interpolated


class DataQuality(str, enum.Enum):
    GOOD      = "GOOD"
    ESTIMATED = "ESTIMATED"
    SUSPECT   = "SUSPECT"
    MISSING   = "MISSING"


class UtilityAssetStatus(str, enum.Enum):
    ACTIVE             = "ACTIVE"
    IDLE               = "IDLE"
    UNDER_MAINTENANCE  = "UNDER_MAINTENANCE"
    DECOMMISSIONED     = "DECOMMISSIONED"


class LifecycleStatus(str, enum.Enum):
    IN_USE       = "IN_USE"
    STORED       = "STORED"
    RETIRED      = "RETIRED"
    DISPOSED     = "DISPOSED"


class CriticalityLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class DeviceType(str, enum.Enum):
    METER      = "METER"
    SENSOR     = "SENSOR"
    LOGGER     = "LOGGER"
    CONTROLLER = "CONTROLLER"
    ANALYSER   = "ANALYSER"


class ReadingType(str, enum.Enum):
    CUMULATIVE    = "CUMULATIVE"
    INSTANTANEOUS = "INSTANTANEOUS"
    DIFFERENTIAL  = "DIFFERENTIAL"


class ReadingSource(str, enum.Enum):
    MANUAL   = "MANUAL"
    IOT      = "IOT"
    API      = "API"
    SCADA    = "SCADA"
    IMPORTED = "IMPORTED"


class ReadingFrequency(str, enum.Enum):
    CONTINUOUS    = "CONTINUOUS"
    EVERY_15MIN   = "EVERY_15MIN"
    HOURLY        = "HOURLY"
    EVERY_4H      = "EVERY_4H"
    DAILY         = "DAILY"
    WEEKLY        = "WEEKLY"
    ON_DEMAND     = "ON_DEMAND"


class ValidatedStatus(str, enum.Enum):
    PENDING       = "PENDING"
    VALIDATED     = "VALIDATED"
    REJECTED      = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


class TariffType(str, enum.Enum):
    FLAT        = "FLAT"
    TIME_OF_USE = "TIME_OF_USE"
    DEMAND      = "DEMAND"
    STEPPED     = "STEPPED"


class AlarmSeverity(str, enum.Enum):
    INFO     = "INFO"
    WARNING  = "WARNING"
    ALERT    = "ALERT"
    CRITICAL = "CRITICAL"


class AlarmStatus(str, enum.Enum):
    ACTIVE       = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED     = "RESOLVED"
    SUPPRESSED   = "SUPPRESSED"


class AlarmOperator(str, enum.Enum):
    GT        = "GT"         # greater than
    LT        = "LT"         # less than
    GTE       = "GTE"        # greater than or equal
    LTE       = "LTE"        # less than or equal
    EQ        = "EQ"         # equal
    NEQ       = "NEQ"        # not equal
    DELTA_PCT = "DELTA_PCT"  # % change vs previous reading


class AllocationMethod(str, enum.Enum):
    METERED       = "METERED"       # Dedicated meter reading
    PROPORTIONAL  = "PROPORTIONAL"  # Share by production volume
    FIXED         = "FIXED"         # Fixed rate per period
    CALCULATED    = "CALCULATED"    # Formula / algorithm


class BillStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    PAID     = "PAID"
    DISPUTED = "DISPUTED"


class SoftenerStatus(str, enum.Enum):
    ONLINE       = "ONLINE"
    REGENERATING = "REGENERATING"
    STANDBY      = "STANDBY"
    FAULT        = "FAULT"


class BoilerStatus(str, enum.Enum):
    RUNNING  = "RUNNING"
    STANDBY  = "STANDBY"
    SHUTDOWN = "SHUTDOWN"
    FAULT    = "FAULT"


class CompressorStatus(str, enum.Enum):
    RUNNING     = "RUNNING"
    STANDBY     = "STANDBY"
    FAULT       = "FAULT"
    MAINTENANCE = "MAINTENANCE"


class TreatmentType(str, enum.Enum):
    COAGULATION      = "COAGULATION"
    FLOCCULATION     = "FLOCCULATION"
    DISINFECTION     = "DISINFECTION"
    SOFTENING        = "SOFTENING"
    REVERSE_OSMOSIS  = "REVERSE_OSMOSIS"
    BIOLOGICAL       = "BIOLOGICAL"
    PH_ADJUSTMENT    = "PH_ADJUSTMENT"
    DECHLORINATION   = "DECHLORINATION"
    FILTRATION       = "FILTRATION"
    OTHER            = "OTHER"


class ChemicalCategory(str, enum.Enum):
    BOILER_TREATMENT    = "BOILER_TREATMENT"
    OXYGEN_SCAVENGER    = "OXYGEN_SCAVENGER"
    ANTISCALANT         = "ANTISCALANT"
    CORROSION_INHIBITOR = "CORROSION_INHIBITOR"
    BIOCIDE             = "BIOCIDE"
    COAGULANT           = "COAGULANT"
    FLOCCULANT          = "FLOCCULANT"
    PH_ADJUSTER         = "PH_ADJUSTER"
    NEUTRALIZER         = "NEUTRALIZER"
    DEFOAMER            = "DEFOAMER"
    CHLORINE            = "CHLORINE"
    DECHLORINATION      = "DECHLORINATION"
    BIO_NUTRIENT        = "BIO_NUTRIENT"
    OTHER               = "OTHER"


class DosingMode(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO   = "AUTO"


class WastewaterProcess(str, enum.Enum):
    PRIMARY         = "PRIMARY"
    SECONDARY       = "SECONDARY"
    TERTIARY        = "TERTIARY"
    SLUDGE_HANDLING = "SLUDGE_HANDLING"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT     = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    BORDERLINE    = "BORDERLINE"
    NOT_TESTED    = "NOT_TESTED"


# ── Chemical Treatment Master ──────────────────────────────────────────────────

class WaterTreatmentChemical(Base, TimestampMixin):
    """
    Chemical master catalog for water and utility treatment chemicals.
    Covers boiler chemicals, oxygen scavengers, antiscalants, biocides, etc.
    Referenced by TreatmentChemicalRecord for lot-traceable dosing logs.
    """
    __tablename__ = "water_treatment_chemicals"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chemical_code   = Column(String(50), nullable=False, unique=True, index=True)
    chemical_name   = Column(String(255), nullable=False)
    chemical_category = Column(SAEnum(ChemicalCategory), nullable=False, index=True)
    description     = Column(Text, nullable=True)

    # Supplier
    supplier_id     = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)

    # Units of measure
    stock_uom       = Column(String(30), nullable=False)   # storage UOM  e.g. kg, L, drum
    dosing_uom      = Column(String(30), nullable=False)   # dosing UOM   e.g. ml, g, ppm

    # Cost
    unit_cost       = Column(Numeric(14, 6), nullable=True)   # cost per stock_uom

    # Dosing targets for anomaly detection
    target_dose_min = Column(Numeric(12, 4), nullable=True)   # minimum target dose (dosing_uom)
    target_dose_max = Column(Numeric(12, 4), nullable=True)   # maximum target dose (dosing_uom)

    # Stock control
    low_stock_threshold = Column(Numeric(14, 4), nullable=True)   # alert when closing_stock falls below

    # Link to materials master (optional — for inventory integration)
    material_id     = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)

    is_active       = Column(Boolean, nullable=False, default=True)
    notes           = Column(Text, nullable=True)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier        = relationship("Supplier")
    material        = relationship("Material")
    created_by      = relationship("User", foreign_keys=[created_by_id])
    treatment_records = relationship("TreatmentChemicalRecord", back_populates="chemical")


# ── Master Data ────────────────────────────────────────────────────────────────

class UtilityAssetCategory(Base, TimestampMixin):
    """Master category for utility assets (e.g. Boiler, Compressor, Solar Inverter)."""
    __tablename__ = "utility_asset_categories"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code         = Column(String(50), nullable=False, unique=True, index=True)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)
    default_unit = Column(String(30), nullable=True)
    is_active    = Column(Boolean, nullable=False, default=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    assets     = relationship("UtilityAsset", back_populates="category")


class UtilityAsset(Base, TimestampMixin):
    """
    Utility infrastructure asset register.
    Covers boilers, compressors, softeners, solar arrays, WWTP units, etc.
    Optionally linked to the maintenance module's Asset record.
    """
    __tablename__ = "utility_assets"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_no     = Column(String(50), nullable=False, unique=True, index=True)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    category_id  = Column(UUID(as_uuid=True), ForeignKey("utility_asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)

    # Physical location
    location      = Column(String(255), nullable=True)
    building_area = Column(String(100), nullable=True, index=True)  # e.g. Block A, Boiler Room
    department    = Column(String(100), nullable=True, index=True)
    subsystem     = Column(String(100), nullable=True, index=True)   # e.g. Cooling Loop, Main Supply

    # Production linkage
    line_id    = Column(String(100), nullable=True, index=True)   # production line code
    machine_id = Column(String(100), nullable=True, index=True)   # machine/equipment code

    # Hierarchy
    parent_asset_id = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True)

    # Equipment detail
    manufacturer    = Column(String(255), nullable=True)
    model           = Column(String(255), nullable=True)
    serial_no       = Column(String(100), nullable=True)
    install_date    = Column(Date, nullable=True)
    warranty_expiry = Column(Date, nullable=True)

    # Capacity / rating
    rated_capacity    = Column(Numeric(14, 3), nullable=True)
    capacity_unit     = Column(String(30), nullable=True)    # e.g. kW, kVA, bar, kg/h
    rated_power       = Column(Numeric(14, 3), nullable=True)
    rated_power_unit  = Column(String(30), nullable=True)    # e.g. kW, kVA
    flow_capacity     = Column(Numeric(14, 3), nullable=True)
    pressure_capacity = Column(Numeric(14, 3), nullable=True)
    temperature_range = Column(String(100), nullable=True)   # e.g. "-10°C to 60°C"

    # Status / classification
    status             = Column(SAEnum(UtilityAssetStatus), nullable=False, default=UtilityAssetStatus.ACTIVE, index=True)
    lifecycle_status   = Column(SAEnum(LifecycleStatus), nullable=True, index=True)
    criticality_level  = Column(SAEnum(CriticalityLevel), nullable=True, index=True)
    maintenance_strategy = Column(String(100), nullable=True)
    is_active          = Column(Boolean, nullable=False, default=True)
    notes              = Column(Text, nullable=True)

    # Link to maintenance module asset record (optional, for PM/breakdown linkage)
    maintenance_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    created_by_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    category          = relationship("UtilityAssetCategory", back_populates="assets")
    parent_asset      = relationship("UtilityAsset", remote_side="UtilityAsset.id", foreign_keys="[UtilityAsset.parent_asset_id]")
    maintenance_asset = relationship("Asset")
    created_by        = relationship("User", foreign_keys=[created_by_id])
    devices           = relationship("UtilityDevice", back_populates="asset")
    boiler_records    = relationship("BoilerSteamRecord", back_populates="asset")
    compressor_records = relationship("CompressorRecord", back_populates="asset")
    soft_water_records = relationship("SoftWaterRecord", back_populates="asset")
    solar_records      = relationship("SolarRecord", back_populates="asset")
    treatment_records  = relationship("TreatmentChemicalRecord", back_populates="asset")
    wastewater_records = relationship("WastewaterRecord", back_populates="asset")
    alarm_events       = relationship("UtilityAlarmEvent", back_populates="asset")


class UtilityDevice(Base, TimestampMixin):
    """
    Meters, sensors, loggers, and analysers installed on utility systems.
    A device produces UtilityReading records.
    """
    __tablename__ = "utility_devices"
    __table_args__ = (
        Index("ix_utility_devices_utility_type", "utility_type"),
        Index("ix_utility_devices_asset_id", "asset_id"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code = Column(String(50), nullable=False, unique=True, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    device_type  = Column(SAEnum(DeviceType), nullable=False)
    utility_type = Column(SAEnum(UtilityType), nullable=False)

    # The utility asset this device monitors (optional — a device may monitor a pipe/panel)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True)

    # Physical location (may differ from asset location e.g. submeter on a panel)
    location      = Column(String(255), nullable=True)
    building_area = Column(String(100), nullable=True, index=True)
    department    = Column(String(100), nullable=True, index=True)

    # Equipment details
    manufacturer  = Column(String(255), nullable=True)
    model         = Column(String(255), nullable=True)
    serial_no     = Column(String(100), nullable=True)
    install_date  = Column(Date, nullable=True)

    # Calibration
    last_calibration_date = Column(Date, nullable=True)
    next_calibration_date = Column(Date, nullable=True, index=True)

    # Reading classification
    reading_type      = Column(SAEnum(ReadingType), nullable=True)
    reading_source    = Column(SAEnum(ReadingSource), nullable=True)
    reading_frequency = Column(SAEnum(ReadingFrequency), nullable=True)

    # Production linkage (device-level)
    related_line_id    = Column(String(100), nullable=True, index=True)
    related_machine_id = Column(String(100), nullable=True, index=True)

    # Range / engineering
    unit_of_measure = Column(String(30), nullable=False)   # e.g. kWh, m³, bar, °C
    min_value       = Column(Numeric(14, 4), nullable=True)
    max_value       = Column(Numeric(14, 4), nullable=True)
    pulse_factor    = Column(Numeric(14, 6), nullable=True)  # pulse → engineering unit

    # Alarm limits (quick thresholds; detailed rules in UtilityAlarmRule)
    min_alarm_limit = Column(Numeric(14, 4), nullable=True)
    max_alarm_limit = Column(Numeric(14, 4), nullable=True)

    # Calibration
    calibration_required       = Column(Boolean, nullable=False, default=False)
    calibration_frequency_days = Column(Integer, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    notes     = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    asset      = relationship("UtilityAsset", back_populates="devices")
    created_by = relationship("User", foreign_keys=[created_by_id])
    readings   = relationship("UtilityReading", back_populates="device")
    alarm_rules = relationship("UtilityAlarmRule", back_populates="device")
    alarm_events = relationship("UtilityAlarmEvent", back_populates="device")
    machine_mappings = relationship("MachineUtilityMapping", back_populates="device")


class UtilityTariff(Base, TimestampMixin):
    """
    Utility tariff / pricing structure.
    Used to value consumption transactions and bill verification.
    Supports flat, time-of-use, demand, and stepped tariff types.
    """
    __tablename__ = "utility_tariffs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tariff_code  = Column(String(50), nullable=False, unique=True, index=True)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)
    tariff_type  = Column(SAEnum(TariffType), nullable=False, default=TariffType.FLAT)

    # Supplier/utility company
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date, nullable=True)

    # Rates
    unit          = Column(String(30), nullable=False)    # e.g. kWh, m³, kg
    currency_code = Column(String(10), nullable=False, default="USD")
    base_rate     = Column(Numeric(14, 6), nullable=False)   # $/unit (flat or first block)
    demand_rate   = Column(Numeric(14, 6), nullable=True)    # $/kW for demand tariffs
    fixed_charge  = Column(Numeric(14, 4), nullable=True)    # fixed monthly/billing charge
    tax_rate_pct  = Column(Numeric(7, 4), nullable=True)     # VAT / levy %

    is_active = Column(Boolean, nullable=False, default=True)
    notes     = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier   = relationship("Supplier")
    created_by = relationship("User", foreign_keys=[created_by_id])
    bills      = relationship("UtilityBill", back_populates="tariff")
    transactions = relationship("UtilityTransaction", back_populates="tariff")


class UtilityAlarmRule(Base, TimestampMixin):
    """
    Threshold / anomaly detection rule for a device or asset parameter.
    The alarm engine evaluates incoming readings against these rules.
    """
    __tablename__ = "utility_alarm_rules"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code   = Column(String(50), nullable=False, unique=True, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)
    device_id    = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="CASCADE"), nullable=True, index=True)
    asset_id     = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="CASCADE"), nullable=True, index=True)

    # What to evaluate
    parameter       = Column(String(100), nullable=False)   # e.g. "power_kw", "flow_m3h", "pressure_bar"
    operator        = Column(SAEnum(AlarmOperator), nullable=False)
    threshold_value = Column(Numeric(16, 4), nullable=False)
    threshold_unit  = Column(String(30), nullable=True)

    severity          = Column(SAEnum(AlarmSeverity), nullable=False, default=AlarmSeverity.WARNING)
    cooldown_minutes  = Column(Integer, nullable=False, default=15)
    is_active         = Column(Boolean, nullable=False, default=True)

    # Notification routing
    notification_emails  = Column(Text, nullable=True)   # comma-separated
    notification_channel = Column(String(100), nullable=True)  # e.g. slack_channel, sms

    notes         = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    device     = relationship("UtilityDevice", back_populates="alarm_rules")
    asset      = relationship("UtilityAsset")
    created_by = relationship("User", foreign_keys=[created_by_id])
    events     = relationship("UtilityAlarmEvent", back_populates="rule")


# ── Transactional / Operational ────────────────────────────────────────────────

class UtilityReading(Base, TimestampMixin):
    """
    Raw reading from a meter or sensor.
    Immutable ledger — never edited, only corrected via a new reading.
    Anomaly flag set by the alarm engine or manually.
    """
    __tablename__ = "utility_readings"
    __table_args__ = (
        Index("ix_utility_readings_device_dt", "device_id", "reading_datetime"),
        Index("ix_utility_readings_datetime", "reading_datetime"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reading_no       = Column(String(50), nullable=False, unique=True, index=True)
    device_id        = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_id         = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True, index=True)

    reading_datetime     = Column(DateTime(timezone=True), nullable=False)
    raw_value            = Column(Numeric(18, 4), nullable=False)
    adjusted_value       = Column(Numeric(18, 4), nullable=True)   # after calibration correction
    unit_of_measure      = Column(String(30), nullable=False)
    cumulative_value     = Column(Numeric(20, 4), nullable=True)   # totalizer / index value
    interval_consumption = Column(Numeric(18, 4), nullable=True)   # delta from previous reading

    source_method    = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    source_reference = Column(String(255), nullable=True)   # e.g. IoT message id, batch ref
    quality          = Column(SAEnum(DataQuality), nullable=False, default=DataQuality.GOOD)
    is_anomaly       = Column(Boolean, nullable=False, default=False)
    anomaly_note     = Column(Text, nullable=True)

    # Validation workflow
    validated_status = Column(SAEnum(ValidatedStatus), nullable=False, default=ValidatedStatus.PENDING)
    validation_notes = Column(Text, nullable=True)

    # Operational context
    department    = Column(String(100), nullable=True, index=True)
    building_area = Column(String(100), nullable=True)
    shift_ref     = Column(String(50), nullable=True)   # shift code reference
    batch_id      = Column(String(100), nullable=True, index=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    device     = relationship("UtilityDevice", back_populates="readings")
    asset      = relationship("UtilityAsset")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class TxReferenceType(str, enum.Enum):
    """What kind of record spawned this transaction."""
    READING            = "READING"
    BILL               = "BILL"
    BILL_ALLOCATION    = "BILL_ALLOCATION"
    BOILER_RECORD      = "BOILER_RECORD"
    COMPRESSOR_RECORD  = "COMPRESSOR_RECORD"
    SOLAR_RECORD       = "SOLAR_RECORD"
    SOFT_WATER_RECORD  = "SOFT_WATER_RECORD"
    TREATMENT_RECORD   = "TREATMENT_RECORD"
    WASTEWATER_RECORD  = "WASTEWATER_RECORD"
    MANUAL             = "MANUAL"
    CALCULATION        = "CALCULATION"
    IMPORT             = "IMPORT"
    IOT                = "IOT"


class UtilityTransaction(Base, TimestampMixin):
    """
    Unified utility consumption / production / cost transaction.
    The shared backbone for all utility types — electricity, water, steam,
    compressed air, solar, natural gas, treatment chemicals, wastewater, etc.

    Every consumption event — whether read from a meter, allocated from a bill,
    derived from a specialized operational record, or entered manually — maps to
    exactly one row here.  This enables cross-utility cost allocation, KPI
    reporting, line/machine drilldown, and tariff costing from a single table.
    """
    __tablename__ = "utility_transactions"
    __table_args__ = (
        Index("ix_utility_tx_type_date",   "utility_type", "transaction_date"),
        Index("ix_utility_tx_dept_date",   "department", "transaction_date"),
        Index("ix_utility_tx_prod_order",  "production_order_id"),
        Index("ix_utility_tx_ref_type",    "reference_type"),
        Index("ix_utility_tx_ref_id",      "reference_id"),
        Index("ix_utility_tx_is_anomaly",  "is_anomaly"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_no   = Column(String(50), nullable=False, unique=True, index=True)
    utility_type     = Column(SAEnum(UtilityType), nullable=False, index=True)

    # Date / time — date required; time optional for sub-day precision
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_time = Column(
        # Use DateTime instead of Time to avoid driver compatibility issues
        DateTime(timezone=True), nullable=True
    )
    period_start     = Column(DateTime(timezone=True), nullable=True)
    period_end       = Column(DateTime(timezone=True), nullable=True)

    # Source — meter and/or asset this transaction originates from
    device_id = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True, index=True)

    # Reference — link back to the originating record
    reference_type = Column(SAEnum(TxReferenceType), nullable=True)   # e.g. READING, BILL
    reference_id   = Column(String(100), nullable=True)               # UUID or code of source

    # Allocation dimensions (denormalized for query performance)
    department       = Column(String(100), nullable=True, index=True)
    building_area    = Column(String(100), nullable=True, index=True)
    production_line  = Column(String(100), nullable=True, index=True)  # spec: line_id
    machine_ref      = Column(String(100), nullable=True, index=True)  # spec: machine_id
    shift_ref        = Column(String(50), nullable=True)               # spec: shift_id

    # Production linkage
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_no            = Column(String(100), nullable=True, index=True)  # spec: batch_id
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Consumption / quantity
    quantity        = Column(Numeric(18, 4), nullable=False)
    unit_of_measure = Column(String(30), nullable=False)

    # Cost
    tariff_id     = Column(UUID(as_uuid=True), ForeignKey("utility_tariffs.id", ondelete="SET NULL"), nullable=True)
    cost_rate     = Column(Numeric(14, 6), nullable=True)    # rate per unit applied
    total_cost    = Column(Numeric(16, 4), nullable=True)
    currency_code = Column(String(10), nullable=True, default="USD")

    # Variance — actual vs standard/budgeted consumption
    variance_from_standard = Column(Numeric(16, 4), nullable=True)

    # Quality / flags
    source_method = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    quality       = Column(SAEnum(DataQuality), nullable=False, default=DataQuality.GOOD)
    is_estimated  = Column(Boolean, nullable=False, default=False)   # spec: estimated_or_actual
    is_anomaly    = Column(Boolean, nullable=False, default=False)   # spec: anomaly_flag
    anomaly_note  = Column(Text, nullable=True)

    notes         = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    device           = relationship("UtilityDevice")
    asset            = relationship("UtilityAsset")
    production_order = relationship("ProductionOrder")
    product          = relationship("Product")
    tariff           = relationship("UtilityTariff", back_populates="transactions")
    created_by       = relationship("User", foreign_keys=[created_by_id])


class SoftWaterRecord(Base, TimestampMixin):
    """
    Operational log for a soft water / ion exchange unit.
    Tracks water quality, salt consumption, and regeneration cycles.
    """
    __tablename__ = "soft_water_records"
    __table_args__ = (
        Index("ix_soft_water_asset_dt", "asset_id", "record_datetime"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime = Column(DateTime(timezone=True), nullable=False)

    # Water quality
    feed_water_hardness_ppm    = Column(Numeric(10, 2), nullable=True)   # mg/L as CaCO₃
    product_water_hardness_ppm = Column(Numeric(10, 2), nullable=True)
    feed_water_tds_ppm         = Column(Numeric(10, 2), nullable=True)   # Total Dissolved Solids
    product_water_tds_ppm      = Column(Numeric(10, 2), nullable=True)
    feed_ph                    = Column(Numeric(5, 2), nullable=True)
    product_ph                 = Column(Numeric(5, 2), nullable=True)

    # Flow / volume
    flow_rate_lpm       = Column(Numeric(10, 3), nullable=True)   # L/min
    volume_treated_m3   = Column(Numeric(14, 3), nullable=True)

    # Chemical consumption
    salt_consumed_kg    = Column(Numeric(10, 3), nullable=True)
    resin_volume_litres = Column(Numeric(10, 3), nullable=True)

    # Additional water quality
    conductivity_feed_uscm    = Column(Numeric(10, 2), nullable=True)   # µS/cm
    conductivity_product_uscm = Column(Numeric(10, 2), nullable=True)

    # Extended flow / volume
    raw_water_input_m3 = Column(Numeric(14, 3), nullable=True)   # raw water fed to softener

    # Regeneration cycle tracking
    regen_start = Column(DateTime(timezone=True), nullable=True)
    regen_end   = Column(DateTime(timezone=True), nullable=True)

    # Cycle data
    regeneration_count  = Column(Integer, nullable=True, default=0)
    service_run_hours   = Column(Numeric(10, 2), nullable=True)

    # Performance
    efficiency_pct     = Column(Numeric(7, 3), nullable=True)
    status             = Column(SAEnum(SoftenerStatus), nullable=False, default=SoftenerStatus.ONLINE)

    # Operational flags
    downtime_minutes  = Column(Integer, nullable=True)
    maintenance_flag  = Column(Boolean, nullable=False, default=False)
    destination_tag   = Column(String(100), nullable=True)   # e.g. "Boiler Feed", "CIP", "Process"
    department        = Column(String(100), nullable=True, index=True)

    source_method  = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    is_anomaly     = Column(Boolean, nullable=False, default=False)
    anomaly_note   = Column(Text, nullable=True)
    shift_ref      = Column(String(50), nullable=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset      = relationship("UtilityAsset", back_populates="soft_water_records")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class BoilerSteamRecord(Base, TimestampMixin):
    """
    Operational log for a boiler / steam generation unit.
    Tracks steam parameters, fuel consumption, efficiency, and water chemistry.
    """
    __tablename__ = "boiler_steam_records"
    __table_args__ = (
        Index("ix_boiler_asset_dt", "asset_id", "record_datetime"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime = Column(DateTime(timezone=True), nullable=False)

    # Steam parameters
    steam_pressure_bar   = Column(Numeric(8, 3), nullable=True)
    steam_temp_c         = Column(Numeric(8, 2), nullable=True)
    steam_flow_kgh       = Column(Numeric(10, 3), nullable=True)   # kg/hour
    steam_quality_pct    = Column(Numeric(7, 3), nullable=True)    # dryness fraction %

    # Feed water
    feed_water_temp_c     = Column(Numeric(8, 2), nullable=True)
    feed_water_flow_lpm   = Column(Numeric(10, 3), nullable=True)
    feed_water_ph         = Column(Numeric(5, 2), nullable=True)
    feed_water_tds_ppm    = Column(Numeric(10, 2), nullable=True)

    # Blowdown
    blowdown_pct          = Column(Numeric(7, 3), nullable=True)
    blowdown_volume_litres = Column(Numeric(12, 3), nullable=True)

    # Fuel
    fuel_type         = Column(String(50), nullable=True)   # NATURAL_GAS, LPG, DIESEL, BIOMASS
    fuel_consumption  = Column(Numeric(14, 4), nullable=True)
    fuel_unit         = Column(String(20), nullable=True)   # m³, L, kg

    # Combustion / efficiency
    boiler_efficiency_pct = Column(Numeric(7, 3), nullable=True)
    flue_gas_temp_c       = Column(Numeric(8, 2), nullable=True)
    o2_pct                = Column(Numeric(7, 3), nullable=True)
    co2_pct               = Column(Numeric(7, 3), nullable=True)
    co_ppm                = Column(Numeric(10, 2), nullable=True)

    # Boiler water chemistry
    boiler_tds_ppm     = Column(Numeric(10, 2), nullable=True)
    boiler_ph          = Column(Numeric(5, 2), nullable=True)
    boiler_hardness_ppm = Column(Numeric(10, 2), nullable=True)
    conductivity_uscm  = Column(Numeric(10, 2), nullable=True)

    # Period totals (accumulated over the log period, vs instantaneous readings above)
    steam_generated_kg    = Column(Numeric(14, 3), nullable=True)  # total steam produced (kg)
    feedwater_consumed_m3 = Column(Numeric(14, 3), nullable=True)  # total feed water used (m³)
    condensate_returned_m3 = Column(Numeric(14, 3), nullable=True) # condensate return volume (m³)

    # Operational metrics
    boiler_load_pct       = Column(Numeric(7, 3), nullable=True)   # % of rated capacity
    burner_runtime_hours  = Column(Numeric(10, 3), nullable=True)  # firing time in period
    start_stop_count      = Column(Integer, nullable=True)         # number of starts
    period_hours          = Column(Numeric(8, 2), nullable=True)   # hours this record covers

    # Chemical treatment
    chemical_dosing_amount = Column(Numeric(10, 4), nullable=True)
    chemical_dosing_unit   = Column(String(20), nullable=True)     # kg, L, ppm

    # Downtime
    downtime_minutes = Column(Integer, nullable=True)
    downtime_reason  = Column(Text, nullable=True)

    # Flags
    maintenance_flag = Column(Boolean, nullable=False, default=False)

    # Allocation
    department = Column(String(100), nullable=True, index=True)

    # Operational context
    running_hours_cumulative = Column(Numeric(12, 2), nullable=True)
    status       = Column(SAEnum(BoilerStatus), nullable=False, default=BoilerStatus.RUNNING)
    source_method = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    is_anomaly    = Column(Boolean, nullable=False, default=False)
    anomaly_note  = Column(Text, nullable=True)
    shift_ref     = Column(String(50), nullable=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset      = relationship("UtilityAsset", back_populates="boiler_records")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class CompressorRecord(Base, TimestampMixin):
    """
    Operational log for a compressor / compressed air system.
    Tracks pressures, flow, specific energy, time breakdown, leak testing,
    dryer status, and night idle consumption.
    """
    __tablename__ = "compressor_records"
    __table_args__ = (
        Index("ix_compressor_asset_dt",   "asset_id", "record_datetime"),
        Index("ix_compressor_department", "department"),
        Index("ix_compressor_leak_test",  "leak_test_done"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime = Column(DateTime(timezone=True), nullable=False)

    # Period totals
    air_generated_nm3    = Column(Numeric(14, 3), nullable=True)   # Nm³ produced this period
    air_unit             = Column(String(20), nullable=True, default="Nm3")
    electricity_used_kwh = Column(Numeric(14, 4), nullable=True)   # kWh consumed this period

    # Time breakdown (hours)
    period_hours      = Column(Numeric(8, 2),  nullable=True)   # total period duration
    runtime_hours     = Column(Numeric(10, 3), nullable=True)   # compressor running hours
    load_time_hours   = Column(Numeric(10, 3), nullable=True)   # hours running under load
    unload_time_hours = Column(Numeric(10, 3), nullable=True)   # hours unloading
    idle_time_hours   = Column(Numeric(10, 3), nullable=True)   # hours idling (no demand)

    # Pressure (instantaneous / average readings)
    inlet_pressure_bar          = Column(Numeric(8, 3), nullable=True)
    discharge_pressure_bar      = Column(Numeric(8, 3), nullable=True)
    system_pressure_bar         = Column(Numeric(8, 3), nullable=True)   # header / plant
    receiver_tank_pressure_bar  = Column(Numeric(8, 3), nullable=True)   # air receiver tank
    line_pressure_bar           = Column(Numeric(8, 3), nullable=True)   # distribution line

    # Flow & power (instantaneous)
    flow_rate_m3h          = Column(Numeric(12, 3), nullable=True)   # m³/hour FAD
    power_kw               = Column(Numeric(10, 3), nullable=True)
    specific_energy_kwh_m3 = Column(Numeric(10, 4), nullable=True)   # kWh/Nm³ instantaneous

    # Load & cumulative runtime
    load_pct                  = Column(Numeric(7, 3),  nullable=True)
    running_hours_cumulative  = Column(Numeric(12, 2), nullable=True)
    loaded_hours_cumulative   = Column(Numeric(12, 2), nullable=True)

    # Air quality
    air_temperature_c    = Column(Numeric(8, 2), nullable=True)
    dew_point_c          = Column(Numeric(8, 2), nullable=True)
    pressure_dew_point_c = Column(Numeric(8, 2), nullable=True)

    # Dryer
    dryer_status      = Column(String(30),    nullable=True)   # ON, OFF, FAULT, BYPASS
    dryer_dew_point_c = Column(Numeric(8, 2), nullable=True)   # dryer outlet dew point °C

    # Oil & filter
    oil_pressure_bar = Column(Numeric(8, 3),  nullable=True)
    oil_temp_c       = Column(Numeric(8, 2),  nullable=True)
    filter_dp_bar    = Column(Numeric(8, 4),  nullable=True)   # filter differential pressure
    oil_level        = Column(String(20),     nullable=True)   # HIGH, NORMAL, LOW

    # Leak testing
    leak_test_done       = Column(Boolean,       nullable=False, default=False)
    leak_estimation_pct  = Column(Numeric(7, 3), nullable=True)   # estimated leak % of production
    leak_volume_nm3      = Column(Numeric(14, 3), nullable=True)  # estimated leak volume Nm³

    # Night / non-production consumption
    night_idle_kwh = Column(Numeric(14, 4), nullable=True)   # kWh during non-production
    night_idle_nm3 = Column(Numeric(14, 3), nullable=True)   # Nm³ during non-production

    # Operational
    start_stop_count   = Column(Integer,      nullable=True)
    downtime_minutes   = Column(Integer,      nullable=True)
    downtime_reason    = Column(Text,         nullable=True)
    maintenance_flag   = Column(Boolean,      nullable=False, default=False)
    department         = Column(String(100),  nullable=True, index=True)
    production_line    = Column(String(100),  nullable=True)

    status        = Column(SAEnum(CompressorStatus), nullable=False, default=CompressorStatus.RUNNING)
    source_method = Column(SAEnum(SourceMethod),     nullable=False, default=SourceMethod.MANUAL)
    is_anomaly    = Column(Boolean, nullable=False, default=False)
    anomaly_note  = Column(Text,    nullable=True)
    shift_ref     = Column(String(50), nullable=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset      = relationship("UtilityAsset", back_populates="compressor_records")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class SolarRecord(Base, TimestampMixin):
    """
    Operational log for a solar PV installation.
    Tracks irradiance, generation, self-consumption, grid export, and performance ratio.
    """
    __tablename__ = "solar_records"
    __table_args__ = (
        Index("ix_solar_asset_dt", "asset_id", "record_datetime"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime = Column(DateTime(timezone=True), nullable=False)

    # Irradiance / environmental
    irradiance_wm2   = Column(Numeric(10, 3), nullable=True)   # W/m²
    panel_temp_c     = Column(Numeric(8, 2), nullable=True)
    ambient_temp_c   = Column(Numeric(8, 2), nullable=True)

    # DC side
    dc_voltage_v  = Column(Numeric(10, 3), nullable=True)
    dc_current_a  = Column(Numeric(10, 3), nullable=True)
    dc_power_kw   = Column(Numeric(12, 4), nullable=True)

    # AC / inverter output
    ac_power_kw            = Column(Numeric(12, 4), nullable=True)
    energy_generated_kwh   = Column(Numeric(14, 4), nullable=True)
    grid_export_kwh        = Column(Numeric(14, 4), nullable=True)
    self_consumption_kwh   = Column(Numeric(14, 4), nullable=True)

    # Performance
    inverter_efficiency_pct = Column(Numeric(7, 3), nullable=True)
    pr_ratio                = Column(Numeric(7, 4), nullable=True)   # performance ratio
    availability_pct        = Column(Numeric(7, 3), nullable=True)
    capacity_factor_pct     = Column(Numeric(7, 3), nullable=True)

    source_method = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.IOT)
    is_anomaly    = Column(Boolean, nullable=False, default=False)
    anomaly_note  = Column(Text, nullable=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset      = relationship("UtilityAsset", back_populates="solar_records")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class TreatmentChemicalRecord(Base, TimestampMixin):
    """
    Dosing transaction for chemical water treatment.
    Covers all treatment areas: boiler, cooling, process water, WWTP, etc.
    Each record is a stock-movement event AND a quality-assurance log.
    """
    __tablename__ = "treatment_chemical_records"
    __table_args__ = (
        Index("ix_treatment_asset_dt",       "asset_id", "record_datetime"),
        Index("ix_treatment_chemical_id",    "chemical_id"),
        Index("ix_treatment_supplier_id",    "supplier_id"),
        Index("ix_treatment_date",           "date"),
        Index("ix_treatment_area",           "treatment_area"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime  = Column(DateTime(timezone=True), nullable=False)
    date             = Column(Date, nullable=True, index=True)    # calendar date for easy filtering
    treatment_type   = Column(SAEnum(TreatmentType), nullable=False, index=True)

    # Chemical master link
    chemical_id      = Column(UUID(as_uuid=True), ForeignKey("water_treatment_chemicals.id", ondelete="SET NULL"), nullable=True, index=True)
    chemical_code    = Column(String(50), nullable=True, index=True)   # denormalized
    chemical_name    = Column(String(255), nullable=False)             # denormalized for quick display
    chemical_category = Column(SAEnum(ChemicalCategory), nullable=True, index=True)

    # Treatment location
    treatment_area   = Column(String(255), nullable=True, index=True)  # e.g. Boiler Feed, Cooling Tower
    dosing_point     = Column(String(255), nullable=True)              # e.g. Pump skid A, Injection valve 3

    # Supplier & lot traceability
    supplier_id      = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_lot_no     = Column(String(100), nullable=True, index=True)

    # Cost
    unit_cost        = Column(Numeric(14, 6), nullable=True)

    # Units of measure
    stock_uom        = Column(String(30), nullable=True)   # UOM for stock quantities (kg, L, drum)
    dosing_uom       = Column(String(30), nullable=True)   # UOM for dosing quantities (ml, g, ppm)

    # Stock movement (each record is a stock snapshot)
    opening_stock    = Column(Numeric(14, 4), nullable=True)
    received_qty     = Column(Numeric(14, 4), nullable=True, default=0)
    consumed_qty     = Column(Numeric(14, 4), nullable=True, default=0)
    closing_stock    = Column(Numeric(14, 4), nullable=True)   # computed or manually entered

    # Dosing quantities (legacy + extended)
    quantity_dosed   = Column(Numeric(14, 4), nullable=False)
    unit             = Column(String(20), nullable=False)       # dosing unit (backward compat)
    target_dose_ppm  = Column(Numeric(10, 4), nullable=True)
    actual_dose_ppm  = Column(Numeric(10, 4), nullable=True)
    water_volume_m3  = Column(Numeric(14, 3), nullable=True)

    # Dosing mode
    manual_or_auto_dose = Column(SAEnum(DosingMode), nullable=True, default=DosingMode.MANUAL)

    # Related meter / device (for KPI linkage)
    related_meter_id = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="SET NULL"), nullable=True)

    # Materials master (for inventory integration)
    material_id      = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)

    # KPI denominators
    water_treated_m3    = Column(Numeric(14, 3), nullable=True)   # m3 water treated this period
    steam_produced_ton  = Column(Numeric(14, 3), nullable=True)   # ton steam produced this period

    # Water quality
    feed_ph               = Column(Numeric(5, 2), nullable=True)
    product_ph            = Column(Numeric(5, 2), nullable=True)
    feed_turbidity_ntu    = Column(Numeric(10, 3), nullable=True)
    product_turbidity_ntu = Column(Numeric(10, 3), nullable=True)
    residual_chlorine_ppm = Column(Numeric(10, 3), nullable=True)
    tds_feed_ppm          = Column(Numeric(10, 2), nullable=True)
    tds_product_ppm       = Column(Numeric(10, 2), nullable=True)

    # Anomaly flags
    source_method  = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    is_anomaly     = Column(Boolean, nullable=False, default=False)
    anomaly_note   = Column(Text, nullable=True)
    overdose_flag  = Column(Boolean, nullable=False, default=False)
    underdose_flag = Column(Boolean, nullable=False, default=False)
    shift_ref      = Column(String(50), nullable=True)

    # Inventory integration audit
    inventory_synced   = Column(Boolean, nullable=False, default=False)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset         = relationship("UtilityAsset", back_populates="treatment_records")
    chemical      = relationship("WaterTreatmentChemical", back_populates="treatment_records")
    material      = relationship("Material")
    supplier      = relationship("Supplier")
    related_meter = relationship("UtilityDevice", foreign_keys=[related_meter_id])
    entered_by    = relationship("User", foreign_keys=[entered_by_id])


class WastewaterRecord(Base, TimestampMixin):
    """
    Operational record for a biological or physico-chemical wastewater treatment plant.
    Tracks influent/effluent quality, process parameters, sludge, and compliance.
    """
    __tablename__ = "wastewater_records"
    __table_args__ = (
        Index("ix_wastewater_asset_dt", "asset_id", "record_datetime"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_no = Column(String(50), nullable=False, unique=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    record_datetime = Column(DateTime(timezone=True), nullable=False)
    process_stage   = Column(SAEnum(WastewaterProcess), nullable=False, default=WastewaterProcess.SECONDARY, index=True)

    # Flow
    influent_flow_m3h = Column(Numeric(12, 3), nullable=True)
    effluent_flow_m3h = Column(Numeric(12, 3), nullable=True)

    # Organic load — COD
    influent_cod_mgl  = Column(Numeric(10, 3), nullable=True)
    effluent_cod_mgl  = Column(Numeric(10, 3), nullable=True)

    # Organic load — BOD
    influent_bod_mgl  = Column(Numeric(10, 3), nullable=True)
    effluent_bod_mgl  = Column(Numeric(10, 3), nullable=True)

    # Solids — TSS
    influent_tss_mgl  = Column(Numeric(10, 3), nullable=True)
    effluent_tss_mgl  = Column(Numeric(10, 3), nullable=True)

    # pH
    influent_ph       = Column(Numeric(5, 2), nullable=True)
    effluent_ph       = Column(Numeric(5, 2), nullable=True)

    # Biological process parameters
    do_mgl            = Column(Numeric(8, 3), nullable=True)   # Dissolved Oxygen in aeration tank
    mlss_mgl          = Column(Numeric(10, 3), nullable=True)  # Mixed Liquor Suspended Solids
    mlvss_mgl         = Column(Numeric(10, 3), nullable=True)  # Mixed Liquor Volatile SS
    svi               = Column(Numeric(10, 3), nullable=True)  # Sludge Volume Index
    srt_days          = Column(Numeric(8, 2), nullable=True)   # Sludge Retention Time

    # Sludge
    sludge_produced_kg     = Column(Numeric(12, 3), nullable=True)
    sludge_dewatered_pct   = Column(Numeric(7, 3), nullable=True)

    # Energy
    power_consumed_kwh     = Column(Numeric(14, 4), nullable=True)
    aeration_runtime_hours = Column(Numeric(10, 2), nullable=True)

    compliance_status = Column(SAEnum(ComplianceStatus), nullable=False, default=ComplianceStatus.COMPLIANT, index=True)
    source_method     = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.MANUAL)
    is_anomaly        = Column(Boolean, nullable=False, default=False)
    anomaly_note      = Column(Text, nullable=True)
    shift_ref         = Column(String(50), nullable=True)

    entered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)

    asset      = relationship("UtilityAsset", back_populates="wastewater_records")
    entered_by = relationship("User", foreign_keys=[entered_by_id])


class UtilityBill(Base, TimestampMixin):
    """
    Utility bill received from a supplier / utility company.
    Supports multi-utility (electricity, water, gas, etc.).
    Linked to a tariff for rate validation against actual.
    """
    __tablename__ = "utility_bills"
    __table_args__ = (
        Index("ix_utility_bills_type_period", "utility_type", "billing_period_from"),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_no      = Column(String(50), nullable=False, unique=True, index=True)
    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)

    supplier_id    = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    tariff_id      = Column(UUID(as_uuid=True), ForeignKey("utility_tariffs.id", ondelete="SET NULL"), nullable=True)
    bill_reference = Column(String(100), nullable=True)   # supplier's own invoice number

    billing_period_from = Column(Date, nullable=False)
    billing_period_to   = Column(Date, nullable=False)
    invoice_date        = Column(Date, nullable=True)
    due_date            = Column(Date, nullable=True, index=True)

    # Consumption
    consumption_quantity = Column(Numeric(18, 4), nullable=True)
    consumption_unit     = Column(String(30), nullable=True)

    # Charges
    base_charge    = Column(Numeric(14, 4), nullable=True)
    energy_charge  = Column(Numeric(14, 4), nullable=True)
    demand_charge  = Column(Numeric(14, 4), nullable=True)
    tax_amount     = Column(Numeric(14, 4), nullable=True)
    total_amount   = Column(Numeric(16, 4), nullable=False)
    currency_code  = Column(String(10), nullable=False, default="USD")

    status       = Column(SAEnum(BillStatus), nullable=False, default=BillStatus.RECEIVED, index=True)
    payment_date = Column(Date, nullable=True)

    notes         = Column(Text, nullable=True)
    verified_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier     = relationship("Supplier")
    tariff       = relationship("UtilityTariff", back_populates="bills")
    verified_by  = relationship("User", foreign_keys=[verified_by_id])
    created_by   = relationship("User", foreign_keys=[created_by_id])
    allocations  = relationship("UtilityCostAllocation", back_populates="bill")


class UtilityCostAllocation(Base, TimestampMixin):
    """
    Allocates utility cost to a cost object: department, line, product, batch, building area.
    Supports metered, proportional, fixed, and calculated allocation methods.
    Enables answers to: cost per ton of product, cost per line, cost per department.
    """
    __tablename__ = "utility_cost_allocations"
    __table_args__ = (
        Index("ix_util_cost_alloc_type_date", "utility_type", "allocation_date"),
        Index("ix_util_cost_alloc_dept", "department", "allocation_date"),
        Index("ix_util_cost_alloc_prod_order", "production_order_id"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_no   = Column(String(50), nullable=False, unique=True, index=True)
    utility_type    = Column(SAEnum(UtilityType), nullable=False, index=True)
    allocation_date = Column(Date, nullable=False, index=True)
    period_start    = Column(Date, nullable=True)
    period_end      = Column(Date, nullable=True)

    allocation_method = Column(SAEnum(AllocationMethod), nullable=False, default=AllocationMethod.METERED)

    # Cost object dimensions
    department      = Column(String(100), nullable=True, index=True)
    production_line = Column(String(100), nullable=True, index=True)
    building_area   = Column(String(100), nullable=True)
    machine_ref     = Column(String(100), nullable=True)

    # Production linkage
    production_order_id = Column(UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_no            = Column(String(100), nullable=True, index=True)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Allocation basis
    allocated_quantity = Column(Numeric(18, 4), nullable=True)
    quantity_unit      = Column(String(30), nullable=True)
    production_volume_kg = Column(Numeric(18, 3), nullable=True)  # denominator for per-ton calc

    # Costs
    total_cost       = Column(Numeric(16, 4), nullable=False)
    allocated_cost   = Column(Numeric(16, 4), nullable=False)
    currency_code    = Column(String(10), nullable=False, default="USD")
    cost_per_unit    = Column(Numeric(14, 6), nullable=True)    # cost / quantity_unit
    cost_per_ton     = Column(Numeric(14, 6), nullable=True)    # cost / tonne of product

    # Source
    bill_id       = Column(UUID(as_uuid=True), ForeignKey("utility_bills.id", ondelete="SET NULL"), nullable=True)
    source_method = Column(SAEnum(SourceMethod), nullable=False, default=SourceMethod.CALCULATED)

    notes         = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    production_order = relationship("ProductionOrder")
    product          = relationship("Product")
    bill             = relationship("UtilityBill", back_populates="allocations")
    created_by       = relationship("User", foreign_keys=[created_by_id])


class UtilityAlarmEvent(Base, TimestampMixin):
    """
    A triggered alarm event produced when a UtilityAlarmRule condition is met.
    Tracks acknowledgement and resolution lifecycle.
    """
    __tablename__ = "utility_alarm_events"
    __table_args__ = (
        Index("ix_alarm_events_status", "status"),
        Index("ix_alarm_events_rule_dt", "rule_id", "triggered_at"),
    )

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_no = Column(String(50), nullable=False, unique=True, index=True)

    rule_id   = Column(UUID(as_uuid=True), ForeignKey("utility_alarm_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id  = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True, index=True)

    triggered_at     = Column(DateTime(timezone=True), nullable=False, index=True)
    acknowledged_at  = Column(DateTime(timezone=True), nullable=True)
    resolved_at      = Column(DateTime(timezone=True), nullable=True)

    status   = Column(SAEnum(AlarmStatus), nullable=False, default=AlarmStatus.ACTIVE, index=True)
    severity = Column(SAEnum(AlarmSeverity), nullable=False, default=AlarmSeverity.WARNING)

    triggered_value  = Column(Numeric(18, 4), nullable=True)
    threshold_value  = Column(Numeric(18, 4), nullable=True)
    threshold_unit   = Column(String(30), nullable=True)
    parameter        = Column(String(100), nullable=True)

    root_cause         = Column(Text, nullable=True)
    corrective_action  = Column(Text, nullable=True)

    acknowledged_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes              = Column(Text, nullable=True)

    rule             = relationship("UtilityAlarmRule", back_populates="events")
    device           = relationship("UtilityDevice", back_populates="alarm_events")
    asset            = relationship("UtilityAsset", back_populates="alarm_events")
    acknowledged_by  = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by      = relationship("User", foreign_keys=[resolved_by_id])


class MachineUtilityMapping(Base, TimestampMixin):
    """
    Maps a production machine to the utility device(s) and assets that serve it.
    Supports shared-meter allocation (allocation_pct) and records nameplate consumption.
    Used to attribute utility transactions to machine-level and line-level cost objects.
    """
    __tablename__ = "machine_utility_mappings"
    __table_args__ = (
        UniqueConstraint("machine_ref", "utility_type", "device_id", name="uq_machine_utility_device"),
        Index("ix_machine_util_map_dept_line", "department", "production_line"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_ref     = Column(String(100), nullable=False, index=True)   # machine code / tag
    machine_name    = Column(String(255), nullable=False)
    department      = Column(String(100), nullable=True, index=True)
    production_line = Column(String(100), nullable=True, index=True)
    building_area   = Column(String(100), nullable=True)

    utility_type = Column(SAEnum(UtilityType), nullable=False, index=True)
    device_id    = Column(UUID(as_uuid=True), ForeignKey("utility_devices.id", ondelete="SET NULL"), nullable=True)
    asset_id     = Column(UUID(as_uuid=True), ForeignKey("utility_assets.id", ondelete="SET NULL"), nullable=True)

    # If the machine shares a meter with others, this is its allocation share
    allocation_pct = Column(Numeric(7, 4), nullable=True)    # e.g. 35.5 → 35.5%

    # Nameplate / design consumption
    rated_consumption = Column(Numeric(14, 4), nullable=True)
    rated_unit        = Column(String(30), nullable=True)    # e.g. kW, m³/h, kg/h

    is_active = Column(Boolean, nullable=False, default=True)
    notes     = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    device     = relationship("UtilityDevice", back_populates="machine_mappings")
    asset      = relationship("UtilityAsset")
    created_by = relationship("User", foreign_keys=[created_by_id])
