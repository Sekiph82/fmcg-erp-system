import { apiClient } from "./api";

// ── Authenticated file download helper ────────────────────────────────────────

async function _downloadBlob(path: string, filename: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const res = await fetch(`${base}${path}`, {
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Download failed (${res.status}): ${text}`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ImportRowError {
  row:     number;
  field:   string | null;
  message: string;
}

export interface ImportResult {
  total_rows:  number;
  valid_rows:  number;
  failed_rows: number;
  imported:    boolean;
  import_mode: string;
  module:      string;
  errors:      ImportRowError[];
  // Convenience fields used by some pages
  success?: boolean;
  message?: string;
  inserted?: number;
}

export interface ImportHistoryEntry {
  id:            string;
  module:        string;
  file_name:     string | null;
  import_mode:   string;
  total_rows:    number;
  success_count: number;
  failure_count: number;
  status:        "completed" | "partial" | "failed" | "validated";
  username:      string | null;
  user_roles:    string | null;
  created_at:    string | null;
}

export interface ModuleFieldMeta {
  name:        string;
  required:    boolean;
  type:        string;
  enum_values: string[] | null;
  default:     string | null;
}

export interface ImportModuleInfo {
  module:      string;
  perm_module: string;
  unique_key:  string[];
  fields:      ModuleFieldMeta[];
}

export type ImportMode = "import_valid_only" | "strict";

// ── API client ────────────────────────────────────────────────────────────────

export const importApi = {
  /** Download the CSV template for a module (triggers browser download). */
  downloadTemplate(module: string): Promise<void> {
    return _downloadBlob(
      `/api/v1/bulk-import/${module}/template`,
      `${module}_template.csv`,
    );
  },

  /** Validate a CSV file without writing to the DB. */
  async validate(module: string, file: File): Promise<ImportResult> {
    const form = new FormData();
    form.append("file", file);
    const r = await apiClient.post<ImportResult>(
      `/api/v1/bulk-import/${module}/validate`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return r.data;
  },

  /** Run the actual import. */
  async runImport(
    module: string,
    file: File,
    mode: ImportMode = "import_valid_only",
  ): Promise<ImportResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    const r = await apiClient.post<ImportResult>(
      `/api/v1/bulk-import/${module}/import`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return r.data;
  },

  /** Upload and import a file (alias for runImport). */
  upload: async (module: string, file: File): Promise<ImportResult> => {
    const form = new FormData();
    form.append("file", file);
    const r = await apiClient.post<ImportResult>(
      `/api/v1/bulk-import/${module}/import`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return r.data;
  },

  /** Fetch import history with optional filters. */
  async getHistory(params?: {
    module?:    string;
    username?:  string;
    date_from?: string;
    date_to?:   string;
    skip?:      number;
    limit?:     number;
  }): Promise<ImportHistoryEntry[]> {
    const r = await apiClient.get<ImportHistoryEntry[]>(
      "/api/v1/bulk-import/history",
      { params },
    );
    return r.data;
  },

  /** Download error CSV for a specific history entry. */
  downloadErrors(historyId: string): Promise<void> {
    return _downloadBlob(
      `/api/v1/bulk-import/history/${historyId}/errors`,
      `errors_${historyId}.csv`,
    );
  },

  /** Get module manifest (fields, permissions, unique keys). */
  async getModules(): Promise<ImportModuleInfo[]> {
    const r = await apiClient.get<ImportModuleInfo[]>("/api/v1/bulk-import/modules");
    return r.data;
  },
};

// ── Module display config (for UI labels / icons) ─────────────────────────────

export const MODULE_LABELS: Record<string, string> = {
  products:                   "Products",
  materials:                  "Raw Materials",
  suppliers:                  "Suppliers",
  warehouses:                 "Warehouses",
  employees:                  "Employees",
  inventory_stock:            "Inventory Stock",
  recipes:                    "Recipe Headers",
  recipe_items:               "Recipe BOM Items",
  recipe_steps:               "Recipe Process Steps",
  qc_parameters:              "QC Parameters",
  // Utility Management — Master data
  utility_asset_categories:   "Utility Asset Categories",
  utility_assets:             "Utility Assets",
  utility_devices:            "Utility Meters & Sensors",
  utility_tariffs:            "Utility Tariffs",
  utility_alarm_rules:        "Utility Alarm Rules",
  // Utility Management — Transactional
  utility_transactions:       "Utility Transactions (Generic)",
  utility_readings:           "Utility Meter Readings",
  electricity_transactions:   "Electricity Transactions",
  electricity_consumption:    "Electricity Consumption Records",
  water_transactions:         "Water Transactions",
  water_consumption:          "Water Consumption Records",
  utility_bills:              "Utility Bills",
  utility_allocations:        "Utility Cost Allocations",
  // Utility Management — Operational records
  soft_water_records:         "Soft Water Operational Records",
  boiler_records:             "Boiler Steam Operational Records",
  steam_transactions:         "Steam Consumption Records",
  compressor_records:         "Compressor Operational Records",
  air_transactions:           "Compressed Air Consumption Records",
  solar_records:              "Solar PV Operational Records",
  treatment_chemical_records: "Treatment Chemical Records",
  wastewater_records:         "Wastewater Treatment Records",
};

export const STATUS_COLORS: Record<string, string> = {
  completed: "text-emerald-400",
  partial:   "text-amber-400",
  failed:    "text-red-400",
  validated: "text-blue-400",
};

export const STATUS_BG: Record<string, string> = {
  completed: "bg-emerald-500/10 border-emerald-500/20",
  partial:   "bg-amber-500/10 border-amber-500/20",
  failed:    "bg-red-500/10 border-red-500/20",
  validated: "bg-blue-500/10 border-blue-500/20",
};
