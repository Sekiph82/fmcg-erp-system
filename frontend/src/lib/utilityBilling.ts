/**
 * Utility Billing, Tariffs & Cost Allocation — TypeScript types and API client.
 */
import { apiClient } from "./api";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type UtilityTypeBilling =
  | "ELECTRICITY" | "WATER" | "SOFT_WATER" | "PROCESS_WATER"
  | "STEAM" | "COMPRESSED_AIR" | "NATURAL_GAS" | "SOLAR"
  | "WASTEWATER" | "DIESEL" | "CHILLED_WATER" | "OTHER";

export const UTILITY_TYPE_LABELS: Record<UtilityTypeBilling, string> = {
  ELECTRICITY:    "Electricity",
  WATER:          "Water",
  SOFT_WATER:     "Soft Water",
  PROCESS_WATER:  "Process Water",
  STEAM:          "Steam",
  COMPRESSED_AIR: "Compressed Air",
  NATURAL_GAS:    "Natural Gas",
  SOLAR:          "Solar",
  WASTEWATER:     "Wastewater",
  DIESEL:         "Diesel",
  CHILLED_WATER:  "Chilled Water",
  OTHER:          "Other",
};

export const UTILITY_TYPE_COLORS: Record<UtilityTypeBilling, string> = {
  ELECTRICITY:    "#fbbf24",
  WATER:          "#60a5fa",
  SOFT_WATER:     "#93c5fd",
  PROCESS_WATER:  "#3b82f6",
  STEAM:          "#f97316",
  COMPRESSED_AIR: "#22d3ee",
  NATURAL_GAS:    "#a78bfa",
  SOLAR:          "#facc15",
  WASTEWATER:     "#6b7280",
  DIESEL:         "#94a3b8",
  CHILLED_WATER:  "#67e8f9",
  OTHER:          "#9ca3af",
};

export type BillStatus = "DRAFT" | "RECEIVED" | "VERIFIED" | "PAID" | "DISPUTED" | "OVERDUE" | "VOID";

export const BILL_STATUS_LABELS: Record<BillStatus, string> = {
  DRAFT:    "Draft",
  RECEIVED: "Received",
  VERIFIED: "Verified",
  PAID:     "Paid",
  DISPUTED: "Disputed",
  OVERDUE:  "Overdue",
  VOID:     "Void",
};

export const BILL_STATUS_COLORS: Record<BillStatus, string> = {
  DRAFT:    "#6b7280",
  RECEIVED: "#3b82f6",
  VERIFIED: "#8b5cf6",
  PAID:     "#22c55e",
  DISPUTED: "#f97316",
  OVERDUE:  "#ef4444",
  VOID:     "#9ca3af",
};

export type TariffType = "FLAT" | "TIME_OF_USE" | "DEMAND" | "STEPPED";

export const TARIFF_TYPE_LABELS: Record<TariffType, string> = {
  FLAT:        "Flat Rate",
  TIME_OF_USE: "Time-of-Use",
  DEMAND:      "Demand",
  STEPPED:     "Stepped / Block",
};

export type AllocationMethod =
  | "METERED" | "PROPORTIONAL" | "FIXED" | "CALCULATED"
  | "RUNTIME" | "STANDARD_CONSUMPTION" | "COST_CENTER";

export const ALLOCATION_METHOD_LABELS: Record<AllocationMethod, string> = {
  METERED:              "Direct Metered",
  PROPORTIONAL:         "Proportional",
  FIXED:                "Fixed",
  CALCULATED:           "Calculated",
  RUNTIME:              "Est. by Runtime",
  STANDARD_CONSUMPTION: "Est. by Std. Consumption",
  COST_CENTER:          "Cost-Center Based",
};

export type TargetType =
  | "DEPARTMENT" | "PRODUCTION_LINE" | "MACHINE" | "PRODUCT"
  | "PRODUCTION_ORDER" | "BATCH" | "SUPPORT_AREA" | "OVERHEAD_POOL";

export const TARGET_TYPE_LABELS: Record<TargetType, string> = {
  DEPARTMENT:       "Department",
  PRODUCTION_LINE:  "Production Line",
  MACHINE:          "Machine",
  PRODUCT:          "Product",
  PRODUCTION_ORDER: "Production Order",
  BATCH:            "Batch",
  SUPPORT_AREA:     "Support Area",
  OVERHEAD_POOL:    "Overhead Pool",
};

// ── Tariff types ──────────────────────────────────────────────────────────────

export interface UtilityTariff {
  id:            string;
  tariff_code:   string;
  name:          string;
  description?:  string | null;
  utility_type:  UtilityTypeBilling;
  tariff_type:   TariffType;
  supplier_id?:  string | null;
  effective_from: string;
  effective_to?:  string | null;
  unit:          string;
  currency_code: string;
  base_rate:     number;
  peak_rate?:    number | null;
  offpeak_rate?: number | null;
  demand_rate?:  number | null;
  fixed_charge?: number | null;
  tax_rate_pct?: number | null;
  tax_rule?:     string | null;
  is_active:     boolean;
  notes?:        string | null;
  created_at?:   string | null;
  updated_at?:   string | null;
}

