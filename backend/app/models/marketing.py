"""
Marketing Module — FMCG Growth Engine
──────────────────────────────────────
Campaigns · Promotions · CRM · Visits · Spend · Surveys
Influencers · Social · E-commerce · Ads · AI Optimizer
"""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, Boolean,
    ForeignKey, Enum as SAEnum, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# ── Enumerations ──────────────────────────────────────────────────────────────

class CampaignType(str, enum.Enum):
    TRADE          = "TRADE"
    DIGITAL        = "DIGITAL"
    RETAIL         = "RETAIL"
    DISTRIBUTOR    = "DISTRIBUTOR"
    LAUNCH         = "LAUNCH"
    SEASONAL       = "SEASONAL"
    LOYALTY        = "LOYALTY"
    AWARENESS      = "AWARENESS"
    ACQUISITION    = "ACQUISITION"
    RETENTION      = "RETENTION"


class CampaignStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    PLANNED    = "PLANNED"
    ACTIVE     = "ACTIVE"
    PAUSED     = "PAUSED"
    COMPLETED  = "COMPLETED"
    CANCELLED  = "CANCELLED"


class ApprovalStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PromotionType(str, enum.Enum):
    DISCOUNT             = "DISCOUNT"
    BUNDLE               = "BUNDLE"
    FREE_ITEM            = "FREE_ITEM"
    REBATE               = "REBATE"
    BUY_X_GET_Y          = "BUY_X_GET_Y"
    RETAILER_SUPPORT     = "RETAILER_SUPPORT"
    DISTRIBUTOR_SUPPORT  = "DISTRIBUTOR_SUPPORT"
    CASHBACK             = "CASHBACK"


class PromotionStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    EXPIRED  = "EXPIRED"
    PAUSED   = "PAUSED"


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED      = "FIXED"


class SegmentType(str, enum.Enum):
    RETAIL        = "RETAIL"
    WHOLESALE     = "WHOLESALE"
    KIOSK         = "KIOSK"
    SUPERMARKET   = "SUPERMARKET"
    DISTRIBUTOR   = "DISTRIBUTOR"
    HORECA        = "HORECA"
    PHARMACY      = "PHARMACY"
    MODERN_TRADE  = "MODERN_TRADE"
    GENERAL_TRADE = "GENERAL_TRADE"
    ONLINE        = "ONLINE"


class RelationshipStatus(str, enum.Enum):
    PROSPECT  = "PROSPECT"
    ACTIVE    = "ACTIVE"
    AT_RISK   = "AT_RISK"
    DORMANT   = "DORMANT"
    CHURNED   = "CHURNED"
    VIP       = "VIP"


class LoyaltyStatus(str, enum.Enum):
    BRONZE   = "BRONZE"
    SILVER   = "SILVER"
    GOLD     = "GOLD"
    PLATINUM = "PLATINUM"
    NONE     = "NONE"


class AcquisitionSource(str, enum.Enum):
    ADS         = "ADS"
    INFLUENCER  = "INFLUENCER"
    ORGANIC     = "ORGANIC"
    REFERRAL    = "REFERRAL"
    MARKETPLACE = "MARKETPLACE"
    DIRECT      = "DIRECT"
    SOCIAL      = "SOCIAL"
    FIELD_SALES = "FIELD_SALES"
    EVENT       = "EVENT"
    OTHER       = "OTHER"


class VisitType(str, enum.Enum):
    SALES          = "SALES"
    MARKETING      = "MARKETING"
    TRADE_AUDIT    = "TRADE_AUDIT"
    MERCHANDISING  = "MERCHANDISING"
    FEEDBACK       = "FEEDBACK"
    STORE_CHECK    = "STORE_CHECK"


class TradeSpendType(str, enum.Enum):
    DISCOUNT_SUPPORT     = "DISCOUNT_SUPPORT"
    DISPLAY_FEE          = "DISPLAY_FEE"
    SHELF_PLACEMENT      = "SHELF_PLACEMENT"
    ACTIVATION_SUPPORT   = "ACTIVATION_SUPPORT"
    REBATE               = "REBATE"
    DISTRIBUTOR_SUPPORT  = "DISTRIBUTOR_SUPPORT"
    MERCHANDISING        = "MERCHANDISING"


