import { apiClient } from "@/lib/api";

export type ZoneType =
  | "RAW_MATERIAL"
  | "SEMI_FINISHED"
  | "FINISHED_GOODS"
  | "QUARANTINE"
  | "RETURNS"
  | "STAGING";

export type StockCountType = "CYCLE" | "FULL";
export type StockCountStatus =
  | "DRAFT"
  | "IN_PROGRESS"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "CANCELLED";

export interface WarehouseZone {
  id: string;
  warehouse_id: string;
  warehouse_name?: string;
  code: string;
  name: string;
  zone_type: ZoneType;
  description?: string;
  is_active: boolean;
  location_count: number;
}

export interface StorageLocation {
  id: string;
  zone_id: string;
  zone_code?: string;
  zone_name?: string;
  zone_type?: ZoneType;
  warehouse_id?: string;
  warehouse_name?: string;
  code: string;
  name: string;
  barcode?: string;
  max_weight_kg?: number;
  max_volume_m3?: number;
  location_type?: string;
  is_active: boolean;
  is_blocked: boolean;
}

export interface StockCount {
  id: string;
  count_no: string;
  warehouse_id: string;
  warehouse_name?: string;
  zone_id?: string;
  zone_name?: string;
  count_type: StockCountType;
  status: StockCountStatus;
  scheduled_date: string;
  completed_date?: string;
  created_by?: string;
  approved_by?: string;
  notes?: string;
  total_lines: number;
  counted_lines: number;
}

export interface StockCountLine {
  id: string;
  count_id: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  material_id?: string;
  material_name?: string;
  material_code?: string;
  lot_id?: string;
  lot_number?: string;
  location_id?: string;
  location_code?: string;
  system_quantity: number;
  counted_quantity?: number;
  variance?: number;
  unit: string;
  is_counted: boolean;
  notes?: string;
}

export interface StockCountDetail extends StockCount {
  lines: StockCountLine[];
}

export interface FEFOSuggestion {
  lot_id: string;
  lot_number: string;
  expiry_date?: string;
  manufacture_date?: string;
  available_quantity: number;
  location_code?: string;
  days_to_expiry?: number;
}

export interface NearExpiryRow {
  lot_number: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  material_name?: string;
  expiry_date: string;
  days_to_expiry: number;
  warehouse_name: string;
  quantity_available: number;
  is_expired: boolean;
}

export interface LowStockRow {
  product_id?: string;
  product_sku?: string;
  product_name?: string;
  warehouse_name: string;
  quantity_available: number;
  reorder_point: number;
  shortage: number;
}

export interface StockAgingRow {
  product_sku?: string;
  product_name?: string;
  lot_number?: string;
  warehouse_name: string;
  quantity_on_hand: number;
  first_received_date?: string;
  age_days?: number;
  age_bucket: string;
  is_blocked: boolean;
}

export interface LotTraceEvent {
  event_type: string;
  event_date: string;
  reference: string;
  description: string;
  quantity: number;
  warehouse_name?: string;
  order_no?: string;
}

export interface LotTraceResult {
  lot_number: string;
  product_name?: string;
  product_sku?: string;
  material_name?: string;
  expiry_date?: string;
  manufacture_date?: string;
  events: LotTraceEvent[];
}

export interface MovementLedgerRow {
  id: string;
  reference_number: string;
  movement_type: string;
  stock_type: string;
  movement_date: string;
  product_sku?: string;
  product_name?: string;
  lot_number?: string;
  source_warehouse?: string;
  destination_warehouse?: string;
  quantity: number;
  unit_cost?: number;
  total_cost?: number;
  notes?: string;
  created_by?: string;
  created_at?: string;
}

