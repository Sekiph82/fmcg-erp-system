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

export interface StockAdjustRequest {
  new_quantity: number;
  reason: string;
  reference?: string;
}

export interface StockMovementUpdate {
  reference_number?: string;
  notes?: string;
}

export interface ProductInUseError {
  code: "PRODUCT_IN_USE";
  message: string;
  details: {
    productId: string;
    productName: string;
    references: Array<{ module: string; count: number; hint: string }>;
  };
}

export interface InventoryDeleteBlockedError {
  code: "INVENTORY_RECORD_NOT_EMPTY" | "INVENTORY_RECORD_LOCKED";
  message: string;
  details: {
    stockId?: string;
    quantityOnHand?: number;
    references: Array<{ module: string; count: number; hint: string }>;
  };
}

export interface MovementDeleteBlockedError {
  code: "MOVEMENT_LOCKED" | "MOVEMENT_REVERSAL_WOULD_CAUSE_NEGATIVE_STOCK";
  message: string;
  details: {
    movementId?: string;
    hint?: string;
  };
}

export function extractStructuredError(err: unknown): ProductInUseError | InventoryDeleteBlockedError | MovementDeleteBlockedError | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "object" && detail !== null && "code" in detail) {
    return detail as ProductInUseError | InventoryDeleteBlockedError | MovementDeleteBlockedError;
  }
  return null;
}

// ── Serial Number Tracking ────────────────────────────────────────────────────

export type SerialStatus = "IN_STOCK" | "SOLD" | "SCRAPPED" | "IN_REPAIR" | "RETURNED";

export interface SerialNumber {
  id: string;
  serial_no: string;
  product_id: string;
  product_name?: string;
  lot_id?: string;
  lot_number?: string;
  warehouse_id?: string;
  warehouse_name?: string;
  status: SerialStatus;
  warranty_expiry?: string;
  notes?: string;
  created_at: string;
}

export interface SerialMovement {
  id: string;
  serial_id: string;
  from_status?: SerialStatus;
  to_status: SerialStatus;
  from_warehouse_id?: string;
  from_warehouse_name?: string;
  to_warehouse_id?: string;
  to_warehouse_name?: string;
  reference_type?: string;
  reference_no?: string;
  created_at: string;
  moved_by_username?: string;
}

export interface SerialTransferRequest {
  to_status: SerialStatus;
  to_warehouse_id?: string;
  reference_type?: string;
  reference_no?: string;
}

export const serialApi = {
  async list(params?: {
    product_id?: string; warehouse_id?: string; status?: SerialStatus; search?: string;
  }): Promise<SerialNumber[]> {
    const res = await apiClient.get<SerialNumber[]>("/api/v1/inventory/serials/", { params });
    return res.data;
  },
  async create(data: {
    serial_no: string; product_id: string; lot_id?: string; warehouse_id?: string;
    warranty_expiry?: string; notes?: string;
  }): Promise<SerialNumber> {
    const res = await apiClient.post<SerialNumber>("/api/v1/inventory/serials/", data);
    return res.data;
  },
  async bulkCreate(serials: {
    serial_no: string; product_id: string; lot_id?: string; warehouse_id?: string;
    warranty_expiry?: string; notes?: string;
  }[]): Promise<SerialNumber[]> {
    const res = await apiClient.post<SerialNumber[]>("/api/v1/inventory/serials/bulk", { serials });
    return res.data;
  },
  async lookup(serialNo: string): Promise<SerialNumber> {
    const res = await apiClient.get<SerialNumber>(`/api/v1/inventory/serials/lookup/${encodeURIComponent(serialNo)}`);
    return res.data;
  },
  async get(id: string): Promise<SerialNumber> {
    const res = await apiClient.get<SerialNumber>(`/api/v1/inventory/serials/${id}`);
    return res.data;
  },
  async history(id: string): Promise<SerialMovement[]> {
    const res = await apiClient.get<SerialMovement[]>(`/api/v1/inventory/serials/${id}/history`);
    return res.data;
  },
  async transfer(id: string, data: SerialTransferRequest): Promise<SerialNumber> {
    const res = await apiClient.post<SerialNumber>(`/api/v1/inventory/serials/${id}/transfer`, data);
    return res.data;
  },
};

// ── Inventory Valuation Types ─────────────────────────────────────────────────

export interface ValuationRow {
  stock_type:       string;
  item_id:          string;
  item_sku?:        string | null;
  item_name?:       string | null;
  warehouse_id?:    string | null;
  warehouse_name?:  string | null;
  lot_id?:          string | null;
  lot_number?:      string | null;
  qty_on_hand:      number;
  fifo_unit_cost?:  number | null;
  fifo_total_value?: number | null;
  wac_unit_cost?:   number | null;
  wac_total_value?: number | null;
  std_unit_cost?:   number | null;
  std_total_value?: number | null;
}

export interface ValuationSummary {
  method:      string;
  total_value: number;
  item_count:  number;
  rows:        ValuationRow[];
}

export interface AgingRow {
  stock_type:    string;
  item_id:       string;
  item_sku?:     string | null;
  item_name?:    string | null;
  lot_id?:       string | null;
  lot_number?:   string | null;
  receipt_date:  string;
  days_held:     number;
  qty_remaining: number;
  unit_cost:     number;
  total_value:   number;
  aging_bucket:  string;
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

  async adjustStock(stockId: string, data: StockAdjustRequest) {
    const res = await apiClient.post(`/api/v1/inventory/stock/${stockId}/adjust`, data);
    return res.data;
  },

  async deleteStock(stockId: string): Promise<void> {
    await apiClient.delete(`/api/v1/inventory/stock/${stockId}`).then((r) => r.data);
  },

  async updateMovement(movementId: string, data: StockMovementUpdate) {
    const res = await apiClient.patch(`/api/v1/inventory/movements/${movementId}`, data);
    return res.data;
  },

  async deleteMovement(movementId: string): Promise<void> {
    await apiClient.delete(`/api/v1/inventory/movements/${movementId}`).then((r) => r.data);
  },

  async listLots() {
    const res = await apiClient.get("/api/v1/inventory/lots");
    return res.data;
  },

  async deleteLot(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/inventory/lots/${id}`).then((r) => r.data);
  },

  async valuation(warehouse_id?: string): Promise<ValuationSummary> {
    const res = await apiClient.get<ValuationSummary>("/api/v1/inventory/valuation", {
      params: warehouse_id ? { warehouse_id } : undefined,
    });
    return res.data;
  },

  async aging(warehouse_id?: string): Promise<AgingRow[]> {
    const res = await apiClient.get<AgingRow[]>("/api/v1/inventory/aging", {
      params: warehouse_id ? { warehouse_id } : undefined,
    });
    return res.data;
  },
};