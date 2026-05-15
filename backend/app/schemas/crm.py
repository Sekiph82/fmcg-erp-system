from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
import uuid

from app.models.crm import (
    CRMRecordType, CRMAccountType, CRMSourceType, CRMStageType,
    CRMTemperature, CRMStatus, CRMActivityType, CRMActivityResult,
    CRMLossReason, CRMWinReason, CRMAIAgentType, CRMAIRecStatus,
)
from app.schemas.sales import CommercialAccessHint, CommercialScopeFields


# ── Stage ─────────────────────────────────────────────────────────────────────

class CRMStageCreate(BaseModel):
    stage_code: str
    stage_name: str
    stage_type: CRMStageType
    default_probability: Optional[Decimal] = Decimal("0")
    sequence_no: int = 0
    active_flag: bool = True
    color_code: Optional[str] = None
    notes: Optional[str] = None


class CRMStageRead(CRMStageCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: Optional[datetime] = None


class CRMStageUpdate(BaseModel):
    stage_name: Optional[str] = None
    stage_type: Optional[CRMStageType] = None
    default_probability: Optional[Decimal] = None
    sequence_no: Optional[int] = None
    active_flag: Optional[bool] = None
    color_code: Optional[str] = None
    notes: Optional[str] = None


# ── Interest Line ─────────────────────────────────────────────────────────────

class CRMInterestLineCreate(BaseModel):
    crm_record_id: uuid.UUID
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    expected_qty: Optional[Decimal] = None
    expected_frequency: Optional[str] = None
    expected_value: Optional[Decimal] = None
    competitive_brand: Optional[str] = None
    competitor_price: Optional[Decimal] = None
    notes: Optional[str] = None


class CRMInterestLineRead(CRMInterestLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    crm_record_id: uuid.UUID


# ── Activity ──────────────────────────────────────────────────────────────────

class CRMActivityCreate(BaseModel):
    crm_record_id: uuid.UUID
    activity_type: CRMActivityType
    subject: str
    description: Optional[str] = None
    activity_datetime: Optional[datetime] = None
    due_datetime: Optional[datetime] = None
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


class CRMActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    crm_record_id: uuid.UUID
    activity_type: CRMActivityType
    subject: str
    description: Optional[str] = None
    activity_datetime: Optional[datetime] = None
    due_datetime: Optional[datetime] = None
    completed_datetime: Optional[datetime] = None
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    result_status: CRMActivityResult
    outcome_code: Optional[str] = None
    next_step: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class CRMActivityComplete(BaseModel):
    result_status: CRMActivityResult
    outcome_code: Optional[str] = None
    next_step: Optional[str] = None
    notes: Optional[str] = None


# ── Competitor ────────────────────────────────────────────────────────────────

class CRMCompetitorCreate(BaseModel):
    crm_record_id: uuid.UUID
    competitor_name: str
    competitor_product: Optional[str] = None
    offer_type: Optional[str] = None
    competitor_price: Optional[Decimal] = None
    competitor_strength: Optional[str] = None
    competitor_weakness: Optional[str] = None
    risk_level: Optional[str] = None
    notes: Optional[str] = None


class CRMCompetitorRead(CRMCompetitorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: Optional[datetime] = None


# ── Record (Lead / Opportunity) ───────────────────────────────────────────────

class CRMRecordCreate(CommercialScopeFields):
    record_type: CRMRecordType = CRMRecordType.LEAD
    company_name: str
    account_type: CRMAccountType = CRMAccountType.PROSPECT
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    alternate_contact: Optional[str] = None
    customer_id: Optional[str] = None
    distributor_id: Optional[str] = None
    source_type: CRMSourceType = CRMSourceType.MANUAL
    source_detail: Optional[str] = None
    region_id: Optional[str] = None
    country_id: Optional[str] = None
    channel_id: Optional[str] = None
    industry_segment: Optional[str] = None
    assigned_rep_id: Optional[str] = None
    assigned_team_id: Optional[str] = None
    stage_id: Optional[uuid.UUID] = None
    territory_id: Optional[uuid.UUID] = None
    assigned_customer_id: Optional[uuid.UUID] = None
    probability_pct: Optional[Decimal] = Decimal("0")
    expected_close_date: Optional[date] = None
    expected_revenue: Optional[Decimal] = Decimal("0")
    expected_margin: Optional[Decimal] = Decimal("0")
    currency: str = "KES"
    temperature: CRMTemperature = CRMTemperature.COLD
    next_action_date: Optional[date] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


class CRMRecordUpdate(CommercialScopeFields):
    company_name: Optional[str] = None
    account_type: Optional[CRMAccountType] = None
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    stage_id: Optional[uuid.UUID] = None
    territory_id: Optional[uuid.UUID] = None
    probability_pct: Optional[Decimal] = None
    probability_override: Optional[bool] = None
    expected_close_date: Optional[date] = None
    expected_revenue: Optional[Decimal] = None
    expected_margin: Optional[Decimal] = None
    temperature: Optional[CRMTemperature] = None
    next_action_date: Optional[date] = None
    assigned_rep_id: Optional[str] = None
    assigned_team_id: Optional[str] = None
    assigned_customer_id: Optional[uuid.UUID] = None
    linked_quotation_id: Optional[str] = None
    linked_order_id: Optional[str] = None
    updated_by: Optional[str] = None
    notes: Optional[str] = None


class CRMRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    record_type: CRMRecordType
    lead_code: Optional[str] = None
    opportunity_code: Optional[str] = None
    account_type: CRMAccountType
    company_name: str
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    customer_id: Optional[str] = None
    distributor_id: Optional[str] = None
    source_type: CRMSourceType
    region_id: Optional[str] = None
    channel_id: Optional[str] = None
    assigned_rep_id: Optional[str] = None
    assigned_team_id: Optional[str] = None
    stage_id: Optional[uuid.UUID] = None
    territory_id: Optional[uuid.UUID] = None
    assigned_customer_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    sales_region_id: Optional[str] = None
    sales_team_id: Optional[str] = None
    customer_group_id: Optional[str] = None
    probability_pct: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    expected_revenue: Optional[Decimal] = None
    expected_margin: Optional[Decimal] = None
    currency: str
    lead_score: int
    temperature: CRMTemperature
    next_action_date: Optional[date] = None
    status: CRMStatus
    qualified_flag: bool
    qualified_date: Optional[date] = None
    converted_date: Optional[date] = None
    linked_quotation_id: Optional[str] = None
    linked_order_id: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    access: Optional[CommercialAccessHint] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Qualification ─────────────────────────────────────────────────────────────

class CRMQualifyRequest(BaseModel):
    budget_fit: bool = False
    need_fit: bool = False
    timeline_fit: bool = False
    authority_fit: bool = False
    product_fit: bool = False
    geo_fit: bool = False
    notes: Optional[str] = None
    qualified_by: Optional[str] = None


class CRMConvertRequest(BaseModel):
    expected_revenue: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    stage_id: Optional[uuid.UUID] = None
    converted_by: Optional[str] = None
    notes: Optional[str] = None


# ── Close Won/Lost ────────────────────────────────────────────────────────────

class CRMCloseWonRequest(BaseModel):
    final_revenue: Optional[Decimal] = None
    final_margin: Optional[Decimal] = None
    win_reason_code: Optional[CRMWinReason] = None
    competitor_name: Optional[str] = None
    narrative: Optional[str] = None
    linked_order_id: Optional[str] = None
    recorded_by: Optional[str] = None


class CRMCloseLostRequest(BaseModel):
    loss_reason_code: Optional[CRMLossReason] = None
    competitor_name: Optional[str] = None
    narrative: Optional[str] = None
    recorded_by: Optional[str] = None


# ── Win/Loss ──────────────────────────────────────────────────────────────────

class CRMWinLossRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    crm_record_id: uuid.UUID
    final_status: str
    close_date: Optional[date] = None
    final_revenue: Optional[Decimal] = None
    final_margin: Optional[Decimal] = None
    loss_reason_code: Optional[CRMLossReason] = None
    win_reason_code: Optional[CRMWinReason] = None
    competitor_name: Optional[str] = None
    narrative: Optional[str] = None
    recorded_by: Optional[str] = None
    notes: Optional[str] = None


# ── AI ────────────────────────────────────────────────────────────────────────

class CRMAIRecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_type: CRMAIAgentType
    crm_record_id: Optional[uuid.UUID] = None
    title: str
    body: str
    priority: Optional[str] = None
    action_label: Optional[str] = None
    status: CRMAIRecStatus
    acknowledged_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class CRMAIRecAck(BaseModel):
    status: CRMAIRecStatus
    acknowledged_by: Optional[str] = None
    notes: Optional[str] = None


# ── Territory ─────────────────────────────────────────────────────────────────

class CRMTerritoryCreate(CommercialScopeFields):
    territory_code: str
    territory_name: str
    region: Optional[str] = None
    parent_territory_id: Optional[uuid.UUID] = None
    assigned_rep_ids: Optional[str] = None
    active_flag: bool = True
    notes: Optional[str] = None


class CRMTerritoryRead(CRMTerritoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    access: Optional[CommercialAccessHint] = None
    created_at: Optional[datetime] = None


class CRMTerritoryUpdate(CommercialScopeFields):
    territory_name: Optional[str] = None
    region: Optional[str] = None
    parent_territory_id: Optional[uuid.UUID] = None
    assigned_rep_ids: Optional[str] = None
    active_flag: Optional[bool] = None
    notes: Optional[str] = None


class CRMTerritoryPerformance(BaseModel):
    territory_id: str
    territory_name: str
    region: Optional[str]
    assigned_rep_ids: Optional[str]
    total_records: int
    open_records: int
    won_records: int
    lost_records: int
    pipeline_value: float
    weighted_value: float
    win_rate_pct: float


# ── Customer 360 View ─────────────────────────────────────────────────────────

class CRM360View(BaseModel):
    record_id: str
    company_name: str
    record_type: str
    status: str
    lead_score: int
    temperature: str
    pipeline_age_days: int
    days_since_last_activity: Optional[int]
    last_activity_type: Optional[str]
    total_activities: int
    completed_activities: int
    overdue_activities: int
    activity_completion_rate: float
    communication_risk: str
    interest_product_count: int
    expected_revenue: float
    probability_pct: float
    weighted_value: float
    deal_risk_flag: bool
    credit_signal: str
    qualified_flag: bool
    territory_name: Optional[str]
    assigned_rep_id: Optional[str]
    next_action_date: Optional[date]
    expected_close_date: Optional[date]
    days_to_close: Optional[int]
    activity_health_score: int
    summary_flags: List[str]


# ── Dashboard & Reports ───────────────────────────────────────────────────────

class CRMDashboard(BaseModel):
    total_leads: int
    total_opportunities: int
    open_records: int
    won_this_month: int
    lost_this_month: int
    total_pipeline_value: Decimal
    weighted_pipeline_value: Decimal
    overdue_activities: int
    hot_records: int
    conversion_rate_pct: float
    avg_deal_size: Decimal
    stage_distribution: List[dict]
    top_reps: List[dict]


class CRMForecastRow(BaseModel):
    month: str
    expected_revenue: Decimal
    weighted_revenue: Decimal
    deal_count: int


class CRMPipelineRow(BaseModel):
    stage_name: str
    stage_code: str
    record_count: int
    total_value: Decimal
    weighted_value: Decimal
    avg_probability: float


class CRMWinLossRow(BaseModel):
    reason_code: str
    count: int
    total_revenue: Decimal
    pct_of_total: float
