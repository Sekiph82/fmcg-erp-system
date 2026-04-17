import { apiClient } from "./api";

// ── Enums ──────────────────────────────────────────────────────────────────────

export type UtilityType =
  | "ELECTRICITY"
  | "WATER"
  | "SOFT_WATER"
  | "PROCESS_WATER"
  | "STEAM"
  | "COMPRESSED_AIR"
  | "SOLAR"
  | "NATURAL_GAS"
  | "WASTEWATER"
  | "DIESEL"
  | "CHILLED_WATER"
  | "OTHER";

export type UtilityAssetStatus =
  | "ACTIVE"
  | "IDLE"
  | "UNDER_MAINTENANCE"
  | "DECOMMISSIONED";

export type LifecycleStatus =
  | "IN_USE"
  | "STORED"
  | "RETIRED"
  | "DISPOSED";

export type CriticalityLevel =
  | "CRITICAL"
  | "HIGH"
  | "MEDIUM"
  | "LOW";

// ── Label maps ────────────────────────────────────────────────────────────────

export const UTILITY_TYPE_LABELS: Record<UtilityType, string> = {
  ELECTRICITY:    "Electricity",
  WATER:          "Water",
  SOFT_WATER:     "Soft Water",
  PROCESS_WATER:  "Process Water",
  STEAM:          "Steam",
  COMPRESSED_AIR: "Compressed Air",
  SOLAR:          "Solar",
  NATURAL_GAS:    "Natural Gas",
  WASTEWATER:     "Wastewater",
  DIESEL:         "Diesel",
  CHILLED_WATER:  "Chilled Water",
  OTHER:          "Other",
};