class BrandSpendCategory(str, enum.Enum):
    TV                  = "TV"
    RADIO               = "RADIO"
    DIGITAL_ADS         = "DIGITAL_ADS"
    INFLUENCER          = "INFLUENCER"
    EVENT               = "EVENT"
    SAMPLING            = "SAMPLING"
    BRANDING_MATERIAL   = "BRANDING_MATERIAL"
    AGENCY_COST         = "AGENCY_COST"
    CREATIVE_PRODUCTION = "CREATIVE_PRODUCTION"
    MEDIA_BUYING        = "MEDIA_BUYING"


class SurveyType(str, enum.Enum):
    CUSTOMER_FEEDBACK   = "CUSTOMER_FEEDBACK"
    MARKET_AUDIT        = "MARKET_AUDIT"
    RETAILER_FEEDBACK   = "RETAILER_FEEDBACK"
    BRAND_AWARENESS     = "BRAND_AWARENESS"
    COMPETITOR_CHECK    = "COMPETITOR_CHECK"
    PRODUCT_FEEDBACK    = "PRODUCT_FEEDBACK"
    SHELF_AUDIT         = "SHELF_AUDIT"


class InfluencerPlatform(str, enum.Enum):
    INSTAGRAM  = "INSTAGRAM"
    TIKTOK     = "TIKTOK"
    YOUTUBE    = "YOUTUBE"
    FACEBOOK   = "FACEBOOK"
    X          = "X"
    OTHER      = "OTHER"


class InfluencerStatus(str, enum.Enum):
    PROSPECT = "PROSPECT"
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED  = "BLOCKED"


class ContentType(str, enum.Enum):
    POST        = "POST"
    STORY       = "STORY"
    REEL        = "REEL"
    VIDEO       = "VIDEO"
    LIVE        = "LIVE"
    REVIEW      = "REVIEW"
    UNBOXING    = "UNBOXING"


class SentimentScore(str, enum.Enum):
    VERY_POSITIVE = "VERY_POSITIVE"
    POSITIVE      = "POSITIVE"
    NEUTRAL       = "NEUTRAL"
    NEGATIVE      = "NEGATIVE"
    VERY_NEGATIVE = "VERY_NEGATIVE"


class StorePlatform(str, enum.Enum):
    WEBSITE     = "WEBSITE"
    INSTAGRAM   = "INSTAGRAM"
    TIKTOK      = "TIKTOK"
    MARKETPLACE = "MARKETPLACE"
    OTHER       = "OTHER"


class StoreStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED   = "PAUSED"


class AdPlatform(str, enum.Enum):
    META      = "META"
    TIKTOK    = "TIKTOK"
    GOOGLE    = "GOOGLE"
    YOUTUBE   = "YOUTUBE"
    TWITTER   = "TWITTER"
    LINKEDIN  = "LINKEDIN"
    OTHER     = "OTHER"


class OptimizerStatus(str, enum.Enum):
    PENDING  = "PENDING"
    COMPLETE = "COMPLETE"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


# ── Campaign ──────────────────────────────────────────────────────────────────

class Campaign(Base, TimestampMixin):
    __tablename__ = "mkt_campaigns"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_code    = Column(String(50), unique=True, nullable=False, index=True)
    campaign_name    = Column(String(255), nullable=False)
    campaign_type    = Column(SAEnum(CampaignType), nullable=False)
    objective        = Column(Text, nullable=True)
    region           = Column(String(100), nullable=True)
    country          = Column(String(100), nullable=True)
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=False)
    status           = Column(SAEnum(CampaignStatus), nullable=False, default=CampaignStatus.DRAFT)
    budget           = Column(Numeric(16, 2), nullable=True)
    expected_revenue = Column(Numeric(16, 2), nullable=True)
    actual_revenue   = Column(Numeric(16, 2), nullable=True)
    expected_roi     = Column(Numeric(8, 4), nullable=True)
    actual_roi       = Column(Numeric(8, 4), nullable=True)
    approval_status  = Column(SAEnum(ApprovalStatus, name="marketing_approvalstatus"), nullable=False, default=ApprovalStatus.PENDING)
    owner_user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes            = Column(Text, nullable=True)

    promotions        = relationship("MarketingPromotion",  back_populates="campaign")
    trade_spends      = relationship("TradeSpend",          back_populates="campaign")
    brand_spends      = relationship("BrandSpend",          back_populates="campaign")
    social_activities = relationship("SocialMediaActivity", back_populates="campaign")
    ad_performances   = relationship("AdPerformance",       back_populates="campaign")
    influencer_links  = relationship("InfluencerCampaignLink", back_populates="campaign")
    optimizer_runs    = relationship("OptimizerRun",         back_populates="campaign")


