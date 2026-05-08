import { apiClient } from "@/lib/api";

const BASE = "/api/v1/loyalty";

export interface LoyaltyTier {
  id: string;
  tier_code: string;
  tier_name: string;
  min_lifetime_points: number;
  points_per_100_spend: number;
  discount_pct: number;
  perks: string[];
  color: string;
  member_count: number;
}

export interface LoyaltyAccount {
  id: string;
  customer_id: string;
  customer_name?: string;
  customer_code?: string;
  tier_id?: string;
  tier_name: string;
  tier_color: string;
  total_points: number;
  lifetime_points: number;
  enrolled_at?: string;
  last_activity_at?: string;
}

export interface LoyaltyTransaction {
  id: string;
  transaction_type: string;
  points_delta: number;
  description?: string;
  balance_after: number;
  reference_type?: string;
  reference_id?: string;
  created_by_name?: string;
  created_at: string;
}

export interface LoyaltyAccountDetail extends LoyaltyAccount {
  discount_pct: number;
  transactions: LoyaltyTransaction[];
}

export interface LoyaltyStats {
  total_members: number;
  total_points_outstanding: number;
  total_transactions: number;
  top_members: { customer_name?: string; tier_name: string; total_points: number }[];
}

export const loyaltyApi = {
  listTiers: () => apiClient.get<LoyaltyTier[]>(`${BASE}/tiers`).then(r => r.data),
  createTier: (data: object) => apiClient.post<{ id: string }>(`${BASE}/tiers`, data).then(r => r.data),
  updateTier: (id: string, data: object) => apiClient.patch<{ id: string }>(`${BASE}/tiers/${id}`, data).then(r => r.data),

  listAccounts: (params?: { tier_id?: string; limit?: number }) =>
    apiClient.get<LoyaltyAccount[]>(`${BASE}/accounts`, { params }).then(r => r.data),
  getAccount: (customerId: string) =>
    apiClient.get<LoyaltyAccountDetail>(`${BASE}/accounts/${customerId}`).then(r => r.data),
  enrollCustomer: (data: { customer_id: string; initial_points?: number }) =>
    apiClient.post<{ id: string }>(`${BASE}/accounts/enroll`, data).then(r => r.data),

  earnPoints: (customerId: string, data: { points?: number; spend_amount?: number; description?: string; reference_type?: string; reference_id?: string }) =>
    apiClient.post<{ points_earned: number; total_points: number }>(`${BASE}/accounts/${customerId}/earn`, data).then(r => r.data),
  redeemPoints: (customerId: string, data: { points: number; description?: string }) =>
    apiClient.post<{ points_redeemed: number; total_points: number }>(`${BASE}/accounts/${customerId}/redeem`, data).then(r => r.data),

  getStats: () => apiClient.get<LoyaltyStats>(`${BASE}/stats`).then(r => r.data),
};

export const TXN_COLORS: Record<string, string> = {
  EARN: "text-green-600",
  REDEEM: "text-red-600",
  BONUS: "text-blue-600",
  EXPIRE: "text-gray-500",
  ADJUST: "text-amber-600",
};
