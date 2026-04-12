import { apiClient } from "./api";

export interface TrendPoint { date: string; value: number; label?: string }
export interface DistributionSlice { label: string; value: number; count: number }
export interface ExceptionRow { id: string; label: string; detail: string; severity: string; href: string }

export interface InventoryAnalytics {
  total_stock_value: number;
  total_sku_count: number;
  low_stock_count: number;
  zero_stock_count: number;
  blocked_stock_count: number;
  product_count: number;
  material_count: number;
  movement_trend_30d: TrendPoint[];
  receipts_trend_30d: TrendPoint[];
  issues_trend_30d: TrendPoint[];
  by_movement_type: DistributionSlice[];
  low_stock_items: ExceptionRow[];
}

export interface ProductionAnalytics {
  total_orders: number;
  active_orders: number;
  completed_today: number;
  completion_rate: number;
  delayed_orders: number;
  machines_down: number;
  open_breakdowns: number;
  avg_downtime_hours: number;
  production_trend: TrendPoint[];
  plan_vs_actual: TrendPoint[];
  plan_vs_actual_actual: TrendPoint[];
  downtime_trend: TrendPoint[];
  rejection_trend: TrendPoint[];
  by_status: DistributionSlice[];
  exceptions: ExceptionRow[];
}

export interface ProcurementAnalytics {
  open_po_count: number;
  open_po_value: number;
  overdue_po_count: number;
  pending_pr_count: number;
  received_this_month: number;
  avg_po_lead_days: number;
  top_suppliers: DistributionSlice[];
  po_value_trend: TrendPoint[];
  grn_trend: TrendPoint[];
  exceptions: ExceptionRow[];
}

export interface SalesAnalytics {
  today_orders: number;
  today_revenue: number;
  mtd_revenue: number;
  ytd_revenue: number;
  open_orders: number;
  overdue_invoices: number;
  overdue_value: number;
  pending_shipments: number;
  avg_order_value: number;
  revenue_trend: TrendPoint[];
  order_count_trend: TrendPoint[];
  by_channel: DistributionSlice[];
  by_status: DistributionSlice[];
  top_customers: DistributionSlice[];
  exceptions: ExceptionRow[];
}

export interface FinanceAnalytics {
  cash_on_hand: number;
  bank_balance: number;
  open_receivables: number;
  overdue_receivables: number;
  open_payables: number;
  mtd_revenue: number;
  mtd_expenses: number;
  cash_receipts_trend: TrendPoint[];
  cash_payments_trend: TrendPoint[];
  by_account_type: DistributionSlice[];
  exceptions: ExceptionRow[];
}

export interface MpesaAnalytics {
  today_collected: number;
  today_transactions: number;
  today_success_rate: number;
  today_failed: number;
  today_pending: number;
  today_reversed: number;
  period_collected: number;
  period_total_transactions: number;
  period_failed: number;
  period_success_rate: number;
  avg_amount: number;
  avg_completion_time_minutes: number;
  daily_collection_trend: TrendPoint[];
  daily_transaction_count: TrendPoint[];
  daily_failure_count: TrendPoint[];
  by_status: DistributionSlice[];
  recent_failures: ExceptionRow[];
}

export interface DailyKPIs {
  as_of: string;
  daily_sales_amount: number;
  daily_sales_orders: number;
  open_receivables: number;
  stock_value: number;
  low_stock_count: number;
  zero_stock_count: number;
  production_plan_qty: number;
  production_actual_qty: number;
  production_completion_pct: number;
  purchase_delay_count: number;
  payment_collection_today: number;
  failed_payment_count: number;
  open_receivables_overdue: number;
  mpesa_collected_today: number;
  mpesa_success_rate: number;
  mpesa_pending_count: number;
  machines_down: number;
  open_breakdowns: number;
  sales_trend_7d: TrendPoint[];
  mpesa_trend_7d: TrendPoint[];
  production_trend_7d: TrendPoint[];
}

export interface MarketingBIKPIs {
  // Campaign
  completed_campaigns: number;
  active_campaigns: number;
  avg_campaign_roi: number;
  total_campaign_budget: number;
  total_campaign_revenue: number;
  overall_campaign_efficiency: number;
  // Spend
  total_trade_spend: number;
  total_brand_spend: number;
  trade_spend_vs_sales_pct: number;
  brand_spend_vs_revenue_pct: number;
  // Influencer
  active_influencers: number;
  total_influencer_revenue: number;
  avg_influencer_score: number;
  influencer_roi: number;
  // Social
  total_impressions: number;
  total_engagements: number;
  avg_engagement_rate: number;
  top_social_platform: string | null;
  // Ads
  total_ad_spend: number;
  total_ad_revenue: number;
  overall_roas: number;
  best_ad_platform: string | null;
  // E-commerce
  ecommerce_revenue: number;
  ecommerce_orders: number;
  avg_conversion_rate: number;
  overall_return_rate: number;
  // CRM
  total_crm_profiles: number;
  at_risk_customers: number;
  vip_customers: number;
  avg_engagement_score: number;
  // Survey
  avg_survey_sentiment: number;
  survey_count: number;
  // Attribution
  campaign_linked_orders: number;
  promotion_linked_orders: number;
  // Trends
  campaign_revenue_trend: TrendPoint[];
  trade_spend_trend: TrendPoint[];
  brand_spend_trend: TrendPoint[];
  ad_spend_trend: TrendPoint[];
  social_engagement_trend: TrendPoint[];
  // Distributions
  by_campaign_type: DistributionSlice[];
  by_ad_platform: DistributionSlice[];
  by_influencer_platform: DistributionSlice[];
  // Exceptions
  exceptions: ExceptionRow[];
}