# ── Promotion ─────────────────────────────────────────────────────────────────

class MarketingPromotion(Base, TimestampMixin):
    __tablename__ = "mkt_promotions"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promotion_name     = Column(String(255), nullable=False)
    promotion_code     = Column(String(50), unique=True, nullable=True, index=True)
    promotion_type     = Column(SAEnum(PromotionType), nullable=False)
    campaign_id        = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    segment_id         = Column(UUID(as_uuid=True), ForeignKey("mkt_customer_segments.id", ondelete="SET NULL"), nullable=True)
    product_id         = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    region             = Column(String(100), nullable=True)
    start_date         = Column(Date, nullable=False)
    end_date           = Column(Date, nullable=False)
    status             = Column(SAEnum(PromotionStatus), nullable=False, default=PromotionStatus.DRAFT)
    discount_type      = Column(SAEnum(DiscountType), nullable=True)
    discount_value     = Column(Numeric(10, 4), nullable=True)
    minimum_quantity   = Column(Numeric(12, 3), nullable=True)
    notes              = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="promotions")


# ── Customer Segment ──────────────────────────────────────────────────────────

class CustomerSegment(Base, TimestampMixin):
    __tablename__ = "mkt_customer_segments"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_name  = Column(String(255), nullable=False)
    segment_type  = Column(SAEnum(SegmentType), nullable=False)
    region        = Column(String(100), nullable=True)
    description   = Column(Text, nullable=True)
    criteria_json = Column(JSONB, nullable=True)
    is_active     = Column(Boolean, default=True, nullable=False)

    promotions   = relationship("MarketingPromotion", back_populates=None, foreign_keys=[MarketingPromotion.segment_id])
    crm_profiles = relationship("CRMProfile", back_populates="segment")


# ── CRM Profile (marketing extension of Customer) ─────────────────────────────

class CRMProfile(Base, TimestampMixin):
    """Marketing CRM layer — one-to-one extension of sales Customer."""
    __tablename__ = "mkt_crm_profiles"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id             = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False)
    segment_id              = Column(UUID(as_uuid=True), ForeignKey("mkt_customer_segments.id", ondelete="SET NULL"), nullable=True)
    owner_user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    relationship_status     = Column(SAEnum(RelationshipStatus), nullable=False, default=RelationshipStatus.ACTIVE)
    loyalty_status          = Column(SAEnum(LoyaltyStatus), nullable=False, default=LoyaltyStatus.NONE)
    acquisition_source      = Column(SAEnum(AcquisitionSource), nullable=True)
    acquisition_campaign_id = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    acquisition_channel     = Column(String(100), nullable=True)
    first_touch_source      = Column(String(100), nullable=True)
    last_touch_source       = Column(String(100), nullable=True)
    last_contact_date       = Column(Date, nullable=True)
    next_followup_date      = Column(Date, nullable=True)
    engagement_score        = Column(Numeric(5, 2), nullable=True)   # 0-100
    preferred_contact_method= Column(String(50), nullable=True)
    notes                   = Column(Text, nullable=True)
    # LTV / churn placeholders
    estimated_ltv           = Column(Numeric(16, 2), nullable=True)
    churn_risk_score        = Column(Numeric(5, 2), nullable=True)   # 0-100

    segment      = relationship("CustomerSegment", back_populates="crm_profiles")
    interactions = relationship("CustomerInteraction", back_populates="crm_profile")
    visits       = relationship("CustomerVisit", back_populates="crm_profile", foreign_keys="CustomerVisit.crm_profile_id")


class CustomerInteraction(Base, TimestampMixin):
    __tablename__ = "mkt_customer_interactions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_profile_id  = Column(UUID(as_uuid=True), ForeignKey("mkt_crm_profiles.id", ondelete="CASCADE"), nullable=False)
    interaction_date= Column(Date, nullable=False)
    channel         = Column(String(50), nullable=True)   # call, email, visit, message
    summary         = Column(Text, nullable=True)
    outcome         = Column(Text, nullable=True)
    follow_up_date  = Column(Date, nullable=True)
    recorded_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    crm_profile = relationship("CRMProfile", back_populates="interactions")


# ── Customer Visit ────────────────────────────────────────────────────────────

