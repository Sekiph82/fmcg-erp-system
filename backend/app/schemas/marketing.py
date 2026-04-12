"""Pydantic schemas for the Marketing module."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.marketing import (
    CampaignType, CampaignStatus, ApprovalStatus,
    PromotionType, PromotionStatus, DiscountType,
    SegmentType, RelationshipStatus, LoyaltyStatus, AcquisitionSource,
    VisitType, TradeSpendType, BrandSpendCategory, SurveyType,
    InfluencerPlatform, InfluencerStatus, ContentType, SentimentScore,
    StorePlatform, StoreStatus, AdPlatform, OptimizerStatus,
)


# ── Campaign ──────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    campaign_code:    str
    campaign_name:    str
    campaign_type:    CampaignType
    objective:        Optional[str] = None
    region:           Optional[str] = None
    country:          Optional[str] = None
    start_date:       date
    end_date:         date
    budget:           Optional[Decimal] = None
    expected_revenue: Optional[Decimal] = None
    notes:            Optional[str] = None


class CampaignUpdate(BaseModel):
    campaign_name:    Optional[str] = None
    campaign_type:    Optional[CampaignType] = None
    objective:        Optional[str] = None
    region:           Optional[str] = None
    country:          Optional[str] = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None
    status:           Optional[CampaignStatus] = None
    budget:           Optional[Decimal] = None
    expected_revenue: Optional[Decimal] = None
    actual_revenue:   Optional[Decimal] = None
    actual_roi:       Optional[Decimal] = None
    notes:            Optional[str] = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    campaign_code:    str
    campaign_name:    str
    campaign_type:    CampaignType
    objective:        Optional[str]
    region:           Optional[str]
    country:          Optional[str]
    start_date:       date
    end_date:         date
    status:           CampaignStatus
    budget:           Optional[Decimal]
    expected_revenue: Optional[Decimal]
    actual_revenue:   Optional[Decimal]
    expected_roi:     Optional[Decimal]
    actual_roi:       Optional[Decimal]
    approval_status:  ApprovalStatus
    owner_user_id:    Optional[uuid.UUID]
    approved_by_id:   Optional[uuid.UUID]
    notes:            Optional[str]
    created_at:       Optional[datetime] = None


# ── Promotion ─────────────────────────────────────────────────────────────────

class PromotionCreate(BaseModel):
    promotion_name:   str
    promotion_code:   Optional[str] = None
    promotion_type:   PromotionType
    campaign_id:      Optional[uuid.UUID] = None
    segment_id:       Optional[uuid.UUID] = None
    product_id:       Optional[uuid.UUID] = None
    region:           Optional[str] = None
    start_date:       date
    end_date:         date
    discount_type:    Optional[DiscountType] = None
    discount_value:   Optional[Decimal] = None
    minimum_quantity: Optional[Decimal] = None
    notes:            Optional[str] = None


class PromotionUpdate(BaseModel):
    promotion_name:   Optional[str] = None
    promotion_type:   Optional[PromotionType] = None
    campaign_id:      Optional[uuid.UUID] = None
    segment_id:       Optional[uuid.UUID] = None
    product_id:       Optional[uuid.UUID] = None
    region:           Optional[str] = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None
    status:           Optional[PromotionStatus] = None
    discount_type:    Optional[DiscountType] = None
    discount_value:   Optional[Decimal] = None
    minimum_quantity: Optional[Decimal] = None
    notes:            Optional[str] = None


class PromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    promotion_name:   str
    promotion_code:   Optional[str]
    promotion_type:   PromotionType
    campaign_id:      Optional[uuid.UUID]
    segment_id:       Optional[uuid.UUID]
    product_id:       Optional[uuid.UUID]
    region:           Optional[str]
    start_date:       date
    end_date:         date
    status:           PromotionStatus
    discount_type:    Optional[DiscountType]
    discount_value:   Optional[Decimal]
    minimum_quantity: Optional[Decimal]
    notes:            Optional[str]
    created_at:       Optional[datetime] = None


# ── Customer Segment ──────────────────────────────────────────────────────────

class SegmentCreate(BaseModel):
    segment_name:   str
    segment_type:   SegmentType
    region:         Optional[str] = None
    description:    Optional[str] = None
    criteria_json:  Optional[Dict[str, Any]] = None
    is_active:      bool = True


class SegmentUpdate(BaseModel):
    segment_name:   Optional[str] = None
    segment_type:   Optional[SegmentType] = None
    region:         Optional[str] = None
    description:    Optional[str] = None
    criteria_json:  Optional[Dict[str, Any]] = None
    is_active:      Optional[bool] = None


class SegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    segment_name:   str
    segment_type:   SegmentType
    region:         Optional[str]
    description:    Optional[str]
    is_active:      bool
    created_at:     Optional[datetime] = None


# ── CRM Profile ───────────────────────────────────────────────────────────────

class CRMProfileCreate(BaseModel):
    customer_id:            uuid.UUID
    segment_id:             Optional[uuid.UUID] = None
    relationship_status:    RelationshipStatus = RelationshipStatus.ACTIVE
    loyalty_status:         LoyaltyStatus = LoyaltyStatus.NONE
    acquisition_source:     Optional[AcquisitionSource] = None
    acquisition_campaign_id:Optional[uuid.UUID] = None
    acquisition_channel:    Optional[str] = None
    first_touch_source:     Optional[str] = None
    last_touch_source:      Optional[str] = None
    next_followup_date:     Optional[date] = None
    preferred_contact_method: Optional[str] = None
    notes:                  Optional[str] = None


class CRMProfileUpdate(BaseModel):
    segment_id:              Optional[uuid.UUID] = None
    relationship_status:     Optional[RelationshipStatus] = None
    loyalty_status:          Optional[LoyaltyStatus] = None
    acquisition_source:      Optional[AcquisitionSource] = None
    acquisition_channel:     Optional[str] = None
    last_touch_source:       Optional[str] = None
    last_contact_date:       Optional[date] = None
    next_followup_date:      Optional[date] = None
    engagement_score:        Optional[Decimal] = None
    estimated_ltv:           Optional[Decimal] = None
    churn_risk_score:        Optional[Decimal] = None
    notes:                   Optional[str] = None


class CRMProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                      uuid.UUID
    customer_id:             uuid.UUID
    segment_id:              Optional[uuid.UUID]
    relationship_status:     RelationshipStatus
    loyalty_status:          LoyaltyStatus
    acquisition_source:      Optional[AcquisitionSource]
    acquisition_campaign_id: Optional[uuid.UUID]
    acquisition_channel:     Optional[str]
    first_touch_source:      Optional[str]
    last_touch_source:       Optional[str]
    last_contact_date:       Optional[date]
    next_followup_date:      Optional[date]
    engagement_score:        Optional[Decimal]
    estimated_ltv:           Optional[Decimal]
    churn_risk_score:        Optional[Decimal]
    notes:                   Optional[str]
    created_at:              Optional[datetime] = None


class InteractionCreate(BaseModel):
    crm_profile_id:   uuid.UUID
    interaction_date: date
    channel:          Optional[str] = None
    summary:          Optional[str] = None
    outcome:          Optional[str] = None
    follow_up_date:   Optional[date] = None


class InteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    crm_profile_id:   uuid.UUID
    interaction_date: date
    channel:          Optional[str]
    summary:          Optional[str]
    outcome:          Optional[str]
    follow_up_date:   Optional[date]
    recorded_by_id:   Optional[uuid.UUID]
    created_at:       Optional[datetime] = None


# ── Customer Visit ────────────────────────────────────────────────────────────

class VisitCreate(BaseModel):
    customer_id:          Optional[uuid.UUID] = None
    crm_profile_id:       Optional[uuid.UUID] = None
    employee_id:          Optional[uuid.UUID] = None
    visit_date:           date
    visit_type:           VisitType
    purpose:              Optional[str] = None
    notes:                Optional[str] = None
    outcome:              Optional[str] = None
    followup_required:    bool = False
    gps_latitude:         Optional[Decimal] = None
    gps_longitude:        Optional[Decimal] = None
    survey_id:            Optional[uuid.UUID] = None
    competitor_notes:     Optional[str] = None
    display_observation:  Optional[str] = None
    stock_observation:    Optional[str] = None


class VisitUpdate(BaseModel):
    visit_type:          Optional[VisitType] = None
    purpose:             Optional[str] = None
    notes:               Optional[str] = None
    outcome:             Optional[str] = None
    followup_required:   Optional[bool] = None
    competitor_notes:    Optional[str] = None
    display_observation: Optional[str] = None
    stock_observation:   Optional[str] = None


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    customer_id:         Optional[uuid.UUID]
    crm_profile_id:      Optional[uuid.UUID]
    employee_id:         Optional[uuid.UUID]
    visit_date:          date
    visit_type:          VisitType
    purpose:             Optional[str]
    outcome:             Optional[str]
    followup_required:   bool
    competitor_notes:    Optional[str]
    display_observation: Optional[str]
    stock_observation:   Optional[str]
    created_at:          Optional[datetime] = None


# ── Trade Spend ───────────────────────────────────────────────────────────────

class TradeSpendCreate(BaseModel):
    campaign_id:    Optional[uuid.UUID] = None
    customer_id:    Optional[uuid.UUID] = None
    distributor_id: Optional[uuid.UUID] = None
    spend_type:     TradeSpendType
    amount:         Decimal
    currency:       str = "KES"
    spend_date:     date
    notes:          Optional[str] = None


class TradeSpendUpdate(BaseModel):
    spend_type:     Optional[TradeSpendType] = None
    amount:         Optional[Decimal] = None
    spend_date:     Optional[date] = None
    approval_status:Optional[ApprovalStatus] = None
    notes:          Optional[str] = None


class TradeSpendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    campaign_id:    Optional[uuid.UUID]
    customer_id:    Optional[uuid.UUID]
    distributor_id: Optional[uuid.UUID]
    spend_type:     TradeSpendType
    amount:         Decimal
    currency:       str
    spend_date:     date
    approval_status:ApprovalStatus
    approved_by_id: Optional[uuid.UUID]
    notes:          Optional[str]
    created_at:     Optional[datetime] = None


# ── Brand Spend ───────────────────────────────────────────────────────────────

class BrandSpendCreate(BaseModel):
    campaign_id:   Optional[uuid.UUID] = None
    spend_category:BrandSpendCategory
    vendor:        Optional[str] = None
    amount:        Decimal
    currency:      str = "KES"
    spend_date:    date
    notes:         Optional[str] = None


class BrandSpendUpdate(BaseModel):
    spend_category: Optional[BrandSpendCategory] = None
    vendor:         Optional[str] = None
    amount:         Optional[Decimal] = None
    spend_date:     Optional[date] = None
    approval_status:Optional[ApprovalStatus] = None
    notes:          Optional[str] = None


class BrandSpendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    campaign_id:    Optional[uuid.UUID]
    spend_category: BrandSpendCategory
    vendor:         Optional[str]
    amount:         Decimal
    currency:       str
    spend_date:     date
    approval_status:ApprovalStatus
    approved_by_id: Optional[uuid.UUID]
    notes:          Optional[str]
    created_at:     Optional[datetime] = None


# ── Survey ────────────────────────────────────────────────────────────────────

class SurveyCreate(BaseModel):
    survey_name:       str
    survey_type:       SurveyType
    region:            Optional[str] = None
    survey_date:       date
    target_segment_id: Optional[uuid.UUID] = None
    questions_json:    Optional[Dict[str, Any]] = None
    summary:           Optional[str] = None
    competitor_notes:  Optional[str] = None


class SurveyUpdate(BaseModel):
    survey_name:      Optional[str] = None
    region:           Optional[str] = None
    summary:          Optional[str] = None
    responses_json:   Optional[Dict[str, Any]] = None
    sentiment_score:  Optional[Decimal] = None
    competitor_notes: Optional[str] = None
    response_count:   Optional[int] = None


class SurveyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                uuid.UUID
    survey_name:       str
    survey_type:       SurveyType
    region:            Optional[str]
    survey_date:       date
    target_segment_id: Optional[uuid.UUID]
    questions_json:    Optional[Dict[str, Any]]
    responses_json:    Optional[Dict[str, Any]]
    summary:           Optional[str]
    sentiment_score:   Optional[Decimal]
    competitor_notes:  Optional[str]
    response_count:    int
    conducted_by_id:   Optional[uuid.UUID]
    created_at:        Optional[datetime] = None


# ── Influencer ────────────────────────────────────────────────────────────────

class InfluencerCreate(BaseModel):
    influencer_name: str
    platform:        InfluencerPlatform
    handle:          Optional[str] = None
    category:        Optional[str] = None
    region:          Optional[str] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[Decimal] = None
    contact_info:    Optional[str] = None
    status:          InfluencerStatus = InfluencerStatus.PROSPECT
    notes:           Optional[str] = None


class InfluencerUpdate(BaseModel):
    influencer_name: Optional[str] = None
    platform:        Optional[InfluencerPlatform] = None
    handle:          Optional[str] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[Decimal] = None
    status:          Optional[InfluencerStatus] = None
    notes:           Optional[str] = None


class InfluencerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    influencer_name: str
    platform:        InfluencerPlatform
    handle:          Optional[str]
    category:        Optional[str]
    region:          Optional[str]
    followers_count: Optional[int]
    engagement_rate: Optional[Decimal]
    status:          InfluencerStatus
    notes:           Optional[str]
    created_at:      Optional[datetime] = None


class InfluencerLinkCreate(BaseModel):
    influencer_id:      uuid.UUID
    campaign_id:        uuid.UUID
    content_type:       Optional[ContentType] = None
    tracking_link:      Optional[str] = None
    agreed_fee:         Optional[Decimal] = None
    expected_posts:     Optional[int] = None
    actual_posts:       Optional[int] = None
    impressions:        Optional[int] = None
    clicks:             Optional[int] = None
    conversions:        Optional[int] = None
    attributed_revenue: Optional[Decimal] = None
    notes:              Optional[str] = None


class InfluencerLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    influencer_id:       uuid.UUID
    campaign_id:         uuid.UUID
    content_type:        Optional[ContentType]
    tracking_link:       Optional[str]
    agreed_fee:          Optional[Decimal]
    paid_fee:            Optional[Decimal]
    expected_posts:      Optional[int]
    actual_posts:        Optional[int]
    impressions:         Optional[int]
    clicks:              Optional[int]
    conversions:         Optional[int]
    attributed_revenue:  Optional[Decimal]
    performance_score:   Optional[Decimal]
    sentiment:           Optional[SentimentScore]
    notes:               Optional[str]


class InfluencerLinkUpdate(BaseModel):
    content_type:       Optional[ContentType] = None
    tracking_link:      Optional[str] = None
    agreed_fee:         Optional[Decimal] = None
    paid_fee:           Optional[Decimal] = None
    expected_posts:     Optional[int] = None
    actual_posts:       Optional[int] = None
    impressions:        Optional[int] = None
    clicks:             Optional[int] = None
    conversions:        Optional[int] = None
    attributed_revenue: Optional[Decimal] = None
    performance_score:  Optional[Decimal] = None
    sentiment:          Optional[SentimentScore] = None
    notes:              Optional[str] = None


# ── Social Media Activity ─────────────────────────────────────────────────────

class SocialActivityCreate(BaseModel):
    campaign_id:    Optional[uuid.UUID] = None
    platform:       InfluencerPlatform
    content_type:   Optional[ContentType] = None
    published_date: date
    post_url:       Optional[str] = None
    impressions:    Optional[int] = None
    reach:          Optional[int] = None
    clicks:         Optional[int] = None
    engagements:    Optional[int] = None
    comments_count: Optional[int] = None
    shares_count:   Optional[int] = None
    saves_count:    Optional[int] = None
    notes:          Optional[str] = None


class SocialActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             uuid.UUID
    campaign_id:    Optional[uuid.UUID]
    platform:       InfluencerPlatform
    content_type:   Optional[ContentType]
    published_date: date
    post_url:       Optional[str]
    impressions:    Optional[int]
    reach:          Optional[int]
    clicks:         Optional[int]
    engagements:    Optional[int]
    comments_count: Optional[int]
    shares_count:   Optional[int]
    saves_count:    Optional[int]
    notes:          Optional[str]
    created_at:     Optional[datetime] = None


class SocialActivityUpdate(BaseModel):
    platform:       Optional[InfluencerPlatform] = None
    content_type:   Optional[ContentType] = None
    published_date: Optional[date] = None
    post_url:       Optional[str] = None
    impressions:    Optional[int] = None
    reach:          Optional[int] = None
    clicks:         Optional[int] = None
    engagements:    Optional[int] = None
    comments_count: Optional[int] = None
    shares_count:   Optional[int] = None
    saves_count:    Optional[int] = None
    notes:          Optional[str] = None


# ── Store ─────────────────────────────────────────────────────────────────────

class StoreCreate(BaseModel):
    store_name: str
    platform:   StorePlatform
    region:     Optional[str] = None
    url:        Optional[str] = None
    owner:      Optional[str] = None
    status:     StoreStatus = StoreStatus.ACTIVE
    notes:      Optional[str] = None


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         uuid.UUID
    store_name: str
    platform:   StorePlatform
    region:     Optional[str]
    url:        Optional[str]
    owner:      Optional[str]
    status:     StoreStatus
    notes:      Optional[str]
    created_at: Optional[datetime] = None


class StoreUpdate(BaseModel):
    store_name: Optional[str] = None
    platform:   Optional[StorePlatform] = None
    region:     Optional[str] = None
    url:        Optional[str] = None
    owner:      Optional[str] = None
    status:     Optional[StoreStatus] = None
    notes:      Optional[str] = None


class StorePerformanceCreate(BaseModel):
    store_id:         uuid.UUID
    perf_date:        date
    total_orders:     int = 0
    total_units_sold: int = 0
    total_revenue:    Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    gross_margin:     Optional[Decimal] = None
    ad_spend:         Optional[Decimal] = None
    impressions:      Optional[int] = None
    clicks:           Optional[int] = None
    conversions:      Optional[int] = None
    returns_count:    int = 0
    cancelled_orders: int = 0
    net_revenue:      Optional[Decimal] = None
    notes:            Optional[str] = None


class StorePerformanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               uuid.UUID
    store_id:         uuid.UUID
    perf_date:        date
    total_orders:     int
    total_units_sold: int
    total_revenue:    Optional[Decimal]
    total_cost:       Optional[Decimal]
    gross_margin:     Optional[Decimal]
    ad_spend:         Optional[Decimal]
    impressions:      Optional[int]
    clicks:           Optional[int]
    ctr:              Optional[Decimal]
    conversions:      Optional[int]
    conversion_rate:  Optional[Decimal]
    returns_count:    int
    return_rate:      Optional[Decimal]
    cancelled_orders: int
    net_revenue:      Optional[Decimal]
    notes:            Optional[str]
    created_at:       Optional[datetime] = None


class StorePerformanceUpdate(BaseModel):
    perf_date:        Optional[date] = None
    total_orders:     Optional[int] = None
    total_units_sold: Optional[int] = None
    total_revenue:    Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    gross_margin:     Optional[Decimal] = None
    ad_spend:         Optional[Decimal] = None
    impressions:      Optional[int] = None
    clicks:           Optional[int] = None
    ctr:              Optional[Decimal] = None
    conversions:      Optional[int] = None
    conversion_rate:  Optional[Decimal] = None
    returns_count:    Optional[int] = None
    return_rate:      Optional[Decimal] = None
    cancelled_orders: Optional[int] = None
    net_revenue:      Optional[Decimal] = None
    notes:            Optional[str] = None


class ProductChannelPerfCreate(BaseModel):
    product_id:      uuid.UUID
    store_id:        uuid.UUID
    perf_date:       date
    units_sold:      int = 0
    revenue:         Optional[Decimal] = None
    impressions:     Optional[int] = None
    clicks:          Optional[int] = None
    conversion_rate: Optional[Decimal] = None
    return_rate:     Optional[Decimal] = None
    ranking:         Optional[int] = None
    stock_level:     Optional[int] = None


class ProductChannelPerfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    product_id:      uuid.UUID
    store_id:        uuid.UUID
    perf_date:       date
    units_sold:      int
    revenue:         Optional[Decimal]
    impressions:     Optional[int]
    clicks:          Optional[int]
    conversion_rate: Optional[Decimal]
    return_rate:     Optional[Decimal]
    ranking:         Optional[int]
    stock_level:     Optional[int]
    created_at:      Optional[datetime] = None


class ProductChannelPerfUpdate(BaseModel):
    units_sold:      Optional[int] = None
    revenue:         Optional[Decimal] = None
    impressions:     Optional[int] = None
    clicks:          Optional[int] = None
    conversion_rate: Optional[Decimal] = None
    return_rate:     Optional[Decimal] = None
    ranking:         Optional[int] = None
    stock_level:     Optional[int] = None


# ── Channel Stock ─────────────────────────────────────────────────────────────

class ChannelStockCreate(BaseModel):
    product_id:      uuid.UUID
    store_id:        uuid.UUID
    allocated_stock: Decimal = Decimal("0")
    reserved_stock:  Decimal = Decimal("0")
    available_stock: Decimal = Decimal("0")


class ChannelStockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    product_id:      uuid.UUID
    store_id:        uuid.UUID
    allocated_stock: Decimal
    reserved_stock:  Decimal
    available_stock: Decimal
    created_at:      Optional[datetime] = None


class ChannelStockUpdate(BaseModel):
    allocated_stock: Optional[Decimal] = None
    reserved_stock:  Optional[Decimal] = None
    available_stock: Optional[Decimal] = None


# ── Ad Performance ────────────────────────────────────────────────────────────

class AdPerformanceCreate(BaseModel):
    campaign_id:   Optional[uuid.UUID] = None
    platform:      AdPlatform
    ad_name:       Optional[str] = None
    ad_date:       date
    impressions:   Optional[int] = None
    clicks:        Optional[int] = None
    ctr:           Optional[Decimal] = None
    cpc:           Optional[Decimal] = None
    spend:         Optional[Decimal] = None
    conversions:   Optional[int] = None
    cost_per_conversion: Optional[Decimal] = None
    revenue_generated:   Optional[Decimal] = None
    notes:         Optional[str] = None


class AdPerformanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    campaign_id:         Optional[uuid.UUID]
    platform:            AdPlatform
    ad_name:             Optional[str]
    ad_date:             date
    impressions:         Optional[int]
    clicks:              Optional[int]
    ctr:                 Optional[Decimal]
    cpc:                 Optional[Decimal]
    spend:               Optional[Decimal]
    conversions:         Optional[int]
    cost_per_conversion: Optional[Decimal]
    revenue_generated:   Optional[Decimal]
    notes:               Optional[str]
    created_at:          Optional[datetime] = None


class AdPerformanceUpdate(BaseModel):
    campaign_id:         Optional[uuid.UUID] = None
    platform:            Optional[AdPlatform] = None
    ad_name:             Optional[str] = None
    ad_date:             Optional[date] = None
    impressions:         Optional[int] = None
    clicks:              Optional[int] = None
    ctr:                 Optional[Decimal] = None
    cpc:                 Optional[Decimal] = None
    spend:               Optional[Decimal] = None
    conversions:         Optional[int] = None
    cost_per_conversion: Optional[Decimal] = None
    revenue_generated:   Optional[Decimal] = None
    notes:               Optional[str] = None


# ── Return Analytics ──────────────────────────────────────────────────────────

class ReturnAnalyticsCreate(BaseModel):
    product_id:    uuid.UUID
    store_id:      Optional[uuid.UUID] = None
    return_date:   date
    return_reason: Optional[str] = None
    return_count:  int = 0
    return_rate:   Optional[Decimal] = None
    notes:         Optional[str] = None


class ReturnAnalyticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            uuid.UUID
    product_id:    uuid.UUID
    store_id:      Optional[uuid.UUID]
    return_date:   date
    return_reason: Optional[str]
    return_count:  int
    return_rate:   Optional[Decimal]
    notes:         Optional[str]
    created_at:    Optional[datetime] = None


class ReturnAnalyticsUpdate(BaseModel):
    return_date:   Optional[date] = None
    return_reason: Optional[str] = None
    return_count:  Optional[int] = None
    return_rate:   Optional[Decimal] = None
    notes:         Optional[str] = None


# ── E-commerce Analytics ──────────────────────────────────────────────────────

class EcommerceAnalytics(BaseModel):
    period_days:           int
    total_revenue:         float
    total_orders:          int
    total_units_sold:      int
    avg_order_value:       float
    total_ad_spend:        float
    overall_roas:          float
    overall_return_rate:   float
    channel_breakdown: List[Dict[str, Any]]
    top_products:      List[Dict[str, Any]]
    return_reasons:    List[Dict[str, Any]]


# ── Optimizer ─────────────────────────────────────────────────────────────────

class OptimizerRunCreate(BaseModel):
    campaign_id:      Optional[uuid.UUID] = None
    campaign_context: Optional[str] = None
    notes:            Optional[str] = None


class OptimizerApprove(BaseModel):
    notes: Optional[str] = None


class OptimizerRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    run_date:            date
    triggered_by_id:     Optional[uuid.UUID]
    campaign_id:         Optional[uuid.UUID]
    campaign_context:    Optional[str]
    input_summary:       Optional[Dict[str, Any]]
    recommendation_json: Optional[Dict[str, Any]]
    status:              OptimizerStatus
    notes:               Optional[str]
    approved_by_id:      Optional[uuid.UUID]
    approved_at:         Optional[datetime]
    created_at:          Optional[datetime] = None


# ── Influencer Attribution ────────────────────────────────────────────────────

class InfluencerAttributionCreate(BaseModel):
    influencer_id:      uuid.UUID
    campaign_id:        Optional[uuid.UUID] = None
    tracking_link:      Optional[str] = None
    clicks:             int = 0
    conversions:        int = 0
    attributed_revenue: Optional[Decimal] = None
    attributed_orders:  int = 0
    attribution_date:   date


class InfluencerAttributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  uuid.UUID
    influencer_id:       uuid.UUID
    campaign_id:         Optional[uuid.UUID]
    tracking_link:       Optional[str]
    clicks:              int
    conversions:         int
    attributed_revenue:  Optional[Decimal]
    attributed_orders:   int
    attribution_date:    date
    created_at:          Optional[datetime] = None
