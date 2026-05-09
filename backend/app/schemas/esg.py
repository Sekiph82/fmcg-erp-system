from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.models.esg import (
    SourceType, EmissionScope, ESGMetricType,
    SupplierSustainabilityRisk, SupplierSustainabilityStatus,
)


# ── Activity Data ─────────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    source_type: SourceType
    source_reference: Optional[str] = None
    activity_date: date
    quantity: Decimal
    unit: str
    location_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class ActivityRead(ActivityCreate):
    id: uuid.UUID
    is_auto_imported: bool
    location_name: Optional[str] = None
    supplier_name: Optional[str] = None
    calculated_emission_kgco2e: Optional[Decimal] = None
    scope: Optional[EmissionScope] = None
    model_config = {"from_attributes": True}


# ── Emission Factor ───────────────────────────────────────────────────────────

class EmissionFactorCreate(BaseModel):
    factor_code: str
    source_type: SourceType
    region: str = "KE"
    valid_from: date
    valid_to: Optional[date] = None
    factor_value: Decimal
    unit: str
    scope: EmissionScope
    source_reference: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class EmissionFactorUpdate(BaseModel):
    factor_value: Optional[Decimal] = None
    valid_to: Optional[date] = None
    source_reference: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class EmissionFactorRead(EmissionFactorCreate):
    id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Emission Record ───────────────────────────────────────────────────────────

class EmissionRecordRead(BaseModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    factor_id: uuid.UUID
    calculated_emission_kgco2e: Decimal
    scope: EmissionScope
    calculated_at: datetime
    source_type: Optional[SourceType] = None
    activity_date: Optional[date] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    factor_code: Optional[str] = None
    factor_value: Optional[Decimal] = None
    location_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Resource Metric ───────────────────────────────────────────────────────────

class ResourceMetricCreate(BaseModel):
    metric_type: ESGMetricType
    quantity: Decimal
    unit: str
    location_id: Optional[uuid.UUID] = None
    period_from: date
    period_to: date
    notes: Optional[str] = None


class ResourceMetricRead(ResourceMetricCreate):
    id: uuid.UUID
    location_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── ESG Target ────────────────────────────────────────────────────────────────

class ESGTargetCreate(BaseModel):
    metric_type: ESGMetricType
    scope: Optional[EmissionScope] = None
    baseline_year: int
    baseline_value: Decimal
    target_value: Decimal
    unit: str
    target_date: date
    is_active: bool = True
    notes: Optional[str] = None


class ESGTargetRead(ESGTargetCreate):
    id: uuid.UUID
    actual_value: Optional[Decimal] = None
    progress_pct: Optional[Decimal] = None
    model_config = {"from_attributes": True}


# â”€â”€ ESG Intelligence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SupplierSustainabilityScoreCreate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: str
    assessment_period_start: date
    assessment_period_end: date
    overall_score: Decimal
    risk_level: SupplierSustainabilityRisk = SupplierSustainabilityRisk.MEDIUM
    status: SupplierSustainabilityStatus = SupplierSustainabilityStatus.ACTIVE
    emissions_score: Optional[Decimal] = None
    energy_score: Optional[Decimal] = None
    water_score: Optional[Decimal] = None
    waste_score: Optional[Decimal] = None
    compliance_score: Optional[Decimal] = None
    labor_score: Optional[Decimal] = None
    renewable_energy_pct: Optional[Decimal] = None
    has_ghg_disclosure: bool = False
    has_science_based_target: bool = False
    iso14001_certified: bool = False
    wastewater_policy_verified: bool = False
    audit_findings: Optional[str] = None
    improvement_plan: Optional[str] = None
    notes: Optional[str] = None


class SupplierSustainabilityScoreUpdate(BaseModel):
    supplier_name: Optional[str] = None
    assessment_period_start: Optional[date] = None
    assessment_period_end: Optional[date] = None
    overall_score: Optional[Decimal] = None
    risk_level: Optional[SupplierSustainabilityRisk] = None
    status: Optional[SupplierSustainabilityStatus] = None
    emissions_score: Optional[Decimal] = None
    energy_score: Optional[Decimal] = None
    water_score: Optional[Decimal] = None
    waste_score: Optional[Decimal] = None
    compliance_score: Optional[Decimal] = None
    labor_score: Optional[Decimal] = None
    renewable_energy_pct: Optional[Decimal] = None
    has_ghg_disclosure: Optional[bool] = None
    has_science_based_target: Optional[bool] = None
    iso14001_certified: Optional[bool] = None
    wastewater_policy_verified: Optional[bool] = None
    audit_findings: Optional[str] = None
    improvement_plan: Optional[str] = None
    notes: Optional[str] = None


class SupplierSustainabilityScoreRead(SupplierSustainabilityScoreCreate):
    id: uuid.UUID
    assessed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class EnergyIntensityRow(BaseModel):
    product_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    product_name: str
    batches: int
    allocation_count: int
    total_energy_kwh: Decimal
    production_volume_kg: Decimal
    kwh_per_kg: Optional[Decimal] = None
    kwh_per_ton: Optional[Decimal] = None
    total_energy_cost: Decimal
    currency_code: Optional[str] = None
    data_quality: str


class WastewaterComplianceSnapshot(BaseModel):
    total_records: int
    compliant_records: int
    borderline_records: int
    non_compliant_records: int
    not_tested_records: int
    compliance_rate_pct: Optional[Decimal] = None
    avg_effluent_cod_mgl: Optional[Decimal] = None
    avg_effluent_bod_mgl: Optional[Decimal] = None
    avg_effluent_tss_mgl: Optional[Decimal] = None
    avg_effluent_ph: Optional[Decimal] = None
    total_power_kwh: Decimal
    latest_deviations: List[dict]


class ESGIntelligenceDashboard(BaseModel):
    supplier_score_count: int
    average_supplier_score: Optional[Decimal] = None
    high_risk_supplier_count: int
    energy_intensity_rows: List[EnergyIntensityRow]
    wastewater_compliance: WastewaterComplianceSnapshot


# ── Reports ───────────────────────────────────────────────────────────────────

class EmissionSummaryRow(BaseModel):
    scope: EmissionScope
    total_kgco2e: Decimal
    total_tco2e: Decimal
    activity_count: int


class EmissionBySourceRow(BaseModel):
    source_type: SourceType
    scope: EmissionScope
    total_kgco2e: Decimal
    activity_count: int


class EmissionByLocationRow(BaseModel):
    location_name: str
    total_kgco2e: Decimal
    scope_breakdown: dict


class ResourceSummaryRow(BaseModel):
    metric_type: ESGMetricType
    total_quantity: Decimal
    unit: str
    period: str


class ESGDashboard(BaseModel):
    total_emissions_kgco2e: Decimal
    scope1_kgco2e: Decimal
    scope2_kgco2e: Decimal
    scope3_kgco2e: Decimal
    total_energy_kwh: Decimal
    total_water_m3: Decimal
    total_waste_kg: Decimal
    recycling_rate_pct: Optional[Decimal] = None
    activity_count: int
    last_updated: str


# ── AI ────────────────────────────────────────────────────────────────────────

class ESGInsight(BaseModel):
    agent: str
    insights: List[str]
    details: Optional[List[dict]] = None
    generated_at: str


# ── Import ────────────────────────────────────────────────────────────────────

class FleetImportResult(BaseModel):
    imported_activities: int
    imported_emissions: int
    skipped: int
    message: str
