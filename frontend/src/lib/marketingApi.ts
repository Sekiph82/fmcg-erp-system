/**
 * Marketing Module API Client
 * Typed wrappers for all marketing endpoints.
 */
import { apiClient as api } from "./api";

// ── Enums ─────────────────────────────────────────────────────────────────────

export type CampaignType =
  | "TRADE" | "DIGITAL" | "RETAIL" | "DISTRIBUTOR" | "LAUNCH"
  | "SEASONAL" | "LOYALTY" | "AWARENESS" | "ACQUISITION" | "RETENTION";

export type CampaignStatus =
  | "DRAFT" | "PLANNED" | "ACTIVE" | "PAUSED" | "COMPLETED" | "CANCELLED";

export type PromotionType =
  | "DISCOUNT" | "BUNDLE" | "FREE_ITEM" | "REBATE" | "BUY_X_GET_Y"
  | "RETAILER_SUPPORT" | "DISTRIBUTOR_SUPPORT" | "CASHBACK";

export type DiscountType = "PERCENTAGE" | "FIXED";

export type SegmentType =
  | "RETAIL" | "WHOLESALE" | "KIOSK" | "SUPERMARKET" | "DISTRIBUTOR"
  | "HORECA" | "PHARMACY" | "MODERN_TRADE" | "GENERAL_TRADE" | "ONLINE";

export type RelationshipStatus =
  | "PROSPECT" | "ACTIVE" | "AT_RISK" | "DORMANT" | "CHURNED" | "VIP";

export type LoyaltyStatus = "BRONZE" | "SILVER" | "GOLD" | "PLATINUM" | "NONE";

export type AcquisitionSource =
  | "ADS" | "INFLUENCER" | "ORGANIC" | "REFERRAL" | "MARKETPLACE"
  | "DIRECT" | "SOCIAL" | "FIELD_SALES" | "EVENT" | "OTHER";

export type VisitType =
  | "SALES" | "MARKETING" | "TRADE_AUDIT" | "MERCHANDISING" | "FEEDBACK" | "STORE_CHECK";

export type TradeSpendType =
  | "DISCOUNT_SUPPORT" | "DISPLAY_FEE" | "SHELF_PLACEMENT"
  | "ACTIVATION_SUPPORT" | "REBATE" | "DISTRIBUTOR_SUPPORT" | "MERCHANDISING";

export type BrandSpendCategory =
  | "TV" | "RADIO" | "DIGITAL_ADS" | "INFLUENCER" | "EVENT" | "SAMPLING"
  | "BRANDING_MATERIAL" | "AGENCY_COST" | "CREATIVE_PRODUCTION" | "MEDIA_BUYING";

export type SurveyType =
  | "CUSTOMER_FEEDBACK" | "MARKET_AUDIT" | "RETAILER_FEEDBACK"
  | "BRAND_AWARENESS" | "COMPETITOR_CHECK" | "PRODUCT_FEEDBACK" | "SHELF_AUDIT";

export type InfluencerPlatform =
  | "INSTAGRAM" | "TIKTOK" | "YOUTUBE" | "FACEBOOK" | "X" | "OTHER";

export type InfluencerStatus = "PROSPECT" | "ACTIVE" | "INACTIVE" | "BLOCKED";

export type ContentType = "POST" | "STORY" | "REEL" | "VIDEO" | "LIVE" | "BLOG" | "OTHER";

export type SentimentScore = "POSITIVE" | "NEUTRAL" | "NEGATIVE";

export type StorePlatform =
  | "JUMIA" | "KILIMALL" | "SHOPIFY" | "WOOCOMMERCE" | "AMAZON"
  | "TIKTOK_SHOP" | "INSTAGRAM_SHOP" | "OTHER";

export type StoreStatus = "ACTIVE" | "INACTIVE" | "PENDING";

export type AdPlatform =
  | "META" | "GOOGLE" | "TIKTOK" | "TWITTER" | "LINKEDIN" | "YOUTUBE" | "OTHER";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";

