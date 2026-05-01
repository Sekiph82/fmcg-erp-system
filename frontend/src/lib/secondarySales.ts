import { apiClient } from "@/lib/api";

export type UploadSource = "POS" | "ERP_INTEGRATION" | "MANUAL_CSV" | "MOBILE" | "API";
export type SecondarySalesStatus = "PENDING" | "VALIDATED" | "PROCESSED" | "REJECTED";
export type RetailChannel = "SUPERMARKET" | "KIOSK" | "WHOLESALE" | "PHARMACY" | "HOTEL" | "ONLINE" | "OTHER";

export interface Retailer {
  id: string;
  distributor_id?: string;
  distributor_name?: string;
  retailer_code?: string;
  name: string;
  location?: string;
  city?: string;
  channel?: RetailChannel;
  is_active: boolean;
}

export interface SecondarySalesLineInput {
  retailer_id?: string;
  retailer_name?: string;
  product_id?: string;
  product_sku?: string;
  quantity_sold: number;
  unit_price?: number;
  total_value?: number;
  sale_date?: string;
}

export interface SecondarySalesLineRead {
  id: string;
  header_id: string;
  retailer_id?: string;
  retailer_name?: string;
  product_id?: string;
  product_sku?: string;
  product_name?: string;
  quantity_sold: number;
  unit_price?: number;
  total_value?: number;
  sale_date?: string;
  is_valid: boolean;
  validation_note?: string;
}

export interface SecondarySalesHeader {
  id: string;
  reference_no: string;
  distributor_id: string;
  distributor_name?: string;
  period_from: string;
  period_to: string;
  upload_source: UploadSource;
  upload_date?: string;
  status: SecondarySalesStatus;
  notes?: string;
  validation_errors?: string;
  total_lines: number;
  total_value: number;
}

export interface SecondarySalesDetail extends SecondarySalesHeader {
  lines: SecondarySalesLineRead[];
}

export interface InventorySnapshot {
  id: string;
  distributor_id: string;
  distributor_name?: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  stock_qty: number;
  snapshot_date: string;
  sell_through_rate?: number;
  days_of_stock?: number;
  notes?: string;
}

export interface SellThroughRow {
  distributor_id: string;
  distributor_name: string;
  product_sku: string;
  product_name: string;
  sell_in_qty: number;
  sell_out_qty: number;
  sell_through_rate: number;
  stock_at_distributor?: number;
  days_of_stock?: number;
  status: "FAST_MOVING" | "NORMAL" | "SLOW_MOVING" | "NO_DATA";
}

export interface DistributorPerformanceRow {
  distributor_id: string;
  distributor_name: string;
  total_sell_out_value: number;
  total_sell_out_qty: number;
  line_count: number;
  period: string;
}

export interface ProductSellThroughRow {
  product_id: string;
  product_sku: string;
  product_name: string;
  total_qty_sold: number;
  total_value: number;
  distributor_count: number;
  avg_sell_through_rate?: number;
}

export interface AIInsightResult {
  agent: string;
  insights: string[];
  details?: any[];
  generated_at: string;
}

const BASE = "/api/v1/secondary-sales";

export const secondarySalesApi = {
  // Retailers
  async listRetailers(params?: { distributor_id?: string }): Promise<Retailer[]> {
    const res = await apiClient.get(`${BASE}/retailers`, { params });
    return res.data?.data ?? res.data;
  },
  async createRetailer(data: Omit<Retailer, "id" | "distributor_name">): Promise<Retailer> {
    const res = await apiClient.post(`${BASE}/retailers`, data);
    return res.data?.data ?? res.data;
  },

  // Secondary Sales
  async upload(data: {
    distributor_id: string;
    period_from: string;
    period_to: string;
    upload_source: UploadSource;
    notes?: string;
    lines: SecondarySalesLineInput[];
  }): Promise<SecondarySalesHeader> {
    const res = await apiClient.post(`${BASE}/upload`, data);
    return res.data?.data ?? res.data;
  },
  async list(params?: { distributor_id?: string; status?: SecondarySalesStatus; limit?: number }): Promise<SecondarySalesHeader[]> {
    const res = await apiClient.get(`${BASE}/`, { params });
    return res.data?.data ?? res.data;
  },
  async get(id: string): Promise<SecondarySalesDetail> {
    const res = await apiClient.get(`${BASE}/${id}`);
    return res.data?.data ?? res.data;
  },
  async process(id: string): Promise<SecondarySalesHeader> {
    const res = await apiClient.post(`${BASE}/${id}/process`);
    return res.data?.data ?? res.data;
  },
  async reject(id: string, reason: string): Promise<SecondarySalesHeader> {
    const res = await apiClient.post(`${BASE}/${id}/reject`, null, { params: { reason } });
    return res.data?.data ?? res.data;
  },

  // Inventory
  async listSnapshots(params?: { distributor_id?: string; product_id?: string }): Promise<InventorySnapshot[]> {
    const res = await apiClient.get(`${BASE}/inventory/snapshots`, { params });
    return res.data?.data ?? res.data;
  },
  async createSnapshot(data: { distributor_id: string; product_id: string; stock_qty: number; snapshot_date: string; notes?: string }): Promise<InventorySnapshot> {
    const res = await apiClient.post(`${BASE}/inventory/snapshots`, data);
    return res.data?.data ?? res.data;
  },

  // Reports
  async sellThroughReport(params?: { distributor_id?: string; date_from?: string; date_to?: string }): Promise<SellThroughRow[]> {
    const res = await apiClient.get(`${BASE}/report/sell-through`, { params });
    return res.data?.data ?? res.data;
  },
  async distributorPerformance(params?: { date_from?: string; date_to?: string }): Promise<DistributorPerformanceRow[]> {
    const res = await apiClient.get(`${BASE}/report/distributor-performance`, { params });
    return res.data?.data ?? res.data;
  },
  async productPerformance(params?: { date_from?: string; date_to?: string }): Promise<ProductSellThroughRow[]> {
    const res = await apiClient.get(`${BASE}/report/product-performance`, { params });
    return res.data?.data ?? res.data;
  },

  // AI
  async aiDemandSignal(params?: { date_from?: string; date_to?: string }): Promise<AIInsightResult> {
    const res = await apiClient.get(`${BASE}/ai/demand-signal`, { params });
    return res.data?.data ?? res.data;
  },
  async aiDistributorRisk(params?: { date_from?: string; date_to?: string }): Promise<AIInsightResult> {
    const res = await apiClient.get(`${BASE}/ai/distributor-risk`, { params });
    return res.data?.data ?? res.data;
  },
  async aiPromotionImpact(params?: { promo_start?: string; promo_end?: string }): Promise<AIInsightResult> {
    const res = await apiClient.get(`${BASE}/ai/promotion-impact`, { params });
    return res.data?.data ?? res.data;
  },
};