class CustomerVisit(Base, TimestampMixin):
    __tablename__ = "mkt_customer_visits"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id           = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    crm_profile_id        = Column(UUID(as_uuid=True), ForeignKey("mkt_crm_profiles.id", ondelete="SET NULL"), nullable=True)
    employee_id           = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    visit_date            = Column(Date, nullable=False)
    visit_type            = Column(SAEnum(VisitType), nullable=False)
    purpose               = Column(Text, nullable=True)
    notes                 = Column(Text, nullable=True)
    outcome               = Column(Text, nullable=True)
    followup_required     = Column(Boolean, default=False)
    gps_latitude          = Column(Numeric(9, 6), nullable=True)
    gps_longitude         = Column(Numeric(9, 6), nullable=True)
    survey_id             = Column(UUID(as_uuid=True), ForeignKey("mkt_surveys.id", ondelete="SET NULL"), nullable=True)
    competitor_notes      = Column(Text, nullable=True)
    display_observation   = Column(Text, nullable=True)
    stock_observation     = Column(Text, nullable=True)

    crm_profile = relationship("CRMProfile", back_populates="visits", foreign_keys=[crm_profile_id])


# ── Trade Spend ───────────────────────────────────────────────────────────────

class TradeSpend(Base, TimestampMixin):
    __tablename__ = "mkt_trade_spend"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id     = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    distributor_id  = Column(UUID(as_uuid=True), ForeignKey("distributors.id", ondelete="SET NULL"), nullable=True)
    spend_type      = Column(SAEnum(TradeSpendType), nullable=False)
    amount          = Column(Numeric(16, 2), nullable=False)
    currency        = Column(String(10), default="KES", nullable=False)
    spend_date      = Column(Date, nullable=False)
    approval_status = Column(SAEnum(ApprovalStatus, name="marketing_approvalstatus"), nullable=False, default=ApprovalStatus.PENDING)
    approved_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes           = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="trade_spends")


# ── Brand Spend ───────────────────────────────────────────────────────────────

class BrandSpend(Base, TimestampMixin):
    __tablename__ = "mkt_brand_spend"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id     = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    spend_category  = Column(SAEnum(BrandSpendCategory), nullable=False)
    vendor          = Column(String(255), nullable=True)
    amount          = Column(Numeric(16, 2), nullable=False)
    currency        = Column(String(10), default="KES", nullable=False)
    spend_date      = Column(Date, nullable=False)
    approval_status = Column(SAEnum(ApprovalStatus, name="marketing_approvalstatus"), nullable=False, default=ApprovalStatus.PENDING)
    approved_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes           = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="brand_spends")


# ── Survey ────────────────────────────────────────────────────────────────────

class Survey(Base, TimestampMixin):
    __tablename__ = "mkt_surveys"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_name       = Column(String(255), nullable=False)
    survey_type       = Column(SAEnum(SurveyType), nullable=False)
    region            = Column(String(100), nullable=True)
    survey_date       = Column(Date, nullable=False)
    conducted_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_segment_id = Column(UUID(as_uuid=True), ForeignKey("mkt_customer_segments.id", ondelete="SET NULL"), nullable=True)
    questions_json    = Column(JSONB, nullable=True)
    responses_json    = Column(JSONB, nullable=True)
    summary           = Column(Text, nullable=True)
    sentiment_score   = Column(Numeric(5, 2), nullable=True)
    competitor_notes  = Column(Text, nullable=True)
    response_count    = Column(Integer, default=0, nullable=False)

    visits = relationship("CustomerVisit", back_populates=None, foreign_keys=[CustomerVisit.survey_id])


# ── Influencer ────────────────────────────────────────────────────────────────

class Influencer(Base, TimestampMixin):
    __tablename__ = "mkt_influencers"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_name = Column(String(255), nullable=False)
    platform        = Column(SAEnum(InfluencerPlatform), nullable=False)
    handle          = Column(String(200), nullable=True)
    category        = Column(String(100), nullable=True)
    region          = Column(String(100), nullable=True)
    followers_count = Column(Integer, nullable=True)
    engagement_rate = Column(Numeric(6, 4), nullable=True)
    contact_info    = Column(String(255), nullable=True)
    status          = Column(SAEnum(InfluencerStatus), nullable=False, default=InfluencerStatus.PROSPECT)
    notes           = Column(Text, nullable=True)

    campaign_links = relationship("InfluencerCampaignLink", back_populates="influencer")
    attributions   = relationship("InfluencerAttribution", back_populates="influencer")