// ── Marketing sub-dashboard types ─────────────────────────────────────────────

export interface CampaignDetailRow {
  id: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  region: string | null;
  budget: number;
  actual_revenue: number;
  actual_roi: number;
  start_date: string | null;
  end_date: string | null;
}

export interface MarketingCampaignsDetail {
  campaigns: CampaignDetailRow[];
  total_budget: number;
  total_revenue: number;
  avg_roi: number;
  by_type: DistributionSlice[];
  revenue_trend: TrendPoint[];
}

export interface InfluencerDetailRow {
  id: string;
  influencer_name: string;
  platform: string;
  handle: string | null;
  category: string | null;
  followers_count: number;
  attributed_revenue: number;
  agreed_fee: number;
  performance_score: number;
  roi: number;
}

export interface MarketingInfluencersDetail {
  influencers: InfluencerDetailRow[];
  total_revenue: number;
  total_fees: number;
  overall_roi: number;
  avg_score: number;
  by_platform: DistributionSlice[];
}

export interface AdPlatformRow {
  platform: string;
  spend: number;
  revenue: number;
  roas: number;
  impressions: number;
  clicks: number;
  conversions: number;
  days_active: number;
}

export interface MarketingAdsDetail {
  by_platform: AdPlatformRow[];
  spend_trend: TrendPoint[];
  revenue_trend: TrendPoint[];
  total_spend: number;
  total_revenue: number;
  overall_roas: number;
}

export interface SocialPlatformRow {
  platform: string;
  impressions: number;
  engagements: number;
  clicks: number;
  post_count: number;
  engagement_rate: number;
}

export interface MarketingSocialDetail {
  by_platform: SocialPlatformRow[];
  engagement_trend: TrendPoint[];
  impression_trend: TrendPoint[];
  total_impressions: number;
  total_engagements: number;
  avg_engagement_rate: number;
}

export interface StoreDetailRow {
  id: string;
  store_name: string;
  platform: string;
  region: string | null;
  total_revenue: number;
  total_orders: number;
  conversion_rate: number;
  return_rate: number;
  gross_margin: number;
}

export interface MarketingStoresDetail {
  stores: StoreDetailRow[];
  revenue_trend: TrendPoint[];
  total_revenue: number;
  total_orders: number;
  avg_conversion_rate: number;
  avg_return_rate: number;
  by_platform: DistributionSlice[];
}

export interface ReturnDetailRow {
  return_date: string;
  return_reason: string | null;
  return_count: number;
  return_rate: number;
}

export interface MarketingReturnsDetail {
  returns: ReturnDetailRow[];
  trend: TrendPoint[];
  total_returns: number;
  avg_return_rate: number;
  by_reason: DistributionSlice[];
}

const base = "/api/v1/analytics";

export const analyticsApi = {
  kpiDaily:    () => apiClient.get<DailyKPIs>(`${base}/kpi/daily`).then(r => r.data),
  inventory:   (days = 30) => apiClient.get<InventoryAnalytics>(`${base}/inventory`, { params: { days } }).then(r => r.data),
  production:  (days = 30) => apiClient.get<ProductionAnalytics>(`${base}/production`, { params: { days } }).then(r => r.data),
  procurement: (days = 30) => apiClient.get<ProcurementAnalytics>(`${base}/procurement`, { params: { days } }).then(r => r.data),
  sales:       (days = 30) => apiClient.get<SalesAnalytics>(`${base}/sales`, { params: { days } }).then(r => r.data),
  finance:     (days = 30) => apiClient.get<FinanceAnalytics>(`${base}/finance`, { params: { days } }).then(r => r.data),
  mpesa:       (days = 30) => apiClient.get<MpesaAnalytics>(`${base}/payments/mpesa`, { params: { days } }).then(r => r.data),
  marketing:      (days = 30) => apiClient.get<MarketingBIKPIs>(`${base}/marketing`, { params: { days } }).then(r => r.data),
  mktCampaigns:   (days = 30) => apiClient.get<MarketingCampaignsDetail>(`${base}/marketing/campaigns`, { params: { days } }).then(r => r.data),
  mktInfluencers: (days = 30) => apiClient.get<MarketingInfluencersDetail>(`${base}/marketing/influencers`, { params: { days } }).then(r => r.data),
  mktAds:         (days = 30) => apiClient.get<MarketingAdsDetail>(`${base}/marketing/ads`, { params: { days } }).then(r => r.data),
  mktSocial:      (days = 30) => apiClient.get<MarketingSocialDetail>(`${base}/marketing/social`, { params: { days } }).then(r => r.data),
  mktStores:      (days = 30) => apiClient.get<MarketingStoresDetail>(`${base}/marketing/stores`, { params: { days } }).then(r => r.data),
  mktReturns:     (days = 30) => apiClient.get<MarketingReturnsDetail>(`${base}/marketing/returns`, { params: { days } }).then(r => r.data),
};

export function fmt(n: number, decimals = 0): string {
  return new Intl.NumberFormat("en-KE", { maximumFractionDigits: decimals }).format(n);
}

export function fmtKES(n: number): string {
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`;
  return `KES ${n.toFixed(0)}`;
}
