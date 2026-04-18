"""
Utilities Module — Seed / Demo Data
====================================
Generates realistic FMCG factory utility data for development and walkthroughs.

Usage (from the backend directory):
    python -m app.db.seed_utilities            # writes to DB configured in .env
    python -m app.db.seed_utilities --reset    # deletes existing utility seed rows first

Scenarios covered
─────────────────
• Main incoming power meter (MEM-001)
• Compressor power meter (CPR-MTR-001)
• Boiler gas meter (BLR-GAS-001)
• Raw water inlet meter (RWM-001) + soft water outlet (SWM-001)
• Inverter group solar (SOLAR-INV-001)
• Aeration blower (WWTP-BLR-001)
• Boiler chemical dosing records — normal range
• High night compressor consumption anomaly (day -5)
• Soft water hardness deviation event (day -3)
• Wastewater pH compliance issue (day -2)
• Alarm rules covering all major thresholds
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings  # provides DATABASE_URL

# ── Models ─────────────────────────────────────────────────────────────────────

from app.models.utility_management import (
    UtilityAssetCategory, UtilityAsset, UtilityDevice, UtilityTariff,
    UtilityTransaction, UtilityReading, UtilityBill, UtilityCostAllocation,
    BoilerSteamRecord, SoftWaterRecord, CompressorRecord, SolarRecord,
    TreatmentChemicalRecord, WastewaterRecord, WaterTreatmentChemical,
    UtilityAlarmRule, UtilityAlarmEvent,
    # Enums
    UtilityType, SourceMethod, DataQuality, UtilityAssetStatus, LifecycleStatus,
    CriticalityLevel, DeviceType, ReadingType, ReadingSource, ReadingFrequency,
    TariffType, AlarmSeverity, AlarmStatus, AlarmOperator,
    AllocationMethod, TargetType, BillStatus, SoftenerStatus, BoilerStatus,
    CompressorStatus, TreatmentType, ChemicalCategory, DosingMode,
    WastewaterProcess, ComplianceStatus,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

TODAY = date.today()
NOW = datetime.utcnow()
rng = random.Random(42)  # deterministic

def _d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)

def _dt(days_ago: int, hour: int = 8, minute: int = 0) -> datetime:
    return datetime.combine(_d(days_ago), datetime.min.time()).replace(hour=hour, minute=minute)

def D(v) -> Decimal:
    return Decimal(str(v))

def _uid() -> uuid.UUID:
    return uuid.uuid4()

def _n(base, variation_pct=10) -> float:
    """Normally distributed value around base with given % variation."""
    lo = base * (1 - variation_pct / 100)
    hi = base * (1 + variation_pct / 100)
    return round(rng.uniform(lo, hi), 3)

# ── IDs (deterministic so repeated runs stay consistent) ──────────────────────

CAT_IDS = {
    "boiler":     uuid.UUID("11111111-0001-0001-0001-000000000001"),
    "compressor": uuid.UUID("11111111-0001-0001-0001-000000000002"),
    "softener":   uuid.UUID("11111111-0001-0001-0001-000000000003"),
    "solar":      uuid.UUID("11111111-0001-0001-0001-000000000004"),
    "wwtp":       uuid.UUID("11111111-0001-0001-0001-000000000005"),
    "elec_meter": uuid.UUID("11111111-0001-0001-0001-000000000006"),
    "water_meter":uuid.UUID("11111111-0001-0001-0001-000000000007"),
}

ASSET_IDS = {
    "boiler1":    uuid.UUID("22222222-0001-0001-0001-000000000001"),
    "boiler2":    uuid.UUID("22222222-0001-0001-0001-000000000002"),
    "comp1":      uuid.UUID("22222222-0001-0001-0001-000000000003"),
    "comp2":      uuid.UUID("22222222-0001-0001-0001-000000000004"),
    "softener1":  uuid.UUID("22222222-0001-0001-0001-000000000005"),
    "solar1":     uuid.UUID("22222222-0001-0001-0001-000000000006"),
    "wwtp1":      uuid.UUID("22222222-0001-0001-0001-000000000007"),
    "main_elec":  uuid.UUID("22222222-0001-0001-0001-000000000008"),
    "raw_water":  uuid.UUID("22222222-0001-0001-0001-000000000009"),
}

DEV_IDS = {
    "main_meter":  uuid.UUID("33333333-0001-0001-0001-000000000001"),
    "comp_meter":  uuid.UUID("33333333-0001-0001-0001-000000000002"),
    "blr_gas":     uuid.UUID("33333333-0001-0001-0001-000000000003"),
    "raw_water":   uuid.UUID("33333333-0001-0001-0001-000000000004"),
    "soft_water":  uuid.UUID("33333333-0001-0001-0001-000000000005"),
    "solar_inv":   uuid.UUID("33333333-0001-0001-0001-000000000006"),
    "wwtp_sensor": uuid.UUID("33333333-0001-0001-0001-000000000007"),
}

TARIFF_IDS = {
    "elec_flat":   uuid.UUID("44444444-0001-0001-0001-000000000001"),
    "water_flat":  uuid.UUID("44444444-0001-0001-0001-000000000002"),
    "gas_flat":    uuid.UUID("44444444-0001-0001-0001-000000000003"),
}

CHEM_IDS = {
    "boiler_treat":  uuid.UUID("55555555-0001-0001-0001-000000000001"),
    "oxy_scavenger": uuid.UUID("55555555-0001-0001-0001-000000000002"),
    "antiscalant":   uuid.UUID("55555555-0001-0001-0001-000000000003"),
    "coagulant":     uuid.UUID("55555555-0001-0001-0001-000000000004"),
    "chlorine":      uuid.UUID("55555555-0001-0001-0001-000000000005"),
}

RULE_IDS = {
    "high_elec_night": uuid.UUID("66666666-0001-0001-0001-000000000001"),
    "high_leak_pct":   uuid.UUID("66666666-0001-0001-0001-000000000002"),
    "low_boiler_eff":  uuid.UUID("66666666-0001-0001-0001-000000000003"),
    "soft_hardness":   uuid.UUID("66666666-0001-0001-0001-000000000004"),
    "wwtp_ph_low":     uuid.UUID("66666666-0001-0001-0001-000000000005"),
    "solar_pr_low":    uuid.UUID("66666666-0001-0001-0001-000000000006"),
    "high_delta_elec": uuid.UUID("66666666-0001-0001-0001-000000000007"),
}


# ── Asset Categories ───────────────────────────────────────────────────────────

CATEGORIES = [
    UtilityAssetCategory(
        id=CAT_IDS["boiler"], code="BOILER", name="Steam Boiler",
        description="Fire-tube and water-tube steam boilers",
        utility_type=UtilityType.STEAM, default_unit="kg/h", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["compressor"], code="COMPRESSOR", name="Air Compressor",
        description="Rotary screw and reciprocating air compressors",
        utility_type=UtilityType.COMPRESSED_AIR, default_unit="Nm³/h", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["softener"], code="SOFTENER", name="Water Softener / Ion Exchanger",
        description="Cation exchange resin softeners for boiler feed and process water",
        utility_type=UtilityType.SOFT_WATER, default_unit="m³/h", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["solar"], code="SOLAR_PV", name="Solar PV Inverter Group",
        description="Roof-mounted photovoltaic arrays with string inverters",
        utility_type=UtilityType.SOLAR, default_unit="kWh", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["wwtp"], code="WWTP", name="Wastewater Treatment Plant",
        description="Biological and physical-chemical effluent treatment systems",
        utility_type=UtilityType.WASTEWATER, default_unit="m³/day", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["elec_meter"], code="ELEC_METER", name="Electricity Meter Panel",
        description="Main and sub-metering panels for electricity",
        utility_type=UtilityType.ELECTRICITY, default_unit="kWh", is_active=True,
    ),
    UtilityAssetCategory(
        id=CAT_IDS["water_meter"], code="WATER_METER", name="Water Meter Station",
        description="Ultrasonic and turbine flow meters for water",
        utility_type=UtilityType.WATER, default_unit="m³", is_active=True,
    ),
]


# ── Assets ─────────────────────────────────────────────────────────────────────

ASSETS = [
    UtilityAsset(
        id=ASSET_IDS["boiler1"], asset_no="BLR-001",
        name="Boiler #1 — 5-ton/h Fire Tube",
        category_id=CAT_IDS["boiler"], utility_type=UtilityType.STEAM,
        location="Boiler Room, Building B", department="Utilities",
        manufacturer="Thermax", model="FT-5000",
        rated_capacity=D("5000"), capacity_unit="kg/h",
        rated_power=D("250"), rated_power_unit="kW",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.CRITICAL,
        install_date=date(2019, 3, 15),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["boiler2"], asset_no="BLR-002",
        name="Boiler #2 — 3-ton/h Fire Tube (Backup)",
        category_id=CAT_IDS["boiler"], utility_type=UtilityType.STEAM,
        location="Boiler Room, Building B", department="Utilities",
        manufacturer="Thermax", model="FT-3000",
        rated_capacity=D("3000"), capacity_unit="kg/h",
        rated_power=D("160"), rated_power_unit="kW",
        status=UtilityAssetStatus.IDLE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.HIGH,
        install_date=date(2021, 6, 1),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["comp1"], asset_no="CPR-001",
        name="Compressor #1 — 250 Nm³/h Rotary Screw",
        category_id=CAT_IDS["compressor"], utility_type=UtilityType.COMPRESSED_AIR,
        location="Compressor Room, Building A", department="Utilities",
        manufacturer="Atlas Copco", model="GA-55",
        rated_capacity=D("250"), capacity_unit="Nm³/h",
        rated_power=D("55"), rated_power_unit="kW",
        pressure_capacity=D("8.5"),
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.CRITICAL,
        install_date=date(2020, 1, 10),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["comp2"], asset_no="CPR-002",
        name="Compressor #2 — 150 Nm³/h (Backup)",
        category_id=CAT_IDS["compressor"], utility_type=UtilityType.COMPRESSED_AIR,
        location="Compressor Room, Building A", department="Utilities",
        manufacturer="Atlas Copco", model="GA-37",
        rated_capacity=D("150"), capacity_unit="Nm³/h",
        rated_power=D("37"), rated_power_unit="kW",
        pressure_capacity=D("8.0"),
        status=UtilityAssetStatus.IDLE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.MEDIUM,
        install_date=date(2022, 3, 20),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["softener1"], asset_no="SFT-001",
        name="Water Softener Unit #1 — 20 m³/h",
        category_id=CAT_IDS["softener"], utility_type=UtilityType.SOFT_WATER,
        location="Water Treatment Room, Building B", department="Utilities",
        manufacturer="Veolia", model="IONEX-20",
        rated_capacity=D("20"), capacity_unit="m³/h",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.HIGH,
        install_date=date(2020, 8, 5),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["solar1"], asset_no="SOLAR-001",
        name="Solar PV Array — Roof Block A (200 kWp)",
        category_id=CAT_IDS["solar"], utility_type=UtilityType.SOLAR,
        location="Roof, Building A", department="Utilities",
        manufacturer="Fronius", model="Symo 200",
        rated_capacity=D("200"), capacity_unit="kWp",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.MEDIUM,
        install_date=date(2021, 11, 20),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["wwtp1"], asset_no="WWTP-001",
        name="Activated Sludge WWTP — 500 m³/day",
        category_id=CAT_IDS["wwtp"], utility_type=UtilityType.WASTEWATER,
        location="Effluent Treatment Plant, Rear Yard", department="Environment",
        manufacturer="Enviro Tech", model="ASP-500",
        rated_capacity=D("500"), capacity_unit="m³/day",
        rated_power=D("45"), rated_power_unit="kW",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.CRITICAL,
        install_date=date(2018, 4, 10),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["main_elec"], asset_no="MEM-001",
        name="Main Incoming Power Panel",
        category_id=CAT_IDS["elec_meter"], utility_type=UtilityType.ELECTRICITY,
        location="Main Sub-station", department="Utilities",
        rated_capacity=D("2000"), capacity_unit="kVA",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.CRITICAL,
        install_date=date(2015, 1, 1),
        is_active=True,
    ),
    UtilityAsset(
        id=ASSET_IDS["raw_water"], asset_no="RWM-001",
        name="Raw Water Inlet Meter",
        category_id=CAT_IDS["water_meter"], utility_type=UtilityType.WATER,
        location="Main Gate Water Supply", department="Utilities",
        status=UtilityAssetStatus.ACTIVE, lifecycle_status=LifecycleStatus.IN_USE,
        criticality_level=CriticalityLevel.HIGH,
        install_date=date(2018, 1, 1),
        is_active=True,
    ),
]


# ── Devices / Meters ───────────────────────────────────────────────────────────

DEVICES = [
    UtilityDevice(
        id=DEV_IDS["main_meter"], device_code="MEM-001-M",
        name="Main Electricity Meter", utility_type=UtilityType.ELECTRICITY,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["main_elec"],
        manufacturer="Schneider", model="PM8000",
        unit_of_measure="kWh", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.SCADA,
        reading_frequency=ReadingFrequency.EVERY_15MIN,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["comp_meter"], device_code="CPR-MTR-001",
        name="Compressor #1 Power Sub-Meter", utility_type=UtilityType.ELECTRICITY,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["comp1"],
        manufacturer="Schneider", model="EM6400",
        unit_of_measure="kWh", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.MANUAL,
        reading_frequency=ReadingFrequency.DAILY,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["blr_gas"], device_code="BLR-GAS-001",
        name="Boiler Gas Meter #1", utility_type=UtilityType.NATURAL_GAS,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["boiler1"],
        manufacturer="Elster", model="G65",
        unit_of_measure="Nm3", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.MANUAL,
        reading_frequency=ReadingFrequency.DAILY,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["raw_water"], device_code="RWM-001-M",
        name="Raw Water Inlet Flow Meter", utility_type=UtilityType.WATER,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["raw_water"],
        manufacturer="Endress+Hauser", model="Promag W 400",
        unit_of_measure="m3", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.IOT,
        reading_frequency=ReadingFrequency.HOURLY,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["soft_water"], device_code="SWM-001-M",
        name="Soft Water Outlet Flow Meter", utility_type=UtilityType.SOFT_WATER,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["softener1"],
        manufacturer="Endress+Hauser", model="Promag W 300",
        unit_of_measure="m3", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.IOT,
        reading_frequency=ReadingFrequency.HOURLY,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["solar_inv"], device_code="SOLAR-INV-001",
        name="Solar Inverter Group - Block A", utility_type=UtilityType.SOLAR,
        device_type=DeviceType.METER, asset_id=ASSET_IDS["solar1"],
        manufacturer="Fronius", model="Symo 200 Logger",
        unit_of_measure="kWh", reading_type=ReadingType.CUMULATIVE,
        reading_source=ReadingSource.API,
        reading_frequency=ReadingFrequency.EVERY_15MIN,
        is_active=True,
    ),
    UtilityDevice(
        id=DEV_IDS["wwtp_sensor"], device_code="WWTP-PH-001",
        name="WWTP Effluent pH Sensor", utility_type=UtilityType.WASTEWATER,
        device_type=DeviceType.SENSOR, asset_id=ASSET_IDS["wwtp1"],
        manufacturer="Hach", model="PHD sc",
        unit_of_measure="pH", reading_type=ReadingType.INSTANTANEOUS,
        reading_source=ReadingSource.IOT,
        reading_frequency=ReadingFrequency.EVERY_15MIN,
        is_active=True,
    ),
]


# ── Tariffs ────────────────────────────────────────────────────────────────────

TARIFFS = [
    UtilityTariff(
        id=TARIFF_IDS["elec_flat"], tariff_code="ELEC-FLAT-2024",
        name="Electricity Flat Rate 2024",
        utility_type=UtilityType.ELECTRICITY, tariff_type=TariffType.FLAT,
        unit="kWh", base_rate=D("0.12"), currency_code="USD",
        effective_from=date(2024, 1, 1),
        is_active=True, notes="Standard industrial tariff",
    ),
    UtilityTariff(
        id=TARIFF_IDS["water_flat"], tariff_code="WATER-FLAT-2024",
        name="Municipal Water Flat Rate 2024",
        utility_type=UtilityType.WATER, tariff_type=TariffType.FLAT,
        unit="m³", base_rate=D("0.85"), currency_code="USD",
        effective_from=date(2024, 1, 1),
        is_active=True,
    ),
    UtilityTariff(
        id=TARIFF_IDS["gas_flat"], tariff_code="GAS-FLAT-2024",
        name="Natural Gas Industrial Rate 2024",
        utility_type=UtilityType.NATURAL_GAS, tariff_type=TariffType.FLAT,
        unit="Nm³", base_rate=D("0.55"), currency_code="USD",
        effective_from=date(2024, 1, 1),
        is_active=True,
    ),
]


# ── Treatment Chemicals ────────────────────────────────────────────────────────

CHEMICALS = [
    WaterTreatmentChemical(
        id=CHEM_IDS["boiler_treat"], chemical_code="CHEM-BT-001",
        chemical_name="Boiler Treatment Compound A",
        chemical_category=ChemicalCategory.BOILER_TREATMENT,
        description="Multi-functional boiler treatment for scale and corrosion",
        stock_uom="kg", dosing_uom="ml",
        unit_cost=D("12.50"),
        target_dose_min=D("80"), target_dose_max=D("150"),
        low_stock_threshold=D("20"), is_active=True,
    ),
    WaterTreatmentChemical(
        id=CHEM_IDS["oxy_scavenger"], chemical_code="CHEM-OX-001",
        chemical_name="Oxygen Scavenger (DEHA)",
        chemical_category=ChemicalCategory.OXYGEN_SCAVENGER,
        description="Diethylhydroxylamine for boiler feedwater deoxygenation",
        stock_uom="L", dosing_uom="ml",
        unit_cost=D("18.00"),
        target_dose_min=D("5"), target_dose_max=D("30"),
        low_stock_threshold=D("10"), is_active=True,
    ),
    WaterTreatmentChemical(
        id=CHEM_IDS["antiscalant"], chemical_code="CHEM-AS-001",
        chemical_name="Antiscalant — RO/Soft Water",
        chemical_category=ChemicalCategory.ANTISCALANT,
        description="Phosphonate-based antiscalant for membrane and ion exchange systems",
        stock_uom="L", dosing_uom="ml",
        unit_cost=D("9.80"),
        target_dose_min=D("3"), target_dose_max=D("15"),
        low_stock_threshold=D("15"), is_active=True,
    ),
    WaterTreatmentChemical(
        id=CHEM_IDS["coagulant"], chemical_code="CHEM-CG-001",
        chemical_name="Aluminium Sulphate Coagulant",
        chemical_category=ChemicalCategory.COAGULANT,
        description="Liquid alum for WWTP primary coagulation",
        stock_uom="L", dosing_uom="L",
        unit_cost=D("1.20"),
        target_dose_min=D("0.5"), target_dose_max=D("3.0"),
        low_stock_threshold=D("50"), is_active=True,
    ),
    WaterTreatmentChemical(
        id=CHEM_IDS["chlorine"], chemical_code="CHEM-CL-001",
        chemical_name="Sodium Hypochlorite (12%)",
        chemical_category=ChemicalCategory.CHLORINE,
        description="Liquid chlorine for disinfection of process water and WWTP effluent",
        stock_uom="L", dosing_uom="ml",
        unit_cost=D("0.45"),
        target_dose_min=D("50"), target_dose_max=D("200"),
        low_stock_threshold=D("100"), is_active=True,
    ),
]


# ── Alarm Rules ────────────────────────────────────────────────────────────────

ALARM_RULES = [
    UtilityAlarmRule(
        id=RULE_IDS["high_elec_night"], rule_code="ALM-ELEC-001",
        name="High Night-time Electricity Consumption",
        utility_type=UtilityType.ELECTRICITY,
        parameter="night_kwh", operator=AlarmOperator.GT,
        threshold_value=D("500"),
        severity=AlarmSeverity.WARNING,
        device_id=DEV_IDS["main_meter"],
        description="Alert when nighttime (22:00–06:00) consumption exceeds 500 kWh",
        is_active=True, cooldown_minutes=60,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["high_leak_pct"], rule_code="ALM-AIR-001",
        name="High Compressed Air Leak Estimate",
        utility_type=UtilityType.COMPRESSED_AIR,
        parameter="leak_estimation_pct", operator=AlarmOperator.GT,
        threshold_value=D("15"),
        severity=AlarmSeverity.ALERT,
        asset_id=ASSET_IDS["comp1"],
        description="Alert when leak fraction exceeds 15% of generated air",
        is_active=True, cooldown_minutes=120,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["low_boiler_eff"], rule_code="ALM-BOIL-001",
        name="Low Boiler Efficiency",
        utility_type=UtilityType.STEAM,
        parameter="boiler_efficiency_pct", operator=AlarmOperator.LT,
        threshold_value=D("72"),
        severity=AlarmSeverity.ALERT,
        asset_id=ASSET_IDS["boiler1"],
        description="Alert when boiler efficiency drops below 72%",
        is_active=True, cooldown_minutes=240,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["soft_hardness"], rule_code="ALM-SOFT-001",
        name="Soft Water Product Hardness Deviation",
        utility_type=UtilityType.SOFT_WATER,
        parameter="product_water_hardness_ppm", operator=AlarmOperator.GT,
        threshold_value=D("5"),
        severity=AlarmSeverity.CRITICAL,
        asset_id=ASSET_IDS["softener1"],
        description="Critical alarm: product water hardness must stay below 5 ppm",
        is_active=True, cooldown_minutes=30,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["wwtp_ph_low"], rule_code="ALM-WWT-001",
        name="WWTP Effluent pH Out of Range (Low)",
        utility_type=UtilityType.WASTEWATER,
        parameter="effluent_ph", operator=AlarmOperator.LT,
        threshold_value=D("6.5"),
        severity=AlarmSeverity.CRITICAL,
        device_id=DEV_IDS["wwtp_sensor"],
        description="Effluent pH must stay 6.5–8.5 per discharge permit DOE-2024-01",
        is_active=True, cooldown_minutes=15,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["solar_pr_low"], rule_code="ALM-SOLAR-001",
        name="Low Solar Performance Ratio",
        utility_type=UtilityType.SOLAR,
        parameter="pr_ratio", operator=AlarmOperator.LT,
        threshold_value=D("0.70"),
        severity=AlarmSeverity.WARNING,
        asset_id=ASSET_IDS["solar1"],
        description="Potential soiling or inverter fault when PR < 0.70",
        is_active=True, cooldown_minutes=480,
    ),
    UtilityAlarmRule(
        id=RULE_IDS["high_delta_elec"], rule_code="ALM-ELEC-002",
        name="Abnormal Day-on-Day Electricity Spike",
        utility_type=UtilityType.ELECTRICITY,
        parameter="daily_kwh", operator=AlarmOperator.DELTA_PCT,
        threshold_value=D("25"),
        severity=AlarmSeverity.WARNING,
        device_id=DEV_IDS["main_meter"],
        description="Alert when daily consumption increases more than 25% vs prior day",
        is_active=True, cooldown_minutes=480,
    ),
]


# ── Transaction / reading generators ──────────────────────────────────────────

def _electricity_transactions(days: int = 35) -> list[UtilityTransaction]:
    rows = []
    for d in range(days, 0, -1):
        kwh = _n(3800, 12)  # ~3800 kWh/day normal
        if d == 5:
            kwh *= 1.45  # anomaly: +45% spike
        rows.append(UtilityTransaction(
            id=_uid(), transaction_no=f"ELEC-{_d(d).strftime('%Y%m%d')}-{rng.randint(1000,9999)}",
            transaction_date=_d(d), utility_type=UtilityType.ELECTRICITY,
            quantity=D(round(kwh, 1)), unit_of_measure="kWh",
            tariff_id=TARIFF_IDS["elec_flat"],
            cost_rate=D("0.12"), total_cost=D(round(kwh * 0.12, 2)),
            currency_code="USD", department="Utilities",
            shift_ref="ALL", source_method=SourceMethod.IMPORTED,
            quality=DataQuality.GOOD,
            is_anomaly=(d == 5),
            anomaly_note="Night consumption spike — compressor left running" if d == 5 else None,
        ))
    return rows


def _water_transactions(days: int = 35) -> list[UtilityTransaction]:
    rows = []
    for d in range(days, 0, -1):
        m3 = _n(120, 8)
        rows.append(UtilityTransaction(
            id=_uid(), transaction_no=f"WATER-{_d(d).strftime('%Y%m%d')}-{rng.randint(1000,9999)}",
            transaction_date=_d(d), utility_type=UtilityType.WATER,
            quantity=D(round(m3, 2)), unit_of_measure="m3",
            tariff_id=TARIFF_IDS["water_flat"],
            cost_rate=D("0.85"), total_cost=D(round(m3 * 0.85, 2)),
            currency_code="USD", department="Utilities",
            shift_ref="ALL", source_method=SourceMethod.IOT,
            quality=DataQuality.GOOD,
        ))
    return rows


def _boiler_records(days: int = 30) -> list[BoilerSteamRecord]:
    rows = []
    for d in range(days, 0, -1):
        eff = _n(82, 5)
        fuel = _n(240, 8)  # Nm³/day
        steam = _n(4500, 6)  # kg/shift
        blowdown = _n(2.5, 15)
        load = _n(75, 10)
        condensate_ret = _n(65, 8)  # % returned
        condensate_m3 = round(steam * 0.001 * condensate_ret / 100, 2)
        is_anomaly = eff < 72
        rows.append(BoilerSteamRecord(
            id=_uid(),
            record_no=f"BLR-{_d(d).strftime('%Y%m%d')}-A",
            asset_id=ASSET_IDS["boiler1"],
            record_datetime=_dt(d, 8, 0),
            shift_ref="A", department="Utilities",
            period_hours=D("8"),
            steam_generated_kg=D(round(steam, 1)),
            steam_pressure_bar=D(_n(8.0, 3)),
            steam_temp_c=D(_n(174, 2)),
            steam_flow_kgh=D(round(steam / 8, 1)),
            fuel_type="NATURAL_GAS",
            fuel_consumption=D(round(fuel / 3, 2)),
            fuel_unit="Nm³",
            boiler_efficiency_pct=D(round(eff, 2)),
            boiler_load_pct=D(round(load, 1)),
            blowdown_pct=D(round(blowdown, 2)),
            feedwater_consumed_m3=D(round(steam * 0.001 + condensate_m3, 2)),
            condensate_returned_m3=D(condensate_m3),
            status=BoilerStatus.RUNNING,
            is_anomaly=is_anomaly,
            anomaly_note="Efficiency below 72% threshold" if is_anomaly else None,
            source_method=SourceMethod.MANUAL,
        ))
    return rows


def _compressor_records(days: int = 30) -> list[CompressorRecord]:
    rows = []
    for d in range(days, 0, -1):
        air_nm3 = _n(1800, 8)
        kwh = _n(440, 10)
        load = _n(72, 8)
        leak = _n(8, 20)
        night_idle = D("0.0")
        is_anomaly = False
        if d == 5:
            # anomaly: high night consumption
            night_idle = D(round(_n(145, 10), 1))
            kwh *= 1.38
            is_anomaly = True
        rows.append(CompressorRecord(
            id=_uid(),
            record_no=f"CPR-{_d(d).strftime('%Y%m%d')}-A",
            asset_id=ASSET_IDS["comp1"],
            record_datetime=_dt(d, 8, 0),
            shift_ref="A", department="Utilities",
            period_hours=D("8"),
            air_generated_nm3=D(round(air_nm3, 1)),
            electricity_used_kwh=D(round(kwh, 1)),
            specific_energy_kwh_m3=D(round(kwh / air_nm3, 4)),
            load_pct=D(round(load, 1)),
            discharge_pressure_bar=D(_n(7.8, 2)),
            leak_test_done=rng.random() > 0.5,
            leak_estimation_pct=D(round(leak, 1)),
            leak_volume_nm3=D(round(air_nm3 * leak / 100, 1)),
            night_idle_kwh=night_idle,
            status=CompressorStatus.RUNNING,
            is_anomaly=is_anomaly,
            anomaly_note="High night idle — unit not shut down after shift" if is_anomaly else None,
            source_method=SourceMethod.MANUAL,
        ))
    return rows


def _soft_water_records(days: int = 30) -> list[SoftWaterRecord]:
    rows = []
    for d in range(days, 0, -1):
        vol = _n(28, 8)
        raw = vol / _n(0.88, 3)  # conversion ~88%
        salt = _n(3.8, 10)  # kg/m³
        eff = round(vol / raw * 100, 1)
        # anomaly: hardness deviation day 3
        prod_hardness = D(round(_n(1.5, 30), 1))
        is_anomaly = False
        if d == 3:
            prod_hardness = D(round(_n(12, 10), 1))  # way above 5 ppm threshold
            is_anomaly = True
        rows.append(SoftWaterRecord(
            id=_uid(),
            record_no=f"SFT-{_d(d).strftime('%Y%m%d')}-A",
            asset_id=ASSET_IDS["softener1"],
            record_datetime=_dt(d, 8, 0),
            shift_ref="A", department="Utilities",
            volume_treated_m3=D(round(vol, 2)),
            raw_water_input_m3=D(round(raw, 2)),
            salt_consumed_kg=D(round(vol * salt, 1)),
            efficiency_pct=D(eff),
            feed_water_hardness_ppm=D(round(_n(185, 5), 1)),
            product_water_hardness_ppm=prod_hardness,
            destination_tag="Boiler Feed + CIP",
            regeneration_count=1 if rng.random() > 0.6 else 0,
            status=SoftenerStatus.ONLINE if not is_anomaly else SoftenerStatus.FAULT,
            source_method=SourceMethod.MANUAL,
            is_anomaly=is_anomaly,
            anomaly_note="Product hardness spike — resin exhaustion suspected" if is_anomaly else None,
        ))
    return rows


def _solar_records(days: int = 30) -> list[SolarRecord]:
    rows = []
    for d in range(days, 0, -1):
        irr = _n(550, 25)  # W/m²
        gen = round(irr / 1000 * 200 * 0.80 * (8 / 24), 1)  # rough estimate kWh
        self_use = round(gen * _n(0.82, 5), 1)
        export = max(0, round(gen - self_use, 1))
        pr = round(_n(0.81, 6), 3)
        total_elec = _n(3800, 12)
        rows.append(SolarRecord(
            id=_uid(),
            record_no=f"SOLAR-{_d(d).strftime('%Y%m%d')}",
            asset_id=ASSET_IDS["solar1"],
            record_datetime=_dt(d, 17, 0),
            energy_generated_kwh=D(gen),
            self_consumption_kwh=D(self_use),
            grid_export_kwh=D(export),
            irradiance_wm2=D(round(irr, 1)),
            pr_ratio=D(pr),
            inverter_efficiency_pct=D(_n(97.5, 1)),
            availability_pct=D(_n(99.5, 0.5)),
            capacity_factor_pct=D(round(gen / (200 * 24) * 100, 2)),
            source_method=SourceMethod.API,
        ))
    return rows


def _chemical_records(days: int = 30) -> list[TreatmentChemicalRecord]:
    rows = []
    dosing_plan = [
        (CHEM_IDS["boiler_treat"], "Boiler Treatment Compound A", TreatmentType.OTHER, "Boiler Feed",          100, 140, 0.05),
        (CHEM_IDS["oxy_scavenger"], "Oxygen Scavenger (DEHA)",    TreatmentType.OTHER, "Boiler Feed",          10,  25, 0.08),
        (CHEM_IDS["antiscalant"],   "Antiscalant - RO/Soft Water", TreatmentType.SOFTENING, "Softener Feed",   5,   12, 0.03),
        (CHEM_IDS["coagulant"],     "Aluminium Sulphate Coagulant", TreatmentType.COAGULATION, "WWTP Primary",  1.0, 2.5, 0.02),
        (CHEM_IDS["chlorine"],      "Sodium Hypochlorite (12%)",   TreatmentType.DISINFECTION, "WWTP Effluent", 80, 180, 0.04),
    ]
    for d in range(days, 0, -1):
        for idx, (chem_id, chem_name, t_type, area, lo, hi, cost_per_unit) in enumerate(dosing_plan):
            qty = round(rng.uniform(lo, hi), 2)
            target_mid = (lo + hi) / 2
            actual_ppm = round(qty / 28 * 1000, 1)  # rough ppm
            target_ppm = round(target_mid / 28 * 1000, 1)
            overdose = qty > hi * 0.98
            underdose = qty < lo * 1.02
            rows.append(TreatmentChemicalRecord(
                id=_uid(),
                record_no=f"CHEM-{_d(d).strftime('%Y%m%d')}-{idx+1:02d}",
                chemical_id=chem_id,
                chemical_name=chem_name,
                asset_id=ASSET_IDS["boiler1"] if "Boiler" in area else (
                    ASSET_IDS["softener1"] if "Softener" in area else ASSET_IDS["wwtp1"]
                ),
                record_datetime=_dt(d, 7, 30),
                treatment_type=t_type,
                treatment_area=area,
                quantity_dosed=D(qty),
                unit="ml",
                target_dose_ppm=D(target_ppm),
                actual_dose_ppm=D(actual_ppm),
                unit_cost=D(cost_per_unit),
                overdose_flag=overdose,
                underdose_flag=underdose,
                manual_or_auto_dose=DosingMode.MANUAL,
                source_method=SourceMethod.MANUAL,
            ))
    return rows


def _wastewater_records(days: int = 30) -> list[WastewaterRecord]:
    rows = []
    for d in range(days, 0, -1):
        inf_cod = _n(620, 15)
        eff_cod = _n(42, 20)
        removal = round((inf_cod - eff_cod) / inf_cod * 100, 1)
        ph = _n(7.2, 3)
        compliance = ComplianceStatus.COMPLIANT

        if d == 2:
            ph = _n(5.8, 2)  # pH compliance issue
            compliance = ComplianceStatus.NON_COMPLIANT

        if 5.5 < ph < 6.5 and compliance == ComplianceStatus.COMPLIANT:
            compliance = ComplianceStatus.BORDERLINE

        rows.append(WastewaterRecord(
            id=_uid(),
            record_no=f"WWT-{_d(d).strftime('%Y%m%d')}-A",
            asset_id=ASSET_IDS["wwtp1"],
            record_datetime=_dt(d, 9, 0),
            process_stage=WastewaterProcess.SECONDARY,
            shift_ref="A", department="Environment",
            influent_flow_m3h=D(_n(18, 8)),
            effluent_flow_m3h=D(_n(16, 8)),
            influent_cod_mgl=D(round(inf_cod, 1)),
            effluent_cod_mgl=D(round(eff_cod, 1)),
            cod_removal_pct=D(removal),
            influent_bod_mgl=D(round(inf_cod * 0.55, 1)),
            effluent_bod_mgl=D(round(eff_cod * 0.40, 1)),
            influent_tss_mgl=D(round(_n(280, 20), 1)),
            effluent_tss_mgl=D(round(_n(18, 20), 1)),
            effluent_ph=D(round(ph, 1)),
            do_mgl=D(round(_n(4.5, 15), 1)),
            compliance_status=compliance,
            permit_limit_ref="DOE-PERMIT-2024-01",
            deviation_reason="pH drop — acid from CIP rinse carryover" if d == 2 else None,
            power_consumed_kwh=D(round(_n(220, 8), 1)),
            sludge_produced_kg=D(round(_n(85, 12), 1)),
            source_method=SourceMethod.MANUAL,
        ))
    return rows


def _alarm_events() -> list[UtilityAlarmEvent]:
    events = []
    # 1. High night compressor consumption
    events.append(UtilityAlarmEvent(
        id=_uid(), event_no="EVT-COMP-20240001",
        rule_id=RULE_IDS["high_elec_night"],
        asset_id=ASSET_IDS["comp1"],
        device_id=DEV_IDS["comp_meter"],
        utility_type=UtilityType.ELECTRICITY,
        triggered_at=_dt(5, 23, 15),
        severity=AlarmSeverity.WARNING,
        triggered_value=D("145.3"),
        threshold_value=D("500"),
        parameter="night_kwh",
        status=AlarmStatus.RESOLVED,
        acknowledged_at=_dt(4, 7, 30),
        resolved_at=_dt(4, 8, 0),
        notes="Compressor auto-start due to line pressure drop — investigated and corrected",
    ))
    # 2. Soft water hardness deviation
    events.append(UtilityAlarmEvent(
        id=_uid(), event_no="EVT-SOFT-20240001",
        rule_id=RULE_IDS["soft_hardness"],
        asset_id=ASSET_IDS["softener1"],
        utility_type=UtilityType.SOFT_WATER,
        triggered_at=_dt(3, 10, 45),
        severity=AlarmSeverity.CRITICAL,
        triggered_value=D("12.4"),
        threshold_value=D("5.0"),
        parameter="product_water_hardness_ppm",
        status=AlarmStatus.RESOLVED,
        acknowledged_at=_dt(3, 11, 0),
        resolved_at=_dt(3, 14, 30),
        notes="Resin exhausted — emergency regeneration performed, hardness back to 1.8 ppm",
    ))
    # 3. WWTP pH compliance issue
    events.append(UtilityAlarmEvent(
        id=_uid(), event_no="EVT-WWT-20240001",
        rule_id=RULE_IDS["wwtp_ph_low"],
        asset_id=ASSET_IDS["wwtp1"],
        device_id=DEV_IDS["wwtp_sensor"],
        utility_type=UtilityType.WASTEWATER,
        triggered_at=_dt(2, 9, 5),
        severity=AlarmSeverity.CRITICAL,
        triggered_value=D("5.8"),
        threshold_value=D("6.5"),
        parameter="effluent_ph",
        status=AlarmStatus.RESOLVED,
        acknowledged_at=_dt(2, 9, 15),
        resolved_at=_dt(2, 12, 0),
        notes="CIP acid rinse carryover; NaOH dosed to correct pH; discharge halted during event",
    ))
    # 4. Low boiler efficiency (unresolved)
    events.append(UtilityAlarmEvent(
        id=_uid(), event_no="EVT-BLR-20240001",
        rule_id=RULE_IDS["low_boiler_eff"],
        asset_id=ASSET_IDS["boiler1"],
        utility_type=UtilityType.STEAM,
        triggered_at=_dt(8, 14, 30),
        severity=AlarmSeverity.ALERT,
        triggered_value=D("69.4"),
        threshold_value=D("72.0"),
        parameter="boiler_efficiency_pct",
        status=AlarmStatus.ACKNOWLEDGED,
        acknowledged_at=_dt(8, 15, 0),
    ))
    # 5. Low solar PR
    events.append(UtilityAlarmEvent(
        id=_uid(), event_no="EVT-SOLAR-20240001",
        rule_id=RULE_IDS["solar_pr_low"],
        asset_id=ASSET_IDS["solar1"],
        utility_type=UtilityType.SOLAR,
        triggered_at=_dt(12, 13, 0),
        severity=AlarmSeverity.WARNING,
        triggered_value=D("0.64"),
        threshold_value=D("0.70"),
        parameter="pr_ratio",
        status=AlarmStatus.RESOLVED,
        acknowledged_at=_dt(12, 13, 30),
        resolved_at=_dt(11, 9, 0),
        notes="Panel soiling — scheduled cleaning restored PR to 0.82",
    ))
    return events


def _utility_bills() -> list[UtilityBill]:
    bills = []
    # Monthly electricity bill
    bills.append(UtilityBill(
        id=_uid(), bill_no="BILL-ELEC-202403",
        utility_type=UtilityType.ELECTRICITY,
        tariff_id=TARIFF_IDS["elec_flat"],
        provider_name="National Power Grid",
        billing_period_from=_d(60),
        billing_period_to=_d(31),
        invoice_date=_d(28),
        due_date=_d(14),
        consumption_quantity=D("114520"),
        consumption_unit="kWh",
        energy_charge=D("13742.40"),
        tax_amount=D("1374.24"),
        total_amount=D("15116.64"),
        currency_code="USD",
        status=BillStatus.PAID,
        notes="March 2024 electricity bill",
    ))
    # Monthly water bill
    bills.append(UtilityBill(
        id=_uid(), bill_no="BILL-WATER-202403",
        utility_type=UtilityType.WATER,
        tariff_id=TARIFF_IDS["water_flat"],
        provider_name="City Water Authority",
        billing_period_from=_d(60),
        billing_period_to=_d(31),
        invoice_date=_d(26),
        due_date=_d(12),
        consumption_quantity=D("3720"),
        consumption_unit="m3",
        energy_charge=D("3162.00"),
        tax_amount=D("316.20"),
        total_amount=D("3478.20"),
        currency_code="USD",
        status=BillStatus.PAID,
        notes="March 2024 water bill",
    ))
    # Current month electricity (unpaid)
    bills.append(UtilityBill(
        id=_uid(), bill_no="BILL-ELEC-202404",
        utility_type=UtilityType.ELECTRICITY,
        tariff_id=TARIFF_IDS["elec_flat"],
        provider_name="National Power Grid",
        billing_period_from=_d(30),
        billing_period_to=_d(1),
        invoice_date=_d(3),
        due_date=_d(-12),
        consumption_quantity=D("116800"),
        consumption_unit="kWh",
        energy_charge=D("14016.00"),
        tax_amount=D("1401.60"),
        total_amount=D("15417.60"),
        currency_code="USD",
        status=BillStatus.RECEIVED,
        notes="April 2024 electricity bill — under verification",
    ))
    return bills


def _cost_allocations(days: int = 30) -> list[UtilityCostAllocation]:
    depts = [
        ("Production - Line A", "LINE-A", 0.35),
        ("Production - Line B", "LINE-B", 0.28),
        ("Utilities",           "UTIL",   0.15),
        ("CIP & Sanitation",   "CIP",    0.12),
        ("Administration",     "ADMIN",  0.10),
    ]
    rows = []
    for d in range(30, 0, -5):  # every 5 days to keep data manageable
        total_elec_cost = round(_n(456, 5), 2)
        for dept_name, dept_code, share in depts:
            alloc_cost = round(total_elec_cost * share, 2)
            alloc_qty = round(3800 * share, 1)
            rows.append(UtilityCostAllocation(
                id=_uid(),
                allocation_no=f"ALLOC-{_d(d).strftime('%Y%m%d')}-{dept_code}",
                utility_type=UtilityType.ELECTRICITY,
                allocation_date=_d(d),
                period_start=_d(d),
                period_end=_d(d),
                target_type=TargetType.DEPARTMENT,
                target_id=dept_code,
                target_name=dept_name,
                department=dept_name,
                allocated_quantity=D(alloc_qty),
                quantity_unit="kWh",
                allocated_cost=D(alloc_cost),
                total_cost=D(total_elec_cost),
                currency_code="USD",
                allocation_method=AllocationMethod.PROPORTIONAL,
                allocation_basis=D(round(share * 100, 1)),
                allocation_basis_unit="pct",
                production_volume_kg=D(round(_n(12000 * share, 10), 0)) if "LINE" in dept_code else None,
                source_method=SourceMethod.CALCULATED,
            ))
    return rows


# ── Main seed function ─────────────────────────────────────────────────────────

SEED_TABLES_ORDER = [
    "utility_alarm_events",
    "utility_cost_allocations",
    "utility_bills",
    "treatment_chemical_records",
    "wastewater_records",
    "solar_records",
    "compressor_records",
    "soft_water_records",
    "boiler_steam_records",
    "utility_transactions",
    "utility_readings",
    "utility_alarm_rules",
    "utility_tariffs",
    "utility_devices",
    "utility_assets",
    "utility_asset_categories",
    "water_treatment_chemicals",
]


async def _delete_seed_data(session: AsyncSession) -> None:
    """Delete rows whose IDs or codes match our deterministic seed set."""
    print("  Clearing existing utility seed data…")
    for tbl in SEED_TABLES_ORDER:
        try:
            await session.execute(text(f"DELETE FROM {tbl} WHERE true"))
        except Exception as exc:
            print(f"    [warn] Could not clear {tbl}: {exc}")
            await session.rollback()
    await session.commit()
    print("  Done clearing.")


async def seed_utilities(session: AsyncSession, reset: bool = False) -> None:
    """Insert all demo utility data. If reset=True, purges existing rows first."""
    if reset:
        await _delete_seed_data(session)

    print("  Seeding asset categories…")
    for obj in CATEGORIES:
        existing = await session.get(UtilityAssetCategory, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding water treatment chemicals…")
    for obj in CHEMICALS:
        existing = await session.get(WaterTreatmentChemical, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding utility assets…")
    for obj in ASSETS:
        existing = await session.get(UtilityAsset, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding utility devices…")
    for obj in DEVICES:
        existing = await session.get(UtilityDevice, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding tariffs…")
    for obj in TARIFFS:
        existing = await session.get(UtilityTariff, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding alarm rules…")
    for obj in ALARM_RULES:
        existing = await session.get(UtilityAlarmRule, obj.id)
        if not existing:
            session.add(obj)
    await session.flush()

    print("  Seeding electricity transactions (35 days)…")
    for obj in _electricity_transactions(35):
        session.add(obj)
    await session.flush()

    print("  Seeding water transactions (35 days)…")
    for obj in _water_transactions(35):
        session.add(obj)
    await session.flush()

    print("  Seeding boiler records (30 days)…")
    for obj in _boiler_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding compressor records (30 days)…")
    for obj in _compressor_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding soft water records (30 days)…")
    for obj in _soft_water_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding solar records (30 days)…")
    for obj in _solar_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding chemical treatment records (30 days × 5 chemicals)…")
    for obj in _chemical_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding wastewater records (30 days)…")
    for obj in _wastewater_records(30):
        session.add(obj)
    await session.flush()

    print("  Seeding alarm events (5 scenario events)…")
    for obj in _alarm_events():
        session.add(obj)
    await session.flush()

    print("  Seeding utility bills (3 bills)…")
    for obj in _utility_bills():
        session.add(obj)
    await session.flush()

    print("  Seeding cost allocations…")
    for obj in _cost_allocations(30):
        session.add(obj)

    await session.commit()
    print("  Utilities seed complete.")


# ── Entry point ────────────────────────────────────────────────────────────────

async def main() -> None:
    reset = "--reset" in sys.argv
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"Utilities seed — target: {settings.DATABASE_URL[:40]}…")
    async with async_session() as session:
        await seed_utilities(session, reset=reset)

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