class InfluencerCampaignLink(Base, TimestampMixin):
    __tablename__ = "mkt_influencer_campaign_links"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id       = Column(UUID(as_uuid=True), ForeignKey("mkt_influencers.id", ondelete="CASCADE"), nullable=False)
    campaign_id         = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="CASCADE"), nullable=False)
    content_type        = Column(SAEnum(ContentType), nullable=True)
    tracking_link       = Column(String(500), nullable=True)
    agreed_fee          = Column(Numeric(14, 2), nullable=True)
    paid_fee            = Column(Numeric(14, 2), nullable=True)
    expected_posts      = Column(Integer, nullable=True)
    actual_posts        = Column(Integer, nullable=True)
    impressions         = Column(Integer, nullable=True)
    clicks              = Column(Integer, nullable=True)
    conversions         = Column(Integer, nullable=True)
    attributed_orders   = Column(Integer, nullable=True)
    attributed_revenue  = Column(Numeric(16, 2), nullable=True)
    performance_score   = Column(Numeric(5, 2), nullable=True)
    sentiment           = Column(SAEnum(SentimentScore), nullable=True)
    notes               = Column(Text, nullable=True)

    influencer = relationship("Influencer", back_populates="campaign_links")
    campaign   = relationship("Campaign", back_populates="influencer_links")


class InfluencerAttribution(Base, TimestampMixin):
    __tablename__ = "mkt_influencer_attribution"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id        = Column(UUID(as_uuid=True), ForeignKey("mkt_influencers.id", ondelete="CASCADE"), nullable=False)
    campaign_id          = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    tracking_link        = Column(String(500), nullable=True)
    clicks               = Column(Integer, default=0)
    conversions          = Column(Integer, default=0)
    attributed_revenue   = Column(Numeric(16, 2), nullable=True)
    attributed_orders    = Column(Integer, default=0)
    attribution_date     = Column(Date, nullable=False)

    influencer = relationship("Influencer", back_populates="attributions")


# ── Social Media Activity ─────────────────────────────────────────────────────

class SocialMediaActivity(Base, TimestampMixin):
    __tablename__ = "mkt_social_media"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id     = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    platform        = Column(SAEnum(InfluencerPlatform), nullable=False)
    content_type    = Column(SAEnum(ContentType), nullable=True)
    published_date  = Column(Date, nullable=False)
    post_url        = Column(String(500), nullable=True)
    impressions     = Column(Integer, nullable=True)
    reach           = Column(Integer, nullable=True)
    clicks          = Column(Integer, nullable=True)
    engagements     = Column(Integer, nullable=True)
    comments_count  = Column(Integer, nullable=True)
    shares_count    = Column(Integer, nullable=True)
    saves_count     = Column(Integer, nullable=True)
    sentiment_score = Column(SAEnum(SentimentScore), nullable=True)
    notes           = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="social_activities")


# ── Store / E-commerce Channel ────────────────────────────────────────────────

class Store(Base, TimestampMixin):
    __tablename__ = "mkt_stores"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_name   = Column(String(255), nullable=False, index=True)
    platform     = Column(SAEnum(StorePlatform), nullable=False)
    region       = Column(String(100), nullable=True)
    url          = Column(String(500), nullable=True)
    owner        = Column(String(255), nullable=True)
    status       = Column(SAEnum(StoreStatus), nullable=False, default=StoreStatus.ACTIVE)
    notes        = Column(Text, nullable=True)

    performances     = relationship("StorePerformance", back_populates="store")
    product_perf     = relationship("ProductChannelPerformance", back_populates="store")
    channel_stocks   = relationship("ChannelStock", back_populates="store")
    return_analytics = relationship("ReturnAnalytics", back_populates="store")


