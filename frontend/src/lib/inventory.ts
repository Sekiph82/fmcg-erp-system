import { apiClient } from "./api";

export type MovementType = "RECEIPT" | "ISSUE" | "TRANSFER" | "ADJUSTMENT" | "RETURN" | "WRITE_OFF";
export type StockType = "PRODUCT" | "MATERIAL";

export interface Stock {
  id: string;
  stock_type: StockType;
  warehouse_id: string;
  product_id?: string;
  material_id?: string;
  lot_id?: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
}

export interface StockSummary {
  id: string;
  stock_type: StockType;
  product_id?: string;
  product_sku?: string;
  product_name?: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  lot_id?: string;
  lot_number?: string;
  expiry_date?: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  is_below_reorder: boolean;
}

export interface MovementDetail {
  id: string;
  reference_number: string;
  movement_type: MovementType;
  stock_type: StockType;
  movement_date: string;
  product_id?: string;
  product_sku?: string;
  product_name?: string;
  lot_id?: string;
  source_warehouse_id?: string;
  source_warehouse_name?: string;
  destination_warehouse_id?: string;
  destination_warehouse_name?: string;
  quantity: number;
  unit_cost?: number;
  total_cost?: number;
  notes?: string;
  created_by_id?: string;
  created_by_username?: string;
}

export interface StockEntryRequest {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  lot_number?: string;
  expiry_date?: string;
  unit_cost?: number;
  reference: string;
  notes?: string;
}

export interface StockIssueRequest {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  lot_number?: string;
  reference: string;
  notes?: string;
}

export interface StockTransferRequest {
  product_id: string;
  from_warehouse_id: string;
  to_warehouse_id: string;
  quantity: number;
  lot_number?: string;
  reference: string;
  notes?: string;
}

export interface InsufficientStockError {
  error: "INSUFFICIENT_STOCK";
  message: string;
  available: number;
  requested: number;
}

export function extractApiError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (!detail) return "An unexpected error occurred.";
  if (typeof detail === "string") return detail;
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    return (detail as InsufficientStockError).message;
  }
  return JSON.stringify(detail);
}

export function isInsufficientStock(err: unknown): InsufficientStockError | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "object" && detail !== null && (detail as InsufficientStockError).error === "INSUFFICIENT_STOCK") {
    return detail as InsufficientStockError;
  }
  return null;
}

export const inventoryApi = {
  async stockSummary(params?: { warehouse_id?: string; product_id?: string }): Promise<StockSummary[]> {
    const res = await apiClient.get<StockSummary[]>("/api/v1/inventory/stock/summary", { params });
    return res.data;
  },

  async movementDetail(params?: { warehouse_id?: string; product_id?: string }): Promise<MovementDetail[]> {
    const res = await apiClient.get<MovementDetail[]>("/api/v1/inventory/movements/detail", { params });
    return res.data;
  },

  async stockEntry(data: StockEntryRequest) {
    const res = await apiClient.post("/api/v1/inventory/stock/entry", data);
    return res.data;
  },

  async stockIssue(data: StockIssueRequest) {
    const res = await apiClient.post("/api/v1/inventory/stock/issue", data);
    return res.data;
  },

  async stockTransfer(data: StockTransferRequest) {
    const res = await apiClient.post("/api/v1/inventory/stock/transfer", data);
    return res.data;
  },

  async listLots() {
    const res = await apiClient.get("/api/v1/inventory/lots");
    return res.data;
  },
};