export type TariffCreate = Omit<UtilityTariff, "id" | "created_at" | "updated_at">;
export type TariffUpdate = Partial<Omit<UtilityTariff, "id" | "tariff_code" | "utility_type" | "created_at" | "updated_at">>;

// ── Bill types ────────────────────────────────────────────────────────────────

export interface UtilityBill {
  id:                  string;
  bill_no:             string;
  utility_type:        UtilityTypeBilling;
  provider_name?:      string | null;
  supplier_id?:        string | null;
  tariff_id?:          string | null;
  tariff_code?:        string | null;
  bill_reference?:     string | null;
  billing_period_from: string;
  billing_period_to:   string;
  invoice_date?:       string | null;
  due_date?:           string | null;
  consumption_quantity?: number | null;
  consumption_unit?:   string | null;
  unit_rate?:          number | null;
  base_charge?:        number | null;
  energy_charge?:      number | null;
  demand_charge?:      number | null;
  fixed_charge?:       number | null;
  surcharge_amount?:   number | null;
  tax_amount?:         number | null;
  total_amount:        number;
  currency_code:       string;
  status:              BillStatus;
  payment_date?:       string | null;
  document_ref?:       string | null;
  notes?:              string | null;
  created_at?:         string | null;
  updated_at?:         string | null;
}

export type BillCreate = Omit<UtilityBill, "id" | "bill_no" | "created_at" | "updated_at">;
export type BillUpdate = Partial<Omit<UtilityBill, "id" | "bill_no" | "utility_type" | "created_at" | "updated_at">>;

// ── Allocation types ──────────────────────────────────────────────────────────

export interface UtilityAllocation {
  id:                    string;
  allocation_no:         string;
  utility_type:          UtilityTypeBilling;
  allocation_date:       string;
  period_start?:         string | null;
  period_end?:           string | null;
  allocation_method:     AllocationMethod;
  target_type?:          TargetType | null;
  target_id?:            string | null;
  target_name?:          string | null;
  department?:           string | null;
  production_line?:      string | null;
  building_area?:        string | null;
  machine_ref?:          string | null;
  production_order_id?:  string | null;
  batch_no?:             string | null;
  product_id?:           string | null;
  source_cost?:          number | null;
  allocation_basis?:     number | null;
  allocation_basis_unit?: string | null;
  allocated_quantity?:   number | null;
  quantity_unit?:        string | null;
  production_volume_kg?: number | null;
  total_cost:            number;
  allocated_cost:        number;
  currency_code:         string;
  cost_per_unit?:        number | null;
  cost_per_ton?:         number | null;
  bill_id?:              string | null;
  source_method:         string;
  is_approved:           boolean;
  notes?:                string | null;
  created_at?:           string | null;
  updated_at?:           string | null;
}

export type AllocationCreate = Omit<UtilityAllocation, "id" | "allocation_no" | "is_approved" | "created_at" | "updated_at">;
export type AllocationUpdate = Partial<Omit<UtilityAllocation, "id" | "allocation_no" | "utility_type" | "allocation_date" | "created_at" | "updated_at">>;

// ── KPI & report types ────────────────────────────────────────────────────────

export interface BillingKPIs {
  date_from?:           string | null;
  date_to?:             string | null;
  utility_type?:        string | null;
  total_bills:          number;
  total_billed_amount:  number;
  total_tax_amount?:    number | null;
  total_consumption?:   number | null;
  consumption_unit?:    string | null;
  avg_unit_rate?:       number | null;
  unpaid_amount?:       number | null;
  overdue_count:        number;
  disputed_count:       number;
  currency_code:        string;
}

export interface AllocationReportRow {
  target_type?:      string | null;
  target_id?:        string | null;
  target_name?:      string | null;
  utility_type?:     string | null;
  allocated_cost:    number;
  allocated_quantity?: number | null;
  quantity_unit?:    string | null;
  cost_per_unit?:    number | null;
  record_count:      number;
}

export interface AllocationReport {
  period_start?:  string | null;
  period_end?:    string | null;
  utility_type?:  string | null;
  group_by:       string;
  rows:           AllocationReportRow[];
  grand_total:    number;
}

// ── Engine types ──────────────────────────────────────────────────────────────

export interface AllocationEngineTarget {
  target_type:   TargetType;
  target_id:     string;
  target_name?:  string | null;
  basis_value:   number;
  basis_unit?:   string | null;
}

export interface AllocationEngineRequest {
  bill_id:           string;
  allocation_method: AllocationMethod;
  allocation_date:   string;
  currency_code?:    string;
  targets:           AllocationEngineTarget[];
}