class StorePerformance(Base, TimestampMixin):
    __tablename__ = "mkt_store_performance"
    __table_args__ = (UniqueConstraint("store_id", "perf_date", name="uq_store_perf_date"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id         = Column(UUID(as_uuid=True), ForeignKey("mkt_stores.id", ondelete="CASCADE"), nullable=False)
    perf_date        = Column(Date, nullable=False)
    total_orders     = Column(Integer, default=0)
    total_units_sold = Column(Integer, default=0)
    total_revenue    = Column(Numeric(16, 2), nullable=True)
    total_cost       = Column(Numeric(16, 2), nullable=True)
    gross_margin     = Column(Numeric(16, 2), nullable=True)
    ad_spend         = Column(Numeric(14, 2), nullable=True)
    impressions      = Column(Integer, nullable=True)
    clicks           = Column(Integer, nullable=True)
    ctr              = Column(Numeric(8, 6), nullable=True)
    conversions      = Column(Integer, nullable=True)
    conversion_rate  = Column(Numeric(8, 6), nullable=True)
    returns_count    = Column(Integer, default=0)
    return_rate      = Column(Numeric(8, 6), nullable=True)
    cancelled_orders = Column(Integer, default=0)
    net_revenue      = Column(Numeric(16, 2), nullable=True)
    notes            = Column(Text, nullable=True)

    store = relationship("Store", back_populates="performances")


class ProductChannelPerformance(Base, TimestampMixin):
    __tablename__ = "mkt_product_channel_perf"
    __table_args__ = (UniqueConstraint("product_id", "store_id", "perf_date", name="uq_prod_store_date"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    store_id        = Column(UUID(as_uuid=True), ForeignKey("mkt_stores.id", ondelete="CASCADE"), nullable=False)
    perf_date       = Column(Date, nullable=False)
    units_sold      = Column(Integer, default=0)
    revenue         = Column(Numeric(16, 2), nullable=True)
    impressions     = Column(Integer, nullable=True)
    clicks          = Column(Integer, nullable=True)
    conversion_rate = Column(Numeric(8, 6), nullable=True)
    return_rate     = Column(Numeric(8, 6), nullable=True)
    ranking         = Column(Integer, nullable=True)
    stock_level     = Column(Integer, nullable=True)

    store = relationship("Store", back_populates="product_perf")


class ChannelStock(Base, TimestampMixin):
    """Channel-level stock allocation (lightweight sync layer)."""
    __tablename__ = "mkt_channel_stock"
    __table_args__ = (UniqueConstraint("product_id", "store_id", name="uq_channel_stock"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    store_id        = Column(UUID(as_uuid=True), ForeignKey("mkt_stores.id", ondelete="CASCADE"), nullable=False)
    allocated_stock = Column(Numeric(14, 3), default=0)
    reserved_stock  = Column(Numeric(14, 3), default=0)
    available_stock = Column(Numeric(14, 3), default=0)

    store = relationship("Store", back_populates="channel_stocks")


# ── Ad Performance ────────────────────────────────────────────────────────────

class AdPerformance(Base, TimestampMixin):
    __tablename__ = "mkt_ad_performance"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id          = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    platform             = Column(SAEnum(AdPlatform), nullable=False)
    ad_name              = Column(String(255), nullable=True)
    ad_date              = Column(Date, nullable=False)
    impressions          = Column(Integer, nullable=True)
    clicks               = Column(Integer, nullable=True)
    ctr                  = Column(Numeric(8, 6), nullable=True)
    cpc                  = Column(Numeric(10, 4), nullable=True)
    spend                = Column(Numeric(14, 2), nullable=True)
    conversions          = Column(Integer, nullable=True)
    conversion_rate      = Column(Numeric(8, 6), nullable=True)
    cost_per_conversion  = Column(Numeric(12, 4), nullable=True)
    revenue_generated    = Column(Numeric(16, 2), nullable=True)
    notes                = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="ad_performances")


# ── Return Analytics ──────────────────────────────────────────────────────────

class ReturnAnalytics(Base, TimestampMixin):
    __tablename__ = "mkt_return_analytics"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    store_id     = Column(UUID(as_uuid=True), ForeignKey("mkt_stores.id", ondelete="SET NULL"), nullable=True)
    return_date  = Column(Date, nullable=False)
    return_reason= Column(String(255), nullable=True)
    return_count = Column(Integer, default=0)
    return_rate  = Column(Numeric(8, 6), nullable=True)
    notes        = Column(Text, nullable=True)

    store = relationship("Store", back_populates="return_analytics")


# ── AI Campaign Optimizer ─────────────────────────────────────────────────────

class OptimizerRun(Base, TimestampMixin):
    __tablename__ = "mkt_optimizer_runs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date            = Column(Date, nullable=False)
    triggered_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    campaign_id         = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    campaign_context    = Column(Text, nullable=True)
    input_summary       = Column(JSONB, nullable=True)
    recommendation_json = Column(JSONB, nullable=True)
    status              = Column(SAEnum(OptimizerStatus), nullable=False, default=OptimizerStatus.PENDING)
    notes               = Column(Text, nullable=True)
    approved_by_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at         = Column(DateTime(timezone=True), nullable=True)

    campaign = relationship("Campaign", back_populates="optimizer_runs")
