import { apiClient } from "./api";

export type PricingLevel = "STANDARD" | "REGION" | "DISTRIBUTOR" | "CUSTOMER";
export type PromoType = "DISCOUNT" | "BUNDLE" | "VOLUME";
export type DiscountType = "PERCENTAGE" | "FIXED_AMOUNT";

export interface PricingRule {
  id: string;
  product_id: string;
  product_name?: string;
  pricing_level: PricingLevel;
  region?: string;
  distributor_id?: string;
  distributor_name?: string;
  customer_id?: string;
  customer_name?: string;
  unit_price: number;
  currency: string;
  min_quantity?: number;
  effective_from?: string;
  effective_to?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
}

export interface Promotion {
  id: string;
  code: string;
  name: string;
  description?: string;
  promo_type: PromoType;
  discount_type?: DiscountType;
  discount_value?: number;
  min_order_value?: number;
  buy_quantity?: number;
  get_quantity?: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  region?: string;
  product_ids: string[];
  created_at: string;
}

export const pricingApi = {
  listRules: (params?: { product_id?: string; pricing_level?: PricingLevel; region?: string; active_only?: boolean }) =>
    apiClient.get<PricingRule[]>("/api/v1/pricing/rules", { params }).then((r) => r.data),
  createRule: (data: Partial<PricingRule>) =>
    apiClient.post<PricingRule>("/api/v1/pricing/rules", data).then((r) => r.data),
  updateRule: (id: string, data: Partial<PricingRule>) =>
    apiClient.patch<PricingRule>(`/api/v1/pricing/rules/${id}`, data).then((r) => r.data),

  listPromotions: (params?: { active_only?: boolean; region?: string }) =>
    apiClient.get<Promotion[]>("/api/v1/pricing/promotions", { params }).then((r) => r.data),
  createPromotion: (data: Partial<Promotion> & { products?: { product_id: string }[] }) =>
    apiClient.post<Promotion>("/api/v1/pricing/promotions", data).then((r) => r.data),
  updatePromotion: (id: string, data: Partial<Promotion>) =>
    apiClient.patch<Promotion>(`/api/v1/pricing/promotions/${id}`, data).then((r) => r.data),
};

export const LEVEL_COLORS: Record<PricingLevel, string> = {
  STANDARD: "bg-gray-100 text-gray-700",
  REGION: "bg-blue-100 text-blue-700",
  DISTRIBUTOR: "bg-purple-100 text-purple-700",
  CUSTOMER: "bg-green-100 text-green-700",
};