export interface AllocationEngineResult {
  bill_id:             string;
  bill_no:             string;
  total_cost:          number;
  allocation_method:   string;
  allocations_created: number;
  rows:                UtilityAllocation[];
}

// ── Filter types ──────────────────────────────────────────────────────────────

export interface BillFilters {
  utility_type?:  UtilityTypeBilling;
  status?:        BillStatus;
  date_from?:     string;
  date_to?:       string;
  supplier_id?:   string;
  skip?:          number;
  limit?:         number;
}

export interface TariffFilters {
  utility_type?:  UtilityTypeBilling;
  is_active?:     boolean;
  as_of_date?:    string;
  skip?:          number;
  limit?:         number;
}

export interface AllocationFilters {
  utility_type?:    UtilityTypeBilling;
  target_type?:     TargetType;
  target_id?:       string;
  department?:      string;
  production_line?: string;
  machine_ref?:     string;
  batch_no?:        string;
  bill_id?:         string;
  date_from?:       string;
  date_to?:         string;
  is_approved?:     boolean;
  skip?:            number;
  limit?:           number;
}

// ── CSV download ──────────────────────────────────────────────────────────────

export async function downloadBillsCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename = "utility_bills.csv",
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const qs    = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])
  ).toString();
  const res = await fetch(`${base}/api/v1/billing/bills/export/csv${qs ? "?" + qs : ""}`,
    { credentials: "include" });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
}

export async function downloadAllocationsCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename = "cost_allocations.csv",
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const qs    = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)])
  ).toString();
  const res = await fetch(`${base}/api/v1/billing/allocations/export/csv${qs ? "?" + qs : ""}`,
    { credentials: "include" });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ── API client ────────────────────────────────────────────────────────────────

export const billingApi = {
  // Tariffs
  async listTariffs(params?: TariffFilters): Promise<UtilityTariff[]> {
    const r = await apiClient.get<UtilityTariff[]>("/api/v1/billing/tariffs", { params });
    return r.data;
  },
  async createTariff(data: TariffCreate): Promise<UtilityTariff> {
    const r = await apiClient.post<UtilityTariff>("/api/v1/billing/tariffs", data);
    return r.data;
  },
  async updateTariff(id: string, data: TariffUpdate): Promise<UtilityTariff> {
    const r = await apiClient.patch<UtilityTariff>(`/api/v1/billing/tariffs/${id}`, data);
    return r.data;
  },
  async deleteTariff(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/billing/tariffs/${id}`).then((r) => r.data);
  },
  async lookupTariff(utilityType: string, asOf?: string): Promise<UtilityTariff | null> {
    const r = await apiClient.get<UtilityTariff | null>("/api/v1/billing/tariffs/lookup",
      { params: { utility_type: utilityType, as_of: asOf } });
    return r.data;
  },

  // Bills
  async kpis(params?: Partial<BillFilters & { currency_code?: string }>): Promise<BillingKPIs> {
    const r = await apiClient.get<BillingKPIs>("/api/v1/billing/bills/kpis", { params });
    return r.data;
  },
  async listBills(params?: BillFilters): Promise<UtilityBill[]> {
    const r = await apiClient.get<UtilityBill[]>("/api/v1/billing/bills", { params });
    return r.data;
  },
  async createBill(data: BillCreate): Promise<UtilityBill> {
    const r = await apiClient.post<UtilityBill>("/api/v1/billing/bills", data);
    return r.data;
  },
  async updateBill(id: string, data: BillUpdate): Promise<UtilityBill> {
    const r = await apiClient.patch<UtilityBill>(`/api/v1/billing/bills/${id}`, data);
    return r.data;
  },
  async deleteBill(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/billing/bills/${id}`).then((r) => r.data);
  },

  // Allocations
  async listAllocations(params?: AllocationFilters): Promise<UtilityAllocation[]> {
    const r = await apiClient.get<UtilityAllocation[]>("/api/v1/billing/allocations", { params });
    return r.data;
  },
  async createAllocation(data: AllocationCreate): Promise<UtilityAllocation> {
    const r = await apiClient.post<UtilityAllocation>("/api/v1/billing/allocations", data);
    return r.data;
  },
  async updateAllocation(id: string, data: AllocationUpdate): Promise<UtilityAllocation> {
    const r = await apiClient.patch<UtilityAllocation>(`/api/v1/billing/allocations/${id}`, data);
    return r.data;
  },
  async deleteAllocation(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/billing/allocations/${id}`).then((r) => r.data);
  },
  async runEngine(req: AllocationEngineRequest): Promise<AllocationEngineResult> {
    const r = await apiClient.post<AllocationEngineResult>("/api/v1/billing/allocations/run-engine", req);
    return r.data;
  },
  async report(params?: {
    group_by?: string; utility_type?: string; date_from?: string; date_to?: string;
  }): Promise<AllocationReport> {
    const r = await apiClient.get<AllocationReport>("/api/v1/billing/allocations/report", { params });
    return r.data;
  },
};