export const UTILITY_TYPE_OPTIONS = Object.entries(UTILITY_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const ASSET_STATUS_LABELS: Record<UtilityAssetStatus, string> = {
  ACTIVE:            "Active",
  IDLE:              "Idle",
  UNDER_MAINTENANCE: "Under Maintenance",
  DECOMMISSIONED:    "Decommissioned",
};

export const ASSET_STATUS_OPTIONS = Object.entries(ASSET_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const LIFECYCLE_STATUS_LABELS: Record<LifecycleStatus, string> = {
  IN_USE:  "In Use",
  STORED:  "Stored",
  RETIRED: "Retired",
  DISPOSED: "Disposed",
};

export const LIFECYCLE_STATUS_OPTIONS = Object.entries(LIFECYCLE_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const CRITICALITY_LABELS: Record<CriticalityLevel, string> = {
  CRITICAL: "Critical",
  HIGH:     "High",
  MEDIUM:   "Medium",
  LOW:      "Low",
};

export const CRITICALITY_OPTIONS = Object.entries(CRITICALITY_LABELS).map(
  ([value, label]) => ({ value, label })
);

// ── Utility Asset Category ─────────────────────────────────────────────────────

export interface UtilityAssetCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  utility_type: UtilityType;
  default_unit: string | null;
  is_active: boolean;
  asset_count: number;
}

export interface UtilityAssetCategoryCreate {
  code: string;
  name: string;
  description?: string | null;
  utility_type: UtilityType;
  default_unit?: string | null;
  is_active?: boolean;
}

export interface UtilityAssetCategoryUpdate {
  name?: string;
  description?: string | null;
  utility_type?: UtilityType;
  default_unit?: string | null;
  is_active?: boolean;
}

// ── Utility Asset ──────────────────────────────────────────────────────────────

export interface UtilityAsset {
  id: string;
  asset_no: string;
  name: string;
  description: string | null;
  category_id: string;
  category_code: string | null;
  category_name: string | null;
  utility_type: UtilityType;
  subsystem: string | null;
  location: string | null;
  building_area: string | null;
  department: string | null;
  line_id: string | null;
  machine_id: string | null;
  parent_asset_id: string | null;
  parent_asset_no: string | null;
  manufacturer: string | null;
  equipment_model: string | null;
  serial_no: string | null;
  install_date: string | null;
  warranty_expiry: string | null;
  rated_capacity: string | null;
  capacity_unit: string | null;
  rated_power: string | null;
  rated_power_unit: string | null;
  flow_capacity: string | null;
  pressure_capacity: string | null;
  temperature_range: string | null;
  status: UtilityAssetStatus;
  lifecycle_status: LifecycleStatus | null;
  criticality_level: CriticalityLevel | null;
  maintenance_strategy: string | null;
  is_active: boolean;
  notes: string | null;
}

export interface UtilityAssetCreate {
  asset_no: string;
  name: string;
  description?: string | null;
  category_id: string;
  utility_type: UtilityType;
  subsystem?: string | null;
  location?: string | null;
  building_area?: string | null;
  department?: string | null;
  line_id?: string | null;
  machine_id?: string | null;
  parent_asset_id?: string | null;
  manufacturer?: string | null;
  equipment_model?: string | null;
  serial_no?: string | null;
  install_date?: string | null;
  warranty_expiry?: string | null;
  rated_capacity?: string | null;
  capacity_unit?: string | null;
  rated_power?: string | null;
  rated_power_unit?: string | null;
  flow_capacity?: string | null;
  pressure_capacity?: string | null;
  temperature_range?: string | null;
  status?: UtilityAssetStatus;
  lifecycle_status?: LifecycleStatus | null;
  criticality_level?: CriticalityLevel | null;
  maintenance_strategy?: string | null;
  is_active?: boolean;
  notes?: string | null;
}

export type UtilityAssetUpdate = Partial<UtilityAssetCreate>;

// ── Asset filter params ───────────────────────────────────────────────────────

export interface AssetFilters {
  utility_type?: UtilityType;
  category_id?: string;
  department?: string;
  building_area?: string;
  line_id?: string;
  machine_id?: string;
  status?: UtilityAssetStatus;
  lifecycle_status?: LifecycleStatus;
  criticality_level?: CriticalityLevel;
  is_active?: boolean;
  search?: string;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/utility-management";

export const utilityManagementApi = {
  // ── Categories ───────────────────────────────────────────────────────────────
  categories: {
    async list(params?: {
      utility_type?: UtilityType;
      is_active?: boolean;
      search?: string;
      skip?: number;
      limit?: number;
    }): Promise<UtilityAssetCategory[]> {
      const res = await apiClient.get<UtilityAssetCategory[]>(
        `${BASE}/asset-categories`,
        { params },
      );
      return res.data;
    },

    async get(id: string): Promise<UtilityAssetCategory> {
      const res = await apiClient.get<UtilityAssetCategory>(
        `${BASE}/asset-categories/${id}`,
      );
      return res.data;
    },

    async create(data: UtilityAssetCategoryCreate): Promise<UtilityAssetCategory> {
      const res = await apiClient.post<UtilityAssetCategory>(
        `${BASE}/asset-categories`,
        data,
      );
      return res.data;
    },

    async update(
      id: string,
      data: UtilityAssetCategoryUpdate,
    ): Promise<UtilityAssetCategory> {
      const res = await apiClient.patch<UtilityAssetCategory>(
        `${BASE}/asset-categories/${id}`,
        data,
      );
      return res.data;
    },

    async delete(id: string): Promise<void> {
      await apiClient.delete(`${BASE}/asset-categories/${id}`);
    },

    exportCsvUrl(): string {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "";
      return `${base}${BASE}/asset-categories/export/csv`;
    },
  },

  // ── Assets ───────────────────────────────────────────────────────────────────
  assets: {
    async list(params?: AssetFilters & { skip?: number; limit?: number }): Promise<UtilityAsset[]> {
      const res = await apiClient.get<UtilityAsset[]>(`${BASE}/assets`, { params });
      return res.data;
    },

    async get(id: string): Promise<UtilityAsset> {
      const res = await apiClient.get<UtilityAsset>(`${BASE}/assets/${id}`);
      return res.data;
    },

    async create(data: UtilityAssetCreate): Promise<UtilityAsset> {
      const res = await apiClient.post<UtilityAsset>(`${BASE}/assets`, data);
      return res.data;
    },

    async update(id: string, data: UtilityAssetUpdate): Promise<UtilityAsset> {
      const res = await apiClient.patch<UtilityAsset>(`${BASE}/assets/${id}`, data);
      return res.data;
    },

    async delete(id: string): Promise<void> {
      await apiClient.delete(`${BASE}/assets/${id}`);
    },

    exportCsvUrl(): string {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "";
      return `${base}${BASE}/assets/export/csv`;
    },
  },
};

// ── Download helper (authenticated) ──────────────────────────────────────────

export async function downloadAuthenticatedCsv(path: string, filename: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${base}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