export const wmsApi = {
  // Zones
  async listZones(params?: { warehouse_id?: string }): Promise<WarehouseZone[]> {
    const res = await apiClient.get<WarehouseZone[]>("/api/v1/wms/zones/", { params });
    return res.data;
  },
  async createZone(data: Omit<WarehouseZone, "id" | "location_count" | "warehouse_name">): Promise<WarehouseZone> {
    const res = await apiClient.post<WarehouseZone>("/api/v1/wms/zones/", data);
    return res.data;
  },

  // Locations
  async listLocations(params?: { zone_id?: string; warehouse_id?: string }): Promise<StorageLocation[]> {
    const res = await apiClient.get<StorageLocation[]>("/api/v1/wms/locations/", { params });
    return res.data;
  },
  async createLocation(data: Omit<StorageLocation, "id" | "zone_code" | "zone_name" | "zone_type" | "warehouse_id" | "warehouse_name">): Promise<StorageLocation> {
    const res = await apiClient.post<StorageLocation>("/api/v1/wms/locations/", data);
    return res.data;
  },
  async updateLocation(id: string, data: Partial<StorageLocation>): Promise<StorageLocation> {
    const res = await apiClient.patch<StorageLocation>(`/api/v1/wms/locations/${id}`, data);
    return res.data;
  },

  // Scan
  async scanLocation(barcode: string) {
    const res = await apiClient.get(`/api/v1/wms/scan/location/${barcode}`);
    return res.data;
  },
  async scanLot(lotNumber: string) {
    const res = await apiClient.get(`/api/v1/wms/scan/lot/${lotNumber}`);
    return res.data;
  },
  async scanProduct(barcode: string) {
    const res = await apiClient.get(`/api/v1/wms/scan/product/${barcode}`);
    return res.data;
  },

  // FEFO
  async getFEFO(productId: string, warehouseId: string, quantity: number): Promise<FEFOSuggestion[]> {
    const res = await apiClient.get<FEFOSuggestion[]>("/api/v1/wms/fefo", {
      params: { product_id: productId, warehouse_id: warehouseId, quantity },
    });
    return res.data;
  },

  // Operations
  async putaway(data: { product_id?: string; material_id?: string; warehouse_id: string; location_id: string; lot_number?: string; quantity: number; reference: string }) {
    const res = await apiClient.post("/api/v1/wms/putaway", data);
    return res.data;
  },
  async quarantine(data: { warehouse_id: string; product_id?: string; material_id?: string; lot_number?: string; reason: string; notes?: string }) {
    const res = await apiClient.post("/api/v1/wms/quarantine", data);
    return res.data;
  },
  async releaseQuarantine(data: { warehouse_id: string; product_id?: string; material_id?: string; lot_number?: string; notes?: string }) {
    const res = await apiClient.post("/api/v1/wms/release", data);
    return res.data;
  },

  // Stock Counts
  async listCounts(params?: { warehouse_id?: string; status?: StockCountStatus }): Promise<StockCount[]> {
    const res = await apiClient.get<StockCount[]>("/api/v1/wms/counts/", { params });
    return res.data;
  },
  async getCount(id: string): Promise<StockCountDetail> {
    const res = await apiClient.get<StockCountDetail>(`/api/v1/wms/counts/${id}`);
    return res.data;
  },
  async createCount(data: { count_no: string; warehouse_id: string; zone_id?: string; count_type: StockCountType; scheduled_date: string; notes?: string }): Promise<StockCount> {
    const res = await apiClient.post<StockCount>("/api/v1/wms/counts/", data);
    return res.data;
  },
  async startCount(id: string): Promise<StockCount> {
    const res = await apiClient.post<StockCount>(`/api/v1/wms/counts/${id}/start`);
    return res.data;
  },
  async recordLine(countId: string, lineId: string, data: { counted_quantity: number; notes?: string }): Promise<StockCountLine> {
    const res = await apiClient.post<StockCountLine>(`/api/v1/wms/counts/${countId}/lines/${lineId}/record`, data);
    return res.data;
  },
  async submitCount(id: string): Promise<StockCount> {
    const res = await apiClient.post<StockCount>(`/api/v1/wms/counts/${id}/submit`);
    return res.data;
  },
  async approveCount(id: string): Promise<StockCount> {
    const res = await apiClient.post<StockCount>(`/api/v1/wms/counts/${id}/approve`);
    return res.data;
  },
  async cancelCount(id: string): Promise<StockCount> {
    const res = await apiClient.post<StockCount>(`/api/v1/wms/counts/${id}/cancel`);
    return res.data;
  },

  // Reports
  async nearExpiryReport(daysAhead = 30, warehouseId?: string): Promise<NearExpiryRow[]> {
    const res = await apiClient.get<NearExpiryRow[]>("/api/v1/wms/reports/near-expiry", {
      params: { days_ahead: daysAhead, warehouse_id: warehouseId },
    });
    return res.data;
  },
  async lowStockReport(warehouseId?: string): Promise<LowStockRow[]> {
    const res = await apiClient.get<LowStockRow[]>("/api/v1/wms/reports/low-stock", {
      params: { warehouse_id: warehouseId },
    });
    return res.data;
  },
  async agingReport(warehouseId?: string): Promise<StockAgingRow[]> {
    const res = await apiClient.get<StockAgingRow[]>("/api/v1/wms/reports/aging", {
      params: { warehouse_id: warehouseId },
    });
    return res.data;
  },
  async lotTrace(lotNumber: string): Promise<LotTraceResult> {
    const res = await apiClient.get<LotTraceResult>(`/api/v1/wms/reports/lot-trace/${lotNumber}`);
    return res.data;
  },
  async movementLedger(params?: { warehouse_id?: string; date_from?: string; date_to?: string; movement_type?: string; limit?: number }): Promise<MovementLedgerRow[]> {
    const res = await apiClient.get<MovementLedgerRow[]>("/api/v1/wms/reports/movement-ledger", { params });
    return res.data;
  },
};