export type OptimizerStatus = "PENDING" | "COMPLETE" | "APPROVED" | "ARCHIVED";

// ── Entity interfaces ─────────────────────────────────────────────────────────

export interface Campaign {
  id: string;
  campaign_code: string;
  campaign_name: string;
  campaign_type: CampaignType;
  objective: string | null;
  region: string | null;
  country: string | null;
  start_date: string;
  end_date: string;
  status: CampaignStatus;
  budget: string | null;
  expected_revenue: string | null;
  actual_revenue: string | null;
  expected_roi: string | null;
  actual_roi: string | null;
  approval_status: ApprovalStatus;
  owner_user_id: string | null;
  approved_by_id: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface MktPromotion {
  id: string;
  promotion_name: string;
  promotion_code: string | null;
  promotion_type: PromotionType;
  status: string;
  campaign_id: string | null;
  segment_id: string | null;
  product_id: string | null;
  region: string | null;
  start_date: string;
  end_date: string;
  discount_type: DiscountType | null;
  discount_value: string | null;
  minimum_quantity: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface MarketingDashboard {
  campaign_by_status: Record<string, number>;
  active_campaigns: number;
  planned_campaigns: number;
  draft_campaigns: number;
  completed_campaigns: number;
  total_budget: number;
  total_expected_revenue: number;
  total_actual_revenue: number;
  expected_roi: number;
  actual_roi: number;
  budget_vs_actual: Array<{
    name: string;
    budget: number;
    actual_revenue: number;
    expected_revenue: number;
  }>;
  total_promotions: number;
  active_promotions: number;
  promotion_by_status: Record<string, number>;
  promotions_by_region: Array<{ region: string; count: number }>;
  recent_campaigns: Array<{ name: string; start_date: string; status: string }>;
}

export interface CustomerSegment {
  id: string;
  segment_name: string;
  segment_type: SegmentType;
  region: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface CRMProfile {
  id: string;
  customer_id: string;
  segment_id: string | null;
  relationship_status: RelationshipStatus;
  loyalty_status: LoyaltyStatus;
  acquisition_source: AcquisitionSource | null;
  acquisition_campaign_id: string | null;
  acquisition_channel: string | null;
  first_touch_source: string | null;
  last_touch_source: string | null;
  last_contact_date: string | null;
  next_followup_date: string | null;
  engagement_score: string | null;
  estimated_ltv: string | null;
  churn_risk_score: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface CustomerInteraction {
  id: string;
  crm_profile_id: string;
  interaction_date: string;
  channel: string | null;
  summary: string | null;
  outcome: string | null;
  follow_up_date: string | null;
  recorded_by_id: string | null;
  created_at: string | null;
}

export interface CustomerVisit {
  id: string;
  customer_id: string | null;
  crm_profile_id: string | null;
  employee_id: string | null;
  visit_date: string;
  visit_type: VisitType;
  purpose: string | null;
  outcome: string | null;
  followup_required: boolean;
  competitor_notes: string | null;
  display_observation: string | null;
  stock_observation: string | null;
  created_at: string | null;
}

export interface Survey {
  id: string;
  survey_name: string;
  survey_type: SurveyType;
  region: string | null;
  survey_date: string;
  target_segment_id: string | null;
  questions_json: Record<string, unknown> | null;
  responses_json: Record<string, unknown> | null;
  summary: string | null;
  sentiment_score: string | null;
  competitor_notes: string | null;
  response_count: number;
  conducted_by_id: string | null;
  created_at: string | null;
}

export interface Influencer {
  id: string;
  influencer_name: string;
  platform: InfluencerPlatform;
  handle: string | null;
  category: string | null;
  region: string | null;
  followers_count: number | null;
  engagement_rate: string | null;
  contact_info: string | null;
  status: InfluencerStatus;
  notes: string | null;
  created_at: string | null;
}

export interface InfluencerCampaignLink {
  id: string;
  influencer_id: string;
  campaign_id: string;
  content_type: ContentType | null;
  tracking_link: string | null;
  agreed_fee: string | null;
  paid_fee: string | null;
  expected_posts: number | null;
  actual_posts: number | null;
  impressions: number | null;
  clicks: number | null;
  conversions: number | null;
  attributed_revenue: string | null;
  performance_score: string | null;
  sentiment: SentimentScore | null;
  notes: string | null;
}

export interface InfluencerAttribution {
  id: string;
  influencer_id: string;
  campaign_id: string | null;
  tracking_link: string | null;
  clicks: number;
  conversions: number;
  attributed_revenue: string | null;
  attributed_orders: number;
  attribution_date: string;
  created_at: string | null;
}

export interface SocialMediaActivity {
  id: string;
  campaign_id: string | null;
  platform: InfluencerPlatform;
  content_type: ContentType | null;
  published_date: string;
  post_url: string | null;
  impressions: number | null;
  reach: number | null;
  clicks: number | null;
  engagements: number | null;
  comments_count: number | null;
  shares_count: number | null;
  saves_count: number | null;
  notes: string | null;
  created_at: string | null;
}

export interface MktStore {
  id: string;
  store_name: string;
  platform: StorePlatform;
  status: StoreStatus;
  url: string | null;
  region: string | null;
  owner: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface StorePerformance {
  id: string;
  store_id: string;
  perf_date: string;
  total_orders: number;
  total_units_sold: number;
  total_revenue: string | null;
  gross_margin: string | null;
  ad_spend: string | null;
  impressions: number | null;
  clicks: number | null;
  conversions: number | null;
  returns_count: number;
  net_revenue: string | null;
  notes: string | null;
}

export interface ProductChannelPerformance {
  id: string;
  product_id: string;
  store_id: string;
  perf_date: string;
  units_sold: number;
  revenue: string | null;
  impressions: number | null;
  clicks: number | null;
  conversion_rate: string | null;
  return_rate: string | null;
  ranking: number | null;
  stock_level: number | null;
}

export interface AdPerformance {
  id: string;
  campaign_id: string | null;
  platform: AdPlatform;
  ad_name: string | null;
  ad_date: string;
  impressions: number | null;
  clicks: number | null;
  ctr: string | null;
  cpc: string | null;
  spend: string | null;
  conversions: number | null;
  cost_per_conversion: string | null;
  revenue_generated: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface TradeSpend {
  id: string;
  campaign_id: string | null;
  customer_id: string | null;
  distributor_id: string | null;
  spend_type: TradeSpendType;
  amount: string;
  currency: string;
  spend_date: string;
  approval_status: ApprovalStatus;
  approved_by_id: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface BrandSpend {
  id: string;
  campaign_id: string | null;
  spend_category: BrandSpendCategory;
  vendor: string | null;
  amount: string;
  currency: string;
  spend_date: string;
  approval_status: ApprovalStatus;
  approved_by_id: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface ReturnAnalytics {
  id: string;
  product_id: string;
  store_id: string | null;
  return_date: string;
  return_reason: string | null;
  return_count: number;
  return_rate: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface ChannelStock {
  id: string;
  product_id: string;
  store_id: string;
  allocated_stock: string;
  reserved_stock: string;
  available_stock: string;
  created_at: string | null;
}

export interface EcommerceAnalytics {
  period_days: number;
  total_revenue: number;
  total_orders: number;
  total_units_sold: number;
  avg_order_value: number;
  total_ad_spend: number;
  overall_roas: number;
  overall_return_rate: number;
  channel_breakdown: Array<{
    store_name: string;
    platform: string;
    revenue: number;
    orders: number;
    units: number;
    ad_spend: number;
    roas: number;
    return_rate: number;
    conv_rate: number;
  }>;
  top_products: Array<{
    product_id: string;
    revenue: number;
    units: number;
    return_rate: number;
  }>;
  return_reasons: Array<{ reason: string; count: number }>;
}

export interface OptimizerRun {
  id: string;
  run_date: string;
  triggered_by_id: string | null;
  campaign_id: string | null;
  campaign_context: string | null;
  input_summary: Record<string, unknown> | null;
  recommendation_json: OptimizerRecommendations | null;
  status: OptimizerStatus;
  notes: string | null;
  approved_by_id: string | null;
  approved_at: string | null;
  created_at: string | null;
}

export interface OptimizerSegment {
  name: string;
  type: string;
  avg_ltv: number;
  engagement: number;
  churn_risk: number;
}

export interface OptimizerRecommendations {
  best_target_segments: { segments: OptimizerSegment[]; reason: string };
  best_target_regions: { regions: Array<{ name: string; avg_roi: number; revenue: number }>; reason: string };
  best_acquisition_channels: { channels: Array<{ source: string; avg_ltv: number; count: number }>; reason: string };
  best_campaign_type: { value: string; all_types: Array<{ type: string; avg_roi: number; efficiency: number }>; reason: string };
  best_promotion_type: { primary: string; secondary: string; reason: string };
  best_budget_split: { trade_spend_pct: number; brand_spend_pct: number; digital_of_brand_pct: number; influencer_of_brand_pct: number; brand_by_category: Array<{ category: string; amount: number }>; reason: string };
  best_store_channel_mix: { top_stores: Array<{ store: string; platform: string; revenue: number; cvr: number }>; reason: string };
  best_ad_platform_mix: { platforms: Array<{ platform: string; roas: number; spend: number; conversions: number }>; reason: string };
  best_influencer_mix: { platforms: Array<{ platform: string; revenue: number; score: number; roi: number }>; reason: string };
  best_social_platforms: { platforms: Array<{ platform: string; eng_rate: number; impressions: number }>; reason: string };
  product_channel_fit: { top_combos: Array<{ product_id: string; store: string; platform: string; revenue: number; cvr: number; return_rate: number }>; reason: string };
  return_risk_signals: { high_return_channels: Array<{ store: string; platform: string; return_rate: number; returns: number }>; reason: string };
  predicted_roi_range: { low: number; high: number; basis: string };
  predicted_uplift: { pct: number; basis: string };
  risk_notes: string[];
  scaling_suggestions: string[];
  campaign_improvement_suggestions: string[];
  content_suggestions: string[];
}

export interface MarketingAnalyticsSummary {
  period_days: number;
  active_campaigns: number;
  total_trade_spend: number;
  total_brand_spend: number;
  total_spend: number;
  campaign_revenue: number;
  campaign_roi_avg: number;
  crm_profiles: number;
  at_risk_customers: number;
  vip_customers: number;
  visits_this_period: number;
  active_influencers: number;
  store_gmv: number;
  total_ad_spend: number;
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// ── API client ────────────────────────────────────────────────────────────────

export const marketingApi = {
  // Campaigns
  campaigns: {
    list: (p?: { skip?: number; limit?: number; status?: string; region?: string }) =>
      api.get<Campaign[]>("/api/v1/marketing/campaigns", { params: p }),
    get: (id: string) => api.get<Campaign>(`/api/v1/marketing/campaigns/${id}`),
    create: (data: Record<string, unknown>) => api.post<Campaign>("/api/v1/marketing/campaigns", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<Campaign>(`/api/v1/marketing/campaigns/${id}`, data),
    approve: (id: string) => api.post<{ status: string }>(`/api/v1/marketing/campaigns/${id}/approve`),
    delete: (id: string) => api.delete(`/api/v1/marketing/campaigns/${id}`),
  },

  // Promotions
  promotions: {
    list: (p?: { skip?: number; limit?: number; status?: string; campaign_id?: string }) =>
      api.get<MktPromotion[]>("/api/v1/marketing/promotions", { params: p }),
    get: (id: string) => api.get<MktPromotion>(`/api/v1/marketing/promotions/${id}`),
    create: (data: Record<string, unknown>) => api.post<MktPromotion>("/api/v1/marketing/promotions", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<MktPromotion>(`/api/v1/marketing/promotions/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/promotions/${id}`),
  },

  // Segments
  segments: {
    list: (p?: { skip?: number; limit?: number; segment_type?: string; region?: string }) =>
      api.get<CustomerSegment[]>("/api/v1/marketing/segments", { params: p }),
    get: (id: string) => api.get<CustomerSegment>(`/api/v1/marketing/segments/${id}`),
    create: (data: Record<string, unknown>) => api.post<CustomerSegment>("/api/v1/marketing/segments", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<CustomerSegment>(`/api/v1/marketing/segments/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/segments/${id}`),
  },

  // CRM
  crm: {
    list: (p?: { skip?: number; limit?: number; segment_id?: string; status?: string }) =>
      api.get<CRMProfile[]>("/api/v1/marketing/crm", { params: p }),
    get: (id: string) => api.get<CRMProfile>(`/api/v1/marketing/crm/${id}`),
    create: (data: Record<string, unknown>) => api.post<CRMProfile>("/api/v1/marketing/crm", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<CRMProfile>(`/api/v1/marketing/crm/${id}`, data),
    interactions: (crmId: string) => api.get<CustomerInteraction[]>(`/api/v1/marketing/crm/${crmId}/interactions`),
    addInteraction: (crmId: string, data: Record<string, unknown>) =>
      api.post<CustomerInteraction>(`/api/v1/marketing/crm/${crmId}/interactions`, data),
  },

  // Visits
  visits: {
    list: (p?: { skip?: number; limit?: number; visit_type?: string; employee_id?: string }) =>
      api.get<CustomerVisit[]>("/api/v1/marketing/visits", { params: p }),
    get: (id: string) => api.get<CustomerVisit>(`/api/v1/marketing/visits/${id}`),
    create: (data: Record<string, unknown>) => api.post<CustomerVisit>("/api/v1/marketing/visits", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<CustomerVisit>(`/api/v1/marketing/visits/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/visits/${id}`),
  },

  // Trade Spend
  tradeSpend: {
    list: (p?: { skip?: number; limit?: number; campaign_id?: string; customer_id?: string; distributor_id?: string; spend_type?: string; status?: string }) =>
      api.get<TradeSpend[]>("/api/v1/marketing/trade-spend", { params: p }),
    get: (id: string) => api.get<TradeSpend>(`/api/v1/marketing/trade-spend/${id}`),
    create: (data: Record<string, unknown>) => api.post<TradeSpend>("/api/v1/marketing/trade-spend", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<TradeSpend>(`/api/v1/marketing/trade-spend/${id}`, data),
    approve: (id: string) => api.post<{ status: string }>(`/api/v1/marketing/trade-spend/${id}/approve`),
    delete: (id: string) => api.delete(`/api/v1/marketing/trade-spend/${id}`),
  },

  // Brand Spend
  brandSpend: {
    list: (p?: { skip?: number; limit?: number; campaign_id?: string; spend_category?: string; status?: string }) =>
      api.get<BrandSpend[]>("/api/v1/marketing/brand-spend", { params: p }),
    get: (id: string) => api.get<BrandSpend>(`/api/v1/marketing/brand-spend/${id}`),
    create: (data: Record<string, unknown>) => api.post<BrandSpend>("/api/v1/marketing/brand-spend", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<BrandSpend>(`/api/v1/marketing/brand-spend/${id}`, data),
    approve: (id: string) => api.post<{ status: string }>(`/api/v1/marketing/brand-spend/${id}/approve`),
    delete: (id: string) => api.delete(`/api/v1/marketing/brand-spend/${id}`),
  },

  // Surveys
  surveys: {
    list: (p?: { skip?: number; limit?: number; survey_type?: string; region?: string }) =>
      api.get<Survey[]>("/api/v1/marketing/surveys", { params: p }),
    get: (id: string) => api.get<Survey>(`/api/v1/marketing/surveys/${id}`),
    create: (data: Record<string, unknown>) => api.post<Survey>("/api/v1/marketing/surveys", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<Survey>(`/api/v1/marketing/surveys/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/surveys/${id}`),
  },

  // Influencers
  influencers: {
    list: (p?: { skip?: number; limit?: number; platform?: string; status?: string }) =>
      api.get<Influencer[]>("/api/v1/marketing/influencers", { params: p }),
    get: (id: string) => api.get<Influencer>(`/api/v1/marketing/influencers/${id}`),
    create: (data: Record<string, unknown>) => api.post<Influencer>("/api/v1/marketing/influencers", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<Influencer>(`/api/v1/marketing/influencers/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/influencers/${id}`),
  },

  // Influencer links & attribution
  influencerLinks: {
    list: (influencerId: string) =>
      api.get<InfluencerCampaignLink[]>(`/api/v1/marketing/influencers/${influencerId}/links`),
    create: (data: Record<string, unknown>) =>
      api.post<InfluencerCampaignLink>("/api/v1/marketing/influencer-links", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<InfluencerCampaignLink>(`/api/v1/marketing/influencer-links/${id}`, data),
  },

  attribution: {
    list: (p?: { influencer_id?: string; campaign_id?: string }) =>
      api.get<InfluencerAttribution[]>("/api/v1/marketing/influencer-attribution", { params: p }),
    create: (data: Record<string, unknown>) =>
      api.post<InfluencerAttribution>("/api/v1/marketing/influencer-attribution", data),
  },

  // Social Media
  social: {
    list: (p?: { skip?: number; limit?: number; campaign_id?: string; platform?: string }) =>
      api.get<SocialMediaActivity[]>("/api/v1/marketing/social-media", { params: p }),
    get: (id: string) => api.get<SocialMediaActivity>(`/api/v1/marketing/social-media/${id}`),
    create: (data: Record<string, unknown>) => api.post<SocialMediaActivity>("/api/v1/marketing/social-media", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<SocialMediaActivity>(`/api/v1/marketing/social-media/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/social-media/${id}`),
  },

  // Stores
  stores: {
    list: (p?: { skip?: number; limit?: number; platform?: string; status?: string }) =>
      api.get<MktStore[]>("/api/v1/marketing/ecommerce/stores", { params: p }),
    get: (id: string) => api.get<MktStore>(`/api/v1/marketing/ecommerce/stores/${id}`),
    create: (data: Record<string, unknown>) => api.post<MktStore>("/api/v1/marketing/ecommerce/stores", data),
    update: (id: string, data: Record<string, unknown>) => api.patch<MktStore>(`/api/v1/marketing/ecommerce/stores/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/ecommerce/stores/${id}`),
  },

  // Store Performance
  storePerformance: {
    list: (p?: { skip?: number; limit?: number; store_id?: string; date_from?: string; date_to?: string }) =>
      api.get<StorePerformance[]>("/api/v1/marketing/ecommerce/performance", { params: p }),
    get: (id: string) => api.get<StorePerformance>(`/api/v1/marketing/ecommerce/performance/${id}`),
    create: (data: Record<string, unknown>) =>
      api.post<StorePerformance>("/api/v1/marketing/ecommerce/performance", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<StorePerformance>(`/api/v1/marketing/ecommerce/performance/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/ecommerce/performance/${id}`),
  },

  // Product Channel Performance
  channelPerformance: {
    list: (p?: { skip?: number; limit?: number; store_id?: string; product_id?: string }) =>
      api.get<ProductChannelPerformance[]>("/api/v1/marketing/ecommerce/products", { params: p }),
    get: (id: string) => api.get<ProductChannelPerformance>(`/api/v1/marketing/ecommerce/products/${id}`),
    create: (data: Record<string, unknown>) =>
      api.post<ProductChannelPerformance>("/api/v1/marketing/ecommerce/products", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<ProductChannelPerformance>(`/api/v1/marketing/ecommerce/products/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/ecommerce/products/${id}`),
  },

  // Channel Stock
  channelStock: {
    list: (p?: { store_id?: string; product_id?: string }) =>
      api.get<ChannelStock[]>("/api/v1/marketing/ecommerce/channel-stock", { params: p }),
    upsert: (data: Record<string, unknown>) =>
      api.post<ChannelStock>("/api/v1/marketing/ecommerce/channel-stock", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<ChannelStock>(`/api/v1/marketing/ecommerce/channel-stock/${id}`, data),
  },

  // Ads
  ads: {
    list: (p?: { skip?: number; limit?: number; campaign_id?: string; platform?: string }) =>
      api.get<AdPerformance[]>("/api/v1/marketing/ads", { params: p }),
    get: (id: string) => api.get<AdPerformance>(`/api/v1/marketing/ads/${id}`),
    create: (data: Record<string, unknown>) => api.post<AdPerformance>("/api/v1/marketing/ads", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<AdPerformance>(`/api/v1/marketing/ads/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/ads/${id}`),
  },

  // Return Analytics
  returns: {
    list: (p?: { skip?: number; limit?: number; product_id?: string; store_id?: string }) =>
      api.get<ReturnAnalytics[]>("/api/v1/marketing/returns", { params: p }),
    get: (id: string) => api.get<ReturnAnalytics>(`/api/v1/marketing/returns/${id}`),
    create: (data: Record<string, unknown>) =>
      api.post<ReturnAnalytics>("/api/v1/marketing/returns", data),
    update: (id: string, data: Record<string, unknown>) =>
      api.patch<ReturnAnalytics>(`/api/v1/marketing/returns/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/marketing/returns/${id}`),
  },

  // E-commerce Analytics
  ecommerceAnalytics: (days = 30) =>
    api.get<EcommerceAnalytics>("/api/v1/marketing/ecommerce/analytics", { params: { days } }),

  // AI Optimizer
  optimizer: {
    run: (data?: { campaign_id?: string; campaign_context?: string; notes?: string }) =>
      api.post<OptimizerRun>("/api/v1/marketing/optimizer/run", data ?? {}),
    list: (p?: { skip?: number; limit?: number }) =>
      api.get<OptimizerRun[]>("/api/v1/marketing/optimizer/runs", { params: p }),
    get: (id: string) => api.get<OptimizerRun>(`/api/v1/marketing/optimizer/runs/${id}`),
    approve: (id: string, notes?: string) =>
      api.post<{ status: string }>(`/api/v1/marketing/optimizer/runs/${id}/approve`, { notes }),
  },

  // Analytics
  analytics: {
    summary: (days: number = 30) =>
      api.get<MarketingAnalyticsSummary>("/api/v1/marketing/analytics/summary", { params: { days } }),
    dashboard: () =>
      api.get<MarketingDashboard>("/api/v1/marketing/analytics/dashboard"),
  },
};

// ── Label / color helpers ─────────────────────────────────────────────────────

export const CAMPAIGN_STATUS_COLORS: Record<CampaignStatus, string> = {
  DRAFT:     "text-slate-400",
  PLANNED:   "text-blue-400",
  ACTIVE:    "text-emerald-400",
  PAUSED:    "text-yellow-400",
  COMPLETED: "text-sky-400",
  CANCELLED: "text-red-400",
};

export const APPROVAL_STATUS_COLORS: Record<ApprovalStatus, string> = {
  PENDING:  "text-yellow-400",
  APPROVED: "text-emerald-400",
  REJECTED: "text-red-400",
};

export const INFLUENCER_STATUS_COLORS: Record<InfluencerStatus, string> = {
  PROSPECT: "text-blue-400",
  ACTIVE:   "text-emerald-400",
  INACTIVE: "text-slate-400",
  BLOCKED:  "text-red-400",
};

export const CRM_STATUS_COLORS: Record<RelationshipStatus, string> = {
  PROSPECT: "text-blue-400",
  ACTIVE:   "text-emerald-400",
  AT_RISK:  "text-orange-400",
  DORMANT:  "text-slate-400",
  CHURNED:  "text-red-400",
  VIP:      "text-yellow-300",
};

export const STORE_STATUS_COLORS: Record<StoreStatus, string> = {
  ACTIVE:   "text-emerald-400",
  INACTIVE: "text-slate-400",
  PENDING:  "text-yellow-400",
};
